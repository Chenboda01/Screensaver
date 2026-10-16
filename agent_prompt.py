#!/usr/bin/env python3
"""Ask before the screensaver covers a terminal running an AI agent."""
import configparser
import json
import os
import sqlite3
import subprocess
import sys
import time
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Final

from PyQt6.QtCore import QEvent, QObject, Qt, QTimer
from PyQt6.QtWidgets import QApplication, QCheckBox, QMessageBox, QWidget


AGENT_NAMES: Final[frozenset[str]] = frozenset(
    {"codex", "claude", "claude-code", "opencode", "gemini", "aider", "goose", "amp", "cline", "cursor-agent"}
)
INTERPRETER_NAMES: Final[frozenset[str]] = frozenset({"bun", "deno", "node", "python", "python3", "uv"})
MIN_AGENT_CPU_TICKS: Final[int] = max(1, int(os.sysconf("SC_CLK_TCK") * 0.25))
SESSION_ACTIVITY_WINDOW_SECONDS: Final[int] = 5 * 60
CONFIG_FILE: Final[Path] = Path.home() / ".config" / "screenbot-screensaver.ini"


class DetectionResult(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    UNKNOWN = "unknown"


class AgentMode(StrEnum):
    ALWAYS_ASK = "ask"
    ALWAYS_START = "start"
    NEVER_START_WHILE_ACTIVE = "block"


class TimeoutAction(StrEnum):
    START = "start"
    CANCEL = "cancel"


@dataclass(frozen=True, slots=True)
class PromptSettings:
    timeout_seconds: int = 10
    action: TimeoutAction = TimeoutAction.START


@dataclass(frozen=True, slots=True)
class PromptResult:
    start: bool
    remember: bool
    automatic: bool = False


@dataclass(frozen=True, slots=True)
class Process:
    pid: int
    parent_pid: int
    terminal: str
    state: str
    elapsed_seconds: int
    name: str
    command: str


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
            return None
        if latest_turn is not None:
            return True
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


def terminal_agent_status() -> DetectionResult:
    """Report active, inactive, or uncertain agent status without guessing."""
    processes = _read_processes()
    if processes is None:
        return DetectionResult.UNKNOWN
    agents: list[Process] = []
    uncertain_agent_candidate = False
    for process in processes:
        if process.pid == os.getpid() or process.terminal in ("?", "??"):
            continue
        agent_match = _is_agent_process(process.pid, process.name)
        if agent_match is True:
            agents.append(process)
        elif agent_match is None:
            uncertain_agent_candidate = True
    if not agents:
        return DetectionResult.UNKNOWN if uncertain_agent_candidate else DetectionResult.INACTIVE
    for agent in agents:
        if agent.name.lower() == "codex":
            turn_active = _codex_turn_is_active()
            if turn_active is True:
                return DetectionResult.ACTIVE
            if turn_active is None:
                uncertain_agent_candidate = True
        elif agent.name.lower() == "opencode":
            turn_active = _opencode_turn_is_active()
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
        if initial_ticks is None or current_ticks is None:
            uncertain_agent_candidate = True
        elif current_ticks - initial_ticks >= MIN_AGENT_CPU_TICKS:
            return DetectionResult.ACTIVE
    for process in work_processes:
        if process.state.startswith("R") or process.elapsed_seconds <= 2:
            return DetectionResult.ACTIVE
        initial_ticks = before[process.pid]
        current_ticks = _cpu_ticks(process.pid)
        if initial_ticks is None or current_ticks is None:
            uncertain_agent_candidate = True
        elif current_ticks > initial_ticks:
            return DetectionResult.ACTIVE
    return DetectionResult.UNKNOWN if uncertain_agent_candidate else DetectionResult.INACTIVE


def _read_mode() -> AgentMode:
    """Read the committed KDE setting; malformed values safely ask each time."""
    config = configparser.ConfigParser()
    try:
        with CONFIG_FILE.open(encoding="utf-8") as config_file:
            config.read_file(config_file)
    except FileNotFoundError:
        return AgentMode.ALWAYS_ASK
    except (OSError, configparser.Error):
        return AgentMode.ALWAYS_ASK
    try:
        return AgentMode(config.get("Screensaver", "agent_detection_mode", fallback="ask"))
    except (configparser.Error, ValueError):
        return AgentMode.ALWAYS_ASK


def _save_mode(mode: AgentMode) -> bool:
    """Persist a remembered answer without replacing settings on write failure."""
    config = configparser.ConfigParser()
    try:
        if CONFIG_FILE.exists():
            with CONFIG_FILE.open(encoding="utf-8") as config_file:
                config.read_file(config_file)
        if not config.has_section("Screensaver"):
            config.add_section("Screensaver")
        config.set("Screensaver", "agent_detection_mode", mode.value)
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        temporary = CONFIG_FILE.with_suffix(".ini.tmp")
        with temporary.open("w", encoding="utf-8") as config_file:
            config.write(config_file)
            config_file.flush()
            os.fsync(config_file.fileno())
        os.replace(temporary, CONFIG_FILE)
    except (OSError, configparser.Error):
        print("ScreenBot: could not save the remembered agent choice.", file=sys.stderr)
        return False
    return True


def _read_prompt_settings() -> PromptSettings:
    """Parse committed timeout settings; zero means wait for a human answer."""
    config = configparser.ConfigParser()
    try:
        with CONFIG_FILE.open(encoding="utf-8") as config_file:
            config.read_file(config_file)
    except (OSError, configparser.Error):
        return PromptSettings()
    try:
        seconds = config.getint("Screensaver", "agent_prompt_timeout_seconds", fallback=10)
    except (configparser.Error, ValueError):
        seconds = 10
    try:
        action = TimeoutAction(config.get("Screensaver", "agent_prompt_timeout_action", fallback="start"))
    except (configparser.Error, ValueError):
        action = TimeoutAction.START
    return PromptSettings(0 if seconds == 0 else max(5, min(120, seconds)), action)


class AgentPromptDialog(QMessageBox):
    """Own the mutable countdown and pause it while the user makes a choice."""

    def __init__(self, settings: PromptSettings) -> None:
        super().__init__()
        self.remaining_seconds = settings.timeout_seconds
        self.automatic = False
        self.explicit_answer = False
        self.automatic_button = (
            QMessageBox.StandardButton.Yes if settings.action is TimeoutAction.START
            else QMessageBox.StandardButton.No
        )
        self.setWindowTitle("ScreenBot Screensaver")
        self.setText("An AI agent is active in a terminal. Keep it working in the background while the screensaver starts?")
        self.setIcon(QMessageBox.Icon.Question)
        self.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        self.setDefaultButton(self.automatic_button)
        self.remember_checkbox = QCheckBox("Remember my choice")
        self.setCheckBox(self.remember_checkbox)
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.timer.timeout.connect(self._tick)
        self.buttonClicked.connect(self._mark_manual_answer)
        self.remember_checkbox.toggled.connect(self.pause_countdown)
        self.finished.connect(self.timer.stop)
        for widget in [self, *self.findChildren(QWidget)]:
            widget.setMouseTracking(True)
            widget.installEventFilter(self)
        if self.remaining_seconds:
            self._update_countdown()
            self.timer.start()
        else:
            self.setInformativeText("Waiting for your choice. There is no automatic answer.")

    def _update_countdown(self) -> None:
        start = self.automatic_button == QMessageBox.StandardButton.Yes
        action = "Starting the screensaver automatically" if start else "Keeping the desktop visible; closing"
        self.setInformativeText(f"{action} in {self.remaining_seconds} s…")
        self.button(self.automatic_button).setText(f"{'Yes' if start else 'No'} ({self.remaining_seconds})")

    def _tick(self) -> None:
        if not self.timer.isActive():
            return
        self.remaining_seconds -= 1
        if self.remaining_seconds <= 0:
            self.automatic = True
            self.done(int(self.automatic_button))
        else:
            self._update_countdown()

    def _mark_manual_answer(self) -> None:
        self.explicit_answer = True

    def pause_countdown(self) -> None:
        if not self.timer.isActive():
            return
        self.timer.stop()
        self.setInformativeText("Countdown paused. Choose Yes or No when you are ready.")
        self.button(self.automatic_button).setText(
            "Yes" if self.automatic_button == QMessageBox.StandardButton.Yes else "No"
        )

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() in {
            QEvent.Type.MouseMove, QEvent.Type.HoverMove, QEvent.Type.KeyPress,
            QEvent.Type.MouseButtonPress, QEvent.Type.Wheel,
        }:
            self.pause_countdown()
        return super().eventFilter(watched, event)

    def prompt_result(self) -> PromptResult:
        selected = self.result() in (int(QMessageBox.StandardButton.Yes), int(QMessageBox.StandardButton.No))
        return PromptResult(
            start=self.result() == int(QMessageBox.StandardButton.Yes),
            remember=selected and self.explicit_answer and self.remember_checkbox.isChecked() and not self.automatic,
            automatic=self.automatic,
        )


def user_wants_agent_in_background() -> PromptResult:
    """Ask with the committed countdown policy and a separate remember choice."""
    app = QApplication.instance() or QApplication(sys.argv[:1])
    dialog = AgentPromptDialog(_read_prompt_settings())
    dialog.exec()
    return dialog.prompt_result()


def main() -> int:
    if "--manual" in sys.argv[1:]:
        return 0
    status = terminal_agent_status()
    if status is DetectionResult.INACTIVE:
        return 0
    if status is DetectionResult.UNKNOWN:
        print("ScreenBot: agent status is uncertain; keeping the desktop visible.", file=sys.stderr)
        return 1
    mode = _read_mode()
    if mode is AgentMode.ALWAYS_START:
        return 0
    if mode is AgentMode.NEVER_START_WHILE_ACTIVE:
        return 1
    try:
        answer = user_wants_agent_in_background()
    except RuntimeError as error:
        print(f"ScreenBot: could not show the agent prompt: {error}", file=sys.stderr)
        return 1
    if answer.remember and not answer.automatic:
        _save_mode(AgentMode.ALWAYS_START if answer.start else AgentMode.NEVER_START_WHILE_ACTIVE)
    return 0 if answer.start else 1


if __name__ == "__main__":
    raise SystemExit(main())
