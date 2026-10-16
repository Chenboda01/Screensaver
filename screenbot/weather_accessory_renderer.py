"""Head-local rendering adapter for Bob's separate Live Sky appearance layer."""
from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Protocol, assert_never

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPen, QPainterPath

from bobos import BobOSStatus
from live_sky import SkyPosition
from live_sky_network import LiveWeather
from screenbot.appearance import BobAppearance
from screenbot.weather_accessories import (
    AccessoryOpacity,
    BobWeatherLook,
    DEFAULT_LOOK,
    WeatherAccessory,
    WeatherAccessoryRequest,
    WeatherConditions,
    WeatherPreview,
    WeatherReaction,
    compose_weather_accessories,
    parse_weather_category,
    resolve_weather_look,
    transition_accessories,
)


TRANSITION_SECONDS = 1.15


class WeatherAccessoryAnimator:
    """Keep state between frames so accessories fade and slide on weather changes."""

    def __init__(self) -> None:
        self._previous: tuple[WeatherAccessory, ...] = ()
        self._target: tuple[WeatherAccessory, ...] = ()
        self._transition_started_at = 0.0
        self._look = DEFAULT_LOOK
        self._last_key: tuple[BobWeatherLook, float, str] | None = None
        self._last_frame: tuple[BobWeatherLook, tuple[AccessoryOpacity, ...]] = (DEFAULT_LOOK, ())

    def update(
        self,
        look: BobWeatherLook,
        elapsed_seconds: float,
        custom_accessory: str,
    ) -> tuple[BobWeatherLook, tuple[AccessoryOpacity, ...]]:
        """Advance one resolved frame and return its look plus visible layers."""
        key = (look, elapsed_seconds, custom_accessory)
        if key == self._last_key:
            return self._last_frame
        target = compose_weather_accessories(custom_accessory, look.accessories)
        if target != self._target:
            self._previous = self._target
            self._target = target
            self._transition_started_at = elapsed_seconds
        self._look = BobWeatherLook(
            target,
            look.reaction,
            look.extra_tilt_degrees,
            look.scarf_flutter,
            look.sleepy_extension_seconds,
        )
        progress = (elapsed_seconds - self._transition_started_at) / TRANSITION_SECONDS
        self._last_key = key
        self._last_frame = (self._look, transition_accessories(self._previous, self._target, progress))
        return self._last_frame


class WeatherAccessoryHost(Protocol):
    """Structural contract supplied by Saver to this rendering mixin."""

    live_weather: LiveWeather
    live_sky_position: SkyPosition | None
    live_sky_enabled: bool
    bob_weather_enabled: bool
    theme: str
    preview_weather_override: WeatherPreview | None
    weather_accessory_animator: WeatherAccessoryAnimator
    bob_appearance: BobAppearance
    lightning_events: list[tuple[float, float, float]]
    reduce_motion: bool


