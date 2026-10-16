"""Orbital lighting, offline lunar phase, cache and real Space scene regressions."""
import configparser
from collections.abc import Iterator
from datetime import datetime, timezone
import math
import os
from pathlib import Path
from unittest.mock import patch

import pytest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PyQt6.QtCore import QObject, Qt
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtWidgets import QApplication

from live_sky import Weather, sky_position
from live_sky_network import LiveWeather
from live_sky_render import SpaceSky, earth_phase
from screensaver import Saver


@pytest.fixture(scope='module', autouse=True)
def app() -> Iterator[QApplication]:
    application = QApplication.instance() or QApplication([])
    yield application


def timestamp(value: str) -> float:
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc).timestamp()


def orbital_frame(now: float, coordinates: tuple[float, float] | None) -> QImage:
    image = QImage(1000, 1000, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.black)
    painter = QPainter(image)
    SpaceSky().draw(painter, 1000, 1000, now, coordinates)
    painter.end()
    return image


@pytest.mark.parametrize(('when', 'coordinates', 'lower', 'upper'), [
    ('2026-03-20T12:00', (0., 0.), .99, 1.),
    ('2026-03-20T00:00', (0., 0.), 0., .01),
    ('2026-03-20T06:00', (0., 0.), .47, .53),
    ('2026-06-21T16:45', (42.36, -71.06), .96, .99),
    ('2026-06-21T04:45', (42.36, -71.06), .28, .31),
    ('2026-06-21T00:00', (89., 0.), .65, .75),
    ('2026-12-21T12:00', (89., 0.), .25, .35),
])
def test_local_terminator_at_known_times(when: str, coordinates: tuple[float, float],
                                       lower: float, upper: float) -> None:
    # Given known equinox, Boston solstice, and polar day/night times.
    sky = sky_position(datetime.fromtimestamp(timestamp(when), timezone.utc), *coordinates)
    # When local sun altitude is projected onto the Earth disc.
    phase = earth_phase(sky.sun_altitude, sky.morning)
    illuminated = (1-math.cos(phase*math.tau))/2
    # Then the visible day-side fraction matches the expected independent range.
    assert lower <= illuminated <= upper


def test_earth_pixels_change_from_day_to_night_with_city_lights() -> None:
    # Given the same equatorial observer at equinox noon and midnight.
    noon = timestamp('2026-03-20T12:00')
    midnight = timestamp('2026-03-20T00:00')
    # When rendering the real cached scene.
    day = orbital_frame(noon, (0., 0.))
    night = orbital_frame(midnight, (0., 0.))
    # Then the center is blue by day and dark at night, with warm city lights.
    assert day.pixelColor(190, 430).blue() > 100
    assert night.pixelColor(190, 430).blue() < 60
    def city_lights(image: QImage) -> int:
        return sum(image.pixelColor(x, y).red() > 160 and image.pixelColor(x, y).blue() < 140
                   for x in range(95, 285) for y in range(335, 525))
    assert city_lights(night) > 40
    assert city_lights(day) == 0


def test_moon_phase_remains_visible_without_location() -> None:
    # Given known full, new, and three-day crescent dates and no location.
    dates = ('2024-03-25T07:00', '2024-04-08T18:00', '2024-04-11T18:00')
    # When rendering Moon sprites (center 400, 322; radius 36).
    frames = [orbital_frame(timestamp(date), None) for date in dates]
    bright_pixels = [sum(image.pixelColor(x, y).lightness() > 130
                        for x in range(364, 437) for y in range(286, 359)) for image in frames]
    # Then full > crescent > new; the new Moon still has a visible dark disc/outline.
    full, new, crescent = bright_pixels
    assert full > 3500
    assert new < 30
    assert 150 < crescent < 700
    assert frames[1].pixelColor(400, 322).lightness() > 0


def test_unknown_location_keeps_earth_neutral_across_dates() -> None:
    # Given no coordinates, including while geocoding is unavailable.
    dates = ('2026-03-20T12:00', '2026-03-20T00:00')
    # When the same Earth is rendered at two very different local times.
    frames = [orbital_frame(timestamp(date), None) for date in dates]
    # Then Earth remains neutral half-lit instead of using the equator as a location.
    assert frames[0].copy(60, 300, 260, 260) == frames[1].copy(60, 300, 260, 260)
    assert frames[0].pixelColor(130, 430).blue() < 60
    assert frames[0].pixelColor(250, 430).blue() > 80


def test_moon_does_not_disappear_below_local_horizon() -> None:
    # Given a full Moon above one observer and below the opposite observer.
    instant = timestamp('2024-03-25T07:00')
    positions = [(40., -74.), (-40., 106.)]
    altitudes = [sky_position(datetime.fromtimestamp(instant, timezone.utc), *point).moon_altitude
                 for point in positions]
    assert altitudes[0] > 0 > altitudes[1]
    # When drawing the orbital Moon at both places.
    frames = [orbital_frame(instant, point) for point in positions]
    # Then the Moon pixels remain the same regardless of the terrestrial horizon.
    assert frames[0].copy(360, 282, 80, 80) == frames[1].copy(360, 282, 80, 80)


