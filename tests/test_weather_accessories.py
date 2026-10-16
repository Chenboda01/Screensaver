"""Behavior tests for Bob's separate weather-owned appearance layer."""
from __future__ import annotations

import pytest

from screenbot.weather_accessories import (
    WeatherAccessory,
    WeatherAccessoryRequest,
    WeatherCategory,
    WeatherConditions,
    WeatherPreview,
    WeatherReaction,
    compose_weather_accessories,
    parse_weather_category,
    parse_weather_preview,
    resolve_weather_look,
    transition_accessories,
)


def _request(
    category: WeatherCategory,
    *,
    fresh: bool = True,
    enabled: bool = True,
    live_sky: bool = True,
    space: bool = False,
    sun_altitude: float | None = 20.0,
    moon_altitude: float | None = -10.0,
    wind_speed: float = 0.0,
    elapsed: float = 5.0,
    lightning: bool = False,
    override: WeatherPreview | None = None,
) -> WeatherAccessoryRequest:
    return WeatherAccessoryRequest(
        conditions=WeatherConditions(
            category=category,
            fresh=fresh,
            sun_altitude=sun_altitude,
            moon_altitude=moon_altitude,
            wind_speed=wind_speed,
            lightning_flash=lightning,
        ),
        live_sky_enabled=live_sky,
        enabled=enabled,
        space_theme=space,
        elapsed_seconds=elapsed,
        preview_override=override,
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [(category.value, category) for category in WeatherCategory]
    + [("provider-surprise", WeatherCategory.UNKNOWN), (None, WeatherCategory.UNKNOWN)],
)
def test_category_parser_maps_provider_values_to_allowlist(
    value: str | None,
    expected: WeatherCategory,
) -> None:
    # Given a provider category at the boundary
    # When it is parsed once
    actual = parse_weather_category(value)
    # Then known values are preserved and all other values are unknown
    assert actual is expected


@pytest.mark.parametrize(
    ("category", "expected"),
    [
        (WeatherCategory.RAIN, (WeatherAccessory.UMBRELLA,)),
        (WeatherCategory.THUNDERSTORM, (WeatherAccessory.UMBRELLA,)),
        (WeatherCategory.SNOW, (WeatherAccessory.WOOL_HAT, WeatherAccessory.SCARF)),
        (WeatherCategory.FOG, ()),
        (WeatherCategory.CLOUDY, ()),
    ],
)
def test_weather_category_selects_its_weather_accessories(
    category: WeatherCategory,
    expected: tuple[WeatherAccessory, ...],
) -> None:
    # Given fresh Live Sky observations in a landscape theme
    request = _request(category)
    # When Bob's weather look is resolved
    actual = resolve_weather_look(request)
    # Then only the category's weather-owned items are selected
    assert actual.accessories == expected


@pytest.mark.parametrize("altitude", [45.0, 65.0, 90.0])
def test_clear_strong_sun_uses_sunglasses(altitude: float) -> None:
    # Given a fresh clear sky with strong sun
    request = _request(WeatherCategory.CLEAR, sun_altitude=altitude)
    # When Bob's look is resolved
    actual = resolve_weather_look(request)
    # Then sunglasses are the only weather item
    assert actual.accessories == (WeatherAccessory.SUNGLASSES,)


@pytest.mark.parametrize("altitude", [44.99, 0.0, -10.0])
def test_weak_or_below_horizon_sun_does_not_add_sunglasses(altitude: float) -> None:
    # Given clear conditions without strong sun
    request = _request(WeatherCategory.CLEAR, sun_altitude=altitude)
    # When Bob's look is resolved
    actual = resolve_weather_look(request)
    # Then he has no sunglasses
    assert WeatherAccessory.SUNGLASSES not in actual.accessories


