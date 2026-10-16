"""Opt-in Qt asynchronous weather fetches, bounded requests and disk cache."""
import json
import math
from pathlib import Path
import time
import tempfile
import os
import unicodedata
from urllib.parse import urlencode

from PyQt6.QtCore import QObject, QTimer, QUrl
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from live_sky import Weather, parse_weather


def location_options() -> frozenset[str]:
    """Read the shipped country/city catalog without any network access."""
    try:
        lines = Path(__file__).with_name('countries_and_cities.txt').read_text(encoding='utf-8').splitlines()
    except OSError:
        return frozenset()
    return frozenset(f'{city.strip()}, {country.strip()}'
                     for line in lines if ',' in line
                     for country, city in [line.split(',', 1)] if country.strip() and city.strip())


def _country_key(value: str) -> str:
    normalized = ''.join(letter for letter in unicodedata.normalize('NFKD', value.casefold())
                         if letter.isascii() and letter.isalnum())
    aliases = {
        'unitedstatesofamerica': 'unitedstates', 'usa': 'unitedstates',
        'cotedivoire': 'ivorycoast', 'czechrepublic': 'czechia',
        'caboverde': 'capeverde', 'republicofthecongo': 'congobrazzaville',
        'congo': 'congobrazzaville', 'democraticrepublicofthecongo': 'congokinshasa',
        'drcongo': 'congokinshasa', 'drc': 'congokinshasa',
        'easttimor': 'timorleste', 'swaziland': 'eswatini', 'turkiye': 'turkey',
        'federatedstatesofmicronesia': 'micronesia', 'vatican': 'vaticancity',
        'holysee': 'vaticancity', 'palestinianterritory': 'palestine',
        'stateofpalestine': 'palestine', 'republicofkorea': 'southkorea',
        'democraticpeoplesrepublicofkorea': 'northkorea',
    }
    return aliases.get(normalized, normalized)


def resolve_location(payload: dict, selected: str) -> tuple[float, float] | None:
    """Never substitute a same-name city in another country."""
    country = selected.rsplit(', ', 1)[-1]
    results = payload.get('results', [])
    if not isinstance(results, list): return None
    for result in results:
        if not isinstance(result, dict) or not isinstance(result.get('country'), str): continue
        if _country_key(result['country']) != _country_key(country): continue
        try:
            latitude, longitude = float(result['latitude']), float(result['longitude'])
        except (KeyError, ValueError, TypeError):
            continue
        if math.isfinite(latitude) and math.isfinite(longitude) and -90 <= latitude <= 90 and -180 <= longitude <= 180:
            return latitude, longitude
    return None


class LiveWeather(QObject):
    """Mutable Qt controller; owns replies and caches successful observations."""
    def __init__(self, parent: QObject, *, enabled: bool,
                 interval: int = 30,
                 location: str = '', cache_path: Path | None = None):
        super().__init__(parent)
        self.enabled = enabled
        self.location = location.strip()
        self.latitude = 0.
        self.longitude = 0.
        self.valid_location = bool(self.location) and self.location in location_options()
        self.located = False
        self.interval = interval if interval in (15, 30, 60) else 30
        self.cache_path = cache_path or Path.home()/'.cache/screenbot/live-sky.json'
        self.key = f'city:{self.location}' if self.location else 'city:unset'
        self.observation = Weather()
        self.observed_at = 0.
        self.attempted_at = 0.
        self.busy = False
        self.manager = QNetworkAccessManager(self)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        if enabled:
            self._load()
            self.timer.start(60000)
            QTimer.singleShot(0, self.refresh)

    @property
    def fresh(self) -> bool:
        return 0 <= time.time()-self.observed_at < 10800

    @property
    def weather(self) -> Weather:
        return self.observation if self.fresh else Weather()

    def _load(self) -> None:
        try:
            if self.cache_path.is_symlink() or self.cache_path.stat().st_size > 16384: return
            self.cache_path.chmod(0o600)
            data = json.loads(self.cache_path.read_text())
            if data['key'] != self.key: return
            attempted = float(data['attempted_at'])
            observed = float(data['observed_at'])
            now = time.time()
            if not math.isfinite(attempted) or not math.isfinite(observed): return
            if not (0 <= attempted <= now and 0 <= observed <= now): return
            self.attempted_at = attempted
            weather = data.get('weather')
            if weather:
                self.observation = parse_weather({'current': weather})
                self.observed_at = observed
            if self.location and data.get('located'):
                lat, lon = float(data['latitude']), float(data['longitude'])
                if math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180:
                    self.latitude, self.longitude, self.located = lat, lon, True
        except (OSError, ValueError, TypeError, KeyError):
            self.observed_at = 0.

    def _save(self) -> None:
        weather = self.observation
        data = {'key': self.key, 'attempted_at': self.attempted_at,
                'observed_at': self.observed_at, 'located': self.located,
                'latitude': self.latitude, 'longitude': self.longitude,
                'weather': {'weather_code': weather.code, 'cloud_cover': weather.cloud,
                            'precipitation': weather.precipitation, 'wind_speed_10m': weather.wind,
                            'temperature_2m': weather.temperature} if self.observed_at else None}
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            temporary_name = None
            try:
                with tempfile.NamedTemporaryFile(mode='w', dir=self.cache_path.parent, prefix='.live-sky-', delete=False) as temporary:
                    temporary_name = temporary.name
                    json.dump(data, temporary)
                os.replace(temporary_name, self.cache_path)
                temporary_name = None
            finally:
                if temporary_name is not None:
                    Path(temporary_name).unlink(missing_ok=True)
        except OSError:
            # Read-only cache directories must not prevent the decorative sky.
            self.cache_error = True

    def refresh(self) -> None:
        elapsed = time.time()-self.attempted_at
        if not self.enabled or not self.valid_location or self.busy or 0 <= elapsed < self.interval*60: return
        self.attempted_at = time.time()
        self._save()
        if self.location and not self.located:
            query = urlencode({'name': self.location,
                               'count': 100, 'language': 'en', 'format': 'json'})
            self._request('https://geocoding-api.open-meteo.com/v1/search?' + query, True)
        else:
            self._forecast()

    def _forecast(self) -> None:
        if not self.located:
            return
        url = ('https://api.open-meteo.com/v1/forecast?'
               f'latitude={self.latitude:.4f}&longitude={self.longitude:.4f}'
               '&current=weather_code,cloud_cover,precipitation,wind_speed_10m,temperature_2m')
        self._request(url, False)

    def _request(self, url: str, location: bool) -> None:
        self.busy = True
        request = QNetworkRequest(QUrl(url))
        request.setTransferTimeout(10000)
        reply = self.manager.get(request)
        reply.downloadProgress.connect(lambda received, total: reply.abort() if received > 262144 else None)
        reply.finished.connect(lambda: self._finished(reply, location))

    def _finished(self, reply: QNetworkReply, location: bool) -> None:
        self.busy = False
        try:
            if reply.error() != QNetworkReply.NetworkError.NoError: return
            payload = json.loads(bytes(reply.readAll()))
            if not isinstance(payload, dict): return
            if location:
                coordinates = resolve_location(payload, self.location)
                if coordinates is None: return
                self.latitude, self.longitude = coordinates
                self.located = True
                self._save()
                self._forecast()
            else:
                self.observation = parse_weather(payload)
                self.observed_at = time.time()
                self._save()
        except (ValueError, KeyError, TypeError):
            self.response_error = True
        finally:
            reply.deleteLater()
