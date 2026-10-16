"""Responsive fact-card rendering and collision avoidance for ScreenBot."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping

from PyQt6.QtCore import QLocale, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QPen

from bobos import BobOSPhase
from screenbot.facts import FactCycler, category_for_scene, localized_labels


FACT_FADE_SECONDS = 1.35
FACT_CARD_MAX_CHARS = 150


def fact_font_size(width: float) -> int:
    return max(10, min(16, round(width * .026)))


@dataclass(frozen=True, slots=True)
class FactPreferences:
    enabled: bool = True
    interval_minutes: int = 3
    content_mode: str = "facts"

    @classmethod
    def from_settings(cls, settings) -> "FactPreferences":
        try:
            enabled = settings.getboolean("Screensaver", "facts_enabled", fallback=True)
        except (ValueError, AttributeError):
            enabled = True
        try:
            interval = settings.getint("Screensaver", "facts_interval_minutes", fallback=3)
        except (ValueError, AttributeError):
            interval = 3
        interval = max(2, min(5, interval))
        try:
            mode = settings.get("Screensaver", "facts_content_mode", fallback="facts").strip().lower()
        except (ValueError, AttributeError):
            mode = "facts"
        if mode not in {"facts", "quotes", "both"}:
            mode = "facts"
        return cls(enabled, interval, mode)


def wrap_complete_text(text: str, font: QFont, width: float) -> tuple[str, ...]:
    """Wrap text at word boundaries without removing any displayed content."""
    metrics = QFontMetricsF(font)
    normalized = " ".join(str(text).split())
    words = normalized.split(" ") if normalized else []
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and metrics.horizontalAdvance(candidate) > width:
            lines.append(current)
            current = word
        else:
            current = candidate
        if metrics.horizontalAdvance(current) > width:
            return ()
    if current:
        lines.append(current)
    return tuple(lines)


def _intersects_any(rect: QRectF, obstacles: tuple[QRectF, ...]) -> bool:
    return any(rect.intersects(obstacle) for obstacle in obstacles)


def fact_card_rect(
    width: int,
    height: int,
    obstacles: tuple[QRectF, ...] = (),
    text: str | tuple[str, ...] = "",
) -> QRectF | None:
    """Find a free measured layout that can display the entire localized sentence."""
    if width < 280 or height < 220:
        return None
    margin = max(12.0, min(22.0, width * .018))
    max_width = min(width * .88, 920.0)
    min_width = max(180.0, min(width * .22, 230.0))
    max_height = min(height * .32, 230.0)
    # Search widths from most readable to most compact. Large screens also cap
    # the card width so long lines remain easy to scan.
    card_widths = [float(value) for value in range(int(max_width), int(min_width) - 1, -12)]
    card_widths.append(min_width)
    texts = (text,) if isinstance(text, str) else text
    for card_width in card_widths:
        if card_width > width - margin * 2:
            continue
        xs = (margin, width - margin - card_width, (width - card_width) / 2)
        for font_size in (fact_font_size(card_width),):
            font = QFont("Sans Serif", font_size)
            line_sets = tuple(wrap_complete_text(item, font, card_width - 28) for item in texts)
            if not line_sets or any(not lines for lines in line_sets):
                continue
            metrics = QFontMetricsF(font)
            card_height = 34 + max(map(len, line_sets)) * metrics.height()
            if card_height > max_height:
                continue
            ys = {margin, height * .18, height * .38, height * .54,
                  height * .76 - card_height - margin}
            ys.update(obstacle.bottom() + margin for obstacle in obstacles)
            ys.update(obstacle.top() - card_height - margin for obstacle in obstacles)
            for y in sorted(ys):
                for x in xs:
                    candidate = QRectF(x, y, card_width, card_height)
                    if (candidate.left() >= margin
                            and candidate.right() <= width - margin
                            and candidate.top() >= margin
                            and candidate.bottom() <= height * .78
                            and not _intersects_any(candidate, obstacles)):
                        return candidate
    return None


class FactOverlayMixin:
    """Paint one theme-aware fact, fading to the next without scene overlap."""

    def init_fact_overlay(self, preferences: FactPreferences) -> None:
        self.facts_enabled = preferences.enabled
        self.facts_interval_minutes = preferences.interval_minutes
        self.facts_content_mode = preferences.content_mode
        language_preference = os.environ.get("LANGUAGE", "").split(":", 1)[0]
        self.fact_cycler = FactCycler(locale=language_preference or QLocale.system().name())
        locale = language_preference or QLocale.system().name()
        self.fact_labels = localized_labels(locale)
        self._fact_states: dict[str, dict[str, object]] = {}
        self._fact_category: str | None = None
        self._fact_current: dict[str, str] | None = None
        self._fact_next: dict[str, str] | None = None
        self._fact_started_at: float | None = None

    def fact_card_geometry(self, width: int, height: int, elapsed: float,
                           text: str | None = None) -> QRectF | None:
        obstacles: list[QRectF] = [
            QRectF(0, height * .78, width, height * .22),  # Bob narration and exit hint
            QRectF(0, height * .84, width, height * .12),  # optional KDE lock countdown
        ]
        bob_bounds = getattr(self, "bob_safe_bounds", None)
        if callable(bob_bounds):
            obstacles.append(bob_bounds(width, height))

        if getattr(self, "show_clock", False):
            row, column = self.clock_position.split("-")
            scene_offset = (0.0, 0.0)
            scene_scale = 1.0
            if getattr(self, "burn_in_protection", "off") != "off":
                from screenbot.burnin import burn_in_scene_scale, burn_in_scene_shift
                scene_offset = burn_in_scene_shift(self.burn_in_protection, elapsed)
                scene_scale = burn_in_scene_scale(width, height)
            clock_bounds = getattr(self, "clock_bounds", None)
            if callable(clock_bounds):
                obstacles.append(clock_bounds(width, height, getattr(self, "burn_in_protection", "off"),
                                              elapsed, scene_offset, scene_scale))

        if getattr(self, "now_playing_enabled", False) and getattr(self, "now_playing", None):
            media_rect = getattr(self, "media_card_rect", None)
            if callable(media_rect):
                obstacles.append(media_rect())
        if (getattr(self, "agent_status_enabled", False)
                and getattr(getattr(self, "agent_status", None), "phase", None)
                and str(getattr(self.agent_status.phase, "value", "")) not in ("hidden", "unknown")):
            badge_width = min(370, max(180, width - 24))
            obstacles.append(QRectF(width - badge_width - 18, height - 62, badge_width, 44))
        displayed_text = text or (self._fact_current or {}).get("text", "")
        next_text = (self._fact_next or {}).get("text", displayed_text)
        return fact_card_rect(width, height, tuple(obstacles), (displayed_text, next_text))

    def _fact_sky_category(self) -> tuple[str, str, bool]:
        weather = "clear"
        if self.theme != "space":
            if getattr(self, "live_sky_enabled", False):
                observation = getattr(self, "live_weather", None)
                if observation is not None and getattr(observation, "fresh", False):
                    weather = observation.weather.category
            elif getattr(self, "rain_enabled", False):
                weather = "rain"
            elif getattr(self, "thunderstorms_enabled", False):
                weather = "thunderstorm"
            elif getattr(self, "snow_enabled", False):
                weather = "snow"
        sky = getattr(self, "live_sky_position", None)
        phase = getattr(sky, "moon_phase", None)
        visible = getattr(sky, "moon_altitude", -90) > 0
        full_moon = bool(getattr(self, "live_sky_enabled", False) and visible
                         and phase is not None and abs(float(phase) - .5) <= .055)
        category = category_for_scene(self.theme, weather, full_moon)
        return category, weather, full_moon

    def _choose_fact(self, weather: str, full_moon: bool) -> dict[str, str]:
        return self.fact_cycler.next(
            self.theme, weather, full_moon, content_mode=self.facts_content_mode
        )

    def pause_fact_overlay(self, elapsed: float) -> None:
        """Pause the active category's visible interval while the card is hidden."""
        if self._fact_category is None or self._fact_started_at is None:
            return
        state = self._fact_states.get(self._fact_category)
        if state is None:
            return
        if state.get("last_visible", False):
            state["phase"] = max(0.0, elapsed - self._fact_started_at)
        state["last_visible"] = False
        self._fact_started_at = elapsed - float(state["phase"])

    def pause_facts_for_bobos_status(self, status, elapsed: float):
        """Keep hidden phone phases from advancing or consuming fact entries."""
        if status.phase is not BobOSPhase.EXPLORING:
            self.pause_fact_overlay(elapsed)
        return status

    def _advance_facts(self, elapsed: float, weather: str, full_moon: bool,
                       visible: bool = True) -> tuple[float, float]:
        category, _, _ = self._fact_sky_category()
        interval = self.facts_interval_minutes * 60.0
        if self._fact_category != category:
            if self._fact_category and self._fact_started_at is not None:
                old_state = self._fact_states[self._fact_category]
                if old_state.get("last_visible", False):
                    old_state["phase"] = max(0.0, elapsed - self._fact_started_at)
            self._fact_category = category
            state = self._fact_states.get(category)
            if state is None:
                state = {
                    "current": self._choose_fact(weather, full_moon),
                    "next": self._choose_fact(weather, full_moon),
                    "phase": 0.0,
                }
                self._fact_states[category] = state
            self._fact_current = state["current"]
            self._fact_next = state["next"]
            self._fact_started_at = elapsed - float(state["phase"])
        assert self._fact_started_at is not None and self._fact_current is not None
        state = self._fact_states[category]
        if not visible:
            phase = float(state["phase"])
            self._fact_started_at = elapsed - phase
            state["last_visible"] = False
            return 1.0, 0.0
        while elapsed - self._fact_started_at >= interval:
            self._fact_current = self._fact_next
            self._fact_next = self._choose_fact(weather, full_moon)
            self._fact_started_at += interval
        state["current"] = self._fact_current
        state["next"] = self._fact_next
        phase = max(0.0, elapsed - self._fact_started_at)
        state["phase"] = phase
        state["last_visible"] = True
        fade = min(FACT_FADE_SECONDS, interval / 2)
        if phase >= interval - fade:
            outgoing = min(1.0, (phase - (interval - fade)) / fade)
            return 1.0 - outgoing, outgoing
        return 1.0, 0.0

    @staticmethod
    def _draw_text(painter: QPainter, rect: QRectF, fact: Mapping[str, str], alpha: float,
                   labels: Mapping[str, str]) -> None:
        if alpha <= 0:
            return
        painter.save()
        painter.setOpacity(alpha)
        is_quote = fact.get("kind") == "quote"
        title = labels["bob_says"] if is_quote else labels["did_you_know"]
        painter.setPen(QColor("#83e8ff" if is_quote else "#9ce7a8"))
        title_font = QFont("Sans Serif", max(9, min(12, round(rect.width() * .032))), QFont.Weight.Bold)
        painter.setFont(title_font)
        painter.drawText(QRectF(rect.x() + 13, rect.y() + 9, rect.width() - 26, 17),
                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, title)
        text_font = QFont("Sans Serif", fact_font_size(rect.width()))
        painter.setFont(text_font)
        lines = wrap_complete_text(fact.get("text", ""), text_font, rect.width() - 28)
        line_text = "\n".join(lines)
        text_rect = QRectF(rect.x() + 14, rect.y() + 29, rect.width() - 28, rect.height() - 35)
        painter.setPen(QColor("#f3f8ff"))
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
                         | Qt.TextFlag.TextWordWrap, line_text)
        painter.restore()

    def draw_fact_overlay(self, painter: QPainter, width: int, height: int,
                          elapsed: float, phase: BobOSPhase) -> None:
        if not self.facts_enabled or phase is not BobOSPhase.EXPLORING:
            return
        _, weather, full_moon = self._fact_sky_category()
        self._advance_facts(elapsed, weather, full_moon, visible=False)
        rect = self.fact_card_geometry(width, height, elapsed, self._fact_current["text"])
        if rect is None:
            return
        current_alpha, next_alpha = self._advance_facts(elapsed, weather, full_moon, visible=True)
        painter.save()
        painter.setPen(QPen(QColor(136, 212, 244, 190), 1.2))
        painter.setBrush(QColor(7, 20, 38, 218))
        painter.drawRoundedRect(rect, 16, 16)
        assert self._fact_current is not None and self._fact_next is not None
        self._draw_text(painter, rect, self._fact_current, current_alpha, self.fact_labels)
        if next_alpha > 0:
            self._draw_text(painter, rect, self._fact_next, next_alpha, self.fact_labels)
        painter.restore()
