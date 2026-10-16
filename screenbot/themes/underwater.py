"""Fictional underwater scene layers; surface precipitation becomes ripples."""
from __future__ import annotations

import math
from typing import Final

from PyQt6.QtCore import QPointF, QRect, QRectF, Qt
from PyQt6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen, QPolygonF

from screenbot.themes.environment import ThemeEnvironment, ThemeFrame

BUBBLE_COUNT: Final = 11
FISH_COUNT: Final = 4


def _daylight(environment: ThemeEnvironment) -> float:
    sky = environment.sky
    if not environment.live_sky_enabled or sky is None:
        return .45
    return min(1.0, max(0.0, (sky.sun_altitude + 12.0) / 30.0))


def draw_background(painter: QPainter, frame: ThemeFrame) -> None:
    """Paint water, sunlit beams, sea floor and simple coral silhouettes."""
    daylight = _daylight(frame.environment)
    top = QColor(round(2 + 7 * daylight), round(19 + 88 * daylight), round(47 + 121 * daylight))
    bottom = QColor(round(1 + 2 * daylight), round(12 + 10 * daylight), round(32 + 24 * daylight))
    water = QLinearGradient(0, 0, 0, frame.height)
    water.setColorAt(0.0, top)
    water.setColorAt(.72, QColor(4, round(46 + 33 * daylight), round(79 + 44 * daylight)))
    water.setColorAt(1.0, bottom)
    painter.fillRect(QRect(0, 0, frame.width, frame.height), water)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(21, 50, 58))
    painter.drawPolygon(QPolygonF([QPointF(0, frame.height * .88), QPointF(frame.width * .16, frame.height * .83),
                                   QPointF(frame.width * .32, frame.height * .90), QPointF(frame.width * .52, frame.height * .84),
                                   QPointF(frame.width * .78, frame.height * .91), QPointF(frame.width, frame.height * .85),
                                   QPointF(frame.width, frame.height), QPointF(0, frame.height)]))
    _draw_coral(painter, QPointF(frame.width * .16, frame.height * .89), frame.height * .16)
    _draw_coral(painter, QPointF(frame.width * .79, frame.height * .90), frame.height * .12)
    painter.setBrush(QColor(45, 110, 89, round(110 + 95 * (1.0 - daylight))))
    painter.drawEllipse(QPointF(frame.width * .51, frame.height * .90), frame.width * .07, frame.height * .035)


