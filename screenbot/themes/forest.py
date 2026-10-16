from PyQt6.QtCore import QPointF, QRect, QRectF, Qt
from PyQt6.QtGui import QColor, QLinearGradient, QPainter, QPolygonF
import math


class ForestTheme:
    def forest_background(self, p: QPainter, w: int, h: int, t: float) -> None:
        if self.live_sky_enabled:
            self.live_background(p, w, h, t)
            p.fillRect(QRectF(0, h*.79, w, h*.21), QColor('#082b2b'))
        else:
            sky=QLinearGradient(0,0,0,h)
            sky.setColorAt(0,QColor('#081a24'))
            sky.setColorAt(.6,QColor('#19564e'))
            sky.setColorAt(1,QColor('#0b2b2a'))
            p.fillRect(QRect(0, 0, w, h),sky)
            p.setPen(Qt.PenStyle.NoPen)
            moon=QPointF(w*.82,h*.2)
            p.setBrush(QColor(216,246,207,55))
            p.drawEllipse(moon,60,60)
            p.setBrush(QColor('#e0f7cb'))
            p.drawEllipse(moon,22,22)
        for layer,color,height_scale in [(0,QColor('#1b544c'),.64),(1,QColor('#103b38'),.73),(2,QColor('#082b2b'),.83)]:
            p.setBrush(color)
            count=15
            for i in range(count+1):
                cx=((i+(.45 if layer%2 else 0))/count)*w
                trunk_y=h*(height_scale+.16)
                tree_h=h*(.17+.06*math.sin(i*2.1+layer))
                sway = math.sin(t*1.4+i)*min(12., self.live_weather.weather.wind*.2) if self.live_sky_enabled else 0
                p.drawPolygon(QPolygonF([QPointF(cx-tree_h*.28,trunk_y),QPointF(cx+sway,trunk_y-tree_h),QPointF(cx+tree_h*.28,trunk_y)]))
                p.drawRect(QRectF(cx-3,trunk_y-2,6,h-trunk_y))

    def forest(self, p, w, h, t):
        """Layered evergreen forest with glowing floating fireflies."""
        if self.live_sky_enabled:
            self.live_background(p, w, h, t)
        else:
            sky=QLinearGradient(0,0,0,h)
            sky.setColorAt(0,QColor('#081a24'))
            sky.setColorAt(.6,QColor('#19564e'))
            sky.setColorAt(1,QColor('#0b2b2a'))
            p.fillRect(QRect(0, 0, w, h),sky)
            p.setPen(Qt.PenStyle.NoPen)
            moon=QPointF(w*.82,h*.2)
            p.setBrush(QColor(216,246,207,55))
            p.drawEllipse(moon,60,60)
            p.setBrush(QColor('#e0f7cb'))
            p.drawEllipse(moon,22,22)
        if self.live_sky_enabled:
            p.fillRect(QRectF(0, h*.79, w, h*.21), QColor('#082b2b'))
        for layer,color,height_scale in [(0,QColor('#1b544c'),.64),(1,QColor('#103b38'),.73),(2,QColor('#082b2b'),.83)]:
            p.setBrush(color)
            count=15
            for i in range(count+1):
                cx=((i+(.45 if layer%2 else 0))/count)*w
                trunk_y=h*(height_scale+.16)
                tree_h=h*(.17+.06*math.sin(i*2.1+layer))
                sway = math.sin(t*1.4+i)*min(12., self.live_weather.weather.wind*.2) if self.live_sky_enabled else 0
                p.drawPolygon(QPolygonF([QPointF(cx-tree_h*.28,trunk_y),QPointF(cx+sway,trunk_y-tree_h),QPointF(cx+tree_h*.28,trunk_y)]))
                p.drawRect(QRectF(cx-3,trunk_y-2,6,h-trunk_y))
        for x,y,size,phase in self.particles[:75]:
            cx=x*w+math.sin(t*.6+phase)*12
            cy=(.18+y*.73)*h+math.cos(t*.55+phase)*8
            alpha=int(80+150*(.5+.5*math.sin(t*2+phase)))
            p.setBrush(QColor(210,255,145,alpha))
            p.drawEllipse(QPointF(cx,cy),size+1,size+1)
