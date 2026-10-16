# /// script
# requires-python = ">=3.11"
# dependencies = ["PyQt6", "pytest"]
# ///
# Run: python -m pytest tests/test_mpris_dbus.py -v
"""Real QtDBus decoding and timing against an isolated, synthetic session bus."""
from dataclasses import asdict
import importlib.util
import json
import os
from pathlib import Path
import selectors
import shutil
import subprocess
import sys
import time

import pytest
from PyQt6.QtCore import QCoreApplication

from screenbot.mpris import Playback, PlayerSample, Track
from screenbot.mpris_bus import SessionBusReader


@pytest.mark.parametrize('scenario', ['missing-bus', 'no-player', 'playing', 'unresponsive'])
def test_private_session_bus(scenario: str, tmp_path: Path) -> None:
    # Given a private bus; never connect these tests to the user's media players.
    runner = shutil.which('dbus-run-session')
    if runner is None or importlib.util.find_spec('PyQt6.QtDBus') is None:
        pytest.skip('real bus integration requires dbus-run-session and QtDBus')
    root = Path(__file__).resolve().parents[1]
    env = dict(os.environ, PYTHONPATH=str(root))
    # When the production adapter reads the synthetic service or absent bus.
    result = subprocess.run([runner, '--', sys.executable, __file__, scenario, str(tmp_path)],
                            cwd=root, env=env, capture_output=True, text=True, timeout=10)
    (tmp_path / 'process.log').write_text(result.stdout + result.stderr)
    # Then the child must finish every assertion and record observed timings/data.
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads((tmp_path / 'result.json').read_text())['passed']


def run_scenario(scenario: str, directory: Path) -> None:
    """Run one scenario in a child so Qt's session-bus connection cannot leak."""
    if scenario == 'missing-bus':
        os.environ['DBUS_SESSION_BUS_ADDRESS'] = f'unix:path={directory}/missing'
    app = QCoreApplication([])
    reader = SessionBusReader(enabled=True)
    if scenario in ('missing-bus', 'no-player'):
        started = time.monotonic()
        for _ in range(100):
            assert reader.read() == ()
        elapsed = time.monotonic() - started
        assert elapsed < 2.0
        (directory / 'result.json').write_text(json.dumps({'passed': True, 'polls': 100, 'seconds': elapsed}))
        assert app is not None
        return
    arguments = [sys.executable, 'tests/mpris_service.py']
    if scenario == 'unresponsive':
        arguments.append('--unresponsive')
    with subprocess.Popen(arguments, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as service:
        try:
            assert service.stdout is not None
            with selectors.DefaultSelector() as ready:
                ready.register(service.stdout, selectors.EVENT_READ)
                assert ready.select(timeout=3.0), 'mock service failed to start'
                assert service.stdout.readline().strip() == 'READY'
            started = time.monotonic()
            samples = reader.read()
            elapsed = time.monotonic() - started
            if scenario == 'unresponsive':
                assert samples == ()
                assert 0.1 <= elapsed < 1.5
            else:
                assert samples == (PlayerSample('org.mpris.MediaPlayer2.screenbot_test', Playback.PLAYING,
                                               Track('Synthetic player', 'Synthetic song', 'Synthetic artist', 'Synthetic album')),)
                assert elapsed < 1.0
            result = {'passed': True, 'seconds': elapsed,
                      'samples': [asdict(sample) for sample in samples]}
        finally:
            service.terminate()
            service.wait(timeout=3)
    assert reader.read() == ()
    (directory / 'result.json').write_text(json.dumps(result))
    assert app is not None


if __name__ == '__main__':
    run_scenario(sys.argv[1], Path(sys.argv[2]))
