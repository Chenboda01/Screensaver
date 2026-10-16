"""Exercise the actual QWidget dispatch for every phase and preview dismissal."""
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

import pytest
from PyQt6.QtGui import QImage, QPainter

from bobos import APP_PHASES, BobOSPhase
from screenbot.settings import PHONE_UI_PHASES
from screensaver import Saver
from test_bobos_variety import application, saver


CAPTIONS = {
    BobOSPhase.CURIOUS: 'Bob spotted a new adventure!',
    BobOSPhase.PHONE_ACTIVATION: 'Bob is waking up his phone…',
    BobOSPhase.WIFI_CONNECTING: 'Connecting to fictional AI Wi-Fi…',
    BobOSPhase.BOOTING: 'BobOS 2.0 is booting…',
    BobOSPhase.ZOOM_IN: 'Opening BobOS…',
    BobOSPhase.ZOOM_OUT: "Bob is putting away Bob's Phone…",
    BobOSPhase.RETURN: 'Bob is heading back to exploring…',
    BobOSPhase.EXPLORING: 'Bob is exploring the forest…',
}


@pytest.mark.parametrize('reduced', [False, True])
def test_complete_preview_uses_runtime_dispatch_and_captions(saver: Saver, reduced: bool) -> None:
    saver.reduce_motion = reduced
    saver.burn_in_protection = 'off'
    saver.show_clock = False
    saver.show()
    saver.timer.stop()
    saver.start_time = 0
    cursor = 0.0
    previous: QImage | None = None
    seen = set()
    observations = []
    original_text = QPainter.drawText
    texts = []

    def draw_text(painter: QPainter, *args) -> None:
        texts.append(args[-1])
        original_text(painter, *args)

    sequence = (*saver.bobos_timeline.adventure_sequence, (BobOSPhase.EXPLORING, 1))
    for phase, duration in sequence:
        transition = phase not in PHONE_UI_PHASES or phase in (BobOSPhase.CAMERA, BobOSPhase.PET)
        samples = (.1, .5, .9) if transition else (.5,)
        for fraction in samples:
            elapsed = cursor + duration * fraction
            texts.clear()
            with patch('screenbot.app.time.monotonic', return_value=elapsed), \
                 patch.object(QPainter, 'drawText', draw_text), \
                 patch.object(saver, 'draw_phone_zoom', wraps=saver.draw_phone_zoom) as zoom, \
                 patch.object(saver, 'draw_phone_os', wraps=saver.draw_phone_os) as phone, \
                 patch.object(saver, 'bob', wraps=saver.bob) as bob:
                image = saver.grab().toImage()
            assert saver.bobos_status(elapsed).phase == phase
            assert not image.isNull()
            if phase in PHONE_UI_PHASES:
                phone.assert_called_once()
                bob.assert_not_called()
                zoom.assert_not_called()
            else:
                bob.assert_called_once()
                phone.assert_not_called()
                assert CAPTIONS[phase] in texts
                if phase in (BobOSPhase.ZOOM_IN, BobOSPhase.ZOOM_OUT):
                    zoom.assert_called_once()
                else:
                    zoom.assert_not_called()
                    assert 'BobOS is powering down' not in texts
            if phase == BobOSPhase.SHUTDOWN:
                assert 'BobOS is powering down' in texts
            if previous is not None:
                assert image != previous
            previous = image
            seen.add(phase)
            evidence = os.environ.get('SCREENBOT_BOBOS_RUNTIME_EVIDENCE')
            if evidence:
                target = Path(evidence) / f'runtime-{phase.value}-{fraction:g}-reduced-{reduced}.png'
                target.parent.mkdir(parents=True, exist_ok=True)
                assert image.save(str(target))
                observations.append({'phase': phase.value, 'seconds': elapsed,
                                     'path': str(target), 'text': texts.copy()})
        cursor += duration
    assert set(APP_PHASES) <= seen
    assert set(CAPTIONS) <= seen
    if evidence:
        (Path(evidence) / f'runtime-observations-reduced-{reduced}.json').write_text(
            json.dumps(observations, indent=2) + '\n', encoding='utf-8')


def test_key_dismisses_actual_preview_during_zoom(tmp_path: Path) -> None:
    config = tmp_path / 'settings.ini'
    config.write_text('[Screensaver]\ntheme=forest\n', encoding='utf-8')
    code = '''
import sys, time
from pathlib import Path
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication
from bobos import BobOSPhase
from screensaver import Saver
app = QApplication([])
saver = Saver(preview_bobos=True, config_path=Path(sys.argv[1]))
saver.show()
saver.timer.stop()
saver.start_time = time.monotonic() - 7
assert saver.bobos_status(7).phase == BobOSPhase.ZOOM_IN
state = {'timeout': False}
def timeout():
    state['timeout'] = True
    app.quit()
QTimer.singleShot(2000, timeout)
QTimer.singleShot(50, lambda: QTest.keyClick(saver, Qt.Key.Key_Escape))
app.exec()
assert not state['timeout'], 'Preview ignored dismissal input'
print('PASS: actual QApplication exited on Escape during zoom-in')
saver.close()
'''

    result = subprocess.run([sys.executable, '-c', code, str(config)], capture_output=True,
                            text=True, timeout=5, check=False)

    assert result.returncode == 0, result.stdout + result.stderr
    assert 'exited on Escape during zoom-in' in result.stdout
    evidence = os.environ.get('SCREENBOT_BOBOS_RUNTIME_EVIDENCE')
    if evidence:
        (Path(evidence) / 'dismissal.log').write_text(result.stdout + result.stderr, encoding='utf-8')
