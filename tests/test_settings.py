import os
from pathlib import Path

import pytest
from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication

from screenbot.app import Saver
from screenbot.settings import read_settings


@pytest.mark.parametrize('preview', [True, False], ids=['preview', 'normal'])
@pytest.mark.parametrize('case', [
    'photo-percent', 'name-percent', 'photo-accent', 'photo-cjk',
    'invalid-bool', 'duplicate-key', 'missing-header', 'partial-file',
    'invalid-utf8', 'unreadable', 'missing',
])
def test_saver_starts_when_settings_contain_edge_cases(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str], preview: bool, case: str) -> None:
    # Given: the same file locations used by preview and normal launch.
    monkeypatch.setattr(Path, 'home', lambda: tmp_path)
    path = tmp_path / '.config' / 'screenbot-screensaver.ini'
    path.parent.mkdir()
    folder = tmp_path / {'photo-percent': '100% Holiday', 'photo-accent': 'Café',
                         'photo-cjk': '图片'}.get(case, 'photos')
    folder.mkdir()
    if case.startswith('photo-') or case == 'name-percent':
        settings = QSettings(str(path), QSettings.Format.IniFormat)
        settings.setValue('Screensaver/theme', 'photos')
        settings.setValue('Screensaver/photo_folder', str(folder))
        settings.setValue('Screensaver/bob_name', 'Bob 100%' if case == 'name-percent' else 'Bob')
        settings.sync()
        assert settings.status() == QSettings.Status.NoError
    elif case == 'invalid-bool':
        path.write_text('[Screensaver]\ntheme=forest\nrain_enabled=maybe\n', encoding='utf-8')
    elif case == 'duplicate-key':
        path.write_text('[Screensaver]\ntheme=space\ntheme=forest\n', encoding='utf-8')
    elif case == 'missing-header':
        path.write_text('theme=forest\n', encoding='utf-8')
    elif case == 'partial-file':
        path.write_text('[Screensaver]\nshow_clock=false\nbroken line\n', encoding='utf-8')
    elif case == 'invalid-utf8':
        path.write_bytes(b'[Screensaver]\nbob_name=\xff\n')
    elif case == 'unreadable':
        path.mkdir()
    original = path.read_bytes() if path.is_file() else None
    # When: the actual Saver loads and paints these settings.
    saver = Saver(preview=preview, config_path=path if preview else None)
    try:
        saver.resize(640, 480)
        saver.show()
        QApplication.processEvents()
        frame = saver.grab()
        # Then: startup succeeds, valid values survive, invalid values use defaults.
        assert saver.isVisible() and not frame.isNull()
        if case.startswith('photo-') or case == 'name-percent':
            assert saver.photo_slideshow is not None
            assert saver.photo_slideshow.folder == folder
            assert saver.bob_appearance.name == ('Bob 100%' if case == 'name-percent' else 'Bob')
        if case in {'duplicate-key', 'invalid-bool'}:
            assert saver.theme == 'forest'
        assert saver.rain_enabled is False
        assert saver.show_clock is True
        warning = capsys.readouterr().err
        if case in {'invalid-bool', 'missing-header', 'partial-file', 'invalid-utf8', 'unreadable'}:
            assert 'ScreenBot:' in warning
        if original is not None:
            assert path.read_bytes() == original
        evidence = os.environ.get('SCREENBOT_SETTINGS_EVIDENCE')
        if evidence:
            assert frame.save(str(Path(evidence) / f'{case}-{preview}.png'))
    finally:
        saver.close()


BOOLEAN_KEYS = (
    'bob_weather_enabled', 'show_clock', 'now_playing_enabled', 'show_date',
    'rain_enabled', 'snow_enabled', 'thunderstorms_enabled', 'fog_enabled',
    'shooting_stars_enabled', 'live_sky_enabled', 'live_sky_conditions',
    'password_lock', 'show_timer', 'bob_phone_enabled', 'ai_backpack_enabled',
    'bobos_enabled', 'show_wifi_animation', 'reduce_motion', 'agent_status_enabled',
    'photo_include_subfolders', 'ambient_sound_enabled', 'ambient_quiet_hours',
    'facts_enabled', 'seasonal_enabled', 'seasonal_new_year_enabled',
    'seasonal_lunar_new_year_enabled', 'seasonal_valentines_enabled',
    'seasonal_spring_enabled', 'seasonal_halloween_enabled',
    'seasonal_winter_holidays_enabled', 'seasonal_birthday_enabled',
)


@pytest.mark.parametrize('key', BOOLEAN_KEYS)
def test_saver_starts_when_one_boolean_is_invalid(
        tmp_path: Path, capsys: pytest.CaptureFixture[str], key: str) -> None:
    # Given: a single invalid boolean and unrelated valid settings.
    path = tmp_path / 'settings.ini'
    path.write_text('[Screensaver]\ntheme=photos\nclock_format=24h\n'
                    f'password_lock=true\n{key}=maybe\n', encoding='utf-8')
    # When: normal startup parses every boolean consumer, including lock settings.
    saver = Saver(config_path=path)
    try:
        # Then: the invalid field warns exactly once and unrelated settings survive.
        assert saver.theme == 'photos' and saver.clock_format == '24h'
        warning = capsys.readouterr().err
        assert warning.count(key) == 1
    finally:
        saver.close()


def test_missing_file_uses_defaults_without_warning(
        tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    # Given: a first launch without a settings file.
    path = tmp_path / 'absent.ini'
    # When: settings are read.
    settings = read_settings(path)
    # Then: defaults remain available and there is no error to report.
    assert settings.sections() == []
    assert capsys.readouterr().err == ''
