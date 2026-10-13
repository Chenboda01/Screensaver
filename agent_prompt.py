#!/usr/bin/env python3
"""Ask before the screensaver covers a terminal running an AI agent."""
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Final


AGENT_NAMES: Final[frozenset[str]] = frozenset(
    {"codex", "claude", "claude-code", "opencode", "gemini", "aider", "goose", "amp", "cline", "cursor-agent"}
)
INTERPRETER_NAMES: Final[frozenset[str]] = frozenset({"bun", "deno", "node", "python", "python3", "uv"})
MIN_AGENT_CPU_TICKS: Final[int] = max(1, int(os.sysconf("SC_CLK_TCK") * 0.25))
SESSION_ACTIVITY_WINDOW_SECONDS: Final[int] = 5 * 60


@dataclass(frozen=True, slots=True)
class Process:
    pid: int
    parent_pid: int
    terminal: str
    state: str
    elapsed_seconds: int
    name: str
    command: str


def _is_agent_process(pid: int, process_name: str) -> bool:
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
        return False

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


def _read_processes() -> list[Process]:
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
        return []
    if result.returncode != 0:
        return []

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


def _codex_turn_is_active() -> bool:
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
        return False

    for path in recent_logs:
        try:
            latest_turn: str | None = None
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
                    if payload.get("type") == "task_started":
                        latest_turn = turn_id
                    elif payload.get("type") in {
                        "task_complete",
                        "task_failed",
                        "turn_aborted",
                        "turn_failed",
                    } and turn_id == latest_turn:
                        latest_turn = None
        except OSError:
            continue
        if latest_turn is not None:
            return True
    return False


def _opencode_turn_is_active() -> bool:
    """Check for a recently updated, incomplete OpenCode assistant message."""
    database = Path.home() / ".local" / "share" / "opencode" / "opencode.db"
    if not database.is_file():
        return False
    try:
        with sqlite3.connect(f"file:{database}?mode=ro", uri=True, timeout=0.25) as connection:
            message = connection.execute(
                "SELECT time_updated, json_type(data, '$.time.completed') "
                "FROM message WHERE json_extract(data, '$.role') = 'assistant' "
                "ORDER BY time_updated DESC LIMIT 1"
            ).fetchone()
            if message is None:
                return False
            updated_ms, completed_type = message
            return (
                time.time() - updated_ms / 1000 <= SESSION_ACTIVITY_WINDOW_SECONDS
                and completed_type is None
            )
    except (OSError, sqlite3.Error):
        return False
    return False


def terminal_agent_is_active() -> bool:
    """Return whether a recognized terminal agent is currently doing work."""
    processes = _read_processes()
    agents = [
        process
        for process in processes
        if process.pid != os.getpid()
        and process.terminal not in ("?", "??")
        and _is_agent_process(process.pid, process.name)
    ]
    if not agents:
        return False
    if any(agent.name.lower() == "codex" for agent in agents) and _codex_turn_is_active():
        return True
    if any(agent.name.lower() == "opencode" for agent in agents) and _opencode_turn_is_active():
        return True

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
            if not _is_idle_agent_service(process):
                work_processes.append(process)

    # Include sustained CPU activity from the terminal UI itself: an agent can
    # be working on a response between child commands. The threshold filters
    # the lower CPU use measured from idle terminal redraws and polling.
    process_ids = {process.pid for process in work_processes}
    process_ids.update(agent.pid for agent in agents)
    before = {pid: _cpu_ticks(pid) for pid in process_ids}
    time.sleep(1)
    for agent in agents:
        initial_ticks = before[agent.pid]
        current_ticks = _cpu_ticks(agent.pid)
        if (
            initial_ticks is not None
            and current_ticks is not None
            and current_ticks - initial_ticks >= MIN_AGENT_CPU_TICKS
        ):
            return True
    for process in work_processes:
        if process.state.startswith("R") or process.elapsed_seconds <= 2:
            return True
        initial_ticks = before[process.pid]
        current_ticks = _cpu_ticks(process.pid)
        if initial_ticks is not None and current_ticks is not None and current_ticks > initial_ticks:
            return True
    return False


def user_wants_agent_in_background() -> bool:
    """Ask whether to keep the terminal agent running behind the saver."""
    notify_send = shutil.which("notify-send")
    if notify_send is None:
        print("ScreenBot: notify-send is unavailable; leaving the desktop visible.", file=sys.stderr)
        return False

    try:
        result = subprocess.run(
            [
                notify_send,
                "--wait",
                "--expire-time=0",
                "--action=keep=Yes",
                "--action=cancel=No",
                "--app-name=ScreenBot Screensaver",
                "ScreenBot Screensaver",
                "An AI agent is active in a terminal. Keep it working in the background while the screensaver starts?",
            ],
            capture_output=True,
            check=False,
            text=True,
        )
    except OSError as error:
        print(f"ScreenBot: could not show the agent prompt: {error}", file=sys.stderr)
        return False

    return result.returncode == 0 and result.stdout.strip() == "keep"


def main() -> int:
    if not terminal_agent_is_active():
        return 0
    return 0 if user_wants_agent_in_background() else 1


if __name__ == "__main__":
    raise SystemExit(main())
