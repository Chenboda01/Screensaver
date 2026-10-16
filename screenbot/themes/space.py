from PyQt6.QtCore import QPointF, QRect, QRectF, Qt
from PyQt6.QtGui import QColor, QLinearGradient, QPainter, QPen, QRadialGradient
import math
import time


class SpaceTheme:
    def space_background(self, p: QPainter, w: int, h: int) -> None:
        bg = QLinearGradient(0, 0, w, h)
        bg.setColorAt(0, QColor('#030817'))
        bg.setColorAt(.55, QColor('#141b45'))
        bg.setColorAt(1, QColor('#050a1d'))
        p.fillRect(QRect(0, 0, w, h), bg)
        haze = QRadialGradient(QPointF(w*.51, h*.58), max(w, h)*.43)
        haze.setColorAt(0, QColor(51, 90, 209, 75))
        haze.setColorAt(1, QColor(51, 90, 209, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(haze)
        p.drawRect(QRect(0, 0, w, h))

    def space(self, p, w, h, t):
        bg = QLinearGradient(0, 0, w, h)
        bg.setColorAt(0, QColor('#030817'))
        bg.setColorAt(.55, QColor('#141b45'))
        bg.setColorAt(1, QColor('#050a1d'))
        p.fillRect(QRect(0, 0, w, h), bg)
        haze = QRadialGradient(QPointF(w*.51, h*.58), max(w, h)*.43)
        haze.setColorAt(0, QColor(51, 90, 209, 75))
        haze.setColorAt(1, QColor(51, 90, 209, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(haze)
        p.drawRect(QRect(0, 0, w, h))
        for x, y, size, phase in self.particles:
            brightness = int(110 + 120*(.5 + .5*math.sin(t*1.4 + phase)))
            p.setBrush(QColor(177, 212, 255, brightness))
            p.drawEllipse(QPointF((x*w + t*size*1.3) % max(w, 1), y*h), size, size)
        unit = min(w, h)
        self.planet(p, w*.77, h*.31, unit*.105, '#d78350', '#f6c678', '#56385a', ring=True)
        if self.live_sky_enabled:
            coordinates = (self.live_weather.latitude, self.live_weather.longitude) if self.live_weather.located else None
            self.space_sky.draw(p, w, h, time.time(), coordinates)
        else:
            self.planet(p, w*.19, h*.43, unit*.047, '#347cbe', '#92e4f4', '#253e85')
        self.planet(p, w*.81, h*.68, unit*.032, '#a85576', '#f3a3b2', '#4c397f')

    @staticmethod
    def planet(p, x, y, radius, shadow, light, edge, ring=False):
        """Paint a softly shaded planet, optionally wrapped in a lit ring."""
        bounds = QRectF(x-radius, y-radius, radius*2, radius*2)
        if ring:
            ring_bounds = QRectF(x-radius*1.72, y-radius*.48, radius*3.44, radius*.96)
            p.save()
            p.setClipRect(QRectF(x-radius*2, y-radius, radius*4, radius))
            p.setPen(QPen(QColor('#f5ca91'), max(2, radius*.11)))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(ring_bounds)
            p.restore()

        glow = QRadialGradient(QPointF(x-radius*.36, y-radius*.43), radius*1.65)
        glow.setColorAt(0, QColor(light))
        glow.setColorAt(.52, QColor(shadow))
        glow.setColorAt(1, QColor(edge))
        p.setPen(QPen(QColor(light).lighter(118), max(1, radius*.025)))
        p.setBrush(glow)
        p.drawEllipse(bounds)

        if ring:
            p.save()
            p.setClipRect(QRectF(x-radius*2, y, radius*4, radius))
            p.setPen(QPen(QColor('#ffdca7'), max(2, radius*.11)))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(ring_bounds)
            p.setPen(QPen(QColor(255, 241, 204, 125), max(1, radius*.025)))
            p.drawEllipse(ring_bounds)
            p.restore()
