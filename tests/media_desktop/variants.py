# /// script
# requires-python = ">=3.11"
# dependencies = ["PyQt6"]
# ///
# Run through tests/test_media_desktop.sh on its private virtual Wayland display.
"""Capture production card layouts and motion states on an isolated desktop."""
import json
import os
from pathlib import Path
import time

from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication
from screenbot.app import Saver
from screenbot.mpris import NowPlaying, Track
from screenbot.now_playing import card_opacity
from screenbot.settings import CLOCK_POSITIONS

assert os.environ['XDG_RUNTIME_DIR'].startswith('/tmp/screenbot-media-')
assert os.environ['DBUS_SYSTEM_BUS_ADDRESS'] == os.environ['DBUS_SESSION_BUS_ADDRESS']
EVIDENCE = Path(os.environ['SCREENBOT_MEDIA_EVIDENCE']) / ('variants-200' if os.environ.get('QT_SCALE_FACTOR') == '2' else 'variants-100')
EVIDENCE.mkdir()
APP = QApplication([])
CONFIG = EVIDENCE / 'settings.ini'
CONFIG.write_text('[Screensaver]\nnow_playing_enabled=true\nagent_status_enabled=false\n'
                  'bobos_enabled=false\nburn_in_protection=off\ntheme=forest\nshow_date=true\n')
TRACK = Track('Elisa', 'A quiet night beneath the stars — 星空の音楽', 'The Night Orchestra')
receipts = []


def capture(saver: Saver, label: str) -> None:
    saver.update()
    QTest.qWait(150)
    image = saver.grab()
    assert image.save(str(EVIDENCE / f'{label}.png'))
    rect = saver.media_card_rect()
    receipts.append({'card_bounds': [rect.x(), rect.y(), rect.width(), rect.height()],
                     'card_visible': not rect.isEmpty(), 'label': label, 'width': image.width(), 'height': image.height(),
                     'device_pixel_ratio': image.devicePixelRatio(), 'clock': saver.show_clock,
                     'clock_position': saver.clock_position, 'reduce_motion': saver.reduce_motion,
                     'opacity': card_opacity(saver.now_playing, time.monotonic(), saver.reduce_motion),
                     'title': saver.now_playing.track.title if saver.now_playing.track else None})


sizes = [(390, 422), (700, 460)] if os.environ.get('QT_SCALE_FACTOR') == '2' else [(390, 844), (1200, 840)]
for width, height in sizes:
    saver = Saver(config_path=CONFIG)
    saver.resize(width, height)
    saver.set_now_playing(NowPlaying(TRACK))
    saver.show()
    QTest.qWait(150)
    for position in CLOCK_POSITIONS:
        saver.clock_position = position
        capture(saver, f'clock-{position}-{width}')
    saver.show_clock = False
    capture(saver, f'no-clock-{width}')
    saver.close()

saver = Saver(config_path=CONFIG)
saver.resize(*sizes[-1])
saver.show_clock = False
saver.show()
saver.reduce_motion = True
saver.set_now_playing(NowPlaying(TRACK, paused_at=time.monotonic() - 2.0))
capture(saver, 'reduced-motion-before-hide')
assert receipts[-1]['opacity'] == 1
QTest.qWait(1050)
capture(saver, 'reduced-motion-hidden')
assert receipts[-1]['opacity'] == 0
saver.reduce_motion = False
saver.set_now_playing(NowPlaying(TRACK, paused_at=time.monotonic() - 2.1))
capture(saver, 'interrupt-before-resume')
assert 0 < receipts[-1]['opacity'] < 1
saver.set_now_playing(NowPlaying(Track('Elisa', 'Resumed: a new adventure', 'The Night Orchestra')))
capture(saver, 'interrupt-resumed')
assert receipts[-1]['opacity'] == 1
QTest.qWait(1000)
capture(saver, 'interrupt-after-old-deadline')
assert receipts[-1]['opacity'] == 1
saver.close()
(EVIDENCE / 'receipts.json').write_text(json.dumps({'passed': True, 'frames': receipts}, indent=2))
print(f'PASS {len(receipts)} rendered layout/motion frames at scale {os.environ.get("QT_SCALE_FACTOR", "1")}')
