from pathlib import Path

import pytest
from PyQt6.QtCore import QSettings

import agent_prompt
from screenbot.settings import get_bool, read_settings


@pytest.mark.parametrize('default', [False, True])
@pytest.mark.parametrize('value', ['maybe', '100%', ''])
def test_invalid_boolean_uses_requested_default(
        tmp_path: Path, capsys: pytest.CaptureFixture[str], default: bool, value: str) -> None:
    # Given: a present but invalid value, with a caller-specific default.
    path = tmp_path / 'settings.ini'
    path.write_text(f'[Screensaver]\nrain_enabled={value}\n', encoding='utf-8')
    settings = read_settings(path)
    # When: the boolean crosses the settings boundary.
    result = get_bool(settings, 'rain_enabled', default)
    # Then: the exact default is returned, with one warning and no config mutation.
    assert result is default
    assert capsys.readouterr().err.count('rain_enabled') == 1
    assert settings.get('Screensaver', 'rain_enabled') == value


@pytest.mark.parametrize(('value', 'expected'), [('yes', True), ('no', False), ('1', True), ('0', False)])
def test_valid_boolean_overrides_default(
        tmp_path: Path, capsys: pytest.CaptureFixture[str], value: str, expected: bool) -> None:
    # Given: a recognized boolean value that differs from the default.
    path = tmp_path / 'settings.ini'
    path.write_text(f'[Screensaver]\nrain_enabled={value}\n', encoding='utf-8')
    # When: the value is read.
    result = get_bool(read_settings(path), 'rain_enabled', not expected)
    # Then: the saved value wins without a warning.
    assert result is expected
    assert capsys.readouterr().err == ''


def test_agent_settings_preserve_qt_percent_values_when_saving(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Given: KDE wrote literal percent signs and Unicode before a remembered choice.
    path = tmp_path / 'settings.ini'
    qt = QSettings(str(path), QSettings.Format.IniFormat)
    qt.setValue('Screensaver/bob_name', 'Bob 100%')
    qt.setValue('Screensaver/photo_folder', '/pictures/100% Café/图片')
    qt.sync()
    monkeypatch.setattr(agent_prompt, 'CONFIG_FILE', path)
    # When: the user remembers a blocking preference.
    saved = agent_prompt._save_mode(agent_prompt.AgentMode.NEVER_START_WHILE_ACTIVE)
    # Then: the policy persists and the unrelated literal values survive.
    assert saved
    assert agent_prompt._read_mode() is agent_prompt.AgentMode.NEVER_START_WHILE_ACTIVE
    settings = read_settings(path)
    assert settings.get('Screensaver', 'bob_name') == 'Bob 100%'
    assert settings.get('Screensaver', 'photo_folder') == '/pictures/100% Café/图片'


def test_agent_readers_use_last_duplicate_values(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Given: settings with duplicate keys and distinct last values.
    path = tmp_path / 'settings.ini'
    path.write_text('[Screensaver]\nagent_detection_mode=ask\nagent_detection_mode=block\n'
                    'agent_prompt_timeout_seconds=10\nagent_prompt_timeout_seconds=45\n'
                    'agent_prompt_timeout_action=start\nagent_prompt_timeout_action=cancel\n',
                    encoding='utf-8')
    monkeypatch.setattr(agent_prompt, 'CONFIG_FILE', path)
    # When: both agent settings readers load the same file.
    mode, prompt = agent_prompt._read_mode(), agent_prompt._read_prompt_settings()
    # Then: each reader agrees with Qt duplicate-key semantics.
    assert mode is agent_prompt.AgentMode.NEVER_START_WHILE_ACTIVE
    assert prompt == agent_prompt.PromptSettings(45, agent_prompt.TimeoutAction.CANCEL)


def test_invalid_encoding_keeps_agent_preferences_safe(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Given: a file which cannot be decoded as Qt 6 UTF-8 settings.
    path = tmp_path / 'settings.ini'
    original = b'[Screensaver]\nbob_name=\xff\n'
    path.write_bytes(original)
    monkeypatch.setattr(agent_prompt, 'CONFIG_FILE', path)
    # When: readers fall back and a remembered preference attempts to save.
    mode, prompt = agent_prompt._read_mode(), agent_prompt._read_prompt_settings()
    saved = agent_prompt._save_mode(agent_prompt.AgentMode.ALWAYS_START)
    # Then: defaults apply without overwriting the unreadable original.
    assert mode is agent_prompt.AgentMode.ALWAYS_ASK
    assert prompt == agent_prompt.PromptSettings()
    assert not saved
    assert path.read_bytes() == original
