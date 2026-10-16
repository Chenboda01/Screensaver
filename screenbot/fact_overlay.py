"""Responsive fact-card rendering and collision avoidance for ScreenBot."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping

from PyQt6.QtCore import QLocale, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QPen

from bobos import BobOSPhase
from screenbot.burnin import burn_in_clock_drift
from screenbot.facts import FactCycler, category_for_scene


FACT_FADE_SECONDS = 1.35
FACT_CARD_MAX_WIDTH = 420.0
FACT_CARD_MIN_WIDTH = 120.0
FACT_CARD_MAX_CHARS = 150


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


def wrap_two_lines(text: str, font: QFont, width: float) -> tuple[str, ...]:
    """Wrap text to at most two visually measured lines, eliding excess words."""
    metrics = QFontMetricsF(font)
    words = " ".join(str(text).split()).split(" ")
    lines: list[str] = []
    current = ""
    index = 0
    while index < len(words):
        candidate = f"{current} {words[index]}".strip()
        if current and metrics.horizontalAdvance(candidate) > width:
            lines.append(current)
            current = ""
            if len(lines) == 2:
                break
            continue
        if not current and metrics.horizontalAdvance(candidate) > width:
            candidate = metrics.elidedText(candidate, Qt.TextElideMode.ElideRight, int(width))
        current = candidate
        index += 1
    if current and len(lines) < 2:
        lines.append(current)
    if index < len(words) and lines:
        lines[-1] = metrics.elidedText(lines[-1] + " …", Qt.TextElideMode.ElideRight, int(width))
    return tuple(lines[:2])


def _intersects_any(rect: QRectF, obstacles: tuple[QRectF, ...]) -> bool:
    return any(rect.intersects(obstacle) for obstacle in obstacles)


def fact_card_rect(
    width: int,
    height: int,
    obstacles: tuple[QRectF, ...] = (),
) -> QRectF | None:
    """Choose a compact free corner/side slot; return None on crowded layouts."""
    if width < 280 or height < 220:
        return None
    card_width = min(FACT_CARD_MAX_WIDTH, width * .23)
    card_width = max(FACT_CARD_MIN_WIDTH, card_width)
    if card_width >= width * .40:
        card_width = width * .23
    if card_width < FACT_CARD_MIN_WIDTH:
        return None
    card_height = min(114.0, max(76.0, height * .18))
    margin = max(12.0, min(22.0, width * .018))
    xs = (margin, width - margin - card_width)
    ys = (margin, height * .56)
    candidates = [QRectF(x, y, card_width, card_height) for y in ys for x in xs]
    for candidate in candidates:
        if (candidate.left() >= margin and candidate.right() <= width - margin
                and candidate.top() >= margin and candidate.bottom() <= height * .78
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
        self._fact_current: dict[str, str] | None = None
        self._fact_next: dict[str, str] | None = None
        self._fact_category: str | None = None
        self._fact_started_at: float | None = None

    def fact_card_geometry(self, width: int, height: int, elapsed: float) -> QRectF | None:
        obstacles: list[QRectF] = [
            QRectF(0, height * .78, width, height * .22),  # Bob narration and exit hint
            QRectF(0, height * .84, width, height * .12),  # optional KDE lock countdown
        ]
        scale = min(width / 1250, height / 800, 1.35)
        sway = min(width * .075, 85)
        # Includes Bob's glow, animated floating range, ears, and his small phone.
        obstacles.append(QRectF(width * .5 - sway - 210 * scale,
                                height * .56 - 9 - 200 * scale,
                                2 * sway + 420 * scale, 18 + 320 * scale))

        if getattr(self, "show_clock", False):
            row, column = self.clock_position.split("-")
            x = {"left": .035, "center": .29, "right": .545}[column] * width
            y = {"top": .08, "center": .38, "bottom": .65}[row] * height
            conditions = (getattr(self, "live_sky_enabled", False)
                          and getattr(self, "live_sky_conditions", False)
                          and getattr(self, "theme", "") != "space")
            clock_height = self.clock_font_size * (
                1.5 + .62 * (bool(self.show_date) + conditions)
            )
            scene_offset = (0.0, 0.0)
            scene_scale = 1.0
            if getattr(self, "burn_in_protection", "off") != "off":
                from screenbot.burnin import burn_in_scene_scale, burn_in_scene_shift
                scene_offset = burn_in_scene_shift(self.burn_in_protection, elapsed)
                scene_scale = burn_in_scene_scale(width, height)
            drift_x, drift_y = burn_in_clock_drift(
                getattr(self, "burn_in_protection", "off"), elapsed, width, height,
                self.clock_position, self.clock_font_size, bool(self.show_date),
                conditions, scene_offset, scene_scale,
            )
            obstacles.append(QRectF(x + drift_x, y + drift_y, width * .42, clock_height))

        if getattr(self, "now_playing_enabled", False) and getattr(self, "now_playing", None):
            media_rect = getattr(self, "media_card_rect", None)
            if callable(media_rect):
                obstacles.append(media_rect())
        if (getattr(self, "agent_status_enabled", False)
                and getattr(getattr(self, "agent_status", None), "phase", None)
                and str(getattr(self.agent_status.phase, "value", "")) not in ("hidden", "unknown")):
            badge_width = min(370, max(180, width - 24))
            obstacles.append(QRectF(width - badge_width - 18, height - 62, badge_width, 44))
        return fact_card_rect(width, height, tuple(obstacles))

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

    def _advance_facts(self, elapsed: float, weather: str, full_moon: bool) -> tuple[float, float]:
        category, _, _ = self._fact_sky_category()
        interval = self.facts_interval_minutes * 60.0
        if self._fact_current is None or self._fact_category != category:
            self._fact_category = category
            self._fact_current = self._choose_fact(weather, full_moon)
            self._fact_next = self._choose_fact(weather, full_moon)
            self._fact_started_at = elapsed
        assert self._fact_started_at is not None
        while elapsed - self._fact_started_at >= interval:
            self._fact_current = self._fact_next
            self._fact_next = self._choose_fact(weather, full_moon)
            self._fact_started_at += interval
        phase = max(0.0, elapsed - self._fact_started_at)
        fade = min(FACT_FADE_SECONDS, interval / 2)
        if phase >= interval - fade:
            outgoing = min(1.0, (phase - (interval - fade)) / fade)
            return 1.0 - outgoing, outgoing
        return 1.0, 0.0

    @staticmethod
    def _draw_text(painter: QPainter, rect: QRectF, fact: Mapping[str, str], alpha: float) -> None:
        if alpha <= 0:
            return
        painter.save()
        painter.setOpacity(alpha)
        is_quote = fact.get("kind") == "quote"
        title = "BOB SAYS" if is_quote else "DID YOU KNOW?"
        painter.setPen(QColor("#83e8ff" if is_quote else "#9ce7a8"))
        title_font = QFont("Sans Serif", max(9, min(12, round(rect.width() * .032))), QFont.Weight.Bold)
        painter.setFont(title_font)
        painter.drawText(QRectF(rect.x() + 13, rect.y() + 9, rect.width() - 26, 17),
                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, title)
        text_font = QFont("Sans Serif", max(9, min(15, round(rect.width() * .035))))
        painter.setFont(text_font)
        lines = wrap_two_lines(fact.get("text", ""), text_font, rect.width() - 28)
        line_text = "\n".join(lines)
        text_rect = QRectF(rect.x() + 14, rect.y() + 29, rect.width() - 28, rect.height() - 37)
        painter.setPen(QColor("#f3f8ff"))
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
                         | Qt.TextFlag.TextWordWrap, line_text)
        painter.restore()

    def draw_fact_overlay(self, painter: QPainter, width: int, height: int,
                          elapsed: float, phase: BobOSPhase) -> None:
        if not self.facts_enabled or phase is not BobOSPhase.EXPLORING:
            return
        rect = self.fact_card_geometry(width, height, elapsed)
        if rect is None:
            return
        _, weather, full_moon = self._fact_sky_category()
        current_alpha, next_alpha = self._advance_facts(elapsed, weather, full_moon)
        painter.save()
        painter.setPen(QPen(QColor(136, 212, 244, 190), 1.2))
        painter.setBrush(QColor(7, 20, 38, 218))
        painter.drawRoundedRect(rect, 16, 16)
        assert self._fact_current is not None and self._fact_next is not None
        self._draw_text(painter, rect, self._fact_current, current_alpha)
        if next_alpha > 0:
            self._draw_text(painter, rect, self._fact_next, next_alpha)
        painter.restore()