@pytest.mark.parametrize(
    "request_data",
    [
        _request(WeatherCategory.RAIN, fresh=False),
        _request(WeatherCategory.UNKNOWN),
        _request(WeatherCategory.SNOW, live_sky=False),
        _request(WeatherCategory.SNOW, enabled=False),
    ],
)
def test_unknown_offline_or_disabled_weather_has_no_weather_accessories(
    request_data: WeatherAccessoryRequest,
) -> None:
    # Given unavailable or disabled weather observations
    # When Bob's appearance is resolved
    actual = resolve_weather_look(request_data)
    # Then no weather accessory is invented or recovered from a stale cache
    assert actual.accessories == ()


def test_space_suppresses_weather_items_but_keeps_time_reactions() -> None:
    # Given Space with a known nighttime sky and snow observation
    request = _request(
        WeatherCategory.SNOW,
        space=True,
        sun_altitude=-25.0,
        moon_altitude=14.0,
        elapsed=23.5,
        wind_speed=70.0,
    )
    # When the appearance is resolved
    actual = resolve_weather_look(request)
    # Then no apparel, wind movement, or nightcap enters the space theme
    assert actual.accessories == ()
    assert actual.extra_tilt_degrees == 0.0
    assert actual.sleepy_extension_seconds == 8.0


def test_offline_weather_has_no_accessories_but_keeps_known_moon_reaction() -> None:
    # Given expired weather with a locally known sky position
    request = _request(
        WeatherCategory.RAIN,
        fresh=False,
        sun_altitude=12.0,
        moon_altitude=20.0,
        elapsed=23.5,
    )
    # When the current sky is resolved
    actual = resolve_weather_look(request)
    # Then stale rain is ignored while the local moon reaction remains available
    assert actual.accessories == ()
    assert actual.reaction is WeatherReaction.LOOK_UP


def test_weather_reactions_cover_fog_lightning_wind_moon_and_deep_night() -> None:
    # Given visible weather and astronomy conditions
    fog = resolve_weather_look(_request(WeatherCategory.FOG))
    lightning = resolve_weather_look(_request(WeatherCategory.THUNDERSTORM, lightning=True))
    wind = resolve_weather_look(_request(WeatherCategory.SNOW, wind_speed=40.0))
    moon = resolve_weather_look(_request(WeatherCategory.CLEAR, moon_altitude=12.0, elapsed=23.5))
    night = resolve_weather_look(_request(WeatherCategory.CLEAR, sun_altitude=-25.0))
    # When each condition is resolved
    # Then the matching expressive hint is available to the renderer
    assert fog.reaction is WeatherReaction.SQUINT
    assert lightning.reaction is WeatherReaction.SURPRISED
    assert wind.reaction is WeatherReaction.CURIOUS
    assert wind.scarf_flutter > 0.0
    assert wind.extra_tilt_degrees > 0.0
    assert moon.reaction is WeatherReaction.LOOK_UP
    assert night.reaction is WeatherReaction.SLEEPY
    assert night.sleepy_extension_seconds > 0.0
    assert WeatherAccessory.NIGHTCAP in night.accessories


@pytest.mark.parametrize(
    ("override", "expected", "live_sky"),
    [
        (WeatherPreview.RAIN, WeatherAccessory.UMBRELLA, False),
        (WeatherPreview.SNOW, WeatherAccessory.WOOL_HAT, False),
        (WeatherPreview.CLEAR_NOON, WeatherAccessory.SUNGLASSES, False),
    ],
)
def test_preview_overrides_work_without_live_observations(
    override: WeatherPreview,
    expected: WeatherAccessory,
    live_sky: bool,
) -> None:
    # Given unavailable weather and Live Sky off, with a forced preview condition
    request = _request(WeatherCategory.UNKNOWN, fresh=False, live_sky=live_sky, override=override)
    # When Bob's look is resolved
    actual = resolve_weather_look(request)
    # Then the requested accessory is shown deterministically
    assert expected in actual.accessories


def test_preview_cannot_force_weather_accessories_in_space() -> None:
    # Given a rain preview override in Space
    request = _request(WeatherCategory.UNKNOWN, space=True, override=WeatherPreview.RAIN)
    # When Bob's look is resolved
    actual = resolve_weather_look(request)
    # Then the Space theme stays free of weather items
    assert actual.accessories == ()


