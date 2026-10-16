"""Offline astronomy, weather cache safety and real Qt render regression cases."""
import configparser
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject
from PyQt6.QtGui import QImage, QPainter
from live_sky import SkyPosition, Weather, parse_weather, sky_position, sun_phase
from live_sky_network import LiveWeather, location_options, resolve_location
from live_sky_render import draw_sky
from screensaver import Saver


class AstronomyTests(unittest.TestCase):
    def test_equinox_equator_noon_and_midnight(self):
        noon = sky_position(datetime(2026, 3, 20, 12, tzinfo=timezone.utc), 0, 0)
        night = sky_position(datetime(2026, 3, 20, 0, tzinfo=timezone.utc), 0, 0)
        self.assertGreater(noon.sun_altitude, 85)
        self.assertLess(night.sun_altitude, -85)

    def test_polar_seasons_need_no_sunrise(self):
        summer = sky_position(datetime(2026, 6, 21, 0, tzinfo=timezone.utc), 89, 0)
        winter = sky_position(datetime(2026, 12, 21, 12, tzinfo=timezone.utc), 89, 0)
        self.assertGreater(summer.sun_altitude, 20)
        self.assertLess(winter.sun_altitude, -20)

    def test_known_full_and_new_moon(self):
        full = sky_position(datetime(2024, 3, 25, 7, tzinfo=timezone.utc), 40, -74)
        new = sky_position(datetime(2024, 4, 8, 18, tzinfo=timezone.utc), 40, -74)
        self.assertAlmostEqual(full.moon_phase, .5, delta=.03)
        self.assertLess(min(new.moon_phase, 1-new.moon_phase), .03)
        self.assertGreater(full.moon_altitude, 0)

    def test_phase_boundaries(self):
        self.assertEqual(sun_phase(-20, True), 'night')
        self.assertEqual(sun_phase(-10, True), 'twilight')
        self.assertEqual(sun_phase(0, True), 'sunrise')
        self.assertEqual(sun_phase(0, False), 'sunset')
        self.assertEqual(sun_phase(30, False), 'day')

    def test_timezone_same_instant(self):
        from zoneinfo import ZoneInfo
        utc = datetime(2026, 11, 1, 6, 30, tzinfo=timezone.utc)
        self.assertEqual(sky_position(utc, 40, -74), sky_position(utc.astimezone(ZoneInfo('America/New_York')), 40, -74))


class WeatherTests(unittest.TestCase):
    def test_wmo_groups_and_intensity(self):
        for code, expected in [(0,'clear'), (2,'cloudy'), (3,'overcast'), (45,'fog'), (51,'rain'), (65,'rain'), (81,'rain'), (73,'snow'), (86,'snow'), (95,'thunderstorm'), (97,'thunderstorm'), (64,'rain')]:
            with self.subTest(code=code): self.assertEqual(Weather(code=code).category, expected)
        self.assertLess(Weather(precipitation=.2).intensity, Weather(precipitation=8).intensity)
        self.assertEqual(Weather(code=10, cloud=100).category, 'overcast')

    def test_invalid_payloads_are_rejected(self):
        for value in [float('nan'), float('inf'), -1, 101]:
            with self.assertRaises(ValueError):
                parse_weather({'current': {'weather_code': 0, 'cloud_cover': value, 'precipitation': 0, 'wind_speed_10m': 0, 'temperature_2m': 5}})


class QtSkyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_disabled_mode_never_requests(self):
        controller = LiveWeather(QObject(), enabled=False, location='Kabul, Afghanistan', interval=15)
        with patch.object(controller, '_request') as request:
            controller.refresh()
            request.assert_not_called()

    def test_cache_reuse_expiry_and_attempt_rate_limit(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'cache.json'
            parent = QObject()
            first = LiveWeather(parent, enabled=False, location='Paris, France', interval=30, cache_path=path)
            first.observation = Weather(65, 100, 8, 15, 12)
            first.observed_at = time.time()
            first.attempted_at = time.time()
            first._save()
            second = LiveWeather(parent, enabled=False, location='Paris, France', interval=30, cache_path=path)
            second._load()
            self.assertEqual(second.weather.category, 'rain')
            second.enabled = True
            with patch.object(second, '_request') as request:
                second.refresh()
                request.assert_not_called()
            second.observed_at -= 10801
            self.assertEqual(second.weather.category, 'clear')
            self.assertFalse(second.fresh)
            path.write_text('{corrupt')
            second._load()
            self.assertFalse(second.fresh)

    def test_cache_permissions_future_data_and_location_isolation(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'cache.json'
            parent = QObject()
            controller = LiveWeather(parent, enabled=False, location='Paris, France', interval=15, cache_path=path)
            controller.observation = Weather(65, 100, 8, 15, 12)
            controller.observed_at = time.time()
            controller.attempted_at = time.time()
            controller._save()
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            path.chmod(0o644)
            controller._load()
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            other = LiveWeather(parent, enabled=False, location='Lyon, France', interval=15, cache_path=path)
            other._load()
            self.assertFalse(other.fresh)
            data = json.loads(path.read_text())
            data['observed_at'] = time.time()+3600
            path.write_text(json.dumps(data))
            controller.observed_at = 0
            controller._load()
            self.assertFalse(controller.fresh)

    def test_empty_location_default_coordinates_do_not_request_weather(self):
        parent = QObject()
        controller = LiveWeather(parent, enabled=False, location='')
        controller.enabled = True
        self.assertFalse(controller.located)
        with patch.object(controller, '_request') as request:
            controller.refresh()
            request.assert_not_called()
        self.assertEqual(controller.attempted_at, 0.)

    def test_catalog_and_country_specific_geocoding(self):
        catalog = location_options()
        self.assertEqual(len(catalog), 896)
        self.assertIn('Kabul, Afghanistan', catalog)
        self.assertIn('New York City, United States of America', catalog)
        payload = {'results': [
            {'name': 'Paris', 'country': 'United States', 'latitude': 33.66, 'longitude': -95.55},
            {'name': 'Paris', 'country': 'France', 'latitude': 48.85, 'longitude': 2.35}]}
        self.assertEqual(resolve_location(payload, 'Paris, France'), (48.85, 2.35))
        self.assertIsNone(resolve_location(payload, 'Paris, Japan'))
        self.assertEqual(resolve_location(payload, 'Paris, United States of America'), (33.66, -95.55))
        self.assertIsNone(resolve_location({'results': [{'country': 'France', 'latitude': float('nan'), 'longitude': 2}]}, 'Paris, France'))

    def test_selected_city_geocodes_then_requests_forecast_without_ip_service(self):
        from PyQt6.QtNetwork import QNetworkReply
        from unittest.mock import Mock
        with tempfile.TemporaryDirectory() as folder:
            parent = QObject()
            controller = LiveWeather(parent, enabled=False, location='Paris, France', cache_path=Path(folder)/'cache.json')
            controller.enabled = True
            with patch.object(controller, '_request') as request:
                controller.refresh()
                url, is_location = request.call_args.args
                self.assertTrue(is_location)
                self.assertTrue(url.startswith('https://geocoding-api.open-meteo.com/v1/search?'))
                self.assertIn('name=Paris', url)
                reply = Mock()
                reply.error.return_value = QNetworkReply.NetworkError.NoError
                reply.readAll.return_value = json.dumps({'results': [{'country': 'France', 'latitude': 48.85, 'longitude': 2.35}]}).encode()
                controller._finished(reply, True)
                self.assertTrue(controller.located)
                url, is_location = request.call_args.args
                self.assertFalse(is_location)
                self.assertIn('latitude=48.8500&longitude=2.3500', url)
                self.assertTrue(url.startswith('https://api.open-meteo.com/'))
            restored = LiveWeather(parent, enabled=False, location='Paris, France', cache_path=Path(folder)/'cache.json')
            restored._load()
            self.assertTrue(restored.located)
            self.assertEqual(restored.latitude, 48.85)
            self.assertEqual(restored.longitude, 2.35)
            invalid = LiveWeather(parent, enabled=False, location='Imaginary, Nowhere', cache_path=Path(folder)/'cache.json')
            invalid.enabled = True
            with patch.object(invalid, '_request') as request:
                invalid.refresh()
                request.assert_not_called()

    def test_async_request_returns_without_waiting_for_network(self):
        parent = QObject()
        controller = LiveWeather(parent, enabled=False, location='Paris, France', interval=30)
        start = time.monotonic()
        controller._request('http://127.0.0.1:1/unreachable', False)
        self.assertLess(time.monotonic()-start, .5)
        deadline = time.monotonic()+2
        while controller.busy and time.monotonic() < deadline:
            self.app.processEvents()
        self.assertFalse(controller.busy)
        self.assertFalse(controller.fresh)

    def test_sky_pixels_move_clouds_and_preserve_horizon_rules(self):
        def frame(sky, weather, t):
            image = QImage(640, 360, QImage.Format.Format_ARGB32)
            painter = QPainter(image)
            draw_sky(painter, 640, 360, t, sky, weather)
            painter.end()
            return image
        sky = SkyPosition(-30, 0, 45, 180, .5, False)
        night = frame(sky, Weather(), 0)
        below = frame(SkyPosition(-30, 0, -10, 180, .5, False), Weather(), 0)
        self.assertNotEqual(night, below)
        self.assertNotEqual(frame(sky, Weather(2, 60), 0), frame(sky, Weather(2, 60), 20))
        self.assertEqual(frame(sky, Weather(3,100), 0), frame(SkyPosition(-30,0,-10,180,.5,False),Weather(3,100),0))

    def test_all_landscapes_render_and_manual_settings_survive(self):
        for theme in ('mountains', 'forest', 'snow', 'city', 'space', 'aurora', 'ocean', 'desert', 'underwater'):
            settings = configparser.ConfigParser()
            settings['Screensaver'] = {'theme': theme, 'live_sky_enabled': 'true', 'rain_enabled': 'true'}
            with patch('screenbot.app.read_settings', return_value=settings), patch.object(LiveWeather, 'refresh'):
                saver = Saver()
                saver.resize(640,360)
                image = QImage(640,360,QImage.Format.Format_ARGB32)
                saver.render(image)
                self.assertFalse(image.isNull())
                self.assertTrue(saver.rain_enabled)
                if theme == 'space': self.assertTrue(saver.live_weather.enabled)
                saver.close()
                saver.deleteLater()

    def test_space_theme_suppresses_every_weather_and_shooting_star_effect(self):
        for live_sky in ('false', 'true'):
            settings = configparser.ConfigParser()
            settings['Screensaver'] = {
                'theme': 'space', 'live_sky_enabled': live_sky,
                'rain_enabled': 'true', 'snow_enabled': 'true',
                'thunderstorms_enabled': 'true', 'fog_enabled': 'true',
                'shooting_stars_enabled': 'true',
            }
            with self.subTest(live_sky=live_sky), \
                 patch('screenbot.app.read_settings', return_value=settings), \
                 patch.object(LiveWeather, 'refresh'):
                saver = Saver()
                image = QImage(640, 360, QImage.Format.Format_ARGB32)
                painter = QPainter(image)
                with patch.object(saver, 'draw_rain') as rain, \
                     patch.object(saver, 'draw_snowfall') as snow, \
                     patch.object(saver, 'draw_thunderstorms') as thunder, \
                     patch.object(saver, 'draw_fog') as fog, \
                     patch.object(saver, 'draw_shooting_stars') as shooting_stars:
                    saver.weather(painter, 640, 360, 1.0)
                    rain.assert_not_called()
                    snow.assert_not_called()
                    thunder.assert_not_called()
                    fog.assert_not_called()
                    shooting_stars.assert_not_called()
                painter.end()
                saver.close()
                saver.deleteLater()

    def test_manual_shooting_stars_remain_available_on_landscapes(self):
        settings = configparser.ConfigParser()
        settings['Screensaver'] = {
            'theme': 'forest', 'live_sky_enabled': 'false',
            'shooting_stars_enabled': 'true',
        }
        with patch('screenbot.app.read_settings', return_value=settings), \
             patch.object(LiveWeather, 'refresh'):
            saver = Saver()
            image = QImage(640, 360, QImage.Format.Format_ARGB32)
            painter = QPainter(image)
            with patch.object(saver, 'draw_shooting_stars') as shooting_stars:
                saver.weather(painter, 640, 360, 1.0)
                shooting_stars.assert_called_once_with(painter, 640, 360, 1.0)
            painter.end()
            saver.close()
            saver.deleteLater()