class WeatherAccessoryRenderer:
    """Implement BobRenderer weather hooks without owning custom appearance."""

    def weather_look(
        self: WeatherAccessoryHost,
        elapsed_seconds: float,
    ) -> tuple[BobWeatherLook, tuple[AccessoryOpacity, ...]]:
        """Resolve the current Live Sky and preview values once at the painter seam."""
        sky = self.live_sky_position
        live = self.live_weather
        conditions = WeatherConditions(
            category=parse_weather_category(live.weather.category),
            fresh=live.fresh,
            sun_altitude=sky.sun_altitude if sky is not None else None,
            moon_altitude=sky.moon_altitude if sky is not None else None,
            wind_speed=live.weather.wind,
            lightning_flash=self._lightning_visible(elapsed_seconds),
        )
        request = WeatherAccessoryRequest(
            conditions=conditions,
            live_sky_enabled=self.live_sky_enabled,
            enabled=self.bob_weather_enabled,
            space_theme=self.theme == 'space',
            elapsed_seconds=elapsed_seconds,
            preview_override=self.preview_weather_override,
        )
        look = resolve_weather_look(request)
        return self.weather_accessory_animator.update(
            look, elapsed_seconds, self.bob_appearance.accessory
        )

    def _lightning_visible(self: WeatherAccessoryHost, elapsed_seconds: float) -> bool:
        """Match the scene effect's reduced-motion policy for Bob's reaction."""
        for index, (offset, period, _x) in enumerate(self.lightning_events):
            if self.reduce_motion and index % 2:
                continue
            phase = (elapsed_seconds + offset) % period
            if phase < (0.12 if self.reduce_motion else 0.2):
                return True
        return False

    def weather_mood_override(
        self: WeatherAccessoryHost,
        status: BobOSStatus,
        elapsed_seconds: float,
    ) -> str | None:
        """Map an active weather reaction to Bob's existing expression vocabulary."""
        del status
        look, _layers = self.weather_look(elapsed_seconds)
        match look.reaction:
            case WeatherReaction.SQUINT:
                return 'squint'
            case WeatherReaction.CURIOUS:
                return 'curious'
            case WeatherReaction.SURPRISED:
                return 'surprised'
            case WeatherReaction.LOOK_UP:
                return 'look-up'
            case WeatherReaction.SLEEPY:
                return 'sleepy'
            case WeatherReaction.NONE:
                return None
            case unreachable:
                assert_never(unreachable)

    def weather_tilt_degrees(
        self: WeatherAccessoryHost,
        status: BobOSStatus,
        elapsed_seconds: float,
    ) -> float:
        """Return the bounded Live Sky wind tilt in head-local degrees."""
        del status
        look, _layers = self.weather_look(elapsed_seconds)
        return look.extra_tilt_degrees

    def draw_weather_accessory(
        self: WeatherAccessoryHost,
        painter: QPainter,
        elapsed_seconds: float,
        palette: Mapping[str, tuple[int, int, int]],
    ) -> None:
        """Paint weather accessories in Bob's transformed coordinates."""
        _look, layers = self.weather_look(elapsed_seconds)
        accent = QColor(*palette['outline'])
        for layer in layers:
            painter.save()
            painter.setOpacity(painter.opacity() * layer.opacity)
            painter.translate(0.0, layer.slide_y)
            self._paint_accessory(
                painter, layer.accessory, accent, elapsed_seconds, _look.scarf_flutter
            )
            painter.restore()

    @staticmethod
    def _paint_accessory(
        painter: QPainter,
        accessory: WeatherAccessory,
        accent: QColor,
        elapsed_seconds: float,
        scarf_flutter: float,
    ) -> None:
        """Draw one simple head-only item with a consistent cyan accent."""
        painter.save()
        painter.setPen(QPen(accent, 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        match accessory:
            case WeatherAccessory.UMBRELLA:
                painter.setBrush(QColor(19, 55, 86, 238))
                canopy = QPainterPath()
                canopy.moveTo(-78, -111)
                canopy.quadTo(-68, -153, 0, -153)
                canopy.quadTo(68, -153, 78, -111)
                canopy.quadTo(57, -119, 39, -108)
                canopy.quadTo(20, -120, 0, -108)
                canopy.quadTo(-20, -120, -39, -108)
                canopy.quadTo(-58, -119, -78, -111)
                painter.drawPath(canopy)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawLine(QPointF(0, -111), QPointF(0, -89))
                painter.drawArc(QRectF(-7, -96, 15, 16), 180 * 16, -180 * 16)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor('#d8f7ff'))
                for index in range(3):
                    bounce = abs(math.sin(elapsed_seconds * 7.0 + index)) * 5.0
                    painter.drawEllipse(QPointF(-34 + index * 34, -105 - bounce), 2.2, 2.2)
            case WeatherAccessory.SUNGLASSES:
                painter.setBrush(QColor(6, 22, 43, 235))
                painter.drawRoundedRect(QRectF(-55, -34, 43, 27), 9, 9)
                painter.drawRoundedRect(QRectF(12, -34, 43, 27), 9, 9)
                painter.drawLine(QPointF(-12, -22), QPointF(12, -22))
                painter.drawLine(QPointF(-55, -26), QPointF(-65, -30))
                painter.drawLine(QPointF(55, -26), QPointF(65, -30))
            case WeatherAccessory.WOOL_HAT:
                painter.setBrush(QColor('#1b5366'))
                painter.drawRoundedRect(QRectF(-62, -129, 124, 49), 30, 25)
                painter.drawRoundedRect(QRectF(-69, -91, 138, 15), 7, 7)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor('#dffbff'))
                painter.drawEllipse(QPointF(0, -134), 8, 8)
            case WeatherAccessory.SCARF:
                flutter = math.sin(elapsed_seconds * 8.0) * 7.0 * scarf_flutter
                painter.setBrush(QColor('#287b87'))
                painter.drawRoundedRect(QRectF(-58, 48, 116, 21), 9, 9)
                scarf_tail = QPainterPath()
                scarf_tail.moveTo(37, 62)
                scarf_tail.quadTo(49, 72 + flutter, 44 + flutter, 93)
                scarf_tail.lineTo(27 + flutter, 88)
                scarf_tail.quadTo(34, 72, 29, 62)
                scarf_tail.closeSubpath()
                painter.drawPath(scarf_tail)
            case WeatherAccessory.NIGHTCAP:
                painter.setBrush(QColor('#2e477a'))
                cap = QPainterPath()
                cap.moveTo(-58, -90)
                cap.quadTo(-47, -130, 6, -124)
                cap.quadTo(24, -120, 47, -143)
                cap.quadTo(44, -117, 61, -107)
                cap.quadTo(7, -83, -58, -90)
                painter.drawPath(cap)
                painter.drawRoundedRect(QRectF(-61, -94, 122, 12), 6, 6)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor('#effbff'))
                painter.drawEllipse(QPointF(49, -145), 6, 6)
            case unreachable:
                assert_never(unreachable)
        painter.restore()
