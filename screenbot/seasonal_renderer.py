"""Small vector decorations layered over themes without altering their scene art."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
import configparser

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen

from screenbot.seasonal import (
    CalendarState,
    SeasonalEvent,
    SeasonalPreferences,
    calendar_state,
    effective_preview_datetime,
    new_year_countdown_seconds,
    seasonal_preferences,
)


@dataclass(frozen=True, slots=True)
class SeasonalSession:
    """Local settings and preview clock for one screensaver session."""

    preferences: SeasonalPreferences
    is_preview: bool
    forced_preview_datetime: datetime | None

    @classmethod
    def from_settings(
        cls,
        settings: configparser.ConfigParser,
        *,
        is_preview: bool,
        forced_preview_datetime: datetime | None,
    ) -> SeasonalSession:
        """Parse local seasonal preferences once at screensaver startup."""
        return cls(seasonal_preferences(settings), is_preview, forced_preview_datetime)

    def draw(
        self,
        painter: QPainter,
        width: int,
        height: int,
        elapsed: float,
        theme: str,
        latitude: float | None,
        reduce_motion: bool,
    ) -> str:
        """Draw this frame's local-date decorations and return Bob's event hat."""
        local_now = effective_preview_datetime(
            datetime.now().astimezone(), self.forced_preview_datetime,
            preview_mode=self.is_preview,
        )
        calendar = calendar_state(
            local_now.date(), enabled=self.preferences.enabled, events=self.preferences.events,
            latitude=latitude, birthday=self.preferences.birthday,
        )
        SeasonalRenderer.draw(
            painter, width, height, elapsed, theme, local_now, calendar,
            self.preferences.birthday.name if self.preferences.birthday is not None else "",
            reduce_motion,
        )
        if SeasonalEvent.HALLOWEEN in calendar.events:
            return "witch"
        if SeasonalEvent.WINTER_HOLIDAYS in calendar.events:
            return "santa"
        return ""


class SeasonalRenderer:
    """Draw optional event art above scenery, below Bob and the clock."""

    @staticmethod
    def draw(
        painter: QPainter,
        width: int,
        height: int,
        elapsed: float,
        theme: str,
        local_now: datetime,
        calendar: CalendarState,
        birthday_name: str,
        reduce_motion: bool,
    ) -> None:
        """Render active calendar decorations with stable geometry and bounded motion."""
        events = calendar.events
        if width <= 0 or height <= 0 or not events:
            return

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        if SeasonalEvent.SPRING in events and theme in ("forest", "mountains"):
            SeasonalRenderer._petals(painter, width, height, elapsed, reduce_motion)
        if SeasonalEvent.WINTER_HOLIDAYS in events:
            SeasonalRenderer._holiday_lights(painter, width, height, elapsed, reduce_motion)
            if theme not in ("space", "underwater", "ocean"):
                SeasonalRenderer._holiday_snow(painter, width, height, elapsed, reduce_motion)
        if SeasonalEvent.LUNAR_NEW_YEAR in events:
            SeasonalRenderer._lanterns(painter, width, height, elapsed, reduce_motion)
        if SeasonalEvent.VALENTINES_DAY in events:
            SeasonalRenderer._hearts(painter, width, height, elapsed, reduce_motion)
        if SeasonalEvent.HALLOWEEN in events:
            SeasonalRenderer._halloween(painter, width, height, elapsed, reduce_motion)
        if SeasonalEvent.NEW_YEAR in events:
            SeasonalRenderer._new_year(painter, width, height, elapsed, local_now, reduce_motion)
        if SeasonalEvent.BIRTHDAY in events:
            SeasonalRenderer._birthday(painter, width, height, elapsed, birthday_name, reduce_motion)
        painter.restore()

    @staticmethod
    def _petals(painter: QPainter, width: int, height: int, elapsed: float, reduce_motion: bool) -> None:
        painter.setPen(Qt.PenStyle.NoPen)
        colors = (QColor("#ffd5e5"), QColor("#ffe8a9"), QColor("#f7b9d9"))
        for index in range(16):
            phase = index * 2.399963 + (0.0 if reduce_motion else elapsed * .28)
            x = (index * .618034 % 1) * width + math.sin(phase) * width * .045
            y = (index * .414214 % 1) * height * .73 + (0 if reduce_motion else (elapsed * (8 + index % 4 * 2)) % (height * .24))
            painter.save()
            painter.translate(x % width, y % (height * .82))
            painter.rotate(phase * 24)
            painter.setBrush(colors[index % len(colors)])
            painter.drawEllipse(QRectF(-4, -7, 8, 14))
            painter.restore()

    @staticmethod
    def _holiday_lights(painter: QPainter, width: int, height: int, elapsed: float, reduce_motion: bool) -> None:
        y = height * .085
        painter.setPen(QPen(QColor(26, 37, 49, 190), max(1.5, width * .0015)))
        wire = QPainterPath(QPointF(width * .04, y))
        wire.cubicTo(width * .3, y + height * .055, width * .68, y + height * .055, width * .96, y)
        painter.drawPath(wire)
        palette = ("#ff7474", "#ffd46d", "#75e7bd", "#85caff", "#dd9cff")
        painter.setPen(Qt.PenStyle.NoPen)
        for index in range(13):
            x = width * (.055 + index * .074)
            sag = height * .055 * 4 * (index / 12) * (1 - index / 12)
            pulse = .76 if reduce_motion else .58 + .42 * (.5 + .5 * math.sin(elapsed * 1.4 + index * 1.7))
            color = QColor(palette[index % len(palette)])
            color.setAlpha(round(220 * pulse))
            painter.setBrush(color)
            painter.drawEllipse(QPointF(x, y + sag + height * .021), max(4, width * .006), max(6, height * .012))

    @staticmethod
    def _holiday_snow(painter: QPainter, width: int, height: int, elapsed: float, reduce_motion: bool) -> None:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(238, 247, 255, 118 if reduce_motion else 165))
        for index in range(48):
            x = (index * .618034 % 1) * width
            y = (index * .414214 % 1) * height
            if not reduce_motion:
                x += math.sin(elapsed * .25 + index) * 12
                y += elapsed * (5 + index % 5 * 2)
            painter.drawEllipse(QPointF(x % width, y % height), 1.4 + index % 3 * .45, 1.4 + index % 3 * .45)

    @staticmethod
    def _lanterns(painter: QPainter, width: int, height: int, elapsed: float, reduce_motion: bool) -> None:
        firework_palette = []
        for color, alpha in (("#e34650", 115 if reduce_motion else 170),
                             ("#f8d27a", 110 if reduce_motion else 165)):
            spark_color = QColor(color)
            spark_color.setAlpha(alpha)
            firework_palette.append(spark_color)
        firework_centers = ((.24, .34), (.76, .39)) if reduce_motion else ((.19, .33), (.45, .29), (.78, .35))
        for index, (x, y) in enumerate(firework_centers):
            SeasonalRenderer._firework(
                painter, QPointF(width * x, height * y),
                min(width, height) * (.022 if reduce_motion else .027 + .004 * math.sin(elapsed * .5 + index)),
                firework_palette[index % len(firework_palette)], 8,
            )
        y = height * .12
        painter.setPen(QPen(QColor("#e6c77d"), max(1, width * .0012)))
        painter.drawLine(QPointF(width * .08, y), QPointF(width * .92, y))
        for index, x_fraction in enumerate((.18, .34, .5, .66, .82)):
            sway = 0 if reduce_motion else math.sin(elapsed * .7 + index) * 5
            x = width * x_fraction + sway
            drop = height * (.09 + index % 2 * .035)
            painter.drawLine(QPointF(x, y), QPointF(x, y + drop))
            painter.setPen(QPen(QColor("#ffe1a2"), 2))
            painter.setBrush(QColor("#c81f35"))
            painter.drawRoundedRect(QRectF(x - width * .023, y + drop, width * .046, height * .067), width * .018, width * .018)
            painter.setPen(QPen(QColor("#ffd571"), max(1, width * .002)))
            for stripe in (-.012, .012):
                painter.drawLine(QPointF(x + width * stripe, y + drop + height * .008),
                                 QPointF(x + width * stripe, y + drop + height * .059))
            painter.drawLine(QPointF(x, y + drop + height * .067), QPointF(x, y + drop + height * .085))
            painter.setPen(Qt.PenStyle.NoPen)

    @staticmethod
    def _heart(painter: QPainter, center: QPointF, size: float, color: QColor) -> None:
        path = QPainterPath()
        path.moveTo(center.x(), center.y() + size * .45)
        path.cubicTo(center.x() - size * .95, center.y() - size * .15,
                     center.x() - size * .52, center.y() - size * .85,
                     center.x(), center.y() - size * .35)
        path.cubicTo(center.x() + size * .52, center.y() - size * .85,
                     center.x() + size * .95, center.y() - size * .15,
                     center.x(), center.y() + size * .45)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawPath(path)

    @staticmethod
    def _hearts(painter: QPainter, width: int, height: int, elapsed: float, reduce_motion: bool) -> None:
        palette = []
        for color, alpha in (("#ff80ab", 205), ("#ffbdc9", 190), ("#ffd7e1", 200)):
            heart_color = QColor(color)
            heart_color.setAlpha(alpha)
            palette.append(heart_color)
        for index in range(9):
            phase = index * .91 + (0 if reduce_motion else elapsed * .18)
            x = (index * .618034 % 1) * width
            y = height * (.28 + (index * .414214 % 1) * .56)
            if not reduce_motion:
                y -= (elapsed * 8) % (height * .14)
            SeasonalRenderer._heart(painter, QPointF(x, y), max(7, min(width, height) * .023), palette[index % len(palette)])

    @staticmethod
    def _bat(painter: QPainter, center: QPointF, scale: float, flap: float) -> None:
        path = QPainterPath()
        path.moveTo(center.x() - scale, center.y())
        path.quadTo(center.x() - scale * .7, center.y() - flap * scale, center.x() - scale * .28, center.y() - scale * .1)
        path.quadTo(center.x(), center.y() - scale * .65, center.x() + scale * .28, center.y() - scale * .1)
        path.quadTo(center.x() + scale * .7, center.y() - flap * scale, center.x() + scale, center.y())
        path.lineTo(center.x() + scale * .35, center.y() + scale * .24)
        path.lineTo(center.x(), center.y() + scale * .14)
        path.lineTo(center.x() - scale * .35, center.y() + scale * .24)
        path.closeSubpath()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#202535"))
        painter.drawPath(path)

    @staticmethod
    def _pumpkin(painter: QPainter, x: float, y: float, scale: float) -> None:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#ff8b32"))
        painter.drawEllipse(QRectF(x - scale, y - scale * .62, scale * 2, scale * 1.22))
        painter.setBrush(QColor("#e96c25"))
        painter.drawEllipse(QRectF(x - scale * .48, y - scale * .58, scale * .96, scale * 1.12))
        painter.setBrush(QColor("#427846"))
        painter.drawRoundedRect(QRectF(x - scale * .09, y - scale * .78, scale * .18, scale * .26), scale * .05, scale * .05)
        painter.setBrush(QColor("#332638"))
        for eye_x in (-.36, .36):
            painter.drawPolygon([QPointF(x + scale * (eye_x - .12), y - scale * .1),
                                 QPointF(x + scale * (eye_x + .12), y - scale * .1),
                                 QPointF(x + scale * eye_x, y + scale * .15)])
        painter.drawRoundedRect(QRectF(x - scale * .35, y + scale * .22, scale * .7, scale * .18), scale * .05, scale * .05)

    @staticmethod
    def _halloween(painter: QPainter, width: int, height: int, elapsed: float, reduce_motion: bool) -> None:
        for index in range(7):
            phase = index * 1.7
            x = width * (.08 + index * .14)
            y = height * (.18 + (index % 3) * .14)
            if not reduce_motion:
                x += math.sin(elapsed * .25 + phase) * 12
                y += math.sin(elapsed * .4 + phase) * 8
            SeasonalRenderer._bat(painter, QPointF(x, y), min(width, height) * .024, 1 if reduce_motion else math.sin(elapsed * 2 + index))
        for x_fraction in (.18, .5, .82):
            SeasonalRenderer._pumpkin(painter, width * x_fraction, height * .92, min(width, height) * .045)

    @staticmethod
    def _firework(painter: QPainter, center: QPointF, radius: float, color: QColor, spokes: int) -> None:
        painter.setPen(QPen(color, max(1.4, radius * .025), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        for index in range(spokes):
            angle = math.tau * index / spokes
            inner = radius * .28
            outer = radius * (.82 if index % 2 else 1.0)
            painter.drawLine(QPointF(center.x() + math.cos(angle) * inner, center.y() + math.sin(angle) * inner),
                             QPointF(center.x() + math.cos(angle) * outer, center.y() + math.sin(angle) * outer))

    @staticmethod
    def _new_year(
        painter: QPainter,
        width: int,
        height: int,
        elapsed: float,
        local_now: datetime,
        reduce_motion: bool,
    ) -> None:
        painter.setPen(QColor("#fff3c5"))
        painter.setFont(QFont("Sans Serif", max(15, round(min(width, height) * .035)), QFont.Weight.Bold))
        if (local_now.month, local_now.day) == (1, 1):
            painter.drawText(QRectF(width * .2, height * .15, width * .6, height * .07),
                             Qt.AlignmentFlag.AlignCenter, "Happy New Year!")
        countdown = new_year_countdown_seconds(local_now)
        if countdown is not None:
            label = f"New Year in 00:{countdown:02d}"
            panel = QRectF(width * .36, height * .24, width * .28, height * .065)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(19, 29, 56, 190))
            painter.drawRoundedRect(panel, 14, 14)
            painter.setPen(QColor("#fff3c5"))
            painter.setFont(QFont("Sans Serif", max(12, round(min(width, height) * .022)), QFont.Weight.DemiBold))
            painter.drawText(panel, Qt.AlignmentFlag.AlignCenter, label)
        if (local_now.month, local_now.day, local_now.hour, local_now.minute)[:3] != (1, 1, 0):
            return
        palette = []
        for color, alpha in (("#ffd46d", 135 if reduce_motion else 220),
                             ("#ff8d9b", 125 if reduce_motion else 210),
                             ("#9fe7ff", 120 if reduce_motion else 205)):
            firework_color = QColor(color)
            firework_color.setAlpha(alpha)
            palette.append(firework_color)
        centers = ((.25, .38), (.5, .32), (.75, .4)) if reduce_motion else ((.2, .36), (.38, .28), (.58, .35), (.78, .3), (.48, .48))
        for index, (x, y) in enumerate(centers):
            radius = min(width, height) * (.055 if reduce_motion else .06 + .008 * math.sin(elapsed * .6 + index))
            SeasonalRenderer._firework(painter, QPointF(width * x, height * y), radius, palette[index % len(palette)], 8 if reduce_motion else 12)

    @staticmethod
    def _balloon(painter: QPainter, x: float, y: float, scale: float, color: QColor, sway: float) -> None:
        x += sway
        painter.setPen(QPen(QColor(240, 240, 255, 170), max(1, scale * .025)))
        painter.drawLine(QPointF(x, y + scale * .48), QPointF(x - sway * .4, y + scale * 1.18))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawEllipse(QRectF(x - scale * .36, y - scale * .56, scale * .72, scale))
        painter.drawPolygon([QPointF(x - scale * .08, y + scale * .4),
                             QPointF(x + scale * .08, y + scale * .4),
                             QPointF(x, y + scale * .54)])
        painter.setBrush(QColor(255, 255, 255, 85))
        painter.drawEllipse(QPointF(x - scale * .12, y - scale * .22), scale * .07, scale * .15)

    @staticmethod
    def _birthday(
        painter: QPainter,
        width: int,
        height: int,
        elapsed: float,
        name: str,
        reduce_motion: bool,
    ) -> None:
        colors = (QColor("#ff7ab6"), QColor("#72d5ff"), QColor("#ffd36e"), QColor("#b996ff"))
        for index, x_fraction in enumerate((.1, .3, .7, .9)):
            sway = 0 if reduce_motion else math.sin(elapsed * .55 + index) * width * .012
            y = height * (.62 + (index % 2) * .08)
            if not reduce_motion:
                y -= math.sin(elapsed * .7 + index * 1.3) * height * .025
            SeasonalRenderer._balloon(painter, width * x_fraction, y, min(width, height) * .075,
                                      colors[index], sway)
        painter.setPen(Qt.PenStyle.NoPen)
        for index in range(28):
            x = (index * .754878 % 1) * width
            y = (index * .569841 % 1) * height * .74
            if not reduce_motion:
                y = (y + elapsed * (4 + index % 5 * 2)) % (height * .78)
            painter.save()
            painter.translate(x, y)
            painter.rotate(index * 29 + (0 if reduce_motion else elapsed * 16))
            painter.setBrush(colors[index % len(colors)])
            painter.drawRoundedRect(QRectF(-3, -6, 6, 12), 2, 2)
            painter.restore()
        caption = f"Happy birthday, {name}!" if name else "Happy birthday!"
        panel = QRectF(width * .2, height * .84, width * .6, height * .075)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(23, 31, 58, 210))
        painter.drawRoundedRect(panel, 18, 18)
        painter.setPen(QColor("#fff1cc"))
        painter.setFont(QFont("Sans Serif", max(15, round(min(width, height) * .035)), QFont.Weight.Bold))
        painter.drawText(panel, Qt.AlignmentFlag.AlignCenter, caption)


def draw_seasonal_bob_hat(painter: QPainter, kind: str) -> None:
    """Draw themed headwear in Bob's established local head coordinates."""
    if kind not in ("witch", "santa"):
        return
    painter.save()
    painter.setPen(QPen(QColor("#f3f4ff"), 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    if kind == "witch":
        painter.setBrush(QColor("#342951"))
        hat = QPainterPath()
        hat.moveTo(-61, -91)
        hat.lineTo(0, -188)
        hat.quadTo(9, -164, 52, -100)
        hat.closeSubpath()
        painter.drawPath(hat)
        painter.setBrush(QColor("#f6a73a"))
        painter.drawRoundedRect(QRectF(-62, -104, 124, 13), 6, 6)
        painter.setBrush(QColor("#f1c85a"))
        painter.drawRoundedRect(QRectF(-16, -132, 28, 10), 4, 4)
    elif kind == "santa":
        painter.setBrush(QColor("#d83a4d"))
        hat = QPainterPath()
        hat.moveTo(-61, -91)
        hat.quadTo(-47, -142, -7, -172)
        hat.quadTo(18, -188, 38, -161)
        hat.lineTo(50, -102)
        hat.closeSubpath()
        painter.drawPath(hat)
        painter.setBrush(QColor("#f8f4ed"))
        painter.drawRoundedRect(QRectF(-63, -104, 126, 17), 8, 8)
        painter.drawEllipse(QPointF(40, -161), 11, 11)
    painter.restore()
