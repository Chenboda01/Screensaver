"""Pure, offline calendar rules for optional seasonal decorations."""

from __future__ import annotations

from dataclasses import dataclass
import configparser
from datetime import date, datetime, timedelta
from enum import StrEnum
import math
import unicodedata
from types import MappingProxyType
from typing import Final, Mapping


class SeasonalEvent(StrEnum):
    """Stable event identifiers persisted by the settings module."""

    NEW_YEAR = "new_year"
    LUNAR_NEW_YEAR = "lunar_new_year"
    VALENTINES_DAY = "valentines_day"
    SPRING = "spring"
    HALLOWEEN = "halloween"
    WINTER_HOLIDAYS = "winter_holidays"
    BIRTHDAY = "birthday"


class Hemisphere(StrEnum):
    """Hemisphere used to select local seasonal dates."""

    NORTH = "north"
    SOUTH = "south"


class Season(StrEnum):
    """Calendar season used by scene decorations."""

    SPRING = "spring"
    SUMMER = "summer"
    AUTUMN = "autumn"
    WINTER = "winter"


LUNAR_NEW_YEAR_DATES: Final[Mapping[int, date]] = MappingProxyType({
    2026: date(2026, 2, 17),
    2027: date(2027, 2, 6),
    2028: date(2028, 1, 26),
    2029: date(2029, 2, 13),
    2030: date(2030, 2, 3),
    2031: date(2031, 1, 23),
    2032: date(2032, 2, 11),
    2033: date(2033, 1, 31),
    2034: date(2034, 2, 19),
    2035: date(2035, 2, 8),
    2036: date(2036, 1, 28),
    2037: date(2037, 2, 15),
    2038: date(2038, 2, 4),
    2039: date(2039, 1, 24),
    2040: date(2040, 2, 12),
    2041: date(2041, 2, 1),
    2042: date(2042, 1, 22),
    2043: date(2043, 2, 10),
    2044: date(2044, 1, 30),
    2045: date(2045, 2, 17),
})

EVENT_SETTINGS: Final[Mapping[SeasonalEvent, str]] = MappingProxyType({
    SeasonalEvent.NEW_YEAR: "seasonal_new_year_enabled",
    SeasonalEvent.LUNAR_NEW_YEAR: "seasonal_lunar_new_year_enabled",
    SeasonalEvent.VALENTINES_DAY: "seasonal_valentines_enabled",
    SeasonalEvent.SPRING: "seasonal_spring_enabled",
    SeasonalEvent.HALLOWEEN: "seasonal_halloween_enabled",
    SeasonalEvent.WINTER_HOLIDAYS: "seasonal_winter_holidays_enabled",
    SeasonalEvent.BIRTHDAY: "seasonal_birthday_enabled",
})


@dataclass(frozen=True, slots=True)
class Birthday:
    """A local-only month/day and optional plain-text display name."""

    month: int
    day: int
    name: str = ""

    @classmethod
    def parse(cls, month_day: str, name: str = "") -> Birthday | None:
        """Parse an ``MM-DD`` setting; invalid or empty dates disable birthday mode."""
        try:
            if len(month_day) != 5 or month_day[2] != "-":
                return None
            month_text, day_text = month_day.split("-", maxsplit=1)
            month, day = int(month_text), int(day_text)
            date(2000, month, day)  # Leap day is a valid recurring birthday.
        except (ValueError, TypeError):
            return None
        safe_name = "".join(char for char in name.strip() if unicodedata.category(char) != "Cc")[:80]
        return cls(month, day, safe_name)

    def matches(self, day: date) -> bool:
        """Return whether a calendar day matches this recurring birthday."""
        return day.month == self.month and day.day == self.day


@dataclass(frozen=True, slots=True)
class CalendarState:
    """Resolved season and enabled events for one local calendar date."""

    hemisphere: Hemisphere
    season: Season
    events: frozenset[SeasonalEvent]


@dataclass(frozen=True, slots=True)
class SeasonalPreferences:
    """User's local seasonal options, parsed from the existing settings file."""

    enabled: bool
    events: frozenset[SeasonalEvent]
    birthday: Birthday | None


