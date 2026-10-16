"""Quick-preview settings, rendering, and security regression scenarios."""
import configparser
import os
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import pytest
from PyQt6.QtCore import QEvent, QPointF, Qt
from PyQt6.QtGui import QKeyEvent, QMouseEvent
from PyQt6.QtWidgets import QApplication

from bobos import BobOSPhase
from screensaver import Saver


@pytest.fixture(scope='module')
def app() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture
def preview_config(tmp_path: Path) -> Path:
    path = tmp_path / 'preview.ini'
    path.write_text('[Screensaver]\ntheme=forest\npassword_lock=true\nshow_timer=true\n'
                    'lock_minutes=1\nbobos_enabled=true\nshow_clock=true\n'
                    'clock_format=24h\nclock_position=bottom-right\nclock_font_size=24\n'
                    'show_date=true\nrain_enabled=true\nsnow_enabled=true\n'
                    'thunderstorms_enabled=true\nfog_enabled=true\nshooting_stars_enabled=true\n')
    return path


def test_preview_uses_temporary_settings_without_writing_saved_values(
        app: QApplication, preview_config: Path, tmp_path: Path) -> None:
    # Given a saved choice different from the staged configuration.
    saved = tmp_path / '.config/screenbot-screensaver.ini'
    saved.parent.mkdir()
    saved.write_text('[Screensaver]\ntheme=space\n')
    original = saved.read_bytes()
    with patch.object(Path, 'home', return_value=tmp_path):
        # When preview reads the temporary config.
        saver = Saver(preview=True, config_path=preview_config)
    # Then staged visual values are used and saved bytes stay unchanged.
    assert (saver.theme, saver.clock_format, saver.clock_position, saver.clock_font_size) == (
        'forest', '24h', 'bottom-right', 24)
    assert all((saver.show_clock, saver.show_date, saver.rain_enabled, saver.snow_enabled,
                saver.thunderstorms_enabled, saver.fog_enabled, saver.shooting_stars_enabled))
    assert saved.read_bytes() == original
    saver.close()


@pytest.mark.parametrize('bobos', [False, True])
def test_preview_never_requests_lock_after_deadline(
        app: QApplication, preview_config: Path, bobos: bool) -> None:
    # Given lock and countdown enabled in the staged file.
    saver = Saver(preview=not bobos, preview_bobos=bobos, config_path=preview_config)
    saver.showFullScreen()
    saver.start_time -= 3600
    # When rendering beyond the deadline and exercising the lock entry point.
    with patch('screensaver.subprocess.run', side_effect=AssertionError('lock requested')):
        saver.grab()
        app.processEvents()
        saver.request_kde_lock()
    # Then previews remain visible, without a lock countdown.
    assert saver.isFullScreen() and saver.isVisible()
    assert not saver.password_lock and not saver.show_timer
    assert not saver.lock_attempted
    saver.close()


def test_quick_preview_never_starts_bobos(app: QApplication, preview_config: Path) -> None:
    # Given enabled BobOS in the input.
    saver = Saver(preview=True, config_path=preview_config)
    # When evaluating its schedule throughout a long preview.
    phases = [saver.bobos_status(seconds).phase for seconds in (0, 60, 180, 600, 3600)]
    # Then Bob keeps exploring.
    assert phases == [BobOSPhase.EXPLORING] * 5
    saver.close()


@pytest.mark.parametrize('input_kind', ['key', 'mouse'])
def test_preview_closes_on_input_immediately(
        app: QApplication, preview_config: Path, input_kind: str) -> None:
    # Given a just-opened preview (no grace period).
    saver = Saver(preview=True, config_path=preview_config)
    saver.showFullScreen()
    if input_kind == 'key':
        event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Space, Qt.KeyboardModifier.NoModifier)
    else:
        event = QMouseEvent(QEvent.Type.MouseMove, QPointF(5, 5),
                            QPointF(saver.preview_mouse_origin) + QPointF(1, 0),
                            Qt.MouseButton.NoButton, Qt.MouseButton.NoButton,
                            Qt.KeyboardModifier.NoModifier)
    # When the real Qt input dispatcher delivers the input.
    with patch.object(QApplication, 'quit') as quit_app:
        QApplication.sendEvent(saver, event)
    # Then application shutdown is requested.
    quit_app.assert_called_once()
    saver.close()


@pytest.mark.parametrize('theme', ['space', 'mountains', 'snow', 'forest', 'city', 'random'])
@pytest.mark.parametrize('live', [False, True])
def test_preview_renders_selected_theme_with_live_sky(
        app: QApplication, preview_config: Path, theme: str, live: bool) -> None:
    # Given current unsaved theme/sky choices and no configured city.
    config = configparser.ConfigParser()
    config.read(preview_config)
    config['Screensaver']['theme'] = theme
    config['Screensaver']['live_sky_enabled'] = str(live)
    config['Screensaver']['show_clock'] = 'false' if live else 'true'
    with preview_config.open('w') as output:
        config.write(output)
    saver = Saver(preview=True, config_path=preview_config)
    # When the full-screen preview is painted.
    saver.showFullScreen()
    app.processEvents()
    image = saver.grab()
    # Then an actual rendered frame exists with the current mode.
    assert not image.isNull() and saver.isFullScreen()
    assert saver.live_sky_enabled == live
    assert saver.theme == theme or theme == 'random'
    evidence = os.environ.get('SCREENBOT_PREVIEW_EVIDENCE')
    if evidence:
        assert image.save(str(Path(evidence) / f'{theme}-live-{live}.png'))
    saver.close()


@pytest.mark.parametrize('fresh', [False, True])
def test_preview_reuses_selected_city_cache_and_handles_unavailable_weather(
        app: QApplication, preview_config: Path, tmp_path: Path, fresh: bool) -> None:
    import json
    import time
    # Given cached coordinates for a selected city, with fresh or expired weather.
    now = time.time()
    cache = tmp_path / '.cache/screenbot/live-sky.json'
    cache.parent.mkdir(parents=True)
    cache.write_text(json.dumps({
        'key': 'city:Paris, France', 'located': True, 'latitude': 48.85, 'longitude': 2.35,
        'attempted_at': now, 'observed_at': now if fresh else now - 20000,
        'weather': {'weather_code': 61, 'cloud_cover': 75, 'precipitation': 3,
                    'wind_speed_10m': 4, 'temperature_2m': 12},
    }))
    with preview_config.open('a') as output:
        output.write('live_sky_enabled=true\nlive_sky_location=Paris, France\n')
    with patch.object(Path, 'home', return_value=tmp_path):
        saver = Saver(preview=True, config_path=preview_config)
    # When the live preview paints using the ordinary cache/request limiter.
    saver.showFullScreen()
    app.processEvents()
    frame = saver.grab()
    # Then the selected position is resolved and stale observations cannot cause rain.
    assert saver.live_weather.located
    assert saver.live_weather.weather.category == ('rain' if fresh else 'clear')
    assert not saver.live_weather.busy
    assert saver.live_sky_position is not None
    evidence = os.environ.get('SCREENBOT_PREVIEW_EVIDENCE')
    if evidence:
        assert frame.save(str(Path(evidence) / f'paris-weather-fresh-{fresh}.png'))
    saver.close()
