"""Pure scene-to-loop policy used by the optional ambient audio engine."""
from dataclasses import dataclass
from enum import StrEnum
from typing import Final, assert_never


class SceneTheme(StrEnum):
    """Finite visual themes accepted by the ambient sound mapping."""

    SPACE = 'space'
    MOUNTAINS = 'mountains'
    SNOW = 'snow'
    FOREST = 'forest'
    CITY = 'city'
    AURORA = 'aurora'
    OCEAN = 'ocean'
    DESERT = 'desert'
    UNDERWATER = 'underwater'
    UNKNOWN = 'unknown'


class WeatherCategory(StrEnum):
    """Finite Live Sky categories that influence scene audio."""

    CLEAR = 'clear'
    CLOUDY = 'cloudy'
    OVERCAST = 'overcast'
    RAIN = 'rain'
    THUNDERSTORM = 'thunderstorm'
    SNOW = 'snow'
    FOG = 'fog'
    UNKNOWN = 'unknown'


@dataclass(frozen=True, slots=True)
class SceneSound:
    """Validated view of the scene values that affect ambient sound."""

    theme: SceneTheme
    weather: WeatherCategory
    live_sky_enabled: bool
    live_sky_fresh: bool
    live_sky_only: bool
    rain_enabled: bool
    snow_enabled: bool
    thunder_enabled: bool
    elapsed_hours: float


AMBIENT_THEMES: Final[frozenset[SceneTheme]] = frozenset({
    SceneTheme.SPACE, SceneTheme.MOUNTAINS, SceneTheme.SNOW, SceneTheme.FOREST,
    SceneTheme.CITY, SceneTheme.AURORA, SceneTheme.OCEAN, SceneTheme.DESERT,
    SceneTheme.UNDERWATER,
})


def parse_theme(value: str) -> SceneTheme:
    """Map settings to the known theme set, silencing invalid values."""
    try:
        return SceneTheme(value)
    except ValueError:
        return SceneTheme.UNKNOWN


def parse_weather(value: str) -> WeatherCategory:
    """Map Live Sky's validated output to a finite category."""
    try:
        return WeatherCategory(value)
    except ValueError:
        return WeatherCategory.UNKNOWN


def choose_loop(scene: SceneSound) -> str | None:
    """Choose one bundled loop, or silence when policy says there is no match."""
    if scene.theme not in AMBIENT_THEMES:
        return None
    if scene.theme is SceneTheme.SPACE:
        return None if scene.live_sky_only else 'space'
    live_matches = scene.live_sky_enabled and scene.live_sky_fresh
    if scene.live_sky_only and not live_matches:
        return None
    if live_matches:
        match scene.weather:
            case WeatherCategory.RAIN:
                return 'rain'
            case WeatherCategory.THUNDERSTORM:
                return 'thunder'
            case WeatherCategory.SNOW | WeatherCategory.FOG:
                return 'wind'
            case WeatherCategory.CLEAR | WeatherCategory.CLOUDY | WeatherCategory.OVERCAST:
                pass
            case WeatherCategory.UNKNOWN:
                return None
            case unreachable:
                assert_never(unreachable)
    if not scene.live_sky_enabled:
        if scene.thunder_enabled:
            return 'thunder'
        if scene.rain_enabled:
            return 'rain'
        if scene.snow_enabled:
            return 'wind'
    match scene.theme:
        case SceneTheme.FOREST:
            return 'crickets' if 19.0 <= scene.elapsed_hours or scene.elapsed_hours < 6.0 else 'forest'
        case SceneTheme.CITY:
            return 'city'
        case SceneTheme.OCEAN | SceneTheme.UNDERWATER:
            return 'waves'
        case SceneTheme.MOUNTAINS | SceneTheme.SNOW | SceneTheme.AURORA | SceneTheme.DESERT:
            return 'wind'
        case SceneTheme.SPACE:
            return 'space'
        case SceneTheme.UNKNOWN:
            return None
        case unreachable:
            assert_never(unreachable)
