"""Offscreen pixel checks for the unregistered issue #22 theme modules."""
from __future__ import annotations

import os
from collections.abc import Callable

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtWidgets import QApplication

from live_sky import SkyPosition, Weather
from screenbot.themes import aurora, desert, ocean, underwater
from screenbot.themes.environment import ThemeEnvironment, ThemeFrame

WIDTH = 640
HEIGHT = 360
NIGHT_NEW_MOON = SkyPosition(-35.0, 15.0, 25.0, 210.0, 0.0, False)
DAY_SKY = SkyPosition(42.0, 110.0, -5.0, 0.0, 0.5, True)


@pytest.fixture(scope="module")
def app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _frame(environment: ThemeEnvironment, elapsed: float = 12.0, motion_scale: float = 1.0) -> ThemeFrame:
    return ThemeFrame(WIDTH, HEIGHT, elapsed, environment, motion_scale)


def _render_layers(
        background: Callable[[QPainter, ThemeFrame], None],
        motion: Callable[[QPainter, ThemeFrame], None], frame: ThemeFrame) -> QImage:
    image = QImage(WIDTH, HEIGHT, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    try:
        background(painter, frame)
        motion(painter, frame)
    finally:
        painter.end()
    return image


def _pixels(image: QImage) -> bytes:
    normalized = image.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
    return normalized.bits().asstring(normalized.sizeInBytes())


def _ink_pixels(image: QImage) -> int:
    return sum(1 for y in range(image.height()) for x in range(image.width())
               if image.pixelColor(x, y).alpha() > 0)


def test_aurora_strength_requires_dark_sky_and_fades_with_clouds_and_full_moon(app: QApplication) -> None:
    del app
    # Given day, clear night, cloudy night, and full-moon night snapshots.
    day = ThemeEnvironment(True, DAY_SKY, Weather())
    clear = ThemeEnvironment(True, NIGHT_NEW_MOON, Weather())
    cloudy = ThemeEnvironment(True, NIGHT_NEW_MOON, Weather(cloud=100.0))
    full_moon = ThemeEnvironment(
        True, SkyPosition(-35.0, 15.0, 25.0, 210.0, .5, False), Weather())
    # When visibility is resolved from each snapshot.
    strengths = [aurora.aurora_strength(condition) for condition in (day, clear, cloudy, full_moon)]
    # Then daylight hides Aurora; clear night wins over clouds and full moon.
    assert strengths[0] == 0.0
    assert strengths[1] > strengths[2] > 0.0
    assert strengths[1] > strengths[3] > 0.0


def test_aurora_motion_is_pixel_visible_at_night_and_absent_in_daylight(app: QApplication) -> None:
    del app
    # Given identical transparent layers and clear Live Sky at night or day.
    night = QImage(WIDTH, HEIGHT, QImage.Format.Format_ARGB32_Premultiplied)
    day = QImage(WIDTH, HEIGHT, QImage.Format.Format_ARGB32_Premultiplied)
    night.fill(Qt.GlobalColor.transparent)
    day.fill(Qt.GlobalColor.transparent)
    # When Aurora motion is drawn for each sky state.
    for image, environment in ((night, ThemeEnvironment(True, NIGHT_NEW_MOON, Weather())),
                                (day, ThemeEnvironment(True, DAY_SKY, Weather()))):
        painter = QPainter(image)
        try:
            aurora.draw_motion(painter, _frame(environment))
        finally:
            painter.end()
    # Then the night produces pixels while day leaves the layer fully transparent.
    assert _ink_pixels(night) > 0
    assert _ink_pixels(day) == 0


def test_new_theme_backgrounds_are_deterministic_and_render_pixels(app: QApplication) -> None:
    del app
    # Given four modules with the same fixed local-night snapshot.
    environment = ThemeEnvironment(True, NIGHT_NEW_MOON, Weather(0, 8.0, 0.0, 6.0, 4.0))
    themes = (aurora, ocean, desert, underwater)
    # When every static and animated layer is rendered twice at the same time.
    frames = [_render_layers(theme.draw_background, theme.draw_motion, _frame(environment)) for theme in themes]
    repeats = [_render_layers(theme.draw_background, theme.draw_motion, _frame(environment)) for theme in themes]
    # Then all scenes contain visible pixels, repeat exactly, and remain distinct.
    assert all(_ink_pixels(frame) > WIDTH * HEIGHT // 2 for frame in frames)
    assert all(_pixels(frame) == _pixels(repeated) for frame, repeated in zip(frames, repeats, strict=True))
    assert len({_pixels(frame) for frame in frames}) == len(themes)


def test_new_theme_motion_obeys_zero_effect_budget(app: QApplication) -> None:
    del app
    # Given each new theme and a frame with motion disabled.
    environment = ThemeEnvironment(True, NIGHT_NEW_MOON, Weather(63, 20, 5, 10, 12))
    frame = _frame(environment, motion_scale=0.0)
    for theme in (aurora, ocean, desert, underwater):
        image = QImage(WIDTH, HEIGHT, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        try:
            # When the motion layer receives a zero effect budget.
            theme.draw_motion(painter, frame)
        finally:
            painter.end()
        # Then no animated layer contributes pixels.
        assert _ink_pixels(image) == 0, theme.__name__


def test_ocean_waves_and_desert_shimmer_change_without_rebuilding_the_scene(app: QApplication) -> None:
    del app
    # Given fixed scenes and motion inputs at two elapsed times.
    environment = ThemeEnvironment(True, DAY_SKY, Weather(0, 8.0, 0.0, 24.0, 28.0))
    first = {
        "ocean": _render_layers(ocean.draw_background, ocean.draw_motion, _frame(environment, 1.0)),
        "desert": _render_layers(desert.draw_background, desert.draw_motion, _frame(environment, 1.0)),
    }
    later = {
        "ocean": _render_layers(ocean.draw_background, ocean.draw_motion, _frame(environment, 9.0)),
        "desert": _render_layers(desert.draw_background, desert.draw_motion, _frame(environment, 9.0)),
    }
    # Then both animated scenes have changed visible pixels.
    assert _pixels(first["ocean"]) != _pixels(later["ocean"])
    assert _pixels(first["desert"]) != _pixels(later["desert"])


@pytest.mark.parametrize("weather", [Weather(63, 20, 5, 10, 12), Weather(73, 20, 5, 10, -4)])
def test_underwater_precipitation_is_confined_to_surface_ripples(
        app: QApplication, weather: Weather) -> None:
    del app
    # Given a transparent frame and rain weather with a fixed elapsed time.
    image = QImage(WIDTH, HEIGHT, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    try:
        # When precipitation is rendered by the underwater-specific layer.
        underwater.draw_surface_ripples(
            painter, _frame(ThemeEnvironment(True, NIGHT_NEW_MOON, weather), 3.0))
    finally:
        painter.end()
    # Then visible weather pixels are confined to the top surface band.
    occupied_y = [y for y in range(HEIGHT) for x in range(WIDTH) if image.pixelColor(x, y).alpha() > 0]
    assert occupied_y
    assert max(occupied_y) < HEIGHT * .08


def test_underwater_manual_precipitation_uses_surface_ripples(app: QApplication) -> None:
    del app
    # Given a manual weather preference while Live Sky is disabled.
    image = QImage(WIDTH, HEIGHT, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    try:
        # When the underwater surface layer receives manual precipitation state.
        frame = _frame(ThemeEnvironment(manual_surface_precipitation=True), 4.0)
        underwater.draw_surface_ripples(painter, frame)
    finally:
        painter.end()
    # Then it draws ripples and leaves the lower water free of falling particles.
    occupied_y = [y for y in range(HEIGHT) for x in range(WIDTH) if image.pixelColor(x, y).alpha() > 0]
    assert occupied_y
    assert max(occupied_y) < HEIGHT * .08


def test_underwater_bubbles_jellyfish_and_diving_helmet_are_visible(app: QApplication) -> None:
    del app
    # Given a night water scene and a transparent frame.
    image = QImage(WIDTH, HEIGHT, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    try:
        # When its animated life and optional Bob helmet are drawn.
        underwater.draw_motion(painter, _frame(ThemeEnvironment(True, NIGHT_NEW_MOON, Weather()), 7.0))
        underwater.draw_bob_diving_helmet(painter, QPointF(WIDTH * .5, HEIGHT * .55), 46.0)
    finally:
        painter.end()
    # Then the scene contains visible ocean-life and helmet pixels.
    assert _ink_pixels(image) > 0


def test_production_compositor_keeps_clock_bob_and_bobos_available_in_each_theme(
        app: QApplication, tmp_path) -> None:
    from bobos import BobOSPhase, BobOSStatus
    from screensaver import Saver

    del app
    # Given each new theme using the production Saver and phone renderer.
    config = tmp_path / 'theme-settings.ini'
    config.write_text('[Screensaver]\ntheme=aurora\nlive_sky_enabled=false\n')
    saver = Saver(preview=True, config_path=config)
    for theme in ('aurora', 'ocean', 'desert', 'underwater'):
        saver.theme = theme
        image = QImage(WIDTH, HEIGHT, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        try:
            # When scenery, customizable clock, floating Bob, and fictional BobOS are composited.
            saver.draw_scenery(painter, WIDTH, HEIGHT, 12.0)
            saver.clock(painter, WIDTH, HEIGHT)
            saver.bob(painter, WIDTH, HEIGHT, 12.0, BobOSStatus(BobOSPhase.EXPLORING, 0.0))
            saver.draw_phone_os(painter, WIDTH, HEIGHT, BobOSStatus(BobOSPhase.HOME, 4.0), 12.0)
        finally:
            painter.end()
        # Then the complete themed frame remains renderable.
        assert _ink_pixels(image) > WIDTH * HEIGHT // 2, theme
    saver.close()


@pytest.mark.parametrize("live", [False, True])
def test_underwater_weather_dispatch_uses_only_the_surface_layer(tmp_path, live: bool) -> None:
    from unittest.mock import patch

    from PyQt6.QtGui import QImage, QPainter

    from screensaver import Saver

    # Given the production underwater compositor with manual or Live Sky precipitation.
    config = tmp_path / f"underwater-{live}.ini"
    config.write_text(
        "[Screensaver]\ntheme=underwater\nlive_sky_enabled=" + str(live).lower()
        + "\nrain_enabled=true\nsnow_enabled=true\nthunderstorms_enabled=true\n"
    )
    saver = Saver(preview=True, config_path=config)
    saver.live_weather.located = True
    saver.live_weather.observation = Weather(63, 20.0, 5.0, 10.0, 12.0)
    image = QImage(WIDTH, HEIGHT, QImage.Format.Format_ARGB32_Premultiplied)
    painter = QPainter(image)
    try:
        # When the ordinary weather hook handles precipitation for this selected theme.
        with patch("screenbot.themes.underwater.draw_surface_ripples") as ripples, \
                patch.object(saver, "draw_rain") as rain, \
                patch.object(saver, "draw_snowfall") as snowfall, \
                patch.object(saver, "draw_thunderstorms") as thunder, \
                patch.object(saver, "draw_fog") as fog:
            saver.weather(painter, WIDTH, HEIGHT, 8.0)
        # Then the ripple module receives the same scene snapshot, and falling effects stay off.
        ripples.assert_called_once()
        assert ripples.call_args.args[1].environment.live_sky_enabled is live
        rain.assert_not_called()
        snowfall.assert_not_called()
        thunder.assert_not_called()
        fog.assert_not_called()
    finally:
        painter.end()
        saver.close()
