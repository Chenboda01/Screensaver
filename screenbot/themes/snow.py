from PyQt6.QtCore import QPointF, QRect, Qt
from PyQt6.QtGui import QColor, QLinearGradient, QPainter, QPolygonF, QRadialGradient
import math


class SnowTheme:
    def snow_background(self, p: QPainter, w: int, h: int, t: float) -> None:
        if self.live_sky_enabled:
            self.live_background(p, w, h, t)
        else:
            sky = QLinearGradient(0, 0, 0, h)
            sky.setColorAt(0, QColor('#101b39'))
            sky.setColorAt(.6, QColor('#416d9f'))
            sky.setColorAt(1, QColor('#cee8f4'))
            p.fillRect(QRect(0, 0, w, h), sky)
            p.setPen(Qt.PenStyle.NoPen)
            moon = QPointF(.79*w, .19*h)
            glow = QRadialGradient(moon, h*.18)
            glow.setColorAt(0, QColor(231,245,255,110))
            glow.setColorAt(1, QColor(231,245,255,0))
            p.setBrush(glow)
            p.drawEllipse(moon, h*.18, h*.18)
            p.setBrush(QColor('#f6fbff'))
            p.drawEllipse(moon, 24, 24)
        for color, coords in [
            ('#9ab9d1', [(0,.77),(.13,.59),(.25,.74),(.4,.45),(.54,.73),(.7,.53),(.84,.74),(1,.55)]),
            ('#dae9f2', [(0,.87),(.16,.69),(.29,.84),(.46,.59),(.64,.87),(.81,.64),(1,.82)]),
            ('#6d95b1', [(0,.96),(.19,.79),(.34,.96),(.52,.74),(.74,.96),(.9,.83),(1,.94)]),
        ]:
            p.setBrush(QColor(color))
            p.drawPolygon(QPolygonF([QPointF(x*w,y*h) for x,y in coords]+[QPointF(w,h),QPointF(0,h)]))

    def snow(self, p, w, h, t):
        """Midnight alpine snow scene, with drifting flakes."""
        if self.live_sky_enabled:
            self.live_background(p, w, h, t)
        else:
            sky = QLinearGradient(0, 0, 0, h)
            sky.setColorAt(0, QColor('#101b39'))
            sky.setColorAt(.6, QColor('#416d9f'))
            sky.setColorAt(1, QColor('#cee8f4'))
            p.fillRect(QRect(0, 0, w, h), sky)
            p.setPen(Qt.PenStyle.NoPen)
            moon = QPointF(.79*w, .19*h)
            glow = QRadialGradient(moon, h*.18)
            glow.setColorAt(0, QColor(231,245,255,110))
            glow.setColorAt(1, QColor(231,245,255,0))
            p.setBrush(glow)
            p.drawEllipse(moon, h*.18, h*.18)
            p.setBrush(QColor('#f6fbff'))
            p.drawEllipse(moon, 24, 24)
        for color, coords in [
            ('#9ab9d1', [(0,.77),(.13,.59),(.25,.74),(.4,.45),(.54,.73),(.7,.53),(.84,.74),(1,.55)]),
            ('#dae9f2', [(0,.87),(.16,.69),(.29,.84),(.46,.59),(.64,.87),(.81,.64),(1,.82)]),
            ('#6d95b1', [(0,.96),(.19,.79),(.34,.96),(.52,.74),(.74,.96),(.9,.83),(1,.94)]),
        ]:
            p.setBrush(QColor(color))
            p.drawPolygon(QPolygonF([QPointF(a*w,b*h) for a,b in coords]+[QPointF(w,h),QPointF(0,h)]))
        for x,y,size,phase in ([] if self.live_sky_enabled else self.particles):
            px=(x*w+math.sin(t*.7+phase)*14+t*(5+size*8))%max(1,w)
            py=(y*h+t*(15+size*10))%max(1,h)
            p.setBrush(QColor(245,251,255,165))
            p.drawEllipse(QPointF(px,py),size+0.5,size+0.5)
