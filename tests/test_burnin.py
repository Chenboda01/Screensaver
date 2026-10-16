"""Bounded OLED protection animation and default-off visual parity checks."""
import configparser
import math
import os
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtWidgets import QApplication

from bobos import BobOSPhase
from screensaver import (
    Saver,
    BURN_IN_SHIFT_LIMIT,
    burn_in_clock_drift,
    burn_in_dim_alpha,
    burn_in_scene_scale,
    burn_in_scene_shift,
    normalize_burn_in_mode,
)


@pytest.fixture(scope='module')
def app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_scene_shift_is_smooth_bounded_and_moves_with_elapsed_time() -> None:
    # Given a long screensaver session with five-second frame samples.
    offsets = [burn_in_scene_shift('standard', t) for t in range(0, 3601, 5)]
    # Then each axis stays within the pixel budget and changes smoothly.
    assert all(abs(axis) <= BURN_IN_SHIFT_LIMIT for offset in offsets for axis in offset)
    assert len(set(offsets)) > 100
    assert max(math.dist(before, after) for before, after in zip(offsets, offsets[1:])) < 1.0


@pytest.mark.parametrize('width,height', [(320, 200), (640, 360), (1920, 1080), (3840, 2160)])
def test_scene_overscan_covers_edges_for_every_shift(width: int, height: int) -> None:
    # Given maximum positive or negative shifts and the computed overscan scale.
    scale = burn_in_scene_scale(width, height)
    margin_x, margin_y = (scale - 1) * width / 2, (scale - 1) * height / 2
    # Then the zoom covers the largest possible shift plus rasterization slack.
    assert margin_x >= BURN_IN_SHIFT_LIMIT + 2
    assert margin_y >= BURN_IN_SHIFT_LIMIT + 2


def test_clock_drift_changes_slowly_over_time() -> None:
    # Given a centered clock whose area has room to move in every direction.
    drift = [burn_in_clock_drift('standard', t, 1280, 720, 'center-center',
                                 48, True, False) for t in range(0, 361, 60)]
    # Then the independent clock path moves over minutes while staying smooth.
    assert drift[0] == (0.0, 0.0)
    assert any(math.dist(before, after) > .5 for before, after in zip(drift, drift[1:]))
    assert all(math.dist(before, after) < 18 for before, after in zip(drift, drift[1:]))


@pytest.mark.parametrize('position', [
    'top-left', 'top-center', 'top-right', 'center-left', 'center-center',
    'center-right', 'bottom-left', 'bottom-center', 'bottom-right',
])
def test_clock_drift_remains_bounded_and_onscreen(position: str) -> None:
    # Given the nine supported alignments, maximum font, optional rows, and a
    # scene transform at each part of a long deterministic session.
    for elapsed in range(0, 4 * 60 * 60, 257):
        scene_offset = burn_in_scene_shift('strong', elapsed)
        scale = burn_in_scene_scale(1280, 720)
        dx, dy = burn_in_clock_drift('strong', elapsed, 1280, 720, position,
                                     72, True, True, scene_offset, scale)
        assert abs(dx) <= 1280 * .03
        assert abs(dy) <= 720 * .03
        x_columns = {'left': 1280 * .035, 'center': 1280 * .29, 'right': 1280 * .545}
        y_rows = {'top': 720 * .08, 'center': 720 * .38, 'bottom': 720 * .65}
        row, column = position.split('-')
        rect_x = x_columns[column] + dx
        rect_y = y_rows[row] + dy
        rect_w = 1280 * .42
        rect_h = 72 * (1.5 + .62 + .62)
        tx = 1280 * (1 - scale) / 2 + scene_offset[0]
        ty = 720 * (1 - scale) / 2 + scene_offset[1]
        assert rect_x * scale + tx >= -1e-6
        assert (rect_x + rect_w) * scale + tx <= 1280 + 1e-6
        assert rect_y * scale + ty >= -1e-6
        assert (rect_y + rect_h) * scale + ty <= 720 + 1e-6


def test_off_mode_has_no_transform_clock_drift_or_dimming() -> None:
    # Given protection explicitly switched off.
    assert burn_in_scene_shift('off', 9000) == (0.0, 0.0)
    assert burn_in_clock_drift('off', 9000, 1280, 720, 'bottom-right',
                               48, True, True) == (0.0, 0.0)
    # Then neither optional dimming mode changes its output.
    assert burn_in_dim_alpha('off', 3600) == 0
    assert burn_in_dim_alpha('standard', 3600) == 0


