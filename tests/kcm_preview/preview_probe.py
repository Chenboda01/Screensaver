"""Launch the real preview and record its first frame before sending a key."""
import configparser
import json
import os
from pathlib import Path
import sys
import time

from PyQt6.QtCore import QPoint, QTimer, Qt
from PyQt6.QtTest import QTest

sys.path.insert(0, os.environ['SCREENBOT_SOURCE'])
import screensaver

started = time.monotonic()
evidence = Path(os.environ['SCREENBOT_PREVIEW_EVIDENCE'])
config_path = Path(sys.argv[sys.argv.index('--config') + 1])
config = configparser.ConfigParser()
config.read(config_path)


class Probe(screensaver.Saver):
    """Only the evidence observer differs from the production preview."""
    def showEvent(self, event) -> None:
        super().showEvent(event)
        QTimer.singleShot(100, self.capture)

    def capture(self) -> None:
        filename = 'kcm-bobos-preview.png' if self.preview_bobos else 'kcm-launched-preview.png'
        assert self.grab().save(str(evidence / filename))
        receipt = {
            'executable': sys.executable,
            'config': dict(config['Screensaver']),
            'temporary_path': str(config_path),
            'theme': self.theme,
            'full_screen': self.isFullScreen(),
            'screen_name': self.screen().name(),
            'password_lock': self.password_lock,
            'show_timer': self.show_timer,
            'bobos_enabled': self.bobos_enabled,
            'first_frame_seconds': time.monotonic() - started,
            'clock_position': self.clock_position,
            'live_sky_enabled': self.live_sky_enabled,
        }
        with (evidence / 'launches.jsonl').open('a') as output:
            output.write(json.dumps(receipt) + '\n')
        if os.environ.get('SCREENBOT_PREVIEW_INPUT') == 'mouse':
            QTimer.singleShot(1600, self.move_to_anchor)
        else:
            QTest.keyClick(self, Qt.Key.Key_A)

    def move_to_anchor(self) -> None:
        QTest.mouseMove(self, QPoint(50, 50))
        QTimer.singleShot(100, lambda: QTest.mouseMove(self, QPoint(100, 100)))


screensaver.Saver = Probe
raise SystemExit(screensaver.main())
