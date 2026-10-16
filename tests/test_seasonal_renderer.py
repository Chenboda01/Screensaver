"""Offscreen render coverage for seasonal art on all supported themes."""

import os
from datetime import datetime

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtCore import Qt

from screenbot.seasonal import CalendarState, Hemisphere, Season, SeasonalEvent
from screenbot.seasonal_renderer import SeasonalRenderer


THEMES = ("space", "mountains", "snow", "forest", "city", "aurora", "ocean", "desert", "underwater")


@pytest.fixture(scope="module", autouse=True)
def app() -> QApplication:
    """Initialize Qt's font and paint services for offscreen frames."""
    return QApplication.instance() or QApplication([])


def render(theme: str, events: frozenset[SeasonalEvent], *, reduce_motion: bool = False,
           elapsed: float = 2.0, local_now: datetime = datetime(2026, 12, 24, 18, 0)) -> QImage:
    """Return a transparent canvas with only seasonal art painted into it."""
    image = QImage(960, 540, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    state = CalendarState(Hemisphere.NORTH, Season.WINTER, events)
    SeasonalRenderer.draw(painter, image.width(), image.height(), elapsed, theme,
                          local_now, state, "Pixel", reduce_motion)
    painter.end()
    return image


@pytest.mark.parametrize("theme", THEMES)
def test_winter_holiday_decorations_render_on_each_theme(theme: str) -> None:
    # Given winter holidays selected on a supported theme.
    events = frozenset({SeasonalEvent.WINTER_HOLIDAYS})
    # When the seasonal layer is drawn offscreen.
    image = render(theme, events)
    # Then the theme receives visible lights without requiring Live Sky data.
    assert not image.isNull()
    assert any(image.pixelColor(x, y).alpha() > 0
               for y in range(0, image.height(), 3)
               for x in range(0, image.width(), 3))
    if theme == "space":
        # Space receives holiday lights but never seasonal snowfall.
        assert image.pixelColor(50, 500).alpha() == 0


@pytest.mark.parametrize(
    "event,local_now",
    [
        (SeasonalEvent.NEW_YEAR, datetime(2027, 1, 1, 0, 0)),
        (SeasonalEvent.LUNAR_NEW_YEAR, datetime(2026, 2, 17, 12, 0)),
        (SeasonalEvent.VALENTINES_DAY, datetime(2026, 2, 14, 12, 0)),
        (SeasonalEvent.SPRING, datetime(2026, 4, 10, 12, 0)),
        (SeasonalEvent.HALLOWEEN, datetime(2026, 10, 31, 12, 0)),
        (SeasonalEvent.BIRTHDAY, datetime(2026, 7, 4, 12, 0)),
    ],
)
def test_event_layer_paints_visible_pixels(event: SeasonalEvent, local_now: datetime) -> None:
    # Given one active event and its local date.
    # When rendering the decoration layer over a theme.
    image = render("forest", frozenset({event}), local_now=local_now)
    # Then at least one visible pixel is produced.
    assert any(image.pixelColor(x, y).alpha() > 0
               for y in range(0, image.height(), 8)
               for x in range(0, image.width(), 8))


def test_disabled_events_draw_no_pixels() -> None:
    # Given the master setting produced an empty active-event set.
    # When drawing the seasonal layer.
    image = render("forest", frozenset())
    # Then the decoration layer is transparent at every pixel.
    assert all(image.pixelColor(x, y).alpha() == 0
               for y in range(image.height()) for x in range(image.width()))


def test_reduce_motion_keeps_seasonal_art_static_across_elapsed_time() -> None:
    # Given a reduced-motion event with active winter lights, snow, and holiday text.
    events = frozenset({SeasonalEvent.WINTER_HOLIDAYS})
    # When painting at different animation times with the same local date.
    first = render("forest", events, reduce_motion=True, elapsed=0.0)
    second = render("forest", events, reduce_motion=True, elapsed=100.0)
    # Then the seasonal layer does not animate.
    assert first == second


@pytest.mark.parametrize("event", list(SeasonalEvent))
def test_reduce_motion_freezes_each_enabled_event(event: SeasonalEvent) -> None:
    # Given one active calendar event and Reduce motion enabled.
    events = frozenset({event})
    # When drawing two elapsed-time samples for the same local date.
    first = render("forest", events, reduce_motion=True, elapsed=0.0,
                   local_now=datetime(2026, 1, 1, 0, 0))
    second = render("forest", events, reduce_motion=True, elapsed=45.0,
                    local_now=datetime(2026, 1, 1, 0, 0))
    # Then the selected event remains visually static.
    assert first == second


def test_new_year_countdown_is_visible_during_final_local_minute() -> None:
    # Given New Year Eve during its final local minute.
    events = frozenset({SeasonalEvent.NEW_YEAR})
    # When rendering at 23:59:30 local time.
    image = render("space", events, local_now=datetime(2026, 12, 31, 23, 59, 30))
    # Then the countdown panel paints in the upper-middle region.
    assert image.pixelColor(480, 153).alpha() > 0
