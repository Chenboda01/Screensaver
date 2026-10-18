# /// script
# requires-python = ">=3.10"
# dependencies = ["PyQt6"]
# ///
# How to run: QT_QPA_PLATFORM=offscreen python tests/release_zip_preview.py INSTALL_DIR OUTPUT.png
from pathlib import Path
import sys

from PyQt6.QtWidgets import QApplication

installed = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(installed))
import screensaver

assert Path(screensaver.__file__).parent == installed
app = QApplication([])
saver = screensaver.Saver(preview=True)
assert saver.is_preview and not saver.password_lock
saver.resize(960, 540)
saver.show()
app.processEvents()
assert saver.grab().save(sys.argv[2])
saver.close()
print('PASS extracted ZIP installed preview rendered without password lock')