def seasonal_preferences(settings: configparser.ConfigParser) -> SeasonalPreferences:
    """Read only known local event options; New Year is the sole default event."""
    section = "Screensaver"
    enabled = settings.getboolean(section, "seasonal_enabled", fallback=True)
    events = frozenset(
        event for event, key in EVENT_SETTINGS.items()
        if settings.getboolean(section, key, fallback=event is SeasonalEvent.NEW_YEAR)
    )
    birthday = Birthday.parse(
        settings.get(section, "seasonal_birthday_date", fallback=""),
        settings.get(section, "seasonal_birthday_name", fallback=""),
    )
    return SeasonalPreferences(enabled, events, birthday)


def hemisphere_for_latitude(latitude: float | None) -> Hemisphere:
    """Use the selected Live Sky latitude; missing or invalid data defaults north."""
    if latitude is not None and math.isfinite(latitude) and -90 <= latitude <= 90 and latitude < 0:
        return Hemisphere.SOUTH
    return Hemisphere.NORTH


def season_for_date(day: date, hemisphere: Hemisphere) -> Season:
    """Resolve broad calendar seasons, swapping them across hemispheres."""
    month_day = (day.month, day.day)
    if (3, 20) <= month_day <= (5, 31):
        north_season = Season.SPRING
    elif (6, 1) <= month_day <= (8, 31):
        north_season = Season.SUMMER
    elif (9, 1) <= month_day <= (11, 30):
        north_season = Season.AUTUMN
    else:
        north_season = Season.WINTER

    if hemisphere is Hemisphere.NORTH:
        return north_season
    return {
        Season.SPRING: Season.AUTUMN,
        Season.SUMMER: Season.WINTER,
        Season.AUTUMN: Season.SPRING,
        Season.WINTER: Season.SUMMER,
    }[north_season]


def calendar_state(
    day: date,
    *,
    enabled: bool,
    events: frozenset[SeasonalEvent],
    latitude: float | None = None,
    birthday: Birthday | None = None,
) -> CalendarState:
    """Resolve configured event IDs for ``day`` without clocks, I/O, or networking."""
    hemisphere = hemisphere_for_latitude(latitude)
    season = season_for_date(day, hemisphere)
    if not enabled:
        return CalendarState(hemisphere, season, frozenset())

    active: set[SeasonalEvent] = set()
    if SeasonalEvent.NEW_YEAR in events and (day.month, day.day) in {(12, 31), (1, 1)}:
        active.add(SeasonalEvent.NEW_YEAR)
    if SeasonalEvent.LUNAR_NEW_YEAR in events and LUNAR_NEW_YEAR_DATES.get(day.year) == day:
        active.add(SeasonalEvent.LUNAR_NEW_YEAR)
    if SeasonalEvent.VALENTINES_DAY in events and (day.month, day.day) == (2, 14):
        active.add(SeasonalEvent.VALENTINES_DAY)
    if SeasonalEvent.SPRING in events and season is Season.SPRING:
        active.add(SeasonalEvent.SPRING)
    if SeasonalEvent.HALLOWEEN in events and day.month == 10 and 24 <= day.day <= 31:
        active.add(SeasonalEvent.HALLOWEEN)
    if SeasonalEvent.WINTER_HOLIDAYS in events and day.month == 12 and day.day <= 26:
        active.add(SeasonalEvent.WINTER_HOLIDAYS)
    if SeasonalEvent.BIRTHDAY in events and birthday is not None and birthday.matches(day):
        active.add(SeasonalEvent.BIRTHDAY)
    return CalendarState(hemisphere, season, frozenset(active))


def effective_preview_date(
    system_local_date: date,
    forced_date: date | None,
    *,
    preview_mode: bool,
) -> date:
    """Use a forced date only for preview; regular sessions always use local system date."""
    if preview_mode and forced_date is not None:
        return forced_date
    return system_local_date


def effective_preview_datetime(
    system_local_now: datetime,
    forced_local_datetime: datetime | None,
    *,
    preview_mode: bool,
) -> datetime:
    """Choose a local wall-clock value; only a preview can consume an override."""
    if not preview_mode or forced_local_datetime is None:
        return system_local_now
    if forced_local_datetime.tzinfo is None:
        return forced_local_datetime.replace(tzinfo=system_local_now.tzinfo)
    return forced_local_datetime.astimezone(system_local_now.tzinfo)


def new_year_countdown_seconds(local_now: datetime) -> int | None:
    """Return seconds until local midnight during Dec 31's final minute, else None."""
    if (local_now.month, local_now.day, local_now.hour, local_now.minute) != (12, 31, 23, 59):
        return None
    midnight = (local_now + timedelta(minutes=1)).replace(second=0, microsecond=0)
    return max(0, math.ceil((midnight - local_now).total_seconds()))
