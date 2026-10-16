"""Deterministic local-date and hemisphere behavior for seasonal decorations."""

from datetime import date, datetime, timedelta, timezone

import pytest

from screenbot.seasonal import (
    LUNAR_NEW_YEAR_DATES,
    Birthday,
    Hemisphere,
    Season,
    SeasonalEvent,
    calendar_state,
    effective_preview_date,
    hemisphere_for_latitude,
    new_year_countdown_seconds,
    season_for_date,
)


def test_halloween_is_active_through_october_31_only_after_october_23() -> None:
    # Given Halloween is the only enabled event.
    enabled = frozenset({SeasonalEvent.HALLOWEEN})
    # When resolving the event window boundaries.
    active_start = calendar_state(date(2026, 10, 24), enabled=True, events=enabled)
    active_end = calendar_state(date(2026, 10, 31), enabled=True, events=enabled)
    before = calendar_state(date(2026, 10, 23), enabled=True, events=enabled)
    after = calendar_state(date(2026, 11, 1), enabled=True, events=enabled)
    # Then only October 24 through October 31 include Halloween.
    assert active_start.events == active_end.events == frozenset({SeasonalEvent.HALLOWEEN})
    assert before.events == after.events == frozenset()


def test_winter_holiday_window_covers_december_first_through_twenty_sixth() -> None:
    # Given winter holidays are enabled.
    enabled = frozenset({SeasonalEvent.WINTER_HOLIDAYS})
    # When checking dates around the configured window.
    states = {
        day: calendar_state(date(2026, 12, day), enabled=True, events=enabled).events
        for day in (1, 24, 26, 27)
    }
    # Then the event is active only for December 1–26.
    assert states == {
        1: frozenset({SeasonalEvent.WINTER_HOLIDAYS}),
        24: frozenset({SeasonalEvent.WINTER_HOLIDAYS}),
        26: frozenset({SeasonalEvent.WINTER_HOLIDAYS}),
        27: frozenset(),
    }


@pytest.mark.parametrize("day", [date(2026, 12, 31), date(2027, 1, 1)])
def test_new_year_event_spans_year_boundary(day: date) -> None:
    # Given New Year is enabled.
    enabled = frozenset({SeasonalEvent.NEW_YEAR})
    # When resolving either side of local midnight.
    state = calendar_state(day, enabled=True, events=enabled)
    # Then both dates are part of the New Year event.
    assert state.events == frozenset({SeasonalEvent.NEW_YEAR})


def test_all_events_off_and_master_off_produce_empty_event_sets() -> None:
    # Given every event is disabled or the master switch is off.
    all_events = frozenset(SeasonalEvent)
    # When resolving dates that would otherwise activate decorations.
    all_off = calendar_state(date(2026, 10, 31), enabled=True, events=frozenset())
    master_off = calendar_state(date(2026, 10, 31), enabled=False, events=all_events)
    # Then neither state contains an event.
    assert all_off.events == master_off.events == frozenset()


def test_lunar_new_year_table_matches_supported_dates_and_adjacent_days() -> None:
    # Given the published Gregorian Lunar New Year dates for the bundled years.
    expected_dates = (
        date(2026, 2, 17), date(2027, 2, 6), date(2028, 1, 26), date(2029, 2, 13),
        date(2030, 2, 3), date(2031, 1, 23), date(2032, 2, 11), date(2033, 1, 31),
        date(2034, 2, 19), date(2035, 2, 8), date(2036, 1, 28), date(2037, 2, 15),
        date(2038, 2, 4), date(2039, 1, 24), date(2040, 2, 12), date(2041, 2, 1),
        date(2042, 1, 22), date(2043, 2, 10), date(2044, 1, 30), date(2045, 2, 17),
    )
    enabled = frozenset({SeasonalEvent.LUNAR_NEW_YEAR})
    # When comparing the built-in data and resolving each date with both neighbors.
    assert tuple(LUNAR_NEW_YEAR_DATES.values()) == expected_dates
    for day in expected_dates:
        before = calendar_state(day - timedelta(days=1), enabled=True, events=enabled)
        active = calendar_state(day, enabled=True, events=enabled)
        after = calendar_state(day + timedelta(days=1), enabled=True, events=enabled)
        # Then only the known Lunar New Year date activates the event.
        assert before.events == after.events == frozenset()
        assert active.events == frozenset({SeasonalEvent.LUNAR_NEW_YEAR})


def test_lunar_new_year_outside_built_in_table_is_not_guessed() -> None:
    # Given a year outside the bundled lookup range.
    enabled = frozenset({SeasonalEvent.LUNAR_NEW_YEAR})
    # When resolving a plausible Lunar New Year date beyond the table.
    state = calendar_state(date(2046, 2, 6), enabled=True, events=enabled)
    # Then no approximate event is displayed.
    assert state.events == frozenset()


def test_southern_hemisphere_swaps_spring_and_winter_dates() -> None:
    # Given spring and winter-holiday events are enabled at northern and southern locations.
    enabled = frozenset({SeasonalEvent.SPRING, SeasonalEvent.WINTER_HOLIDAYS})
    # When checking March, October, and December in both hemispheres.
    north_march = calendar_state(date(2026, 3, 20), enabled=True, events=enabled, latitude=42.0)
    south_march = calendar_state(date(2026, 3, 20), enabled=True, events=enabled, latitude=-33.9)
    south_october = calendar_state(date(2026, 10, 1), enabled=True, events=enabled, latitude=-33.9)
    south_december = calendar_state(date(2026, 12, 24), enabled=True, events=enabled, latitude=-33.9)
    # Then the seasonal event and season follow the configured hemisphere.
    assert north_march.season is Season.SPRING
    assert SeasonalEvent.SPRING in north_march.events
    assert south_march.season is Season.AUTUMN
    assert SeasonalEvent.SPRING not in south_march.events
    assert south_october.season is Season.SPRING
    assert SeasonalEvent.SPRING in south_october.events
    assert south_december.season is Season.SUMMER
    assert SeasonalEvent.WINTER_HOLIDAYS in south_december.events