def test_strong_mode_fades_to_black_after_thirty_minutes() -> None:
    # Given Strong mode before, during, and after its long-idle fade.
    assert burn_in_dim_alpha('strong', 30 * 60 - 1) == 0
    alpha = burn_in_dim_alpha('strong', 45 * 60)
    assert 120 <= alpha <= 135
    assert burn_in_dim_alpha('strong', 60 * 60) == 255
    assert burn_in_dim_alpha('strong', 90 * 60) == 255


def test_burn_in_setting_defaults_to_standard_and_rejects_unknown_values(
        app: QApplication, tmp_path: Path) -> None:
    # Given a user configuration with no value, then with an invalid value.
    config = tmp_path / 'screenbot.ini'
    config.write_text('[Screensaver]\ntheme=forest\nbobos_enabled=false\n', encoding='utf-8')
    saver = Saver(config_path=config)
    assert saver.burn_in_protection == 'standard'
    saver.close()
    config.write_text('[Screensaver]\ntheme=forest\nburn_in_protection=unknown\nbobos_enabled=false\n', encoding='utf-8')
    saver = Saver(config_path=config)
    # Then unsupported values safely return to the Standard default.
    assert saver.burn_in_protection == normalize_burn_in_mode('unknown') == 'standard'
    saver.close()


def test_off_rendering_matches_the_unshifted_reference(app: QApplication, tmp_path: Path) -> None:
    # Given a deterministic scene with protection explicitly Off.
    config = configparser.ConfigParser()
    config['Screensaver'] = {
        'theme': 'forest', 'burn_in_protection': 'off', 'show_clock': 'true',
        'show_date': 'true', 'clock_position': 'bottom-right', 'clock_font_size': '24',
        'bob_phone_enabled': 'false', 'bobos_enabled': 'false', 'live_sky_enabled': 'false',
    }
    config_path = tmp_path / 'off.ini'
    with config_path.open('w', encoding='utf-8') as output:
        config.write(output)
    saver = Saver(config_path=config_path)
    saver.resize(640, 360)
    saver.show()
    app.processEvents()
    saver.start_time = 97.0

    # Render through the production paintEvent with a fixed elapsed time.
    actual = QImage(640, 360, QImage.Format.Format_ARGB32_Premultiplied)
    actual.fill(Qt.GlobalColor.transparent)
    with patch('screensaver.time.monotonic', return_value=100.0):
        saver.render(actual)

    # Render the pre-protection V22 sequence: no transforms, unshifted clock,
    # and the same scene/Bob layers at the same timestamp.
    expected = QImage(640, 360, QImage.Format.Format_ARGB32_Premultiplied)
    expected.fill(Qt.GlobalColor.transparent)
    painter = QPainter(expected)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    elapsed = 3.0
    saver.draw_scenery(painter, 640, 360, elapsed)
    saver.clock(painter, 640, 360)
    status = saver.bobos_status(elapsed)
    phase = status.phase
    if phase not in {BobOSPhase.HOME, BobOSPhase.BROWSER, BobOSPhase.NOTIFICATION,
                     BobOSPhase.FILES, BobOSPhase.TERMINAL, BobOSPhase.GAMES,
                     BobOSPhase.SETTINGS, BobOSPhase.CHAT, BobOSPhase.MAPS,
                     BobOSPhase.WEATHER, BobOSPhase.CALENDAR, BobOSPhase.APP_STORE,
                     BobOSPhase.SHUTDOWN}:
        saver.bob(painter, 640, 360, elapsed, status)
        saver.caption(painter, 640, 360, elapsed, phase)
    painter.end()
    assert actual == expected
    saver.close()


def test_user_input_closes_screensaver_during_strong_fade(app: QApplication,
                                                          tmp_path: Path) -> None:
    # Given Strong mode has fully faded the scene to black.
    config = tmp_path / 'strong.ini'
    config.write_text('[Screensaver]\ntheme=forest\nburn_in_protection=strong\nbobos_enabled=false\n',
                      encoding='utf-8')
    saver = Saver(config_path=config)
    saver.start_time -= 60 * 60
    assert burn_in_dim_alpha(saver.burn_in_protection, 60 * 60) == 255
    # When any key is pressed, the existing screensaver input path exits.
    with patch('screensaver.QApplication.quit') as quit_app:
        saver.keyPressEvent(None)
    # Then the fade is dismissed along with the screensaver.
    quit_app.assert_called_once()
    saver.close()
