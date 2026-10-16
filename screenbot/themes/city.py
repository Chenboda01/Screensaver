from PyQt6.QtCore import QPointF, QRect, QRectF, Qt
from PyQt6.QtGui import QColor, QLinearGradient, QPen
import math
from screenbot.runtime import particle_count


class CityTheme:
    def city(self, p, w, h, t):
        """Neon skyline with lit windows and animated lights."""
        if self.live_sky_enabled:
            self.live_background(p, w, h, t)
        else:
            sky=QLinearGradient(0,0,0,h)
            sky.setColorAt(0,QColor('#050920'))
            sky.setColorAt(.6,QColor('#1c2051'))
            sky.setColorAt(1,QColor('#090c25'))
            p.fillRect(QRect(0, 0, w, h),sky)
            p.setPen(Qt.PenStyle.NoPen)
            city_star_count = particle_count(55, .3 if self.reduce_motion else (.5 if self.performance_mode == 'battery-saver' else 1.0))
            for x,y,size,phase in self.particles[:city_star_count]:
                p.setBrush(QColor(177,192,255,170))
                p.drawEllipse(QPointF(x*w,y*h*.6),size*.7,size*.7)
        # Deterministic skyline; each building has a unique height and window grid.
        for i in range(25):
            x0=(i/25)*w
            bw=w/25+2
            bh=h*(.2+.25*(.5+.5*math.sin(i*7.2)))
            top=h*.91-bh
            p.setBrush(QColor('#111a37') if i%2 else QColor('#152140'))
            p.drawRect(QRectF(x0,top,bw,h-top))
            if i%5==0:
                p.setPen(QPen(QColor('#58e8ff'),2))
                p.drawLine(QPointF(x0,top),QPointF(x0+bw,top))
                p.setPen(Qt.PenStyle.NoPen)
            for col in range(2):
                for row in range(max(1,int(bh/24))):
                    if (i*17+col*5+row*3)%5==0: continue
                    flicker=not self.reduce_motion and math.sin(t*.8+i+row)> .95
                    p.setBrush(QColor('#ff65c5') if (i+row)%4==0 else QColor('#61e4ff') if not flicker else QColor('#293958'))
                    p.drawRect(QRectF(x0+7+col*(bw*.35),top+10+row*23, max(3,bw*.13),8))
        p.setBrush(QColor('#070f24'))
        p.drawRect(QRectF(0,h*.91,w,h*.09))
        p.setPen(QPen(QColor('#fc51b9'),3))
        p.drawLine(QPointF(0,h*.91),QPointF(w,h*.91))
        p.setPen(Qt.PenStyle.NoPen)
