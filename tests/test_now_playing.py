"""Render and privacy checks for the primary-screen now-playing card."""
from pathlib import Path
from unittest.mock import patch

import pytest
from PyQt6.QtCore import QRectF, QSizeF
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtWidgets import QApplication

from screenbot.app import Saver
from screenbot.mpris import HIDDEN, NowPlaying, Track
from screenbot.now_playing import STYLE, card_opacity, card_rect, paint_card
from screenbot.settings import CLOCK_POSITIONS
from screen_session import SceneryWindow


@pytest.fixture(scope='module')
def app() -> QApplication:
    return QApplication.instance() or QApplication([])


def configured_saver(tmp_path: Path, *, enabled: bool = True, preview: bool = False) -> Saver:
    config = tmp_path / 'media.ini'
    config.write_text('[Screensaver]\nnow_playing_enabled=' + str(enabled).lower()
                      + '\nagent_status_enabled=false\nbobos_enabled=false\nburn_in_protection=off\n')
    return Saver(config_path=config, preview=preview)


def test_default_off_and_preview_never_construct_media_reader(app: QApplication, tmp_path: Path) -> None:
    config = tmp_path / 'default.ini'
    config.write_text('[Screensaver]\nagent_status_enabled=false\n')
    with patch('screenbot.app.MprisWorker', side_effect=AssertionError('privacy boundary crossed')):
        default = Saver(config_path=config)
        preview = configured_saver(tmp_path, preview=True)
    assert not default.now_playing_enabled
    assert default.media_worker is None
    assert preview.media_worker is None
    default.close()
    preview.close()


def test_close_rejects_queued_metadata(app: QApplication, tmp_path: Path) -> None:
    saver = configured_saver(tmp_path)
    media = NowPlaying(Track('Elisa', 'Song', 'Artist'))
    saver.set_now_playing(media)
    assert saver.now_playing == media
    saver.close()
    saver.set_now_playing(media)
    assert saver.now_playing == HIDDEN


@pytest.mark.parametrize('width,height', [(390, 844), (1440, 900)])
@pytest.mark.parametrize('position', CLOCK_POSITIONS)
def test_card_fits_all_clock_positions(app: QApplication, tmp_path: Path,
                                      width: int, height: int, position: str) -> None:
    saver = configured_saver(tmp_path)
    saver.resize(width, height)
    saver.clock_position = position
    saver.show_date = True
    saver.clock_font_size = 72
    saver.live_sky_enabled = True
    saver.live_sky_conditions = True
    saver.theme = 'forest'
    rect = saver.media_card_rect()
    assert QRectF(0, 0, width, height).contains(rect)
    row = position.split('-')[0]
    clock_top = {'top': .08, 'center': .38, 'bottom': .65}[row] * height
    clock_bottom = clock_top + 72 * (1.5 + .62 * 2)
    assert rect.bottom() <= clock_top or rect.top() >= clock_bottom
    saver.close()


@pytest.mark.parametrize('reduce_motion', [False, True])
def test_pause_fade_and_reduced_motion_have_same_hidden_deadline(reduce_motion: bool) -> None:
    snapshot = NowPlaying(Track('Elisa', 'Song'), paused_at=10)
    assert card_opacity(snapshot, 11, reduce_motion) == 1
    assert card_opacity(snapshot, 12.5, reduce_motion) == (1 if reduce_motion else .5)
    assert card_opacity(snapshot, 13, reduce_motion) == 0


def test_long_unicode_and_markup_stay_inside_card(app: QApplication, tmp_path: Path) -> None:
    image = QImage(390, 180, QImage.Format.Format_ARGB32)
    image.fill(0)
    painter = QPainter(image)
    rect = card_rect(QSizeF(390, 180), None, 'center')
    paint_card(painter, rect, NowPlaying(Track('Elisa', '<b>星空の音楽 — 演奏者と夜の旅</b>' * 20, 'Artist' * 100)))
    painter.end()
    assert image.save(str(tmp_path / 'long-title.png'))
    for x, y in [(0, 0), (389, 0), (0, 179), (389, 179), (20, 160)]:
        assert image.pixelColor(x, y).alpha() == 0
    assert image.pixelColor(30, 40).alpha() > 0


@pytest.mark.parametrize('theme', ['space', 'mountains', 'snow', 'forest', 'city'])
@pytest.mark.parametrize('width,height', [(390, 844), (1440, 900)])
def test_render_card_with_every_theme(app: QApplication, tmp_path: Path, theme: str,
                                     width: int, height: int) -> None:
    saver = configured_saver(tmp_path)
    saver.resize(width, height)
    saver.theme = theme
    saver.show_date = True
    saver.set_now_playing(NowPlaying(Track('Elisa', 'A quiet night beneath the stars', 'The Night Orchestra')))
    with patch('screenbot.app.time.monotonic', return_value=saver.start_time + 2):
        assert saver.grab().save(str(tmp_path / f'{theme}-{width}.png'))
    saver.close()


def test_secondary_screen_has_no_media_card(app: QApplication, tmp_path: Path) -> None:
    saver = configured_saver(tmp_path)
    saver.resize(800, 600)
    secondary = SceneryWindow(saver)
    secondary.resize(800, 600)
    with patch('screenbot.app.time.monotonic', return_value=saver.start_time + 2):
        before = secondary.grab().toImage()
        saver.set_now_playing(NowPlaying(Track('Elisa', 'Personal music title', 'Artist')))
        after = secondary.grab().toImage()
    assert before == after
    assert after.save(str(tmp_path / 'secondary-no-media.png'))
    secondary.close()
    saver.close()
