"""Offline low precision astronomy and validated weather values for Live Sky."""
from dataclasses import dataclass
from datetime import datetime
import math


@dataclass(frozen=True, slots=True)
class SkyPosition:
    sun_altitude: float
    sun_azimuth: float
    moon_altitude: float
    moon_azimuth: float
    moon_phase: float
    morning: bool


def sky_position(now: datetime, latitude: float, longitude: float) -> SkyPosition:
    """Approximate geocentric positions (degrees), adequate for decorative skies.

    Julian days and sidereal time use UTC, so DST and polar latitudes need no
    sunrise special cases. Moon perturbations/refraction are intentionally omitted.
    """
    jd = now.timestamp() / 86400 + 2440587.5
    d = jd - 2451545.0
    rad = math.radians
    sun_mean = rad((357.5291 + .98560028*d) % 360)
    sun_lon = rad((280.46646 + .98564736*d + 1.9148*math.sin(sun_mean) + .0200*math.sin(2*sun_mean)) % 360)
    moon_mean = rad((134.963 + 13.064993*d) % 360)
    moon_lon = rad((218.316 + 13.176396*d + 6.289*math.sin(moon_mean)) % 360)
    moon_lat = rad(5.128*math.sin(rad((93.272 + 13.229350*d) % 360)))
    sidereal = rad((280.46061837 + 360.98564736629*d + longitude) % 360)
    obliquity = rad(23.4393 - .00000036*d)

    def horizontal(lon: float, lat: float) -> tuple[float, float, float]:
        ra = math.atan2(math.sin(lon)*math.cos(obliquity)-math.tan(lat)*math.sin(obliquity), math.cos(lon))
        dec = math.asin(math.sin(lat)*math.cos(obliquity)+math.cos(lat)*math.sin(obliquity)*math.sin(lon))
        hour = (sidereal-ra+math.pi) % math.tau-math.pi
        alt = math.asin(max(-1., min(1., math.sin(rad(latitude))*math.sin(dec)+math.cos(rad(latitude))*math.cos(dec)*math.cos(hour))))
        azimuth = math.atan2(math.sin(hour), math.cos(hour)*math.sin(rad(latitude))-math.tan(dec)*math.cos(rad(latitude)))
        return math.degrees(alt), (math.degrees(azimuth)+180)%360, hour

    sa, sz, hour = horizontal(sun_lon, 0.)
    ma, mz, _ = horizontal(moon_lon, moon_lat)
    return SkyPosition(sa, sz, ma, mz, ((moon_lon-sun_lon)/math.tau)%1, hour < 0)


def sun_phase(altitude: float, morning: bool) -> str:
    if altitude < -18: return 'night'
    if altitude < -6: return 'twilight'
    if altitude <= 6: return 'sunrise' if morning else 'sunset'
    return 'day'


@dataclass(frozen=True, slots=True)
class Weather:
    code: int = 0
    cloud: float = 0.
    precipitation: float = 0.
    wind: float = 0.
    temperature: float = 0.

    @property
    def category(self) -> str:
        if self.code >= 95: return 'thunderstorm'
        if 70 <= self.code <= 79 or self.code in (85, 86): return 'snow'
        if 50 <= self.code <= 69 or 80 <= self.code <= 84: return 'rain'
        if 40 <= self.code <= 49: return 'fog'
        if self.cloud >= 90 or self.code == 3: return 'overcast'
        if self.cloud >= 20 or self.code in (1, 2): return 'cloudy'
        return 'clear'

    @property
    def intensity(self) -> float:
        return min(1., max(.12, self.precipitation/5.))


def parse_weather(payload: dict) -> Weather:
    """Reject malformed/non-finite provider values before drawing or caching."""
    current = payload['current']
    values = [float(current[key]) for key in ('weather_code', 'cloud_cover', 'precipitation', 'wind_speed_10m', 'temperature_2m')]
    if not all(math.isfinite(v) for v in values):
        raise ValueError('Non-finite weather response')
    code, cloud, precipitation, wind, temperature = values
    if not (0 <= code <= 99 and code.is_integer() and 0 <= cloud <= 100 and 0 <= precipitation <= 1000 and 0 <= wind <= 500 and -100 <= temperature <= 70):
        raise ValueError('Weather response outside physical bounds')
    return Weather(int(code), cloud, precipitation, wind, temperature)
