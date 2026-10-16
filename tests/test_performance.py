import os
from pathlib import Path
import time
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from screensaver import battery_powered, frame_interval_ms, particle_count


def write_supply(root: Path, name: str, kind: str, online: str | None = None) -> None:
    supply = root / name
    supply.mkdir()
    (supply / 'type').write_text(kind)
    if online is not None:
        (supply / 'online').write_text(online)


def test_battery_detection_uses_online_mains_and_falls_back_safely(tmp_path):
    assert not battery_powered(tmp_path / 'missing')
    write_supply(tmp_path, 'BAT0', 'Battery')
    assert battery_powered(tmp_path)
    write_supply(tmp_path, 'AC', 'Mains', '1')
    assert not battery_powered(tmp_path)
    (tmp_path / 'AC' / 'online').write_text('0')
    assert battery_powered(tmp_path)


def test_balanced_pacing_drops_on_battery_and_after_fifteen_minutes():
    assert frame_interval_ms('balanced', False, 0) == 33
    assert frame_interval_ms('balanced', True, 0) == 67
    assert frame_interval_ms('balanced', False, 899) == 33
    assert frame_interval_ms('balanced', False, 900) == 67


def test_explicit_modes_and_invalid_mode_are_bounded():
    assert frame_interval_ms('smooth', True, 3600) == 33
    assert frame_interval_ms('battery-saver', False, 0) == 100
    assert frame_interval_ms('invalid', False, 0) == 33
    assert frame_interval_ms('invalid', True, 0) == 67


def test_motion_budget_never_mutates_particles_or_becomes_empty():
    assert particle_count(110, 1) == 110
    assert particle_count(110, .3) == 33
    assert particle_count(1, .01) == 1
    assert particle_count(0, .3) == 0
    assert particle_count(10, 2) == 10


def test_static_scene_layer_is_cached_until_theme_dimensions_change(tmp_path):
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QImage, QPainter
    from PyQt6.QtWidgets import QApplication
    from screensaver import Saver

    app = QApplication.instance() or QApplication([])
    config = tmp_path / 'settings.ini'
    config.write_text('[Screensaver]\ntheme=space\n')
    saver = Saver(preview=True, config_path=config)

    def draw(width: int, height: int) -> None:
        image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.black)
        painter = QPainter(image)
        saver.draw_scenery(painter, width, height, 0.)
        painter.end()

    with patch.object(saver, '_draw_static_scenery', wraps=saver._draw_static_scenery) as static_layer:
        draw(240, 160)
        draw(240, 160)
        assert static_layer.call_count == 1
        draw(320, 160)
        assert static_layer.call_count == 2
        saver.theme = 'mountains'
        draw(320, 160)
        assert static_layer.call_count == 3
    saver.close()
    app.processEvents()


def test_smooth_cached_scenes_match_v22_theme_frames(tmp_path):
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QImage, QPainter
    from PyQt6.QtWidgets import QApplication
    from screensaver import Saver

    app = QApplication.instance() or QApplication([])
    config = tmp_path / 'settings.ini'
    config.write_text('[Screensaver]\ntheme=space\nperformance_mode=smooth\n')
    saver = Saver(preview=True, config_path=config)
    saver.performance_mode = 'smooth'
    width, height, elapsed = 360, 240, 17.25
    for theme in ('space', 'mountains', 'snow', 'forest', 'city'):
        saver.theme = theme
        old_frame = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
        cached_frame = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
        old_frame.fill(Qt.GlobalColor.black)
        cached_frame.fill(Qt.GlobalColor.black)
        original = QPainter(old_frame)
        original.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        getattr(saver, theme)(original, width, height, elapsed)
        saver.weather(original, width, height, elapsed)
        original.end()
        optimized = QPainter(cached_frame)
        optimized.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        saver.draw_scenery(optimized, width, height, elapsed)
        optimized.end()
        max_channel_delta = 0
        for y in range(height):
            for x in range(width):
                old_pixel = old_frame.pixelColor(x, y)
                new_pixel = cached_frame.pixelColor(x, y)
                max_channel_delta = max(max_channel_delta,
                    abs(old_pixel.red() - new_pixel.red()),
                    abs(old_pixel.green() - new_pixel.green()),
                    abs(old_pixel.blue() - new_pixel.blue()),
                    abs(old_pixel.alpha() - new_pixel.alpha()))
        assert max_channel_delta <= 1, f'{theme} Smooth rendering changed beyond one RGB level from V22'
    saver.close()
    app.processEvents()


def test_frame_timer_only_runs_while_widget_is_visible(tmp_path):
    from unittest.mock import patch
    from PyQt6.QtWidgets import QApplication
    from screensaver import Saver

    app = QApplication.instance() or QApplication([])
    config = tmp_path / 'settings.ini'
    config.write_text('[Screensaver]\ntheme=space\npassword_lock=true\nlock_minutes=1\n')
    saver = Saver(config_path=config)
    assert not saver.timer.isActive()
    assert saver.lock_timer.isActive()
    saver.show()
    app.processEvents()
    assert saver.timer.isActive()
    saver.hide()
    app.processEvents()
    assert not saver.timer.isActive()
    assert saver.lock_timer.isActive()
    saver.start_time = time.monotonic() - 61
    with patch.object(saver, 'request_kde_lock') as request_lock:
        saver.check_password_lock()
        app.processEvents()
        request_lock.assert_called_once_with()
    saver.close()
    saver.lock_timer.stop()
