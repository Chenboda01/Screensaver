"""Offscreen integration checks for Bob's weather accessory painter hooks."""
from __future__ import annotations

import os
from pathlib import Path
import time
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtWidgets import QApplication

from bobos import BobOSPhase, BobOSStatus
from live_sky import SkyPosition, Weather
from screenbot.app import Saver
from screenbot.weather_accessories import WeatherAccessory, WeatherPreview


@pytest.fixture(scope='module')
def app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _saver(
    tmp_path: Path,
    *,
    enabled: bool = True,
    theme: str = 'forest',
    custom_accessory: str = 'none',
    preview_weather: WeatherPreview | None = None,
    live_sky: bool = False,
) -> Saver:
    tmp_path.mkdir(parents=True, exist_ok=True)
    config = tmp_path / 'weather-settings.ini'
    config.write_text(
        '[Screensaver]\n'
        f'theme={theme}\n'
        f'bob_weather_enabled={str(enabled).lower()}\n'
        f'bob_accessory={custom_accessory}\n'
        f'live_sky_enabled={str(live_sky).lower()}\n'
        'burn_in_protection=off\n'
        'performance_mode=smooth\n',
        encoding='utf-8',
    )
    return Saver(preview=True, config_path=config, preview_weather=preview_weather)


def _bob_frame(saver: Saver, elapsed: float) -> QImage:
    image = QImage(720, 420, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    saver.bob(painter, image.width(), image.height(), elapsed,
              BobOSStatus(BobOSPhase.EXPLORING, 0.0))
    painter.end()
    return image


def _pixels(image: QImage) -> bytes:
    normalized = image.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
    bits = normalized.bits()
    return bits.asstring(normalized.sizeInBytes())


def test_forced_rain_preview_draws_umbrella_without_live_sky(
    app: QApplication,
    tmp_path: Path,
) -> None:
    # Given identical Bob renderers with accessories enabled and disabled
    enabled = _saver(tmp_path / 'enabled', preview_weather=WeatherPreview.RAIN)
    disabled = _saver(tmp_path / 'disabled', enabled=False,
                      preview_weather=WeatherPreview.RAIN)
    app.processEvents()
    enabled.weather_look(0.0)
    # When both Bob heads are rendered after the transition completes
    actual = _bob_frame(enabled, 2.0)
    baseline = _bob_frame(disabled, 2.0)
    # Then the forced preview draws an umbrella even though Live Sky is off
    assert enabled.live_sky_enabled is False
    assert enabled.weather_look(2.0)[0].accessories == (WeatherAccessory.UMBRELLA,)
    assert _pixels(actual) != _pixels(baseline)
    enabled.close()
    disabled.close()


@pytest.mark.parametrize(
    ('preview', 'expected'),
    [
        (WeatherPreview.RAIN, WeatherAccessory.UMBRELLA),
        (WeatherPreview.SNOW, WeatherAccessory.WOOL_HAT),
        (WeatherPreview.CLEAR_NOON, WeatherAccessory.SUNGLASSES),
    ],
)
def test_each_forced_weather_apparel_changes_offscreen_bob(
    app: QApplication,
    tmp_path: Path,
    preview: WeatherPreview,
    expected: WeatherAccessory,
) -> None:
    # Given a forced weather appearance and the same head without that setting
    saver = _saver(tmp_path / 'enabled', preview_weather=preview)
    baseline_saver = _saver(tmp_path / 'disabled', enabled=False, preview_weather=preview)
    app.processEvents()
    saver.weather_look(0.0)
    # When both Bob heads are rendered after the fade-in
    actual = _bob_frame(saver, 2.0)
    baseline = _bob_frame(baseline_saver, 2.0)
    look, _layers = saver.weather_look(2.0)
    # Then the selected item changes the real head raster
    assert expected in look.accessories
    assert _pixels(actual) != _pixels(baseline)
    saver.close()
    baseline_saver.close()


def test_space_preview_suppresses_weather_layer_pixels(
    app: QApplication,
    tmp_path: Path,
) -> None:
    # Given a forced snow preview in the Space theme
    saver = _saver(tmp_path, theme='space', preview_weather=WeatherPreview.SNOW)
    baseline_saver = _saver(tmp_path / 'baseline', theme='space', enabled=False)
    app.processEvents()
    # When Bob is rendered after the accessory transition window
    saver.weather_look(0.0)
    image = _bob_frame(saver, 2.0)
    baseline = _bob_frame(baseline_saver, 2.0)
    look, layers = saver.weather_look(2.0)
    # Then Space has no weather-owned headwear, scarf, or painted overlay
    assert look.accessories == ()
    assert layers == ()
    assert _pixels(image) == _pixels(baseline)
    saver.close()
    baseline_saver.close()


def test_weather_change_crossfades_between_head_local_items(
    app: QApplication,
    tmp_path: Path,
) -> None:
    # Given rain has already settled into a visible umbrella
    saver = _saver(tmp_path, preview_weather=WeatherPreview.RAIN)
    app.processEvents()
    saver.weather_look(0.0)
    saver.weather_look(2.0)
    # When the forced condition changes to snow and the transition is halfway
    saver.preview_weather_override = WeatherPreview.SNOW
    look, layers = saver.weather_look(2.0)
    assert look.accessories == (WeatherAccessory.WOOL_HAT, WeatherAccessory.SCARF)
    half_look, half_layers = saver.weather_accessory_animator.update(
        look, 2.0 + 1.15 / 2, saver.bob_appearance.accessory
    )
    # Then the old umbrella fades out as the hat and scarf fade in
    by_item = {layer.accessory: layer.opacity for layer in half_layers}
    assert half_look.accessories == look.accessories
    assert by_item[WeatherAccessory.UMBRELLA] == pytest.approx(0.5)
    assert by_item[WeatherAccessory.WOOL_HAT] == pytest.approx(0.5)
    assert by_item[WeatherAccessory.SCARF] == pytest.approx(0.5)
    saver.close()


def test_custom_cap_replaces_only_weather_headwear(
    app: QApplication,
    tmp_path: Path,
) -> None:
    # Given a user-selected cap with weather snow
    saver = _saver(tmp_path, custom_accessory='cap', preview_weather=WeatherPreview.SNOW)
    app.processEvents()
    # When the weather renderer composes its independent layer
    saver.weather_look(0.0)
    look, layers = saver.weather_look(2.0)
    # Then the custom cap remains selected while the non-conflicting scarf stacks
    assert saver.bob_appearance.accessory == 'cap'
    assert look.accessories == (WeatherAccessory.SCARF,)
    assert tuple(layer.accessory for layer in layers) == (WeatherAccessory.SCARF,)
    saver.close()


def test_time_and_weather_reactions_reach_bob_expressions_offscreen(
    app: QApplication,
    tmp_path: Path,
) -> None:
    # Given fog conditions, a lightning flash, moonrise, and deep night
    fog = _saver(tmp_path / 'fog', preview_weather=WeatherPreview.FOG)
    storm = _saver(tmp_path / 'storm', live_sky=True)
    moon = _saver(tmp_path / 'moon', live_sky=True)
    night = _saver(tmp_path / 'night', live_sky=True)
    baseline_fog = _saver(tmp_path / 'baseline-fog', enabled=False)
    baseline_storm = _saver(tmp_path / 'baseline-storm', enabled=False, live_sky=True)
    baseline_moon = _saver(tmp_path / 'baseline-moon', enabled=False, live_sky=True)
    baseline_night = _saver(tmp_path / 'baseline-night', enabled=False, live_sky=True)
    app.processEvents()
    storm.live_weather.observation = Weather(code=95, cloud=85, precipitation=2)
    storm.live_weather.observed_at = time.time()
    storm.live_sky_position = SkyPosition(10.0, 0.0, -5.0, 0.0, 0.25, False)
    storm.lightning_events = [(-2.0, 20.0, 0.5)]
    moon.live_weather.observed_at = time.time()
    moon.live_sky_position = SkyPosition(12.0, 0.0, 25.0, 0.0, 0.5, False)
    night.live_weather.observed_at = time.time()
    night.live_sky_position = SkyPosition(-25.0, 0.0, -5.0, 0.0, 0.25, False)
    # When the expressive Bob frames are rendered
    storm.weather_look(0.0)
    night.weather_look(0.0)
    fog_frame = _bob_frame(fog, 1.5)
    storm_frame = _bob_frame(storm, 2.0)
    moon_frame = _bob_frame(moon, 23.5)
    night_frame = _bob_frame(night, 2.0)
    calm_fog = _bob_frame(baseline_fog, 1.5)
    calm_storm = _bob_frame(baseline_storm, 2.0)
    calm_moon = _bob_frame(baseline_moon, 23.5)
    calm_night = _bob_frame(baseline_night, 2.0)
    fog_look, _ = fog.weather_look(1.5)
    storm_look, _ = storm.weather_look(1.0)
    moon_look, _ = moon.weather_look(23.5)
    night_look, _ = night.weather_look(1.0)
    # Then expression overrides and deep-night accessories are observable
    assert fog.weather_mood_override(BobOSStatus(BobOSPhase.EXPLORING, 0.0), 1.5) == 'squint'
    assert storm.weather_mood_override(BobOSStatus(BobOSPhase.EXPLORING, 0.0), 2.0) == 'surprised'
    assert moon.weather_mood_override(BobOSStatus(BobOSPhase.EXPLORING, 0.0), 23.5) == 'look-up'
    assert night.weather_mood_override(BobOSStatus(BobOSPhase.EXPLORING, 0.0), 2.0) == 'sleepy'
    assert WeatherAccessory.NIGHTCAP in night_look.accessories
    assert all(not frame.isNull() for frame in (fog_frame, storm_frame, moon_frame, night_frame))
    assert fog_look.accessories == ()
    assert storm_look.accessories == (WeatherAccessory.UMBRELLA,)
    assert moon_look.accessories == ()
    assert _pixels(fog_frame) != _pixels(calm_fog)
    assert _pixels(storm_frame) != _pixels(calm_storm)
    assert _pixels(moon_frame) != _pixels(calm_moon)
    assert _pixels(night_frame) != _pixels(calm_night)
    for saver in (fog, storm, moon, night, baseline_fog, baseline_storm, baseline_moon, baseline_night):
        saver.close()


def test_weather_accessory_stays_behind_bobos_phone_layer(
    app: QApplication,
    tmp_path: Path,
) -> None:
    # Given a phone activation frame with a forced weather accessory
    saver = _saver(tmp_path, preview_weather=WeatherPreview.RAIN)
    app.processEvents()
    saver.weather_look(0.0)
    order: list[str] = []
    with patch.object(saver, 'draw_weather_accessory', side_effect=lambda *_args: order.append('weather')):
        with patch.object(saver, 'draw_small_phone', side_effect=lambda *_args: order.append('phone')):
            image = QImage(720, 420, QImage.Format.Format_ARGB32_Premultiplied)
            image.fill(Qt.GlobalColor.transparent)
            painter = QPainter(image)
            saver.bob(painter, image.width(), image.height(), 2.0,
                      BobOSStatus(BobOSPhase.PHONE_ACTIVATION, 1.0))
            painter.end()
    # When Bob paints his weather and phone layers
    # Then the phone is painted last so its display remains clear
    assert order == ['weather', 'phone']
    saver.close()
