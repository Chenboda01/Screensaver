"""Offscreen integration checks for the animated local photo theme."""
from __future__ import annotations

import configparser
import os
from pathlib import Path
import time
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PIL import Image, ImageDraw
from PyQt6.QtCore import Qt, QRectF, QSize
from PyQt6.QtGui import QColor, QImage, QPainter
from PyQt6.QtWidgets import QApplication, QWidget

from screenbot.photo_slideshow import CROSSFADE_SECONDS, PhotoSlideshowRenderer
from screenbot.settings import selected_theme
from screensaver import Saver

_APPLICATION: QApplication | None = None

def _app() -> QApplication:
    global _APPLICATION
    if QApplication.instance() is None:
        _APPLICATION = QApplication([])
    return QApplication.instance()


def _wait(predicate, timeout: float = 4.0) -> None:
    app = _app()
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        app.processEvents()
        if predicate():
            return
        time.sleep(.005)
    assert predicate(), 'photo slideshow did not complete its asynchronous operation'


def _photo(path: Path, color: tuple[int, int, int]) -> None:
    image = Image.new('RGB', (120, 80), color)
    draw = ImageDraw.Draw(image)
    for x in range(0, 120, 12):
        draw.line((x, 0, 119 - x, 79), fill=(255 - color[0], 255 - color[1], 255 - color[2]), width=2)
    image.save(path)


def _portrait(path: Path, color: tuple[int, int, int]) -> None:
    image = Image.new('RGB', (80, 120), color)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 79, 12), fill=(255 - color[0], 255 - color[1], 255 - color[2]))
    image.save(path)


def _checker_portrait(path: Path) -> None:
    image = Image.new('RGB', (80, 120))
    draw = ImageDraw.Draw(image)
    for y in range(0, 120, 2):
        for x in range(0, 80, 2):
            color = (245, 245, 245) if (x // 2 + y // 2) % 2 else (15, 15, 15)
            draw.rectangle((x, y, x + 1, y + 1), fill=color)
    image.save(path)


class FakeClock:
    def __init__(self) -> None:
        self.value = 100.0

    def __call__(self) -> float:
        return self.value


class RenderOwner(QWidget):
    def _draw_photo_fallback_landscape(self, painter: QPainter, width: int,
                                       height: int, _elapsed: float) -> None:
        painter.fillRect(QRectF(0, 0, width, height), QColor('#253b58'))


def _frame(renderer: PhotoSlideshowRenderer, width: int = 120, height: int = 80) -> QImage:
    image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.black)
    painter = QPainter(image)
    renderer.draw(painter, width, height, 0.)
    painter.end()
    return image


def test_theme_can_be_explicitly_selected_but_is_not_in_random() -> None:
    settings = configparser.ConfigParser()
    settings['Screensaver'] = {'theme': 'photos'}
    assert selected_theme(settings) == 'photos'
    settings['Screensaver']['theme'] = 'random'
    assert selected_theme(settings) != 'photos'


def test_local_photo_slideshow_pans_crossfades_and_wraps_in_order(tmp_path: Path) -> None:
    _app()
    _photo(tmp_path / 'a-red.png', (230, 20, 30))
    _photo(tmp_path / 'b-blue.png', (20, 40, 230))
    owner = RenderOwner()
    clock = FakeClock()
    slideshow = PhotoSlideshowRenderer(
        owner, folder=tmp_path, include_subfolders=False,
        interval_seconds=5, order='name', fit='fill', enabled=True, clock=clock,
    )
    # Drawing starts image requests only after the viewport is known.
    _frame(slideshow)
    _wait(lambda: len(slideshow.paths) == 2)
    _frame(slideshow)
    _wait(lambda: slideshow._current_image is not None and slideshow._next_image is not None)
    assert [path.name for path in slideshow.paths] == ['a-red.png', 'b-blue.png']

    first = _frame(slideshow)
    clock.value += .8
    panned = _frame(slideshow)
    assert first != panned

    clock.value = 104.0
    crossfade = _frame(slideshow)
    center = crossfade.pixelColor(60, 40)
    assert center.red() > 40 and center.blue() > 40
    assert slideshow._current_path is not None and slideshow._current_path.name == 'a-red.png'

    clock.value = 105.0 + CROSSFADE_SECONDS
    wrapped = _frame(slideshow)
    assert slideshow._current_path is not None and slideshow._current_path.name == 'b-blue.png'
    colors = [wrapped.pixelColor(x, y) for x in range(10, 120, 11) for y in range(10, 80, 9)]
    assert sum(color.blue() for color in colors) > sum(color.red() for color in colors)
    assert slideshow.library.cached_image_count <= 3
    slideshow.close()
    owner.close()


