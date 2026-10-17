"""Inspect terminal process activity without coupling detection to the prompt UI."""
import json
import os
import sqlite3
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Final

AGENT_NAMES: Final[frozenset[str]] = frozenset(
    {"codex", "claude", "claude-code", "opencode", "gemini", "aider", "goose", "amp", "cline", "cursor-agent"}
)
INTERPRETER_NAMES: Final[frozenset[str]] = frozenset({"bun", "deno", "node", "python", "python3", "uv"})
MIN_AGENT_CPU_TICKS: Final[int] = max(1, int(os.sysconf("SC_CLK_TCK") * 0.25))
SESSION_ACTIVITY_WINDOW_SECONDS: Final[int] = 5 * 60

class DetectionResult(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    UNKNOWN = "unknown"

@dataclass(frozen=True, slots=True)
class Process:
    pid: int
    parent_pid: int
    terminal: str
    state: str
    elapsed_seconds: int
    name: str
    command: str

@dataclass(frozen=True, slots=True)
class DetectionHooks:
    """Inject detection operations so the public facade remains patchable."""
    read_processes: Callable[[], list[Process] | None]
    is_agent_process: Callable[[int, str], bool | None]
    cpu_ticks: Callable[[int], int | None]
    codex_turn_is_active: Callable[[], bool | None]
    opencode_turn_is_active: Callable[[], bool | None]
    is_idle_agent_service: Callable[[Process], bool]
    process_id: int
    sleep: Callable[[float], None]

def _is_agent_process(pid: int, process_name: str) -> bool | None:
    """Match the executable or launcher entry point, not arbitrary arguments."""
    normalized_name = process_name.lower()
    if normalized_name in AGENT_NAMES:
        return True
    normalized_name = normalized_name.split("-", maxsplit=1)[0]
    if normalized_name not in INTERPRETER_NAMES:
        return False

    try:
        arguments = Path(f"/proc/{pid}/cmdline").read_bytes().decode(errors="replace").split("\0")
    except OSError:
        return None

    for argument in arguments[1:]:
        name = Path(argument).name.lower()
        if name.removesuffix(".js").removesuffix(".mjs").removesuffix(".cjs") in AGENT_NAMES:
            return True
        if "/claude-code/" in argument.lower() or "/gemini-cli/" in argument.lower():
            return True
    for index, argument in enumerate(arguments[:-1]):
        if argument == "-m" and arguments[index + 1].lower() in AGENT_NAMES:
            return True
    return False

def _cpu_ticks(pid: int) -> int | None:
    """Return a process's accumulated user and system CPU ticks."""
    try:
        stat = Path(f"/proc/{pid}/stat").read_text()
        fields = stat[stat.rfind(")") + 2 :].split()
        return int(fields[11]) + int(fields[12])
    except (OSError, ValueError, IndexError):
        return None

def _read_processes() -> list[Process] | None:
    """Read process relationships and terminal assignments from procps."""
    try:
        result = subprocess.run(
            ["ps", "-eo", "pid=,ppid=,tty=,stat=,etimes=,comm=,args="],
            capture_output=True,
            check=False,
            text=True,
            timeout=3,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None

    processes: list[Process] = []
    for line in result.stdout.splitlines():
        fields = line.split(maxsplit=6)
        if len(fields) != 7:
            continue
        pid_text, parent_text, terminal, state, elapsed_text, name, command = fields
        try:
            processes.append(
                Process(
                    pid=int(pid_text),
                    parent_pid=int(parent_text),
                    terminal=terminal,
                    state=state,
                    elapsed_seconds=int(elapsed_text),
                    name=name,
                    command=command,
                )
            )
        except ValueError:
            continue
    return processes

def _is_idle_agent_service(process: Process) -> bool:
    """Skip long-lived language and application services attached to an agent."""
    command = process.command.lower()
    return any(
        service in command
        for service in ("lsp-daemon", "codex app-server", "codex-code-mode-host")
    )

def _codex_turn_is_active() -> bool | None:
    """Read Codex turn status events without loading session message contents."""
    session_root = Path.home() / ".codex" / "sessions"
    now = time.time()
    try:
        recent_logs = [
            path
            for path in session_root.rglob("*.jsonl")
            if now - path.stat().st_mtime <= SESSION_ACTIVITY_WINDOW_SECONDS
        ]
    except OSError:
        return None

    for path in recent_logs:
        try:
            active_turns: dict[str, float | None] = {}
            with path.open("rb") as log_file:
                for line in log_file:
                    # Ignore message and tool payloads; only decode turn-status events.
                    if b'"type":"event_msg"' not in line:
                        continue
                    try:
                        record = json.loads(line)
                    except ValueError:
                        continue
                    payload = record.get("payload") or {}
                    turn_id = payload.get("turn_id")
                    if not turn_id:
                        continue
                    timestamp = record.get("timestamp")
                    try:
                        event_time = datetime.fromisoformat(
                            timestamp.replace("Z", "+00:00")
                        ).timestamp()
                    except (AttributeError, OverflowError, OSError, ValueError):
                        event_time = None
                    if payload.get("type") == "task_started":
                        active_turns[turn_id] = event_time
                    elif payload.get("type") in {
                        "task_complete",
                        "task_failed",
                        "turn_aborted",
                        "turn_failed",
                    }:
                        active_turns.pop(turn_id, None)
                    elif turn_id in active_turns and event_time is not None:
                        active_turns[turn_id] = event_time
        except OSError:
            return None
        if any(
            event_time is not None
            and 0 <= now - event_time <= SESSION_ACTIVITY_WINDOW_SECONDS
            for event_time in active_turns.values()
        ):
            return True
        if any(event_time is None for event_time in active_turns.values()):
            return None
    return False

def _opencode_turn_is_active() -> bool | None:
    """Check for a recently updated, incomplete OpenCode assistant message."""
    database = Path.home() / ".local" / "share" / "opencode" / "opencode.db"
    if not database.is_file():
        return None
    try:
        with sqlite3.connect(f"file:{database}?mode=ro", uri=True, timeout=0.25) as connection:
            message = connection.execute(
                "SELECT time_updated, json_type(data, '$.time.completed') "
                "FROM message WHERE json_extract(data, '$.role') = 'assistant' "
                "ORDER BY time_updated DESC LIMIT 1"
            ).fetchone()
            if message is None:
                return None
            updated_ms, completed_type = message
            return (
                time.time() - updated_ms / 1000 <= SESSION_ACTIVITY_WINDOW_SECONDS
                and completed_type is None
            )
    except (OSError, sqlite3.Error):
        return None
    return False

def detect_terminal_agents(hooks: DetectionHooks) -> DetectionResult:
    """Report active, inactive, or uncertain agent status without guessing."""
    processes = hooks.read_processes()
    if processes is None:
        return DetectionResult.UNKNOWN
    agents: list[Process] = []
    uncertain_agent_candidate = False
    for process in processes:
        if process.pid == hooks.process_id or process.terminal in ("?", "??"):
            continue
        agent_match = hooks.is_agent_process(process.pid, process.name)
        if agent_match is True:
            agents.append(process)
        elif agent_match is None:
            uncertain_agent_candidate = True
    if not agents:
        return DetectionResult.UNKNOWN if uncertain_agent_candidate else DetectionResult.INACTIVE
    for agent in agents:
        if agent.name.lower() == "codex":
            turn_active = hooks.codex_turn_is_active()
            if turn_active is True:
                return DetectionResult.ACTIVE
            if turn_active is None:
                uncertain_agent_candidate = True
        elif agent.name.lower() == "opencode":
            turn_active = hooks.opencode_turn_is_active()
            if turn_active is True:
                return DetectionResult.ACTIVE
            if turn_active is None:
                uncertain_agent_candidate = True

    children: dict[int, list[Process]] = {}
    for process in processes:
        children.setdefault(process.parent_pid, []).append(process)

    work_processes: list[Process] = []
    visited: set[int] = set()
    for agent in agents:
        pending = list(children.get(agent.pid, []))
        while pending:
            process = pending.pop()
            if process.pid in visited:
                continue
            visited.add(process.pid)
            pending.extend(children.get(process.pid, []))
            if not hooks.is_idle_agent_service(process):
                work_processes.append(process)

    # Include sustained CPU activity from the terminal UI itself: an agent can
    # be working on a response between child commands. The threshold filters
    # the lower CPU use measured from idle terminal redraws and polling.
    process_ids = {process.pid for process in work_processes}
    process_ids.update(agent.pid for agent in agents)
    before = {pid: hooks.cpu_ticks(pid) for pid in process_ids}
    hooks.sleep(1)
    for agent in agents:
        initial_ticks = before[agent.pid]
        current_ticks = hooks.cpu_ticks(agent.pid)
        if initial_ticks is None or current_ticks is None:
            uncertain_agent_candidate = True
        elif current_ticks - initial_ticks >= MIN_AGENT_CPU_TICKS:
            return DetectionResult.ACTIVE
    for process in work_processes:
        if process.state.startswith("R") or process.elapsed_seconds <= 2:
            return DetectionResult.ACTIVE
        initial_ticks = before[process.pid]
        current_ticks = hooks.cpu_ticks(process.pid)
        if initial_ticks is None or current_ticks is None:
            uncertain_agent_candidate = True
        elif current_ticks > initial_ticks:
            return DetectionResult.ACTIVE
    return DetectionResult.UNKNOWN if uncertain_agent_candidate else DetectionResult.INACTIVE
