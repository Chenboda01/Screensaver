"""Animated tropical coastline with wind-shaped water and a night beacon."""
from __future__ import annotations

import math
from typing import Final

from PyQt6.QtCore import QPointF, QRect, QRectF, Qt
from PyQt6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen, QPolygonF

from live_sky_render import draw_sky
from screenbot.themes.environment import ThemeFrame

PALMS: Final = ((.10, .48, .095), (.87, .51, .075))


def draw_background(painter: QPainter, frame: ThemeFrame) -> None:
    """Paint sky, ocean, beach, palms, and a small lighthouse."""
    width, height = frame.width, frame.height
    environment = frame.environment
    if environment.live_sky_enabled and environment.sky is not None:
        draw_sky(painter, width, height, frame.elapsed, environment.sky, environment.weather)
    else:
        sky = QLinearGradient(0, 0, 0, height * .62)
        sky.setColorAt(0, QColor("#102b52"))
        sky.setColorAt(.72, QColor("#ee9c79"))
        sky.setColorAt(1, QColor("#ffd09b"))
        painter.fillRect(QRect(0, 0, width, height), sky)
    horizon = height * .53
    water = QLinearGradient(0, horizon, 0, height * .91)
    water.setColorAt(0, QColor("#167b98"))
    water.setColorAt(1, QColor("#07536c"))
    painter.fillRect(QRectF(0, horizon, width, height * .39), water)
    beach = QLinearGradient(0, height * .79, 0, height)
    beach.setColorAt(0, QColor("#e6c17c"))
    beach.setColorAt(1, QColor("#8e6c49"))
    painter.fillRect(QRectF(0, height * .79, width, height * .21), beach)
    painter.setPen(Qt.PenStyle.NoPen)
    for x, crown_y, size in PALMS:
        trunk = QPainterPath(QPointF(width * x, height * .86))
        trunk.cubicTo(QPointF(width * (x - .03), height * .78),
                      QPointF(width * (x + .025), height * .72),
                      QPointF(width * (x + .01), height * crown_y))
        painter.setPen(QPen(QColor("#704c34"), max(3, width * .006), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawPath(trunk)
        painter.setPen(QPen(QColor("#23684e"), max(4, width * .009),
                            Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        center = QPointF(width * (x + .01), height * crown_y)
        for index in range(7):
            angle = math.radians(-160 + index * 23)
            end = center + QPointF(math.cos(angle) * width * size, math.sin(angle) * height * size * .55)
            frond = QPainterPath(center)
            frond.quadTo(center + QPointF(math.cos(angle) * width * size * .55,
                                          math.sin(angle) * height * size * .35 - height * .015), end)
            painter.drawPath(frond)
        painter.setPen(Qt.PenStyle.NoPen)
    _draw_lighthouse(painter, frame)


def _draw_lighthouse(painter: QPainter, frame: ThemeFrame) -> None:
    """Paint a small coastal beacon; its moving beam belongs to the motion pass."""
    width, height = frame.width, frame.height
    x, base = width * .75, height * .57
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#e6e4d9"))
    painter.drawPolygon(QPolygonF([QPointF(x - width * .012, base),
                                   QPointF(x + width * .012, base),
                                   QPointF(x + width * .008, base - height * .16),
                                   QPointF(x - width * .008, base - height * .16)]))
    painter.setBrush(QColor("#d85559"))
    painter.drawRect(QRectF(x - width * .012, base - height * .16, width * .024, height * .026))
    painter.setBrush(QColor("#fff0bd"))
    painter.drawRect(QRectF(x - width * .006, base - height * .145, width * .012, height * .022))


def draw_motion(painter: QPainter, frame: ThemeFrame) -> None:
    """Draw bounded wave crests, reflections, gulls, and a night lighthouse sweep."""
    environment = frame.environment
    motion = frame.bounded_motion_scale
    wind = environment.weather.wind if environment.live_sky_enabled else 8.0
    wave_height = frame.height * (.014 + .00014 * min(wind, 60.0))
    horizon = frame.height * .54
    painter.save()
    painter.setClipRect(QRect(0, round(horizon), frame.width, round(frame.height * .32)))
    for index in range(5):
        phase = frame.elapsed * (.35 + index * .035) + index * 1.7
        path = QPainterPath()
        for step in range(31):
            x = frame.width * step / 30
            progress = step / 30
            wave = (math.sin(progress * math.tau * 1.7 + phase) * wave_height
                    + math.sin(progress * math.tau * 3.3 - phase * .6) * wave_height * .14)
            y = horizon + frame.height * (.035 + index * .037) + wave
            if step == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
        alpha = round((70 + 18 * index) * motion)
        painter.setPen(QPen(QColor(148, 233, 231, alpha), max(1, frame.width * .0018)))
        painter.drawPath(path)
    if environment.live_sky_enabled and environment.sky is not None:
        sky = environment.sky
        if abs(sky.sun_altitude) < 10 or sky.moon_altitude > 0:
            phase = frame.elapsed * .3
            painter.setPen(QPen(QColor(255, 231, 163, round(24 * motion)), max(2, frame.width * .002)))
            for index in range(6):
                x = frame.width * (.44 + index * .018) + math.sin(phase + index) * frame.width * .008
                y = horizon + index * frame.height * .022
                painter.drawLine(QPointF(x, y), QPointF(x + frame.width * .013, y))
    painter.restore()
    _draw_gulls(painter, frame)
    if not environment.live_sky_enabled or (
            environment.sky is not None and environment.sky.sun_altitude < -6):
        _draw_lighthouse_beam(painter, frame)
    if environment.live_sky_enabled and environment.weather.category in ("rain", "thunderstorm"):
        _draw_rain_splashes(painter, frame)


def _draw_gulls(painter: QPainter, frame: ThemeFrame) -> None:
    painter.save()
    painter.setOpacity(frame.bounded_motion_scale)
    painter.setPen(QPen(QColor("#273d50"), max(1, frame.width * .0018), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    for index in range(3):
        x = (frame.width * (.22 + index * .18) + frame.elapsed * (7 + index * 2)) % frame.width
        y = frame.height * (.24 + index * .055) + math.sin(frame.elapsed * .7 + index) * frame.height * .008
        painter.drawArc(QRectF(x - frame.width * .012, y, frame.width * .012, frame.height * .012), 15 * 16, 145 * 16)
        painter.drawArc(QRectF(x, y, frame.width * .012, frame.height * .012), 20 * 16, 145 * 16)
    painter.restore()


def _draw_lighthouse_beam(painter: QPainter, frame: ThemeFrame) -> None:
    center = QPointF(frame.width * .75, frame.height * .42)
    angle = frame.elapsed * .18
    end = center + QPointF(math.cos(angle) * frame.width * .72, math.sin(angle) * frame.height * .30)
    path = QPainterPath(center)
    path.lineTo(end + QPointF(0, -frame.height * .025))
    path.lineTo(end + QPointF(0, frame.height * .025))
    path.closeSubpath()
    painter.save()
    painter.setOpacity(.18 * frame.bounded_motion_scale)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#ffe9aa"))
    painter.drawPath(path)
    painter.restore()


def _draw_rain_splashes(painter: QPainter, frame: ThemeFrame) -> None:
    painter.save()
    painter.setPen(QPen(QColor(205, 241, 245, round(100 * frame.bounded_motion_scale)), max(1, frame.width * .0012)))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    for index in range(round(5 + 7 * frame.environment.weather.intensity)):
        progress = (frame.elapsed * .72 + index * .19) % 1.0
        x = frame.width * ((index * .6180339) % 1.0)
        y = frame.height * (.54 + (index % 3) * .035)
        painter.drawEllipse(QPointF(x, y), 2 + progress * 5, 1 + progress * 2)
    painter.restore()
