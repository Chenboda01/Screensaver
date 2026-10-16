"""Warm dunes, cacti, daylight shimmer, and a cold starry desert night."""
from __future__ import annotations

import math
from typing import Final

from PyQt6.QtCore import QPointF, QRect, QRectF, Qt
from PyQt6.QtGui import (
    QColor,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPolygonF,
    QRadialGradient,
)

from live_sky_render import draw_sky
from screenbot.themes.environment import ThemeEnvironment, ThemeFrame

DUNES: Final = (
    (QColor("#b87b4e"), ((0, .66), (.15, .58), (.32, .69), (.51, .55), (.70, .68), (.88, .57), (1, .63))),
    (QColor("#d29a62"), ((0, .77), (.18, .66), (.37, .76), (.55, .65), (.74, .78), (.92, .67), (1, .73))),
    (QColor("#80563e"), ((0, .91), (.2, .79), (.4, .90), (.62, .78), (.8, .92), (.94, .82), (1, .88))),
)


def _daylight(environment: ThemeEnvironment) -> float:
    sky = environment.sky
    if not environment.live_sky_enabled or sky is None:
        return .72
    return min(1.0, max(0.0, (sky.sun_altitude + 12.0) / 60.0))


def draw_background(painter: QPainter, frame: ThemeFrame) -> None:
    """Paint live/offline atmosphere, layered dunes, stars, sun and cacti."""
    width, height = frame.width, frame.height
    environment = frame.environment
    if environment.live_sky_enabled and environment.sky is not None:
        draw_sky(painter, width, height, frame.elapsed, environment.sky, environment.weather)
    else:
        daylight = _daylight(environment)
        sky = QLinearGradient(0, 0, 0, height * .72)
        sky.setColorAt(0, QColor(round(4 + daylight * 47), round(12 + daylight * 104), round(31 + daylight * 132)))
        sky.setColorAt(1, QColor(round(30 + daylight * 220), round(45 + daylight * 145), round(72 + daylight * 80)))
        painter.fillRect(QRect(0, 0, width, height), sky)
        _draw_stars(painter, frame, 1.0 - daylight)
        _draw_sun_glow(painter, frame, daylight)
    painter.setPen(Qt.PenStyle.NoPen)
    for color, points in DUNES:
        path = QPolygonF([QPointF(x * width, y * height) for x, y in points]
                         + [QPointF(width, height), QPointF(0, height)])
        painter.setBrush(color)
        painter.drawPolygon(path)
    _draw_cactus(painter, QPointF(width * .22, height * .73), height * .19)
    _draw_cactus(painter, QPointF(width * .78, height * .72), height * .14)


def _draw_stars(painter: QPainter, frame: ThemeFrame, alpha: float) -> None:
    if alpha <= 0.0:
        return
    painter.setPen(Qt.PenStyle.NoPen)
    for index in range(74):
        x = ((index * .61803398875) % 1.0) * frame.width
        y = ((index * .41421356237) % 1.0) * frame.height * .58
        painter.setBrush(QColor(236, 239, 255, round((95 + index % 4 * 35) * alpha)))
        radius = 1.0 + index % 3 * .3
        painter.drawEllipse(QPointF(x, y), radius, radius)


def _draw_sun_glow(painter: QPainter, frame: ThemeFrame, daylight: float) -> None:
    if daylight <= .45:
        return
    center = QPointF(frame.width * .76, frame.height * .22)
    glow = QRadialGradient(center, frame.height * .22)
    glow.setColorAt(0.0, QColor(255, 226, 153, round(100 * daylight)))
    glow.setColorAt(1.0, QColor(255, 226, 153, 0))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(glow)
    painter.drawEllipse(center, frame.height * .22, frame.height * .22)
    painter.setBrush(QColor(255, 237, 180, round(180 * daylight)))
    painter.drawEllipse(center, frame.height * .027, frame.height * .027)


def _draw_cactus(painter: QPainter, base: QPointF, height: float) -> None:
    width = height * .14
    painter.save()
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#32654d"))
    painter.drawRoundedRect(QRectF(base.x() - width * .34, base.y() - height, width * .68, height), width * .32, width * .32)
    painter.drawRoundedRect(QRectF(base.x() - width, base.y() - height * .67, width * .38, height * .11), width * .18, width * .18)
    painter.drawRoundedRect(QRectF(base.x() - width, base.y() - height * .67, width * .21, height * .31), width * .10, width * .10)
    painter.drawRoundedRect(QRectF(base.x() + width * .35, base.y() - height * .52, width * .62, height * .11), width * .18, width * .18)
    painter.drawRoundedRect(QRectF(base.x() + width * .76, base.y() - height * .52, width * .21, height * .24), width * .10, width * .10)
    painter.restore()


def draw_motion(painter: QPainter, frame: ThemeFrame) -> None:
    """Add restrained daytime heat shimmer or a few quiet night meteors."""
    daylight = _daylight(frame.environment)
    if daylight > .45:
        _draw_heat_shimmer(painter, frame, daylight)
    elif frame.environment.live_sky_enabled and frame.environment.sky is not None:
        _draw_night_specks(painter, frame)


def _draw_heat_shimmer(painter: QPainter, frame: ThemeFrame, daylight: float) -> None:
    painter.save()
    painter.setOpacity((.18 + .14 * daylight) * frame.bounded_motion_scale)
    painter.setPen(QColor(255, 231, 185, 65))
    for index in range(4):
        y = frame.height * (.70 + index * .055) + math.sin(frame.elapsed * .42 + index) * frame.height * .004
        wave = QPainterPath(QPointF(0, y))
        for step in range(1, 25):
            x = frame.width * step / 24
            wave.lineTo(x, y + math.sin(step * .58 + frame.elapsed * .35 + index) * frame.height * .004)
        painter.drawPath(wave)
    painter.restore()


def _draw_night_specks(painter: QPainter, frame: ThemeFrame) -> None:
    painter.save()
    painter.setOpacity(frame.bounded_motion_scale)
    for index in range(3):
        progress = (frame.elapsed * (.025 + index * .004) + index * .31) % 1.0
        x = frame.width * (.08 + progress * .78)
        y = frame.height * (.08 + index * .12 + math.sin(frame.elapsed * .16 + index) * .025)
        painter.setPen(QColor(224, 239, 255, round(120 * (1.0 - progress))))
        painter.drawLine(QPointF(x, y), QPointF(x + frame.width * .018, y - frame.height * .009))
    painter.restore()
