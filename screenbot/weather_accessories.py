"""Pure weather-to-accessory decisions for Bob's independently composable layers."""
from dataclasses import dataclass
from enum import StrEnum
from typing import Final, assert_never


class WeatherCategory(StrEnum):
    """Allowlisted Live Sky categories used by the Bob appearance layer."""

    CLEAR = "clear"
    CLOUDY = "cloudy"
    OVERCAST = "overcast"
    RAIN = "rain"
    SNOW = "snow"
    FOG = "fog"
    THUNDERSTORM = "thunderstorm"
    UNKNOWN = "unknown"


class WeatherPreview(StrEnum):
    """Deterministic weather states available to the safe preview path."""

    RAIN = "rain"
    SNOW = "snow"
    THUNDERSTORM = "thunderstorm"
    FOG = "fog"
    CLEAR_NOON = "clear-noon"
    UNKNOWN = "unknown"


class WeatherAccessory(StrEnum):
    """Items owned by Live Sky; custom accessories remain a separate layer."""

    UMBRELLA = "umbrella"
    SUNGLASSES = "sunglasses"
    WOOL_HAT = "wool-hat"
    SCARF = "scarf"
    NIGHTCAP = "nightcap"


class WeatherReaction(StrEnum):
    """Weather and time-of-day expression hints for BobRenderer."""

    NONE = "none"
    SQUINT = "squint"
    CURIOUS = "curious"
    SURPRISED = "surprised"
    LOOK_UP = "look-up"
    SLEEPY = "sleepy"


@dataclass(frozen=True, slots=True)
class WeatherConditions:
    """Validated, display-only weather and astronomy inputs."""

    category: WeatherCategory
    fresh: bool
    sun_altitude: float | None
    moon_altitude: float | None
    wind_speed: float
    lightning_flash: bool = False


@dataclass(frozen=True, slots=True)
class WeatherAccessoryRequest:
    """All inputs needed to resolve Bob's transient weather styling."""

    conditions: WeatherConditions
    live_sky_enabled: bool
    enabled: bool
    space_theme: bool
    elapsed_seconds: float
    preview_override: WeatherPreview | None = None


@dataclass(frozen=True, slots=True)
class BobWeatherLook:
    """Weather-owned visuals; custom Bob appearance is deliberately untouched."""

    accessories: tuple[WeatherAccessory, ...]
    reaction: WeatherReaction
    extra_tilt_degrees: float
    scarf_flutter: float
    sleepy_extension_seconds: float


@dataclass(frozen=True, slots=True)
class AccessoryOpacity:
    """One accessory's crossfade opacity and slide offset in head-local units."""

    accessory: WeatherAccessory
    opacity: float
    slide_y: float


DEFAULT_LOOK: Final[BobWeatherLook] = BobWeatherLook(
    accessories=(),
    reaction=WeatherReaction.NONE,
    extra_tilt_degrees=0.0,
    scarf_flutter=0.0,
    sleepy_extension_seconds=0.0,
)
CUSTOM_HEADWEAR: Final[frozenset[str]] = frozenset({
    "cap", "crown", "flower", "headphones", "antenna-ball",
})


def parse_weather_category(value: str | None) -> WeatherCategory:
    """Parse provider output once, mapping absent or unknown values safely."""
    if value is None:
        return WeatherCategory.UNKNOWN
    try:
        return WeatherCategory(value)
    except ValueError:
        return WeatherCategory.UNKNOWN


def parse_weather_preview(value: str | None) -> WeatherPreview | None:
    """Parse an explicit command-line preview value; absent/invalid means none."""
    if value is None:
        return None
    try:
        return WeatherPreview(value)
    except ValueError:
        return None


