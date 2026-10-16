"""Full screensaver startup, live MPRIS updates and safe shutdown on a private bus."""
import json
import os
from pathlib import Path
import selectors
import shutil
import subprocess
import sys
import time

import pytest
from PyQt6.QtCore import QTimer


@pytest.mark.parametrize('scenario', ['playing', 'missing-bus'])
def test_real_screensaver_media_session(tmp_path: Path, scenario: str) -> None:
    runner = shutil.which('dbus-run-session')
    if runner is None:
        pytest.skip('dbus-run-session is required for private integration')
    root = Path(__file__).resolve().parents[1]
    env = dict(os.environ, HOME=str(tmp_path), PYTHONPATH=str(root), QT_QPA_PLATFORM='offscreen')
    result = subprocess.run([runner, '--', sys.executable, __file__, str(tmp_path), scenario],
                            cwd=root, env=env, capture_output=True, text=True, timeout=25)
    (tmp_path / 'process.log').write_text(result.stdout + result.stderr)
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads((tmp_path / 'result.json').read_text())['passed']


def run_session(directory: Path) -> None:
    """Observe production main(), changing only the synthetic player's state."""
    import screensaver
    from screenbot.now_playing import card_opacity

    config = directory / '.config' / 'screenbot-screensaver.ini'
    config.parent.mkdir()
    config.write_text('[Screensaver]\nnow_playing_enabled=true\nagent_status_enabled=false\n'
                      'bobos_enabled=false\nshow_clock=true\nshow_date=true\nburn_in_protection=off\ntheme=forest\n')
    state = directory / 'player.json'
    state.write_text(json.dumps({'title': 'First song', 'status': 'Playing'}))
    player_env = dict(os.environ, SCREENBOT_MPRIS_FIXTURE=str(state))
    with subprocess.Popen([sys.executable, 'tests/mpris_service.py'], env=player_env,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as service:
        try:
            assert service.stdout is not None
            with selectors.DefaultSelector() as ready:
                ready.register(service.stdout, selectors.EVENT_READ)
                assert ready.select(timeout=3)
                assert service.stdout.readline().strip() == 'READY'
            started = time.monotonic()
            timings: dict[str, float] = {}

            class ObservedSaver(screensaver.Saver):
                def showEvent(self, event) -> None:
                    super().showEvent(event)
                    self._stage = 0
                    self._seen_fade = False
                    self._probe = QTimer(self)
                    self._probe.setInterval(25)
                    self._probe.timeout.connect(self.observe)
                    self._probe.start()

                def observe(self) -> None:
                    now = time.monotonic()
                    assert now - started < 18, 'media session exceeded its update deadline'
                    track = self.now_playing.track
                    if self._stage == 0 and track and track.title == 'First song':
                        timings['first_seconds'] = now - started
                        assert timings['first_seconds'] < 4
                        assert self.grab().save(str(directory / 'first-song.png'))
                        state.write_text(json.dumps({'title': 'Next song — 星の夜 ' * 20, 'status': 'Playing'}))
                        self._changed_at = now
                        self._stage = 1
                    elif self._stage == 1 and track and track.title.startswith('Next song'):
                        timings['change_seconds'] = now - self._changed_at
                        assert timings['change_seconds'] < 4
                        assert len(track.title) <= 160
                        assert self.grab().save(str(directory / 'changed-long-title.png'))
                        state.write_text(json.dumps({'title': track.title, 'status': 'Paused'}))
                        self._paused_at = now
                        self._stage = 2
                    elif self._stage == 2:
                        opacity = card_opacity(self.now_playing, now, False)
                        if 0 < opacity < .7 and not self._seen_fade:
                            assert self.grab().save(str(directory / 'paused-fading.png'))
                            self._seen_fade = True
                        if opacity == 0:
                            assert self._seen_fade
                            timings['pause_hidden_seconds'] = now - self._paused_at
                            assert timings['pause_hidden_seconds'] < 6
                            assert self.grab().save(str(directory / 'paused-hidden.png'))
                            self._stage = 3
                            self.close()
                            screensaver.QApplication.quit()

            screensaver.Saver = ObservedSaver
            assert screensaver.main([]) == 0
            assert 'pause_hidden_seconds' in timings
            (directory / 'result.json').write_text(json.dumps({'passed': True, 'runtime': screensaver.__file__, **timings}))
        finally:
            service.terminate()
            service.wait(timeout=3)


def run_missing_bus(directory: Path) -> None:
    """Start the real screensaver with a missing bus and verify its quiet empty card."""
    os.environ['DBUS_SESSION_BUS_ADDRESS'] = f'unix:path={directory}/missing-bus'
    import screensaver
    config = directory / '.config' / 'screenbot-screensaver.ini'
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text('[Screensaver]\nnow_playing_enabled=true\nagent_status_enabled=false\nbobos_enabled=false\n')

    class ObservedSaver(screensaver.Saver):
        def showEvent(self, event) -> None:
            super().showEvent(event)
            QTimer.singleShot(350, self.capture)

        def capture(self) -> None:
            assert self.now_playing.track is None
            assert self.media_worker is not None and self.media_worker.isRunning()
            assert self.grab().save(str(directory / 'missing-bus-hidden.png'))
            self.close()
            screensaver.QApplication.quit()

    screensaver.Saver = ObservedSaver
    assert screensaver.main([]) == 0
    (directory / 'result.json').write_text(json.dumps({'passed': True, 'media_hidden': True}))


if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[2] == 'missing-bus':
        run_missing_bus(Path(sys.argv[1]))
    else:
        run_session(Path(sys.argv[1]))