def test_preview_override_respects_disabled_accessory_setting() -> None:
    # Given a forced preview condition with Bob's accessory setting off
    request = _request(
        WeatherCategory.UNKNOWN,
        enabled=False,
        live_sky=False,
        override=WeatherPreview.RAIN,
    )
    # When Bob's look is resolved
    actual = resolve_weather_look(request)
    # Then the preview cannot bypass the appearance setting
    assert actual.accessories == ()


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("rain", WeatherPreview.RAIN),
        ("snow", WeatherPreview.SNOW),
        ("clear-noon", WeatherPreview.CLEAR_NOON),
        ("invalid", None),
        (None, None),
    ],
)
def test_preview_argument_is_allowlisted_once(
    value: str | None,
    expected: WeatherPreview | None,
) -> None:
    # Given a user-supplied preview argument
    # When it is parsed at the command boundary
    actual = parse_weather_preview(value)
    # Then only documented conditions reach the rendering model
    assert actual is expected


@pytest.mark.parametrize(
    ("custom", "weather", "expected"),
    [
        (
            "cap",
            (WeatherAccessory.WOOL_HAT, WeatherAccessory.SCARF, WeatherAccessory.UMBRELLA),
            (WeatherAccessory.SCARF, WeatherAccessory.UMBRELLA),
        ),
        (
            "crown",
            (WeatherAccessory.NIGHTCAP, WeatherAccessory.SUNGLASSES),
            (WeatherAccessory.SUNGLASSES,),
        ),
        (
            "bow-tie",
            (WeatherAccessory.WOOL_HAT, WeatherAccessory.SCARF),
            (WeatherAccessory.WOOL_HAT, WeatherAccessory.SCARF),
        ),
    ],
)
def test_custom_headwear_only_replaces_conflicting_weather_headwear(
    custom: str,
    weather: tuple[WeatherAccessory, ...],
    expected: tuple[WeatherAccessory, ...],
) -> None:
    # Given a custom accessory and a separate weather accessory result
    # When their geometric layers are composed
    actual = compose_weather_accessories(custom, weather)
    # Then custom headwear remains visible while nonconflicting weather items stack
    assert actual == expected


@pytest.mark.parametrize("progress", [-1.0, 0.0, 0.5, 1.0, 2.0])
def test_accessory_transition_crossfades_without_popping(progress: float) -> None:
    # Given a previous umbrella and a target hat plus scarf
    previous = (WeatherAccessory.UMBRELLA,)
    target = (WeatherAccessory.WOOL_HAT, WeatherAccessory.SCARF)
    # When the transition is sampled at any progress value
    actual = transition_accessories(previous, target, progress)
    # Then the transition is clamped and obsolete/new items fade in opposite directions
    amount = max(0.0, min(1.0, progress))
    by_accessory = {frame.accessory: frame for frame in actual}
    if amount < 1.0:
        assert by_accessory[WeatherAccessory.UMBRELLA].opacity == 1.0 - amount
    else:
        assert WeatherAccessory.UMBRELLA not in by_accessory
    if amount > 0.0:
        assert by_accessory[WeatherAccessory.WOOL_HAT].opacity == amount
        assert by_accessory[WeatherAccessory.SCARF].opacity == amount
    else:
        assert WeatherAccessory.WOOL_HAT not in by_accessory
        assert WeatherAccessory.SCARF not in by_accessory
    assert all(0.0 <= frame.opacity <= 1.0 for frame in actual)
    assert all(-18.0 <= frame.slide_y <= 0.0 for frame in actual)


def test_no_change_transition_is_fully_visible_and_empty_is_empty() -> None:
    # Given an unchanged pair and an empty pair
    unchanged = (WeatherAccessory.SCARF,)
    # When both are transitioned
    same = transition_accessories(unchanged, unchanged, 0.25)
    empty = transition_accessories((), (), 0.25)
    # Then the existing item does not dim and empty remains empty
    assert len(same) == 1
    assert same[0].accessory is WeatherAccessory.SCARF
    assert same[0].opacity == 1.0
    assert same[0].slide_y == 0.0
    assert empty == ()
