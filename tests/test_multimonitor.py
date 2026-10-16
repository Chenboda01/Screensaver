"""Real Qt windows on isolated offscreen outputs; no user desktop or locker touched."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.parametrize('scenario', [
    'coverage', 'coverage-live', 'key-primary', 'key-secondary', 'mouse-primary', 'mouse-secondary',
    'lock', 'hotplug', 'single', 'mirror',
])
def test_display_session_when_outputs_change(scenario: str, tmp_path: Path) -> None:
    # Given independent Qt outputs, including different sizes and a mirror case.
    screens = [{'name': 'primary', 'x': 0, 'y': 0, 'width': 1280, 'height': 720}]
    if scenario != 'single':
        screens.append({'name': 'secondary', 'x': 1280, 'y': 0, 'width': 800, 'height': 600})
    if scenario == 'mirror':
        screens[1].update(x=0, width=1280, height=720)
    config = tmp_path / 'outputs.json'
    config.write_text(json.dumps({'screens': screens}))
    env = dict(os.environ, QT_QPA_PLATFORM=f'offscreen:configfile={config}',
               PYTHONPATH=str(Path(__file__).resolve().parents[1]))
    # When the complete production display session runs its scenario.
    result = subprocess.run([sys.executable, __file__, scenario, str(tmp_path)],
                            env=env, capture_output=True, text=True, timeout=30)
    (tmp_path / 'process.log').write_text(result.stdout + result.stderr)
    # Then each scenario reaches its binary assertion and captures its result.
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads((tmp_path / 'result.json').read_text())['passed']


def run_scenario(scenario: str, directory: Path) -> None:
    """Exercise production widgets using actual QScreen objects in a child process."""
    from unittest.mock import patch

    from PyQt6.QtCore import QEvent, QPointF, Qt
    from PyQt6.QtGui import QImage, QKeyEvent, QMouseEvent, QPainter
    from PyQt6.QtWidgets import QApplication

    from screen_session import SceneryWindow, ScreenSession
    from screensaver import Saver

    app = QApplication([])
    config = directory / 'settings.ini'
    config.write_text('[Screensaver]\ntheme=random\npassword_lock=false\n')
    saver = Saver(config_path=config)
    session = ScreenSession(app, saver)
    session.start()
    app.processEvents()
    windows = list(session.windows.values())
    start = saver.start_time
    if scenario in ('single', 'mirror'):
        assert windows == [saver]
        assert saver.isFullScreen() and saver.isVisible()
        assert saver.grab().save(str(directory / 'primary.png'))
    elif scenario.startswith('coverage'):
        assert len(windows) == 2
        saver.live_sky_enabled = scenario == 'coverage-live'
        secondary = windows[1]
        assert isinstance(secondary, SceneryWindow)
        assert secondary.scene is saver
        assert saver.size() != secondary.size()
        for screen, window in session.windows.items():
            assert window.isFullScreen() and window.isVisible()
            assert window.screen() is screen
            assert window.size() == screen.size()
        for theme in ('space', 'mountains', 'snow', 'forest', 'city', 'aurora', 'ocean', 'desert', 'underwater'):
            saver.theme = theme
            with patch('time.monotonic', return_value=start + 20):
                actual = secondary.grab().toImage().convertToFormat(QImage.Format.Format_RGB32)
                expected = QImage(secondary.size(), QImage.Format.Format_RGB32)
                painter = QPainter(expected)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                saver.draw_scenery(painter, secondary.width(), secondary.height(), 20)
                painter.end()
                assert expected.save(str(directory / f'{theme}-expected.png'))
                assert actual.save(str(directory / f'{theme}-secondary.png'))
                assert actual == expected, theme
                assert saver.grab().save(str(directory / f'{theme}-primary.png'))
        saver.preview_bobos = True
        from bobos import BobOSTimeline
        saver.bobos_timeline = BobOSTimeline(activation_delay_seconds=180, show_connection_animation=True, preview_mode=True)
        with patch('time.monotonic', return_value=start + 24):
            assert saver.grab().save(str(directory / 'bobos-primary.png'))
            assert secondary.grab().save(str(directory / 'bobos-secondary.png'))
    elif scenario.startswith(('key-', 'mouse-')):
        target = windows[1] if scenario.endswith('secondary') else saver
        saver.start_time -= 2
        if scenario.startswith('key-'):
            event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier)
        else:
            global_position = QPointF(session.mouse_origin) + QPointF(20, 10)
            event = QMouseEvent(QEvent.Type.MouseMove, QPointF(20, 10), global_position,
                                Qt.MouseButton.NoButton, Qt.MouseButton.NoButton,
                                Qt.KeyboardModifier.NoModifier)
        QApplication.sendEvent(target, event)
        assert all(not window.isVisible() for window in windows)
        assert not saver.timer.isActive()
    elif scenario == 'lock':
        saver.password_lock = True
        saver.start_time -= saver.lock_seconds + 1
        with patch('screensaver.subprocess.run', return_value=subprocess.CompletedProcess([], 0)) as lock:
            with patch.object(QApplication, 'quit'):
                for window in windows:
                    window.grab()
                app.processEvents()
                saver.request_kde_lock()
            assert lock.call_count == 1
            assert lock.call_args.args[0][-1] == 'org.freedesktop.ScreenSaver.Lock'
    elif scenario == 'hotplug':
        first, second = app.screens()
        # Deliver the same membership/signal contract as Qt's platform plugin.
        with patch.object(app, 'screens', return_value=[second]):
            with patch.object(app, 'primaryScreen', return_value=second):
                app.screenRemoved.emit(first)
                assert list(session.windows) == [second]
                assert session.windows[second] is saver
                assert saver.start_time == start
                assert saver.screen() is second
        app.screenAdded.emit(first)
        assert len(session.windows) == 2
        assert session.windows[first] is saver
        assert all(window.isVisible() for window in session.windows.values())
        assert saver.start_time == start
    session.stop()
    (directory / 'result.json').write_text(json.dumps({
        'scenario': scenario, 'passed': True, 'platform': app.platformName(),
        'outputs': [{'name': screen.name(), 'width': screen.size().width(),
                     'height': screen.size().height()} for screen in app.screens()],
    }, indent=2))


if __name__ == '__main__':
    run_scenario(sys.argv[1], Path(sys.argv[2]))
