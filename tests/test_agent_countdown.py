from pathlib import Path

import pytest
from PyQt6.QtCore import QEvent, QPointF, Qt
from PyQt6.QtGui import QHoverEvent, QMouseEvent
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QMessageBox

import agent_prompt


@pytest.fixture(scope="module")
def app() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.mark.parametrize("action, starts", [(agent_prompt.TimeoutAction.START, True), (agent_prompt.TimeoutAction.CANCEL, False)])
def test_timeout_chooses_configured_answer(app: QApplication, action: agent_prompt.TimeoutAction, starts: bool) -> None:
    dialog = agent_prompt.AgentPromptDialog(agent_prompt.PromptSettings(5, action))
    initial_text = dialog.button(dialog.automatic_button).text()

    dialog.timer.timeout.emit()

    assert dialog.remaining_seconds == 4
    assert dialog.button(dialog.automatic_button).text() != initial_text
    assert dialog.defaultButton() == dialog.button(dialog.automatic_button)
    for _ in range(4):
        dialog.timer.timeout.emit()
    assert dialog.prompt_result() == agent_prompt.PromptResult(starts, False, True)
    assert not dialog.timer.isActive()


def test_never_waits_for_a_real_click(app: QApplication) -> None:
    dialog = agent_prompt.AgentPromptDialog(agent_prompt.PromptSettings(0))

    for _ in range(130):
        dialog.timer.timeout.emit()

    assert not dialog.timer.isActive()
    assert not dialog.automatic
    assert dialog.result() == 0
    dialog.button(QMessageBox.StandardButton.Yes).click()
    assert dialog.prompt_result() == agent_prompt.PromptResult(True, False)


@pytest.mark.parametrize("interaction", ["mouse", "hover", "tab", "checkbox"])
def test_interaction_pauses_countdown(app: QApplication, interaction: str) -> None:
    dialog = agent_prompt.AgentPromptDialog(agent_prompt.PromptSettings())
    dialog.show()

    if interaction == "checkbox":
        dialog.remember_checkbox.setChecked(True)
    elif interaction == "tab":
        QTest.keyClick(dialog.button(QMessageBox.StandardButton.No), Qt.Key.Key_Tab)
    elif interaction == "mouse":
        QApplication.sendEvent(dialog.remember_checkbox, QMouseEvent(
            QEvent.Type.MouseMove, QPointF(3, 3), QPointF(3, 3),
            Qt.MouseButton.NoButton, Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
        ))
    else:
        QApplication.sendEvent(dialog.remember_checkbox, QHoverEvent(
            QEvent.Type.HoverMove, QPointF(3, 3), QPointF(3, 3), QPointF(1, 1),
        ))

    assert not dialog.timer.isActive()
    before = dialog.remaining_seconds
    dialog.timer.timeout.emit()
    assert dialog.remaining_seconds == before
    assert not dialog.automatic
    assert dialog.isVisible()
    dialog.close()


def test_automatic_answer_never_remembers_even_if_checkbox_is_checked(app: QApplication) -> None:
    dialog = agent_prompt.AgentPromptDialog(agent_prompt.PromptSettings(5))
    dialog.remember_checkbox.blockSignals(True)
    dialog.remember_checkbox.setChecked(True)

    for _ in range(5):
        dialog.timer.timeout.emit()

    assert dialog.prompt_result() == agent_prompt.PromptResult(True, False, True)


@pytest.mark.parametrize("yes", [True, False])
def test_real_click_keeps_remembered_choice(app: QApplication, yes: bool) -> None:
    dialog = agent_prompt.AgentPromptDialog(agent_prompt.PromptSettings())
    dialog.remember_checkbox.setChecked(True)

    dialog.button(QMessageBox.StandardButton.Yes if yes else QMessageBox.StandardButton.No).click()

    assert dialog.prompt_result() == agent_prompt.PromptResult(yes, True)


