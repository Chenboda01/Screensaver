"""Selected coordinates and V22 location migration through the real Qt adapter."""
import configparser
import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from PyQt6.QtCore import QObject
from PyQt6.QtNetwork import QNetworkReply
from PyQt6.QtWidgets import QApplication

from live_sky_network import LiveWeather


@pytest.fixture(scope='module')
def application():
    return QApplication.instance() or QApplication([])


def test_selected_springfield_coordinates_skip_geocoding(application, tmp_path: Path):
    # Given: Missouri was selected, even though the same city name exists elsewhere.
    parent = QObject()
    weather = LiveWeather(parent, enabled=False,
                          location='Springfield, Missouri, United States',
                          coordinates=(37.21, -93.29), timezone_name='America/Chicago',
                          cache_path=tmp_path / 'weather.json')
    weather.enabled = True
    # When: weather refreshes.
    with patch.object(weather, '_request') as request:
        weather.refresh()
    # Then: the forecast uses the selected coordinates without another lookup.
    url, geocoding = request.call_args.args
    assert not geocoding
    assert 'latitude=37.2100&longitude=-93.2900' in url
    assert weather.timezone_name == 'America/Chicago'


def test_invalid_coordinates_do_not_enable_unknown_location(application, tmp_path: Path):
    # Given: corrupt coordinates for a place that is not a legacy catalog entry.
    parent = QObject()
    weather = LiveWeather(parent, enabled=False, location='Unknown',
                          coordinates=(float('nan'), 2), cache_path=tmp_path / 'weather.json')
    weather.enabled = True
    # When: refresh is attempted.
    with patch.object(weather, '_request') as request:
        weather.refresh()
    # Then: no weather is requested at fabricated default coordinates.
    request.assert_not_called()
    assert not weather.located


def test_legacy_resolution_persists_coordinates_and_unrelated_settings(application, tmp_path: Path):
    # Given: a V22 settings file with a catalog location and an unrelated preference.
    config_path = tmp_path / 'settings.ini'
    config_path.write_text('[Screensaver]\nlive_sky_location=Paris, France\nclock_format=24h\n')
    parent = QObject()
    weather = LiveWeather(parent, enabled=False, location='Paris, France',
                          config_path=config_path, cache_path=tmp_path / 'weather.json')
    reply = Mock()
    reply.error.return_value = QNetworkReply.NetworkError.NoError
    reply.readAll.return_value = json.dumps({'results': [
        {'name': 'Paris', 'country': 'France', 'latitude': 48.85,
         'longitude': 2.35, 'timezone': 'Europe/Paris'}]}).encode()
    # When: the first successful geocoding reply arrives.
    with patch.object(weather, '_forecast'):
        weather._finished(reply, True)
    # Then: future launches can use coordinates and all unrelated preferences survive.
    config = configparser.ConfigParser()
    config.read(config_path)
    assert config.getfloat('Screensaver', 'live_sky_latitude') == 48.85
    assert config.getfloat('Screensaver', 'live_sky_longitude') == 2.35
    assert config.get('Screensaver', 'live_sky_timezone') == 'Europe/Paris'
    assert config.get('Screensaver', 'clock_format') == '24h'


def test_legacy_migration_does_not_overwrite_a_new_selection(application, tmp_path: Path):
    # Given: Settings changed the location while the old lookup was in flight.
    config_path = tmp_path / 'settings.ini'
    original = '[Screensaver]\nlive_sky_location=Boston, Massachusetts, United States\n'
    config_path.write_text(original)
    parent = QObject()
    weather = LiveWeather(parent, enabled=False, location='Paris, France',
                          config_path=config_path, cache_path=tmp_path / 'weather.json')
    weather.latitude, weather.longitude = 48.85, 2.35
    # When: the stale lookup attempts its migration.
    weather._persist_coordinates()
    # Then: the newer selection is untouched.
    assert config_path.read_text() == original


@pytest.mark.parametrize('encoded', ['Paris, France', '"Paris, France"'])
def test_city_ini_quoting_is_read_consistently(application, tmp_path: Path, encoded: str):
    # Given: either a hand-written INI city or the quoted form emitted by KDE.
    from PyQt6.QtCore import QSettings
    from live_sky_network import read_location_setting
    config_path = tmp_path / 'settings.ini'
    config_path.write_text(f'[Screensaver]\nlive_sky_location={encoded}\n')
    # When: loading the location through the shared boundary reader.
    name = read_location_setting(QSettings(str(config_path), QSettings.Format.IniFormat))
    # Then: both produce the catalog name, without literal quotes or a stringified list.
    assert name == 'Paris, France'
