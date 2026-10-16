# /// script
# requires-python = ">=3.10"
# dependencies = ["PyQt6"]
# ///
# ─── How to run ───
# bash tests/test_idle_trigger_wayland.sh (installs this observer in its sandbox)
"""Observe the installed renderer's first frame and exit through its key handler."""
import json
import os
from pathlib import Path
import time

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QShowEvent
from PyQt6.QtTest import QTest

import screenbot_real_entry as screensaver


class CaptureSaver(screensaver.Saver):
    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        QTimer.singleShot(300, self.capture)

    def capture(self) -> None:
        evidence = Path(os.environ['SCREENBOT_IDLE_EVIDENCE'])
        assert self.grab().save(str(evidence / 'idle-started-screenbot.png'))
        with (evidence / 'frames.jsonl').open('a') as output:
            output.write(json.dumps({
                'monotonic': time.monotonic(), 'fullscreen': self.isFullScreen(),
                'theme': self.theme, 'preview': self.is_preview,
                'password_lock': self.password_lock,
                'display': self.screen().name(),
            }) + '\n')
        QTest.keyClick(self, Qt.Key.Key_Escape)


screensaver.Saver = CaptureSaver
raise SystemExit(screensaver.main())