def _draw_coral(painter: QPainter, base: QPointF, size: float) -> None:
    painter.save()
    painter.setPen(QPen(QColor("#e77c87"), max(2, size * .11), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    for index in range(3):
        x = base.x() + index * size * .22
        path = QPainterPath(QPointF(x, base.y()))
        path.cubicTo(QPointF(x - size * .08, base.y() - size * .45),
                     QPointF(x + size * .08, base.y() - size * .55),
                     QPointF(x, base.y() - size * (.72 + index * .06)))
        painter.drawPath(path)
    painter.restore()


def draw_motion(painter: QPainter, frame: ThemeFrame) -> None:
    """Draw a bounded set of sun rays, bubbles, fish and jellyfish."""
    daylight = _daylight(frame.environment)
    if daylight > .08:
        _draw_rays(painter, frame, daylight)
    _draw_bubbles(painter, frame)
    _draw_fish(painter, frame)
    _draw_jellyfish(painter, frame, daylight)


def _draw_rays(painter: QPainter, frame: ThemeFrame, daylight: float) -> None:
    painter.save()
    painter.setClipRect(QRect(0, 0, frame.width, round(frame.height * .73)))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setOpacity(min(1.0, max(0.0, daylight * frame.bounded_motion_scale * .45)))
    for index in range(5):
        drift = math.sin(frame.elapsed * .12 + index) * frame.width * .025
        x = frame.width * (.08 + index * .2) + drift
        path = QPolygonF([QPointF(x, 0), QPointF(x + frame.width * .035, 0),
                          QPointF(x + frame.width * (.16 + index * .006), frame.height * .73),
                          QPointF(x - frame.width * (.02 + index * .003), frame.height * .73)])
        painter.setBrush(QColor(156, 232, 244, 50))
        painter.drawPolygon(path)
    painter.restore()


def _draw_bubbles(painter: QPainter, frame: ThemeFrame) -> None:
    painter.save()
    painter.setPen(QPen(QColor(173, 239, 246, 135), max(1, frame.width * .0015)))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    for index in range(BUBBLE_COUNT):
        progress = (frame.elapsed * (.035 + (index % 3) * .008) + index * .137) % 1.0
        x = frame.width * ((index * .6180339) % 1.0) + math.sin(frame.elapsed * .55 + index) * frame.width * .012
        y = frame.height * (.91 - progress * .82)
        radius = frame.width * (.003 + index % 4 * .0008)
        painter.setOpacity((.35 + .55 * (index % 2)) * frame.bounded_motion_scale)
        painter.drawEllipse(QPointF(x, y), radius, radius)
    painter.restore()


def _draw_fish(painter: QPainter, frame: ThemeFrame) -> None:
    painter.save()
    painter.setPen(Qt.PenStyle.NoPen)
    for index in range(FISH_COUNT):
        progress = (frame.elapsed * (.025 + index * .003) + index * .27) % 1.0
        x = frame.width * (-.08 + progress * 1.16)
        y = frame.height * (.34 + index * .105 + math.sin(frame.elapsed * .4 + index) * .025)
        scale = frame.width * (.014 + index % 2 * .003)
        painter.setOpacity(.7 * frame.bounded_motion_scale)
        painter.setBrush(QColor(94, 206, 199) if index % 2 == 0 else QColor(248, 178, 125))
        painter.drawEllipse(QPointF(x, y), scale, scale * .48)
        painter.drawPolygon(QPolygonF([QPointF(x - scale, y), QPointF(x - scale * 1.7, y - scale * .45),
                                       QPointF(x - scale * 1.7, y + scale * .45)]))
        painter.setBrush(QColor("#08253c"))
        painter.drawEllipse(QPointF(x + scale * .45, y - scale * .07), max(1, scale * .09), max(1, scale * .09))
    painter.restore()


def _draw_jellyfish(painter: QPainter, frame: ThemeFrame, daylight: float) -> None:
    painter.save()
    for index in range(2):
        x = frame.width * (.31 + index * .43) + math.sin(frame.elapsed * .16 + index) * frame.width * .025
        y = frame.height * (.35 + index * .16) + math.sin(frame.elapsed * .24 + index) * frame.height * .02
        radius = frame.width * .018
        painter.setOpacity(.6 * frame.bounded_motion_scale)
        painter.setPen(QPen(QColor(151, 237, 255, 135), max(1, frame.width * .001)))
        painter.setBrush(QColor(117, 101, 235, round(95 + 100 * (1.0 - daylight))))
        painter.drawEllipse(QRectF(x - radius, y - radius * .65, radius * 2, radius * 1.3))
        for strand in range(4):
            sway = math.sin(frame.elapsed * .8 + strand + index) * radius * .18
            painter.drawLine(QPointF(x - radius * .7 + strand * radius * .45, y),
                             QPointF(x - radius * .7 + strand * radius * .45 + sway, y + radius * 1.2))
    painter.restore()


def draw_surface_ripples(painter: QPainter, frame: ThemeFrame) -> None:
    """Represent rain, snow, or storms as ripples without falling particles."""
    environment = frame.environment
    weather = environment.weather
    if environment.live_sky_enabled:
        if weather.category not in ("rain", "snow", "thunderstorm"):
            return
        intensity = weather.intensity
    elif environment.manual_surface_precipitation:
        intensity = .45
    else:
        return
    painter.save()
    painter.setClipRect(QRect(0, 0, frame.width, round(frame.height * .08)))
    painter.setPen(QPen(QColor(187, 238, 247, round(145 * frame.bounded_motion_scale)),
                        max(1, frame.width * .0015)))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    for index in range(round(4 + intensity * 8)):
        progress = (frame.elapsed * .22 + index * .23) % 1.0
        x = frame.width * ((index * .6180339) % 1.0)
        y = frame.height * .035
        painter.drawEllipse(QPointF(x, y), 3 + progress * 14, 1 + progress * 4)
    painter.restore()


def draw_bob_diving_helmet(painter: QPainter, center: QPointF, radius: float) -> None:
    """Draw a separate transparent helmet overlay around Bob's head."""
    painter.save()
    painter.setPen(QPen(QColor(153, 238, 255, 205), max(2, radius * .055)))
    painter.setBrush(QColor(74, 177, 207, 35))
    painter.drawEllipse(center, radius * 1.28, radius * 1.15)
    painter.setPen(QPen(QColor(220, 249, 255, 145), max(1, radius * .025)))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawArc(QRectF(center.x() - radius * 1.05, center.y() - radius * 1.22,
                           radius * 2.1, radius * 1.8), 25 * 16, 130 * 16)
    painter.restore()