def test_dismissed_dialog_does_not_save_checked_preference(app: QApplication) -> None:
    dialog = agent_prompt.AgentPromptDialog(agent_prompt.PromptSettings())
    dialog.remember_checkbox.setChecked(True)

    dialog.reject()

    assert dialog.prompt_result() == agent_prompt.PromptResult(False, False)
    assert not dialog.timer.isActive()


def test_escape_dismisses_without_remembering(app: QApplication) -> None:
    dialog = agent_prompt.AgentPromptDialog(agent_prompt.PromptSettings())
    dialog.remember_checkbox.setChecked(True)

    QTest.keyClick(dialog, Qt.Key.Key_Escape)

    assert dialog.prompt_result() == agent_prompt.PromptResult(False, False)


def test_enter_selects_the_default_answer(app: QApplication) -> None:
    dialog = agent_prompt.AgentPromptDialog(agent_prompt.PromptSettings())
    dialog.show()
    dialog.remember_checkbox.setChecked(True)

    QTest.keyClick(dialog, Qt.Key.Key_Return)

    assert dialog.prompt_result() == agent_prompt.PromptResult(True, True)


@pytest.mark.parametrize("content, seconds, action", [
    ("", 10, agent_prompt.TimeoutAction.START),
    ("agent_prompt_timeout_seconds=invalid\nagent_prompt_timeout_action=invalid", 10, agent_prompt.TimeoutAction.START),
    ("agent_prompt_timeout_seconds=-1", 5, agent_prompt.TimeoutAction.START),
    ("agent_prompt_timeout_seconds=999", 120, agent_prompt.TimeoutAction.START),
    ("agent_prompt_timeout_seconds=0\nagent_prompt_timeout_action=cancel", 0, agent_prompt.TimeoutAction.CANCEL),
    ("agent_prompt_timeout_seconds=55\nagent_prompt_timeout_action=cancel", 55, agent_prompt.TimeoutAction.CANCEL),
])
def test_committed_settings_parse_and_clamp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, content: str, seconds: int, action: agent_prompt.TimeoutAction) -> None:
    config = tmp_path / "settings.ini"
    config.write_text("[Screensaver]\n" + content)
    monkeypatch.setattr(agent_prompt, "CONFIG_FILE", config)

    result = agent_prompt._read_prompt_settings()

    assert result == agent_prompt.PromptSettings(seconds, action)


@pytest.mark.parametrize("contents", [None, "broken ini"])
def test_missing_or_broken_config_uses_defaults(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, contents: str | None) -> None:
    config = tmp_path / "settings.ini"
    if contents is not None:
        config.write_text(contents)
    monkeypatch.setattr(agent_prompt, "CONFIG_FILE", config)

    result = agent_prompt._read_prompt_settings()

    assert result == agent_prompt.PromptSettings()


def test_main_does_not_save_automatic_answer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = tmp_path / "settings.ini"
    config.write_text("[Screensaver]\nagent_detection_mode=ask\n")
    before = config.read_bytes()
    monkeypatch.setattr(agent_prompt, "CONFIG_FILE", config)
    monkeypatch.setattr(agent_prompt.sys, "argv", ["agent_prompt.py"])
    monkeypatch.setattr(agent_prompt, "terminal_agent_status", lambda: agent_prompt.DetectionResult.ACTIVE)
    monkeypatch.setattr(agent_prompt, "user_wants_agent_in_background", lambda: agent_prompt.PromptResult(True, True, True))

    result = agent_prompt.main()

    assert result == 0
    assert config.read_bytes() == before


def test_dialog_failure_cancels_launch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(agent_prompt.sys, "argv", ["agent_prompt.py"])
    monkeypatch.setattr(agent_prompt, "terminal_agent_status", lambda: agent_prompt.DetectionResult.ACTIVE)
    monkeypatch.setattr(agent_prompt, "_read_mode", lambda: agent_prompt.AgentMode.ALWAYS_ASK)

    def failed_prompt() -> agent_prompt.PromptResult:
        raise RuntimeError("display unavailable")

    monkeypatch.setattr(agent_prompt, "user_wants_agent_in_background", failed_prompt)

    assert agent_prompt.main() == 1