def test_cached_location_keeps_local_earth_when_offline(tmp_path: Path) -> None:
    # Given saved coordinates with expired weather and no network refresh.
    parent = QObject()
    cache = tmp_path / 'sky.json'
    controller = LiveWeather(parent, enabled=False, location='Paris, France', cache_path=cache)
    controller.latitude, controller.longitude, controller.located = 48.85, 2.35, True
    controller._save()
    restored = LiveWeather(parent, enabled=False, location='Paris, France', cache_path=cache)
    restored._load()
    # When drawing using restored coordinates, without any weather observation.
    frame = orbital_frame(timestamp('2026-06-21T12:00'), (restored.latitude, restored.longitude))
    # Then the local Earth is lit and Moon present, despite stale/absent weather.
    assert restored.located and not restored.fresh
    assert frame.pixelColor(190, 430).blue() > 100
    assert frame.pixelColor(400, 322).lightness() > 0


def test_cache_reused_between_minutes_and_invalidated_on_location_and_size() -> None:
    # Given one orbital painter and a fixed minute.
    scene = SpaceSky()
    image = QImage(1000, 1000, QImage.Format.Format_ARGB32)
    painter = QPainter(image)
    start = timestamp('2026-03-20T06:00')
    # When rendering many frames and then crossing each invalidation boundary.
    with patch('live_sky_render.sky_position', wraps=sky_position) as astronomy:
        for second in range(60):
            scene.draw(painter, 1000, 1000, start+second, None)
        assert astronomy.call_count == 1
        scene.draw(painter, 1000, 1000, start+60, None)
        scene.draw(painter, 1000, 1000, start+60, (0., 0.))
        scene.draw(painter, 800, 800, start+60, (0., 0.))
        # Then geometry is rebuilt exactly once per changed input, not per frame.
        assert astronomy.call_count == 4
    painter.end()


@pytest.mark.parametrize('live', ['true', 'false'])
def test_space_frames_ignore_weather_and_manual_overlays(live: str) -> None:
    # Given every atmospheric toggle enabled in the real Saver.
    settings = configparser.ConfigParser()
    settings['Screensaver'] = {'theme': 'space', 'live_sky_enabled': live,
        'rain_enabled': 'true', 'snow_enabled': 'true', 'fog_enabled': 'true',
        'thunderstorms_enabled': 'true', 'shooting_stars_enabled': 'true'}
    with patch('screensaver.read_settings', return_value=settings), patch.object(LiveWeather, 'refresh'):
        saver = Saver()
    saver.timer.stop()
    saver.resize(1000, 1000)
    saver.show()
    frames = []
    # When drawing clear and severe weather through the production scene/effects paths.
    with patch('screensaver.time.time', return_value=timestamp('2024-03-25T07:00')):
        for weather in (Weather(), Weather(95, 100, 20, 90, -20)):
            saver.live_weather.observation = weather
            saver.live_weather.observed_at = timestamp('2024-03-25T07:00')
            image = QImage(1000, 1000, QImage.Format.Format_ARGB32)
            painter = QPainter(image)
            saver.space(painter, 1000, 1000, 5)
            saver.weather(painter, 1000, 1000, 5)
            painter.end()
            frames.append(image)
    # Then Space is pixel-identical regardless of all weather data and toggles.
    assert frames[0] == frames[1]
    saver.close()
    saver.deleteLater()


def test_random_space_uses_live_sky_and_preserves_foreground_phone() -> None:
    # Given Random selects Space and a BobOS phone preview overlays it.
    settings = configparser.ConfigParser()
    settings['Screensaver'] = {'theme': 'random', 'live_sky_enabled': 'true', 'show_clock': 'false'}
    with patch('screensaver.read_settings', return_value=settings), patch('screensaver.random.choice', return_value='space'), patch.object(LiveWeather, 'refresh'):
        saver = Saver(preview_bobos=True)
    saver.timer.stop()
    saver.resize(1000, 1000)
    # When the real QWidget paints its phone stage.
    image = QImage(1000, 1000, QImage.Format.Format_ARGB32)
    with patch('screensaver.time.monotonic', return_value=saver.start_time+20):
        saver.render(image)
    # Then Space location resolution is enabled and phone content occludes the backdrop.
    assert saver.live_weather.enabled
    assert not saver.space_sky._image.isNull()
    phone = QImage(1000, 1000, QImage.Format.Format_ARGB32)
    phone.fill(Qt.GlobalColor.transparent)
    painter = QPainter(phone)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    saver.draw_phone_os(painter, 1000, 1000, saver.bobos_status(20), 20)
    painter.end()
    assert image.copy(100, 100, 800, 800) == phone.copy(100, 100, 800, 800)
    saver.close()
    saver.deleteLater()
