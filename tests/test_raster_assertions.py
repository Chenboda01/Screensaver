"""Ensure raster slack tolerates rounding, never geometry or missing content."""
from pathlib import Path

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QImage, QPainter

from raster_assertions import assert_raster_equal


def frame(offset: int = 0) -> QImage:
    image = QImage(640, 360, QImage.Format.Format_ARGB32)
    image.fill(QColor('#102030'))
    painter = QPainter(image)
    painter.setPen(Qt.GlobalColor.white)
    painter.setFont(QFont('Sans Serif', 24))
    painter.drawText(400 + offset, 300, '12:34 PM')
    painter.end()
    return image


def test_clock_moved_ten_pixels_fails_and_saves_images(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv('SCREENBOT_RASTER_ARTIFACTS', str(tmp_path))
    with pytest.raises(AssertionError, match='clock-shift'):
        assert_raster_equal(frame(10), frame(), 'clock-shift')
    for suffix in ('actual', 'expected', 'diff'):
        image = QImage(str(tmp_path / f'clock-shift-{suffix}.png'))
        assert not image.isNull() and image.size() == frame().size()


def test_tolerance_is_bounded_in_area_and_channel(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv('SCREENBOT_RASTER_ARTIFACTS', str(tmp_path))
    expected = frame()
    actual = expected.copy()
    actual.setPixelColor(0, 0, QColor('#202030'))  # one channel changes by 16
    assert_raster_equal(actual, expected, 'rounding')
    with pytest.raises(AssertionError):
        assert_raster_equal(actual, expected, 'exact', exact=True)
    actual.setPixelColor(0, 0, QColor('#212030'))
    with pytest.raises(AssertionError):
        assert_raster_equal(actual, expected, 'large-channel')
    actual = expected.copy()
    for y in range(4):
        for x in range(640):
            actual.setPixelColor(x, y, QColor('#112030'))
    with pytest.raises(AssertionError):
        assert_raster_equal(actual, expected, 'large-area')
