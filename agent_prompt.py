#!/usr/bin/env python3
"""Ask before the screensaver covers a terminal running an AI agent."""
import configparser
import os
import sys
import time
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Final

from PyQt6.QtCore import QEvent, QObject, Qt, QTimer
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import QApplication, QCheckBox, QMessageBox, QWidget

from screenbot.agent_detection import (
    AGENT_NAMES, INTERPRETER_NAMES, MIN_AGENT_CPU_TICKS,
    SESSION_ACTIVITY_WINDOW_SECONDS, DetectionHooks, DetectionResult, Process,
    _codex_turn_is_active, _cpu_ticks, _is_agent_process,
    _is_idle_agent_service, _opencode_turn_is_active, _read_processes,
    detect_terminal_agents,
)

CONFIG_FILE: Final[Path] = Path.home() / ".config" / "screenbot-screensaver.ini"

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

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(event)

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


def terminal_agent_status() -> DetectionResult:
    """Return a safe detection result using this facade's patchable helpers."""
    return detect_terminal_agents(DetectionHooks(
        read_processes=_read_processes,
        is_agent_process=_is_agent_process,
        cpu_ticks=_cpu_ticks,
        codex_turn_is_active=_codex_turn_is_active,
        opencode_turn_is_active=_opencode_turn_is_active,
        is_idle_agent_service=_is_idle_agent_service,
        process_id=os.getpid(),
        sleep=time.sleep,
    ))

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

__all__ = [
    "AGENT_NAMES", "INTERPRETER_NAMES", "MIN_AGENT_CPU_TICKS", "SESSION_ACTIVITY_WINDOW_SECONDS",
    "AgentMode", "AgentPromptDialog", "DetectionHooks", "DetectionResult", "Process",
    "PromptResult", "PromptSettings", "TimeoutAction", "CONFIG_FILE", "_cpu_ticks",
    "_codex_turn_is_active", "_is_agent_process", "_is_idle_agent_service", "_opencode_turn_is_active",
    "_read_mode", "_read_processes", "_read_prompt_settings", "_save_mode", "main",
    "terminal_agent_status", "user_wants_agent_in_background",
]

if __name__ == "__main__":
    raise SystemExit(main())
