"""A fixed, test-only Qt font environment for portable raster baselines."""
import os
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ['QT_FONT_DPI'] = '96'
os.environ['FONTCONFIG_FILE'] = str(Path(__file__).parent / 'fonts' / 'fonts.conf')

import pytest
from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtWidgets import QApplication


@pytest.fixture(scope='session', autouse=True)
def fixed_test_fonts():
    app = QApplication.instance() or QApplication([])
    for name in ('DejaVuSans.ttf', 'DejaVuSans-Bold.ttf'):
        font_id = QFontDatabase.addApplicationFont(str(Path(__file__).parent / 'fonts' / name))
        assert font_id >= 0, f'Could not load bundled test font {name}'
    QFont.insertSubstitution('Sans Serif', 'DejaVu Sans')
    app.setFont(QFont('DejaVu Sans', 10))
    yield app
