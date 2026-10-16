"""Tests for deterministic ambience selection and safe optional playback setup."""
from dataclasses import replace
from pathlib import Path
import sys

from PyQt6.QtCore import QCoreApplication
import pytest

from screenbot.ambient.engine import AmbientSoundEngine, _is_quiet_now
from screenbot.ambient.policy import SceneSound, SceneTheme, WeatherCategory, choose_loop, parse_theme, parse_weather


def _scene() -> SceneSound:
    return SceneSound(theme=SceneTheme.FOREST, weather=WeatherCategory.UNKNOWN, live_sky_enabled=False,
                      live_sky_fresh=False, live_sky_only=False, rain_enabled=False,
                      snow_enabled=False, thunder_enabled=False, elapsed_hours=12.0)


@pytest.mark.parametrize(('theme', 'expected'), [
    (SceneTheme.SPACE, 'space'), (SceneTheme.MOUNTAINS, 'wind'), (SceneTheme.SNOW, 'wind'),
    (SceneTheme.FOREST, 'forest'), (SceneTheme.CITY, 'city'), (SceneTheme.AURORA, 'wind'),
    (SceneTheme.OCEAN, 'waves'), (SceneTheme.DESERT, 'wind'), (SceneTheme.UNDERWATER, 'waves'),
])
def test_every_theme_has_one_deterministic_ambience(theme: SceneTheme, expected: str) -> None:
    assert choose_loop(replace(_scene(), theme=theme)) == expected


def test_invalid_scene_inputs_fall_back_to_silence() -> None:
    assert parse_theme('invalid') is SceneTheme.UNKNOWN
    assert parse_weather('hail') is WeatherCategory.UNKNOWN
    assert choose_loop(replace(_scene(), theme=SceneTheme.UNKNOWN)) is None


def test_forest_switches_to_quiet_crickets_at_night() -> None:
    assert choose_loop(replace(_scene(), elapsed_hours=22.0)) == 'crickets'
    assert choose_loop(replace(_scene(), elapsed_hours=5.5)) == 'crickets'
    assert choose_loop(replace(_scene(), elapsed_hours=8.0)) == 'forest'


@pytest.mark.parametrize(('weather', 'expected'), [
    (WeatherCategory.RAIN, 'rain'), (WeatherCategory.THUNDERSTORM, 'thunder'),
    (WeatherCategory.SNOW, 'wind'), (WeatherCategory.FOG, 'wind'),
])
def test_fresh_live_weather_selects_weather_matched_loop(weather: WeatherCategory, expected: str) -> None:
    scene = replace(_scene(), weather=weather, live_sky_enabled=True, live_sky_fresh=True)
    assert choose_loop(scene) == expected
    assert choose_loop(replace(scene, live_sky_only=True)) == expected


def test_live_sky_only_mode_silences_stale_and_unknown_weather() -> None:
    assert choose_loop(replace(_scene(), live_sky_only=True)) is None
    assert choose_loop(replace(_scene(), live_sky_enabled=True, live_sky_fresh=False, live_sky_only=True)) is None
    assert choose_loop(replace(_scene(), weather=WeatherCategory.UNKNOWN, live_sky_enabled=True, live_sky_fresh=True, live_sky_only=True)) is None


def test_manual_weather_sound_and_space_weather_suppression() -> None:
    assert choose_loop(replace(_scene(), rain_enabled=True)) == 'rain'
    assert choose_loop(replace(_scene(), snow_enabled=True)) == 'wind'
    assert choose_loop(replace(_scene(), thunder_enabled=True)) == 'thunder'
    assert choose_loop(replace(_scene(), theme=SceneTheme.SPACE, rain_enabled=True)) == 'space'
    assert choose_loop(replace(_scene(), theme=SceneTheme.SPACE, live_sky_enabled=True, live_sky_fresh=True,
                              weather=WeatherCategory.RAIN)) == 'space'


@pytest.mark.parametrize(('hour', 'quiet'), [(0, True), (7, True), (8, False), (21, False), (22, True), (23, True)])
def test_quiet_hours_cover_local_night(hour: int, quiet: bool) -> None:
    from datetime import datetime
    assert _is_quiet_now(datetime(2026, 10, 16, hour, 0)) is quiet


def test_missing_multimedia_is_a_silent_optional_feature(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    app = QCoreApplication.instance() or QCoreApplication([])
    monkeypatch.setitem(sys.modules, 'PyQt6.QtMultimedia', None)
    engine = AmbientSoundEngine(app, enabled=True, volume_percent=40,
                                live_sky_only=False, quiet_hours=False, asset_directory=Path('assets/audio'))
    assert not engine.available
    assert 'ambient audio is disabled' in capsys.readouterr().err
    engine.close()


def test_audio_off_does_not_load_multimedia() -> None:
    app = QCoreApplication.instance() or QCoreApplication([])
    engine = AmbientSoundEngine(app, enabled=False, volume_percent=100,
                                live_sky_only=False, quiet_hours=False, asset_directory=Path('assets/audio'))
    assert not engine.available
    engine.close()
