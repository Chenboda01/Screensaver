import math

from PyQt6.QtCore import QPointF, QRect, QRectF, Qt
from PyQt6.QtGui import (
    QColor,
    QLinearGradient,
    QPainter,
    QPen,
    QPolygonF,
    QRadialGradient,
)

from screenbot.runtime import particle_count
from screenbot.themes import underwater


class WeatherEffects:
    def weather(self, p: QPainter, w: int, h: int, t: float) -> None:
        # Space uses a dry, atmosphere-free backdrop. Keep this guard before
        # both the Live Sky and manual-effect paths so saved toggles cannot leak in.
        if self.theme == 'space':
            return
        if self.theme == 'underwater':
            underwater.draw_surface_ripples(p, self.theme_frame(w, h, t))
            return
        if self.live_sky_enabled:
            category = self.live_weather.weather.category
            if category in ('rain', 'thunderstorm'):
                self.draw_rain(p, w, h, t)
            if category == 'snow':
                self.draw_snowfall(p, w, h, t)
            if category == 'fog':
                self.draw_fog(p, w, h, t)
            if category == 'thunderstorm':
                self.draw_thunderstorms(p, w, h, t)
            return
        if self.rain_enabled:
            self.draw_rain(p, w, h, t)
        if self.snow_enabled:
            self.draw_snowfall(p, w, h, t)
        if self.fog_enabled:
            self.draw_fog(p, w, h, t)
        if self.thunderstorms_enabled:
            self.draw_thunderstorms(p, w, h, t)
        if self.shooting_stars_enabled:
            self.draw_shooting_stars(p, w, h, t)

    def draw_rain(self, p: QPainter, w: int, h: int, t: float) -> None:
        scale = min(w, h) / 900
        p.save()
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(171, 218, 255, 125), max(1, scale*1.5)))
        weather = self.live_weather.weather
        drops = self.rain_drops[:max(1, round(len(self.rain_drops)*weather.intensity))] if self.live_sky_enabled else self.rain_drops
        if self.reduce_motion or self.performance_mode == 'battery-saver':
            effect_scale = .3 if self.reduce_motion else .5
            drops = drops[:particle_count(len(drops), effect_scale)]
        wind = weather.wind*.15 if self.live_sky_enabled else 0
        for x, y, speed, phase in drops:
            drop_x = (x*w + t*wind*scale + math.sin(t*.7 + phase)*12*scale) % w
            drop_y = (y*h + t*(170 + speed*100)*scale) % h
            p.drawLine(QPointF(drop_x, drop_y), QPointF(drop_x - (5+wind)*scale, drop_y + 19*scale))
        p.restore()

    def draw_snowfall(self, p: QPainter, w: int, h: int, t: float) -> None:
        scale = min(w, h) / 900
        p.save()
        p.setPen(Qt.PenStyle.NoPen)
        flakes = self.snowflakes[:max(1, round(len(self.snowflakes)*self.live_weather.weather.intensity))] if self.live_sky_enabled else self.snowflakes
        if self.reduce_motion or self.performance_mode == 'battery-saver':
            effect_scale = .3 if self.reduce_motion else .5
            flakes = flakes[:particle_count(len(flakes), effect_scale)]
        for x, y, size, speed, phase in flakes:
            flake_x = (x*w + math.sin(t*.55 + phase)*24*scale) % w
            flake_y = (y*h + t*(18 + speed*17)*scale) % h
            p.setBrush(QColor(237, 247, 255, 185))
            p.drawEllipse(QPointF(flake_x, flake_y), size*scale, size*scale)
        p.restore()

    def draw_fog(self, p: QPainter, w: int, h: int, t: float) -> None:
        p.save()
        p.setPen(Qt.PenStyle.NoPen)
        veil = QLinearGradient(0, h*.47, 0, h)
        veil.setColorAt(0, QColor(190, 211, 232, 0))
        veil.setColorAt(.55, QColor(190, 211, 232, 19))
        veil.setColorAt(1, QColor(190, 211, 232, 46))
        p.setBrush(veil)
        p.drawRect(QRectF(0, h*.47, w, h*.53))
        for index in range(4):
            center_x = ((index*.37 + t*.012) % 1.5 - .25) * w
            center_y = h*(.69 + math.sin(t*.16 + index)*.025)
            radius = min(w*.42, h*.2)
            haze = QRadialGradient(QPointF(center_x, center_y), radius)
            haze.setColorAt(0, QColor(218, 229, 240, 38))
            haze.setColorAt(1, QColor(218, 229, 240, 0))
            p.setBrush(haze)
            p.drawEllipse(QPointF(center_x, center_y), radius*1.8, radius*.62)
        p.restore()

    def draw_thunderstorms(self, p: QPainter, w: int, h: int, t: float) -> None:
        flashes: list[tuple[float, float]] = []
        for index, (offset, period, x) in enumerate(self.lightning_events):
            if self.reduce_motion and index % 2:
                continue
            phase = (t + offset) % period
            if phase < (.12 if self.reduce_motion else .2):
                flashes.append((x, 1 - phase/.2))
        if not flashes:
            return
        p.save()
        p.setPen(Qt.PenStyle.NoPen)
        for x, intensity in flashes:
            alpha = round((30 if self.reduce_motion else 72)*intensity)
            p.fillRect(QRect(0, 0, w, h), QColor(207, 224, 255, alpha))
            points = [
                QPointF(w*x, 0),
                QPointF(w*(x-.035), h*.18),
                QPointF(w*(x+.012), h*.17),
                QPointF(w*(x-.055), h*.40),
                QPointF(w*(x+.004), h*.27),
                QPointF(w*(x-.012), h*.28),
                QPointF(w*x, 0),
            ]
            p.setBrush(QColor(231, 241, 255, round((110 if self.reduce_motion else 230)*intensity)))
            p.drawPolygon(QPolygonF(points))
        p.restore()

    def draw_shooting_stars(self, p: QPainter, w: int, h: int, t: float) -> None:
        scale = min(w, h) / 900
        p.save()
        events = self.shooting_star_events
        if self.reduce_motion:
            events = events[::3]
        for offset, period, x, y in events:
            phase = (t + offset) % period
            if phase >= 1.15:
                continue
            progress = phase / 1.15
            head = QPointF(w*(x + progress*.35), h*(y + progress*.19))
            tail = QPointF(head.x() - w*.065, head.y() - h*.035)
            p.setPen(QPen(QColor(210, 237, 255, round(235*(1-progress))), max(1.5, scale*2.4), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(tail, head)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(242, 250, 255, round(230*(1-progress))))
            p.drawEllipse(head, scale*3, scale*3)
        p.restore()
