"""Exact raster baselines for the five scenes and the BobOS home display."""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest
from PyQt6.QtCore import QDateTime, Qt
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtWidgets import QApplication

from bobos import BobOSPhase, BobOSStatus
from screenbot.appearance import BobAppearance
from screensaver import Saver

GOLDEN_DIR = Path(__file__).parent / 'golden_rendering'
SCENES = ('space', 'mountains', 'snow', 'forest', 'city')
WIDTH = 640
HEIGHT = 360
ELAPSED = 17.25


@pytest.fixture(scope='module')
def app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _renderer(tmp_path: Path) -> Saver:
    config = tmp_path / 'golden-settings.ini'
    config.write_text(
        '[Screensaver]\ntheme=space\nburn_in_protection=off\n'
        'performance_mode=smooth\nlive_sky_enabled=false\n'
        'rain_enabled=false\nsnow_enabled=false\nthunderstorms_enabled=false\n'
        'fog_enabled=false\nshooting_stars_enabled=false\n',
        encoding='utf-8',
    )
    saver = Saver(preview=True, config_path=config)
    saver.particles = [
        (index / 111, (index * 17 % 101) / 101, 1.25, index * .11)
        for index in range(110)
    ]
    return saver


def _scene_frame(saver: Saver, theme: str) -> QImage:
    saver.theme = theme
    saver._scenery_cache = None
    saver._scenery_cache_key = None
    image = QImage(WIDTH, HEIGHT, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    saver.draw_scenery(painter, WIDTH, HEIGHT, ELAPSED)
    saver.bob(painter, WIDTH, HEIGHT, ELAPSED, BobOSStatus(BobOSPhase.EXPLORING, 0.0))
    saver.caption(painter, WIDTH, HEIGHT, ELAPSED, BobOSPhase.EXPLORING)
    painter.end()
    return image


def _bobos_frame(saver: Saver) -> QImage:
    image = QImage(900, 520, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    fixed_clock = QDateTime.fromString('2026-10-16T12:34:00', Qt.DateFormat.ISODate)
    with patch.object(QDateTime, 'currentDateTime', return_value=fixed_clock):
        saver.draw_phone_os(painter, 900, 520, BobOSStatus(BobOSPhase.HOME, 4.0), ELAPSED)
    painter.end()
    return image


def _frames(tmp_path: Path) -> dict[str, QImage]:
    saver = _renderer(tmp_path)
    frames = {f'{theme}.png': _scene_frame(saver, theme) for theme in SCENES}
    frames['bobos-home.png'] = _bobos_frame(saver)
    saver.close()
    return frames


def _pixels(image: QImage) -> bytes:
    normalized = image.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
    pixel_buffer = normalized.bits()
    return pixel_buffer.asstring(normalized.sizeInBytes())


def test_scenes_and_bobos_match_golden_rasters(tmp_path: Path, app: QApplication) -> None:
    del app
    actual = _frames(tmp_path)
    if os.environ.get('SCREENBOT_UPDATE_GOLDENS') == '1':
        GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
        for name, image in actual.items():
            assert image.save(str(GOLDEN_DIR / name)), f'failed writing {name}'
        return

    assert {path.name for path in GOLDEN_DIR.glob('*.png')} == set(actual)
    for name, image in actual.items():
        expected = QImage(str(GOLDEN_DIR / name))
        assert not expected.isNull(), f'missing or unreadable baseline {name}'
        assert expected.size() == image.size(), f'baseline dimensions changed for {name}'
        assert _pixels(image) == _pixels(expected), f'pixels changed from baseline: {name}'


def test_custom_bob_palette_renders_across_all_themes_and_bobos(tmp_path: Path, app: QApplication) -> None:
    del app
    original = _renderer(tmp_path)
    custom = _renderer(tmp_path)
    custom.bob_appearance = BobAppearance(color_preset='purple')
    for theme in SCENES:
        assert _pixels(_scene_frame(original, theme)) != _pixels(_scene_frame(custom, theme))
    assert _pixels(_bobos_frame(original)) != _pixels(_bobos_frame(custom))
    original.close()
    custom.close()