def resolve_weather_look(request: WeatherAccessoryRequest) -> BobWeatherLook:
    """Resolve appearance hints without changing user-selected accessory state."""
    conditions = request.conditions
    category = conditions.category
    sun_altitude = conditions.sun_altitude
    moon_altitude = conditions.moon_altitude
    if request.preview_override is not None:
        category, sun_altitude = _preview_values(request.preview_override)

    active = request.enabled and (
        request.live_sky_enabled or request.preview_override is not None
    )
    weather_known = conditions.fresh or request.preview_override is not None
    accessories: list[WeatherAccessory] = []
    reaction = WeatherReaction.NONE
    sleepy_extension = 0.0

    if active and weather_known and not request.space_theme:
        match category:
            case WeatherCategory.RAIN:
                accessories.append(WeatherAccessory.UMBRELLA)
            case WeatherCategory.THUNDERSTORM:
                accessories.append(WeatherAccessory.UMBRELLA)
                if conditions.lightning_flash:
                    reaction = WeatherReaction.SURPRISED
            case WeatherCategory.SNOW:
                accessories.extend((WeatherAccessory.WOOL_HAT, WeatherAccessory.SCARF))
            case WeatherCategory.FOG:
                reaction = WeatherReaction.SQUINT
            case WeatherCategory.CLEAR | WeatherCategory.CLOUDY | WeatherCategory.OVERCAST:
                if sun_altitude is not None and sun_altitude >= 45.0:
                    accessories.append(WeatherAccessory.SUNGLASSES)
            case WeatherCategory.UNKNOWN:
                pass
            case unreachable:
                assert_never(unreachable)

        if conditions.wind_speed >= 28.0 and accessories:
            reaction = WeatherReaction.CURIOUS

    if active and sun_altitude is not None and sun_altitude < -18.0:
        sleepy_extension = 8.0
        if conditions.fresh and not request.space_theme:
            accessories.append(WeatherAccessory.NIGHTCAP)
        if reaction is WeatherReaction.NONE:
            reaction = WeatherReaction.SLEEPY
    elif active and moon_altitude is not None and moon_altitude > 0.0:
        if request.elapsed_seconds % 23.0 < 1.2 and reaction is WeatherReaction.NONE:
            reaction = WeatherReaction.LOOK_UP

    scarf_flutter = 0.0
    if WeatherAccessory.SCARF in accessories and conditions.wind_speed > 0.0:
        scarf_flutter = min(1.0, conditions.wind_speed / 55.0)

    return BobWeatherLook(
        accessories=tuple(dict.fromkeys(accessories)),
        reaction=reaction,
        extra_tilt_degrees=(
            min(5.0, conditions.wind_speed / 18.0)
            if active and weather_known and not request.space_theme
            else 0.0
        ),
        scarf_flutter=scarf_flutter,
        sleepy_extension_seconds=sleepy_extension,
    )


def transition_accessories(
    previous: tuple[WeatherAccessory, ...],
    target: tuple[WeatherAccessory, ...],
    progress: float,
) -> tuple[AccessoryOpacity, ...]:
    """Crossfade accessories while sliding new items into Bob's head-local pose."""
    amount = max(0.0, min(1.0, progress))
    ordered = tuple(dict.fromkeys((*previous, *target)))
    frames: list[AccessoryOpacity] = []
    for accessory in ordered:
        was_present = accessory in previous
        is_present = accessory in target
        if was_present and is_present:
            opacity = 1.0
        elif was_present:
            opacity = 1.0 - amount
        else:
            opacity = amount
        if opacity > 0.0:
            frames.append(AccessoryOpacity(accessory, opacity, (1.0 - opacity) * -18.0))
    return tuple(frames)


def compose_weather_accessories(
    custom_accessory: str,
    weather_accessories: tuple[WeatherAccessory, ...],
) -> tuple[WeatherAccessory, ...]:
    """Keep user headwear when a weather hat would occupy the same head area."""
    if custom_accessory in CUSTOM_HEADWEAR:
        return tuple(
            accessory for accessory in weather_accessories
            if accessory not in (WeatherAccessory.WOOL_HAT, WeatherAccessory.NIGHTCAP)
        )
    return weather_accessories


def _preview_values(override: WeatherPreview) -> tuple[WeatherCategory, float | None]:
    """Return a fixed weather and sun value for deterministic preview frames."""
    match override:
        case WeatherPreview.RAIN:
            return WeatherCategory.RAIN, 20.0
        case WeatherPreview.SNOW:
            return WeatherCategory.SNOW, 20.0
        case WeatherPreview.THUNDERSTORM:
            return WeatherCategory.THUNDERSTORM, 20.0
        case WeatherPreview.FOG:
            return WeatherCategory.FOG, 20.0
        case WeatherPreview.CLEAR_NOON:
            return WeatherCategory.CLEAR, 65.0
        case WeatherPreview.UNKNOWN:
            return WeatherCategory.UNKNOWN, None
        case unreachable:
            assert_never(unreachable)