def test_fit_whole_photo_mode_uses_local_blurred_backdrop(tmp_path: Path) -> None:
    _app()
    _portrait(tmp_path / 'portrait.png', (90, 180, 230))
    owner = RenderOwner()
    slideshow = PhotoSlideshowRenderer(
        owner, folder=tmp_path, include_subfolders=False,
        interval_seconds=15, order='name', fit='fit-blur', enabled=True,
        clock=lambda: 1.0,
    )
    _wait(lambda: len(slideshow.paths) == 1)
    frame = _frame(slideshow, 180, 120)
    _wait(lambda: slideshow._current_image is not None)
    frame = _frame(slideshow, 180, 120)
    assert not frame.isNull()
    assert frame.pixelColor(2, 2) != frame.pixelColor(90, 60)
    # The complete portrait remains centered and uncut through the interval.
    assert frame.pixelColor(90, 0) != frame.pixelColor(2, 0)
    assert frame.pixelColor(90, 119) != frame.pixelColor(2, 119)
    clock = FakeClock()
    slideshow.clock = clock
    start = _frame(slideshow, 180, 120)
    clock.value += 15
    end = _frame(slideshow, 180, 120)
    assert start == end
    assert len(slideshow._blurred_backdrops) <= 2
    slideshow.close()
    owner.close()


def test_fit_blur_backdrop_smooths_high_frequency_detail(tmp_path: Path) -> None:
    _app()
    _checker_portrait(tmp_path / 'checker.png')
    owner = RenderOwner()
    slideshow = PhotoSlideshowRenderer(
        owner, folder=tmp_path, include_subfolders=False,
        interval_seconds=15, order='name', fit='fit-blur', enabled=True,
    )
    _wait(lambda: len(slideshow.paths) == 1)
    image = QImage(str(tmp_path / 'checker.png'))
    raw = image.scaled(QSize(180, 120), Qt.AspectRatioMode.IgnoreAspectRatio,
                       Qt.TransformationMode.SmoothTransformation)
    blurred = slideshow._blurred_backdrop(image, 180, 120)

    def variation(frame: QImage) -> int:
        return sum(abs(frame.pixelColor(x, 60).red() - frame.pixelColor(x + 1, 60).red())
                   for x in range(179))

    assert variation(blurred) < variation(raw) // 4
    slideshow.close()
    owner.close()


def test_unreadable_photo_is_skipped_and_missing_folder_has_friendly_fallback(tmp_path: Path) -> None:
    _app()
    (tmp_path / 'a-broken.jpg').write_bytes(b'not a real photo')
    _photo(tmp_path / 'b-good.png', (25, 140, 80))
    owner = RenderOwner()
    slideshow = PhotoSlideshowRenderer(
        owner, folder=tmp_path, include_subfolders=False,
        interval_seconds=15, order='name', fit='fill', enabled=True,
    )
    _frame(slideshow)
    _wait(lambda: len(slideshow.paths) == 2)
    _frame(slideshow)
    _wait(lambda: slideshow._current_image is not None)
    assert slideshow._current_path is not None
    assert slideshow._current_path.name == 'b-good.png'
    slideshow.close()
    owner.close()

    missing = tmp_path / 'removed-folder'
    empty_settings = configparser.ConfigParser()
    empty_settings['Screensaver'] = {'theme': 'photos', 'photo_folder': str(missing)}
    with patch('screenbot.app.read_settings', return_value=empty_settings):
        saver = Saver(preview=True)
    saver.resize(320, 180)
    _wait(lambda: saver.photo_slideshow.message == 'No photos found in this folder.')
    image = QImage(320, 180, QImage.Format.Format_ARGB32_Premultiplied)
    painter = QPainter(image)
    saver.photo_slideshow.draw(painter, 320, 180, 0.)
    painter.end()
    assert not image.isNull()
    assert saver.photo_slideshow.message == 'No photos found in this folder.'
    top_text_pixels = sum(
        1 for y in range(10, 90) for x in range(45, 275)
        if image.pixelColor(x, y).red() > 200
        and image.pixelColor(x, y).green() > 200
        and image.pixelColor(x, y).blue() > 200
    )
    center_text_pixels = sum(
        1 for y in range(100, 170) for x in range(45, 275)
        if image.pixelColor(x, y).red() > 200
        and image.pixelColor(x, y).green() > 200
        and image.pixelColor(x, y).blue() > 200
    )
    assert top_text_pixels > 0
    assert center_text_pixels == 0
    saver.photo_slideshow.close()
    saver.close()


def test_saver_composes_bob_clock_and_weather_above_photo_layer(tmp_path: Path) -> None:
    _app()
    _photo(tmp_path / 'scene.png', (25, 45, 140))
    settings = configparser.ConfigParser()
    settings['Screensaver'] = {
        'theme': 'photos', 'photo_folder': str(tmp_path), 'show_clock': 'true',
        'rain_enabled': 'true', 'bobos_enabled': 'false',
    }
    with patch('screenbot.app.read_settings', return_value=settings):
        saver = Saver(preview=True)
    saver.resize(640, 360)
    _wait(lambda: saver.photo_slideshow is not None and len(saver.photo_slideshow.paths) == 1)
    _frame(saver.photo_slideshow, 640, 360)
    _wait(lambda: saver.photo_slideshow is not None and saver.photo_slideshow._current_image is not None)
    frame = QImage(640, 360, QImage.Format.Format_ARGB32_Premultiplied)
    saver.render(frame)
    assert frame.pixelColor(0, 0).blue() > frame.pixelColor(0, 0).red()
    unique = set()
    for y in range(0, 360, 12):
        for x in range(0, 640, 12):
            unique.add(frame.pixelColor(x, y).rgba())
    assert len(unique) > 20  # Bob, clock, and rain remain above the photo layer.
    saver.close()
