"""Tests for deterministic ambience selection and safe optional playback setup."""
from dataclasses import replace
from pathlib import Path
import sys
import time

from PyQt6.QtCore import QCoreApplication
import pytest

from screenbot.ambient.engine import AmbientSoundEngine, _is_quiet_now
from screenbot.ambient.policy import SceneSound, SceneTheme, WeatherCategory, choose_loop, parse_theme, parse_weather, volume_scale
from screenbot.ambient.lightning import is_lightning_visible


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
    (WeatherCategory.RAIN, 'rain'), (WeatherCategory.THUNDERSTORM, 'rain'),
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
    assert choose_loop(replace(_scene(), thunder_enabled=True)) == 'rain'
    assert choose_loop(replace(_scene(), theme=SceneTheme.SPACE, rain_enabled=True)) == 'space'
    assert choose_loop(replace(_scene(), theme=SceneTheme.SPACE, live_sky_enabled=True, live_sky_fresh=True,
                              weather=WeatherCategory.RAIN)) == 'space'


def test_heavy_live_rain_is_louder_but_bounded_by_user_volume() -> None:
    light = replace(_scene(), weather=WeatherCategory.RAIN, live_sky_enabled=True, live_sky_fresh=True,
                    rain_intensity=.1)
    heavy = replace(light, rain_intensity=1.0)
    assert volume_scale(heavy) > volume_scale(light)
    assert volume_scale(heavy) == 1.0
    assert volume_scale(replace(heavy, rain_intensity=8.0)) == 1.0


def test_thunder_audio_policy_is_scene_selected_not_a_free_running_effect() -> None:
    storm = replace(_scene(), weather=WeatherCategory.THUNDERSTORM, live_sky_enabled=True, live_sky_fresh=True)
    assert choose_loop(storm) == 'rain'


def test_visual_and_audio_share_the_same_lightning_event_phase() -> None:
    events = [(1.0, 12.0, .5), (3.0, 20.0, .7)]
    assert not is_lightning_visible(0.0, events)
    assert not is_lightning_visible(10.0, events)
    assert is_lightning_visible(11.0, events)  # first event wraps to phase 0
    assert not is_lightning_visible(0.0, events, reduce_motion=True)
    assert is_lightning_visible(11.0, events, reduce_motion=True)


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


