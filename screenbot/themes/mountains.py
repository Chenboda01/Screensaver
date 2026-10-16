from PyQt6.QtCore import QPointF, QRect, Qt
from PyQt6.QtGui import QColor, QLinearGradient, QPainter, QPolygonF
import math


class MountainsTheme:
    def mountains_background(self, p: QPainter, w: int, h: int, t: float) -> None:
        if self.live_sky_enabled:
            self.live_background(p, w, h, t)
        else:
            gradient = QLinearGradient(0, 0, 0, h)
            gradient.setColorAt(0, QColor('#102048'))
            gradient.setColorAt(.58, QColor('#846d9a'))
            gradient.setColorAt(1, QColor('#0d1d35'))
            p.fillRect(QRect(0, 0, w, h), gradient)
            p.setPen(Qt.PenStyle.NoPen)
            moon = QPointF(w*.79, h*.22)
            for radius, alpha in [(80, 17), (58, 28), (34, 48)]:
                p.setBrush(QColor(255, 235, 196, alpha))
                p.drawEllipse(moon, radius, radius)
            p.setBrush(QColor('#fff0ce'))
            p.drawEllipse(moon, 22, 22)
        for color, coords in [
            ('#566c91', [(0, .75), (.12, .58), (.25, .73), (.4, .49), (.55, .76), (.7, .58), (.82, .73), (1, .53)]),
            ('#2b476b', [(0, .88), (.15, .68), (.28, .86), (.48, .63), (.62, .83), (.77, .64), (1, .8)]),
            ('#132e4c', [(0, .95), (.17, .81), (.34, .95), (.53, .78), (.72, .96), (.87, .79), (1, .91)]),
        ]:
            polygon = QPolygonF([QPointF(x*w, y*h) for x, y in coords] + [QPointF(w, h), QPointF(0, h)])
            p.setBrush(QColor(color))
            p.drawPolygon(polygon)

    def mountains(self, p, w, h, t):
        if self.live_sky_enabled:
            self.live_background(p, w, h, t)
        else:
            gradient = QLinearGradient(0, 0, 0, h)
            gradient.setColorAt(0, QColor('#102048'))
            gradient.setColorAt(.58, QColor('#846d9a'))
            gradient.setColorAt(1, QColor('#0d1d35'))
            p.fillRect(QRect(0, 0, w, h), gradient)
            p.setPen(Qt.PenStyle.NoPen)
            moon = QPointF(w*.79, h*.22)
            for radius, alpha in [(80, 17), (58, 28), (34, 48)]:
                p.setBrush(QColor(255, 235, 196, alpha))
                p.drawEllipse(moon, radius, radius)
            p.setBrush(QColor('#fff0ce'))
            p.drawEllipse(moon, 22, 22)
        peaks = [
            ('#566c91', [(0, .75), (.12, .58), (.25, .73), (.4, .49), (.55, .76), (.7, .58), (.82, .73), (1, .53)]),
            ('#2b476b', [(0, .88), (.15, .68), (.28, .86), (.48, .63), (.62, .83), (.77, .64), (1, .8)]),
            ('#132e4c', [(0, .95), (.17, .81), (.34, .95), (.53, .78), (.72, .96), (.87, .79), (1, .91)]),
        ]
        for color, coords in peaks:
            polygon = QPolygonF([QPointF(x*w, y*h) for x, y in coords] + [QPointF(w, h), QPointF(0, h)])
            p.setBrush(QColor(color))
            p.drawPolygon(polygon)
        for x, y, r, phase in self.particles[:40]:
            p.setBrush(QColor(255, 231, 168, int(70 + 100*(.5 + .5*math.sin(t + phase)))))
            p.drawEllipse(QPointF(x*w, h*(.67 + y*.31)), r, r)
