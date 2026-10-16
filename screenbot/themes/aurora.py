"""Aurora theme layers for a snowy northern landscape."""
from __future__ import annotations

import math
from typing import Final

from PyQt6.QtCore import QPointF, QRect, Qt
from PyQt6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen, QPolygonF

from live_sky_render import draw_sky
from screenbot.themes.environment import ThemeEnvironment, ThemeFrame

RIDGES: Final = (
    (QColor("#718fa6"), ((0, .75), (.12, .56), (.25, .72), (.40, .45), (.54, .74), (.71, .53), (.86, .72), (1, .55))),
    (QColor("#c4d5df"), ((0, .86), (.16, .69), (.30, .83), (.48, .60), (.64, .86), (.82, .65), (1, .82))),
    (QColor("#536f83"), ((0, .96), (.18, .79), (.35, .95), (.53, .75), (.74, .96), (.90, .82), (1, .94))),
)


def aurora_strength(environment: ThemeEnvironment) -> float:
    """Return bounded visibility; Live Sky requires a dark sky and attenuates light pollution."""
    if not environment.live_sky_enabled:
        return 0.82
    sky = environment.sky
    if sky is None or sky.sun_altitude >= -6.0:
        return 0.0
    night = min(1.0, max(0.0, (-6.0 - sky.sun_altitude) / 12.0))
    cloud_factor = 1.0 - 0.78 * min(1.0, max(0.0, environment.weather.cloud / 100.0))
    moon_illumination = (1.0 - math.cos(sky.moon_phase * math.tau)) / 2.0
    moon_factor = 1.0 - (0.62 * moon_illumination if sky.moon_altitude > 0.0 else 0.0)
    return night * cloud_factor * moon_factor


def draw_background(painter: QPainter, frame: ThemeFrame) -> None:
    """Paint a deterministic snowy ridge and Live Sky or offline night sky."""
    width, height = frame.width, frame.height
    environment = frame.environment
    if environment.live_sky_enabled and environment.sky is not None:
        draw_sky(painter, width, height, frame.elapsed, environment.sky, environment.weather)
    else:
        sky = QLinearGradient(0, 0, 0, height)
        sky.setColorAt(0, QColor("#061522"))
        sky.setColorAt(.70, QColor("#173a50"))
        sky.setColorAt(1, QColor("#466b78"))
        painter.fillRect(QRect(0, 0, width, height), sky)
    painter.setPen(Qt.PenStyle.NoPen)
    for color, points in RIDGES:
        polygon = QPolygonF([QPointF(x * width, y * height) for x, y in points]
                            + [QPointF(width, height), QPointF(0, height)])
        painter.setBrush(color)
        painter.drawPolygon(polygon)


def draw_motion(painter: QPainter, frame: ThemeFrame) -> None:
    """Draw three low-cost animated aurora ribbons above the ridge line."""
    intensity = aurora_strength(frame.environment) * frame.bounded_motion_scale
    if intensity <= 0.0:
        return
    painter.save()
    painter.setClipRect(QRect(0, 0, frame.width, round(frame.height * .44)))
    painter.setPen(Qt.PenStyle.NoPen)
    for index, (base_color, offset) in enumerate((("#48ffc2", .0), ("#42dce8", .08), ("#b889ff", .16))):
        path = QPainterPath()
        samples = 28
        phase = frame.elapsed * (.18 + index * .025) + offset * math.tau
        top = frame.height * (.025 + index * .012)
        path.moveTo(0.0, top)
        path.lineTo(frame.width, top)
        for step in range(samples, -1, -1):
            x = frame.width * step / samples
            wave = (math.sin(step / samples * math.tau * 1.5 + phase) * .052
                    + math.sin(step / samples * math.tau * 3.2 - phase * .7) * .021)
            y = frame.height * (.19 + offset + wave)
            path.lineTo(x, y)
        path.closeSubpath()
        gradient = QLinearGradient(0, top, 0, frame.height * .39)
        color = QColor(base_color)
        color.setAlpha(round(112 * intensity))
        dim = QColor(color)
        dim.setAlpha(round(54 * intensity))
        transparent = QColor(color)
        transparent.setAlpha(0)
        gradient.setColorAt(0.0, transparent)
        gradient.setColorAt(.17, color)
        gradient.setColorAt(.58, dim)
        gradient.setColorAt(1.0, transparent)
        painter.setBrush(gradient)
        painter.drawPath(path)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    for index in range(11):
        center_x = frame.width * (.04 + index * .092)
        phase = frame.elapsed * .16 + index * .73
        fold = QPainterPath(QPointF(center_x, frame.height * .035))
        for step in range(1, 11):
            y = frame.height * (.035 + step * .023)
            x = (center_x + math.sin(phase + step * .48) * frame.width * .031
                 + math.sin(phase * .61 + step * .27) * frame.width * .012)
            fold.lineTo(x, y)
        fold_color = QColor("#a5ffe8" if index % 3 else "#d6b5ff")
        fold_color.setAlpha(round((112 + index % 3 * 8) * intensity))
        painter.setPen(QPen(fold_color, max(1.5, frame.width * .0018),
                            Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawPath(fold)
    painter.restore()