def test_engine_fades_mutes_resumes_changes_scene_handles_errors_and_closes(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Exercise the real engine lifecycle against a deterministic fake Qt output."""
    import types

    app = QCoreApplication.instance() or QCoreApplication([])

    class Signal:
        def __init__(self) -> None:
            self.callbacks = []

        def connect(self, callback) -> None:
            self.callbacks.append(callback)

        def emit(self, *args) -> None:
            for callback in self.callbacks:
                callback(*args)

    class Output:
        def __init__(self, _parent) -> None:
            self.level = 0.0

        def setVolume(self, level: float) -> None:
            self.level = level

        def volume(self) -> float:
            return self.level

    class Player:
        class PlaybackState:
            StoppedState, PlayingState = 0, 1

        class Loops:
            Infinite = -1
            Once = 1
        class MediaStatus:
            EndOfMedia = 7

        def __init__(self, _parent) -> None:
            self.errorOccurred = Signal()
            self.mediaStatusChanged = Signal()
            self.state = self.PlaybackState.StoppedState
            self.sources = []
            self.play_count = 0
            self.output = None
            self.loops = None

        def setAudioOutput(self, output) -> None:
            self.output = output

        def setLoops(self, loops) -> None:
            self.loops = loops

        def setSource(self, source) -> None:
            self.sources.append(source)

        def play(self) -> None:
            self.play_count += 1
            self.state = self.PlaybackState.PlayingState

        def stop(self) -> None:
            self.state = self.PlaybackState.StoppedState

        def playbackState(self) -> int:
            return self.state

    monkeypatch.setitem(sys.modules, 'PyQt6.QtMultimedia', types.SimpleNamespace(QAudioOutput=Output, QMediaPlayer=Player))
    for asset in ('forest', 'city', 'rain', 'thunder'):
        (tmp_path / f'{asset}.ogg').touch()
    engine = AmbientSoundEngine(app, enabled=True, volume_percent=80, live_sky_only=False,
                                quiet_hours=False, asset_directory=tmp_path)
    scene = _scene()
    engine.update_scene(scene, playing_media=False)
    player, output = engine._player, engine._output
    assert player.sources and output.volume() == 0.0
    for _ in range(5):
        engine._advance_fade()
    assert 0.0 < output.volume() < .8  # fade is in progress
    for _ in range(25):
        engine._advance_fade()
    assert output.volume() <= .8  # the output never exceeds the configured maximum
    engine.update_scene(scene, playing_media=True)
    assert output.volume() == 0.0 and player.playbackState() == Player.PlaybackState.StoppedState
    engine.update_scene(scene, playing_media=False)
    engine._advance_fade()
    assert output.volume() > 0.0 and player.playbackState() == Player.PlaybackState.PlayingState
    storm = replace(scene, weather=WeatherCategory.THUNDERSTORM, live_sky_enabled=True, live_sky_fresh=True)
    engine.update_scene(storm, playing_media=False)
    engine.set_lightning_visible(True)
    deadline = time.monotonic() + 4.0
    while not player.sources[-1].toLocalFile().endswith('/thunder.ogg') and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(.01)
    assert player.sources[-1].toLocalFile().endswith('/thunder.ogg')
    assert player.loops == Player.Loops.Once
    player.mediaStatusChanged.emit(Player.MediaStatus.EndOfMedia)
    assert player.sources[-1].toLocalFile().endswith('/rain.ogg')
    assert player.loops == Player.Loops.Infinite
    engine.set_lightning_visible(False)
    engine.set_lightning_visible(True)
    deadline = time.monotonic() + 4.0
    while not player.sources[-1].toLocalFile().endswith('/thunder.ogg') and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(.01)
    assert player.loops == Player.Loops.Once
    changed = replace(scene, theme=SceneTheme.CITY)
    engine.update_scene(changed, playing_media=False)
    assert player.sources[-1].toLocalFile().endswith('/city.ogg')
    assert player.loops == Player.Loops.Infinite
    player.errorOccurred.emit(1, 'decode failure')
    assert output.volume() == 0.0 and player.playbackState() == Player.PlaybackState.StoppedState
    failed_count = len(player.sources)
    engine.update_scene(changed, playing_media=False)
    assert len(player.sources) == failed_count
    engine.close()
    assert output.volume() == 0.0 and player.playbackState() == Player.PlaybackState.StoppedState
    assert app is not None


def test_missing_asset_is_cached_across_repeated_scene_updates(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys) -> None:
    import types

    app = QCoreApplication.instance() or QCoreApplication([])

    class Output:
        def __init__(self, _parent): self.level = 0.0
        def setVolume(self, level): self.level = level
        def volume(self): return self.level

    class Signal:
        def connect(self, _callback): pass

    class Player:
        class PlaybackState: StoppedState, PlayingState = 0, 1
        class Loops: Infinite = -1
        def __init__(self, _parent): self.errorOccurred = Signal(); self.mediaStatusChanged = Signal(); self.state = 0; self.sources = []
        def setAudioOutput(self, _output): pass
        def setLoops(self, _loops): pass
        def stop(self): self.state = 0
        def setSource(self, source):
            if source.isValid(): self.sources.append(source)
        def play(self): self.state = 1
        def playbackState(self): return self.state

    monkeypatch.setitem(sys.modules, 'PyQt6.QtMultimedia', types.SimpleNamespace(QAudioOutput=Output, QMediaPlayer=Player))
    engine = AmbientSoundEngine(app, enabled=True, volume_percent=50, live_sky_only=False,
                                quiet_hours=False, asset_directory=tmp_path)
    for _ in range(8):
        engine.update_scene(_scene(), playing_media=False)
    logs = capsys.readouterr().err
    assert logs.count('ambient asset is missing') == 1
    assert len(engine._failed_assets) == 1
    (tmp_path / 'forest.ogg').touch()
    engine._refresh_failed_assets()
    engine.update_scene(_scene(), playing_media=False)
    assert len(engine._player.sources) == 1
    engine.close()