@pytest.mark.parametrize("latitude", [None, 0.0, 91.0, -91.0, float("nan"), float("inf")])
def test_missing_or_invalid_latitude_defaults_to_northern_hemisphere(latitude: float | None) -> None:
    # Given missing, equatorial, or invalid Live Sky latitude.
    # When selecting the season hemisphere.
    hemisphere = hemisphere_for_latitude(latitude)
    # Then the stable fallback is Northern Hemisphere.
    assert hemisphere is Hemisphere.NORTH


def test_birthday_matches_month_and_day_without_storing_birth_year() -> None:
    # Given a locally configured recurring month/day and optional name.
    birthday = Birthday.parse("02-29", " Ada ")
    assert birthday is not None
    enabled = frozenset({SeasonalEvent.BIRTHDAY})
    # When resolving leap day, a nearby day, and the same month/day in another year.
    leap_day = calendar_state(date(2028, 2, 29), enabled=True, events=enabled, birthday=birthday)
    nearby = calendar_state(date(2028, 2, 28), enabled=True, events=enabled, birthday=birthday)
    recurring = calendar_state(date(2032, 2, 29), enabled=True, events=enabled, birthday=birthday)
    # Then only matching month/day values activate the event.
    assert leap_day.events == recurring.events == frozenset({SeasonalEvent.BIRTHDAY})
    assert nearby.events == frozenset()


@pytest.mark.parametrize("value", ["", "02-30", "13-01", "2028-02-29", "x-y"])
def test_invalid_birthday_settings_disable_the_personal_event(value: str) -> None:
    # Given an empty or invalid local month/day setting.
    birthday = Birthday.parse(value, "Bob")
    # When evaluating a date that could otherwise match a birthday.
    state = calendar_state(date(2028, 2, 29), enabled=True,
                           events=frozenset({SeasonalEvent.BIRTHDAY}), birthday=birthday)
    # Then no personal event is activated.
    assert state.events == frozenset()


def test_birthday_name_is_plain_bounded_local_text() -> None:
    # Given a display name containing whitespace and control characters.
    birthday = Birthday.parse("07-04", "  Bob\n\x00 " + "B" * 100)
    assert birthday is not None
    # When parsing the local preference.
    # Then controls are removed and the visible value is bounded.
    assert "\n" not in birthday.name and "\x00" not in birthday.name
    assert birthday.name.startswith("Bob")
    assert len(birthday.name) <= 80


def test_preview_override_is_ignored_for_regular_sessions() -> None:
    # Given a known system-local date and an alternate forced preview date.
    system_date = date(2026, 10, 16)
    forced_date = date(2026, 10, 31)
    # When resolving dates in preview and regular session modes.
    preview_date = effective_preview_date(system_date, forced_date, preview_mode=True)
    session_date = effective_preview_date(system_date, forced_date, preview_mode=False)
    # Then only preview mode receives the test date.
    assert preview_date == forced_date
    assert session_date == system_date


def test_preview_without_override_keeps_system_local_date() -> None:
    # Given a preview with no forced date.
    system_date = date(2026, 1, 1)
    # When selecting its calendar date.
    selected = effective_preview_date(system_date, None, preview_mode=True)
    # Then it follows the supplied local date.
    assert selected == system_date


@pytest.mark.parametrize(
    "local_now,expected",
    [
        (datetime(2026, 12, 31, 23, 58, 59, tzinfo=timezone.utc), None),
        (datetime(2026, 12, 31, 23, 59, 0, tzinfo=timezone.utc), 60),
        (datetime(2026, 12, 31, 23, 59, 30, tzinfo=timezone.utc), 30),
        (datetime(2027, 1, 1, 0, 0, tzinfo=timezone.utc), None),
    ],
)
def test_countdown_uses_the_supplied_local_wall_clock(
    local_now: datetime,
    expected: int | None,
) -> None:
    # Given a local datetime at or around the final minute of New Year's Eve.
    # When computing the New Year countdown.
    countdown = new_year_countdown_seconds(local_now)
    # Then countdown values exist only in the final minute and end at midnight.
    assert countdown == expected


@pytest.mark.parametrize(
    "day,hemisphere,expected",
    [
        (date(2026, 3, 19), Hemisphere.NORTH, Season.WINTER),
        (date(2026, 3, 20), Hemisphere.NORTH, Season.SPRING),
        (date(2026, 6, 1), Hemisphere.NORTH, Season.SUMMER),
        (date(2026, 9, 1), Hemisphere.NORTH, Season.AUTUMN),
        (date(2026, 12, 1), Hemisphere.SOUTH, Season.SUMMER),
        (date(2026, 6, 1), Hemisphere.SOUTH, Season.WINTER),
    ],
)
def test_season_boundaries(day: date, hemisphere: Hemisphere, expected: Season) -> None:
    # Given a date near a broad season boundary and a selected hemisphere.
    # When resolving its season.
    season = season_for_date(day, hemisphere)
    # Then the boundary maps to the expected season.
    assert season is expected
