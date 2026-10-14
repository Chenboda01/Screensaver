#!/usr/bin/env python3
"""ScreenBot screensaver V18: configurable BobOS, clock, and weather effects.

Theme is controlled ONLY by KDE System Settings. This version keeps the
existing settings integration and replaces the previous full-body design with a
floating Bob head so it looks closer to ScreenBot's style.
"""
import configparser
import math
import random
import subprocess
import sys
import time
from pathlib import Path
from typing import Final

from PyQt6.QtCore import QDateTime, QPointF, QRectF, Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen, QPolygonF, QRadialGradient
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtGui import QShowEvent

from bobos import BobOSPhase, BobOSStatus, BobOSTimeline, bobos_may_run

CLOCK_POSITIONS: Final[frozenset[str]] = frozenset(
    {
        'top-left', 'top-center', 'top-right',
        'center-left', 'center-center', 'center-right',
        'bottom-left', 'bottom-center', 'bottom-right',
    }
)


def read_settings():
    settings = configparser.ConfigParser()
    settings.read(Path.home() / '.config' / 'screenbot-screensaver.ini')
    return settings


def selected_theme(settings):
    selection = settings.get('Screensaver', 'theme', fallback='random').strip().lower()
    if selection not in ('random', 'space', 'mountains', 'snow', 'forest', 'city'):
        selection = 'random'
    return random.choice(('space', 'mountains', 'snow', 'forest', 'city')) if selection == 'random' else selection


class Saver(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('ScreenBot Screensaver')
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.BlankCursor)
        settings = read_settings()
        self.theme = selected_theme(settings)
        self.show_clock = settings.getboolean('Screensaver', 'show_clock', fallback=True)
        self.clock_format = settings.get('Screensaver', 'clock_format', fallback='12h').strip()
        if self.clock_format not in ('12h', '24h'):
            self.clock_format = '12h'
        self.show_date = settings.getboolean('Screensaver', 'show_date', fallback=False)
        clock_position = settings.get('Screensaver', 'clock_position', fallback='top-center').strip()
        self.clock_position = clock_position if clock_position in CLOCK_POSITIONS else 'top-center'
        try:
            clock_font_size = settings.getint('Screensaver', 'clock_font_size', fallback=48)
        except ValueError:
            clock_font_size = 48
        self.clock_font_size = max(16, min(72, clock_font_size))
        self.rain_enabled = settings.getboolean('Screensaver', 'rain_enabled', fallback=False)
        self.snow_enabled = settings.getboolean('Screensaver', 'snow_enabled', fallback=False)
        self.thunderstorms_enabled = settings.getboolean('Screensaver', 'thunderstorms_enabled', fallback=False)
        self.fog_enabled = settings.getboolean('Screensaver', 'fog_enabled', fallback=False)
        self.shooting_stars_enabled = settings.getboolean('Screensaver', 'shooting_stars_enabled', fallback=False)
        self.password_lock = settings.getboolean('Screensaver', 'password_lock', fallback=False)
        try:
            minutes = settings.getint('Screensaver', 'lock_minutes', fallback=2)
        except ValueError:
            minutes = 2
        self.lock_seconds = max(1, min(60, minutes)) * 60
        self.show_timer = self.password_lock and settings.getboolean('Screensaver', 'show_timer', fallback=False)
        self.ai_backpack_enabled = settings.getboolean('Screensaver', 'ai_backpack_enabled', fallback=True)
        self.bobos_enabled = settings.getboolean('Screensaver', 'bobos_enabled', fallback=True)
        try:
            bobos_delay_minutes = settings.getint('Screensaver', 'bobos_activation_delay', fallback=3)
        except ValueError:
            bobos_delay_minutes = 3
        self.bobos_activation_delay_seconds = max(1, min(30, bobos_delay_minutes)) * 60
        self.show_wifi_animation = settings.getboolean('Screensaver', 'show_wifi_animation', fallback=True)
        schedule_random = random.Random()
        self.bobos_timeline = BobOSTimeline(
            activation_delay_seconds=self.bobos_activation_delay_seconds,
            show_connection_animation=self.show_wifi_animation,
            first_adventure_offset_seconds=schedule_random.randint(0, 90),
            cooldown_offset_seconds=schedule_random.randint(60, 180),
        )
        self.lock_attempted = False
        self.next_lock_attempt = 0.0
        self.lock_error = False
        self.start_time = time.monotonic()
        self.old_mouse = None
        r = random.Random()
        self.particles = [(r.random(), r.random(), r.uniform(.65, 2.6), r.random()*math.tau) for _ in range(110)]
        self.rain_drops = [(r.random(), r.random(), r.uniform(.8, 1.8), r.random()) for _ in range(150)]
        self.snowflakes = [(r.random(), r.random(), r.uniform(1.2, 4.0), r.uniform(.5, 1.6), r.random()*math.tau) for _ in range(110)]
        self.lightning_events = [(r.uniform(0, 20), r.uniform(12, 24), r.uniform(.15, .85)) for _ in range(4)]
        self.shooting_star_events = [(r.uniform(0, 24), r.uniform(10, 22), r.uniform(.1, .8), r.uniform(.08, .35)) for _ in range(5)]
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(33)

    def showEvent(self, event: QShowEvent) -> None:
        """Start all screensaver-relative timers when Bob first becomes visible."""
        self.start_time = time.monotonic()
        super().showEvent(event)

    def bobos_status(self, elapsed_seconds: float) -> BobOSStatus:
        """Keep BobOS out of disabled states and yield before the real KDE lock."""
        enabled = bobos_may_run(
            backpack_enabled=self.ai_backpack_enabled,
            bobos_enabled=self.bobos_enabled,
            password_lock_enabled=self.password_lock,
            elapsed_seconds=elapsed_seconds,
            lock_seconds=self.lock_seconds,
        )
        return self.bobos_timeline.status_at(elapsed_seconds, enabled=enabled)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        w, h = self.width(), self.height()
        t = time.monotonic() - self.start_time
        if self.theme == 'space':
            self.space(p, w, h, t)
        elif self.theme == 'mountains':
            self.mountains(p, w, h, t)
        elif self.theme == 'snow':
            self.snow(p, w, h, t)
        elif self.theme == 'forest':
            self.forest(p, w, h, t)
        else:
            self.city(p, w, h, t)
        self.weather(p, w, h, t)
        if self.show_clock:
            self.clock(p, w, h)
        bobos_status = self.bobos_status(t)
        self.bob(p, w, h, t, bobos_status)
        self.caption(p, w, h, t, bobos_status.phase)
        if self.show_timer:
            self.countdown(p, w, h, t)
        p.end()
        if self.password_lock and t >= self.lock_seconds and t >= self.next_lock_attempt:
            self.next_lock_attempt = t + 5
            QTimer.singleShot(0, self.request_kde_lock)

    def space(self, p, w, h, t):
        bg = QLinearGradient(0, 0, w, h)
        bg.setColorAt(0, QColor('#030817'))
        bg.setColorAt(.55, QColor('#141b45'))
        bg.setColorAt(1, QColor('#050a1d'))
        p.fillRect(self.rect(), bg)
        haze = QRadialGradient(QPointF(w*.51, h*.58), max(w, h)*.43)
        haze.setColorAt(0, QColor(51, 90, 209, 75))
        haze.setColorAt(1, QColor(51, 90, 209, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(haze)
        p.drawRect(self.rect())
        for x, y, size, phase in self.particles:
            brightness = int(110 + 120*(.5 + .5*math.sin(t*1.4 + phase)))
            p.setBrush(QColor(177, 212, 255, brightness))
            p.drawEllipse(QPointF((x*w + t*size*1.3) % max(w, 1), y*h), size, size)
        unit = min(w, h)
        self.planet(p, w*.77, h*.31, unit*.105, '#d78350', '#f6c678', '#56385a', ring=True)
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

    def mountains(self, p, w, h, t):
        gradient = QLinearGradient(0, 0, 0, h)
        gradient.setColorAt(0, QColor('#102048'))
        gradient.setColorAt(.58, QColor('#846d9a'))
        gradient.setColorAt(1, QColor('#0d1d35'))
        p.fillRect(self.rect(), gradient)
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


    def snow(self, p, w, h, t):
        """Midnight alpine snow scene, with drifting flakes."""
        sky = QLinearGradient(0, 0, 0, h)
        sky.setColorAt(0, QColor('#101b39'))
        sky.setColorAt(.6, QColor('#416d9f'))
        sky.setColorAt(1, QColor('#cee8f4'))
        p.fillRect(self.rect(), sky)
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
        for x,y,size,phase in self.particles:
            px=(x*w+math.sin(t*.7+phase)*14+t*(5+size*8))%max(1,w)
            py=(y*h+t*(15+size*10))%max(1,h)
            p.setBrush(QColor(245,251,255,165))
            p.drawEllipse(QPointF(px,py),size+0.5,size+0.5)

    def forest(self, p, w, h, t):
        """Layered evergreen forest with glowing floating fireflies."""
        sky=QLinearGradient(0,0,0,h)
        sky.setColorAt(0,QColor('#081a24'))
        sky.setColorAt(.6,QColor('#19564e'))
        sky.setColorAt(1,QColor('#0b2b2a'))
        p.fillRect(self.rect(),sky)
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
                p.drawPolygon(QPolygonF([QPointF(cx-tree_h*.28,trunk_y),QPointF(cx,trunk_y-tree_h),QPointF(cx+tree_h*.28,trunk_y)]))
                p.drawRect(QRectF(cx-3,trunk_y-2,6,h-trunk_y))
        for x,y,size,phase in self.particles[:75]:
            cx=x*w+math.sin(t*.6+phase)*12
            cy=(.18+y*.73)*h+math.cos(t*.55+phase)*8
            alpha=int(80+150*(.5+.5*math.sin(t*2+phase)))
            p.setBrush(QColor(210,255,145,alpha))
            p.drawEllipse(QPointF(cx,cy),size+1,size+1)

    def city(self, p, w, h, t):
        """Neon skyline with lit windows and animated lights."""
        sky=QLinearGradient(0,0,0,h)
        sky.setColorAt(0,QColor('#050920'))
        sky.setColorAt(.6,QColor('#1c2051'))
        sky.setColorAt(1,QColor('#090c25'))
        p.fillRect(self.rect(),sky)
        p.setPen(Qt.PenStyle.NoPen)
        for x,y,size,phase in self.particles[:55]:
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
                    flicker=math.sin(t*.8+i+row)> .95
                    p.setBrush(QColor('#ff65c5') if (i+row)%4==0 else QColor('#61e4ff') if not flicker else QColor('#293958'))
                    p.drawRect(QRectF(x0+7+col*(bw*.35),top+10+row*23, max(3,bw*.13),8))
        p.setBrush(QColor('#070f24'))
        p.drawRect(QRectF(0,h*.91,w,h*.09))
        p.setPen(QPen(QColor('#fc51b9'),3))
        p.drawLine(QPointF(0,h*.91),QPointF(w,h*.91))
        p.setPen(Qt.PenStyle.NoPen)

    def clock(self, p: QPainter, w: int, h: int) -> None:
        columns = {
            'left': (w*.035, w*.42, Qt.AlignmentFlag.AlignLeft),
            'center': (w*.29, w*.42, Qt.AlignmentFlag.AlignHCenter),
            'right': (w*.545, w*.42, Qt.AlignmentFlag.AlignRight),
        }
        rows = {'top': h*.08, 'center': h*.38, 'bottom': h*.65}
        row, column = self.clock_position.split('-')
        x, width, horizontal_alignment = columns[column]
        y = rows[row]
        alignment = horizontal_alignment | Qt.AlignmentFlag.AlignVCenter
        date_y = y + self.clock_font_size * 1.5
        p.setPen(QColor('#ecf7ff'))
        p.setFont(QFont('Sans Serif', self.clock_font_size, QFont.Weight.DemiBold))
        time_format = 'HH:mm' if self.clock_format == '24h' else 'h:mm AP'
        p.drawText(QRectF(x, y, width, self.clock_font_size*1.5), alignment,
                   QDateTime.currentDateTime().toString(time_format))
        if self.show_date:
            p.setPen(QColor('#a9c1df'))
            p.setFont(QFont('Sans Serif', max(10, round(self.clock_font_size*.34))))
            p.drawText(QRectF(x, date_y, width, self.clock_font_size*.62), alignment,
                       QDateTime.currentDateTime().toString('ddd, MMM d'))

    def weather(self, p: QPainter, w: int, h: int, t: float) -> None:
        if self.rain_enabled:
            self.draw_rain(p, w, h, t)
        if self.snow_enabled:
            self.draw_snowfall(p, w, h, t)
        if self.fog_enabled:
            self.draw_fog(p, w, h, t)
        if self.thunderstorms_enabled:
            self.draw_thunderstorms(p, w, h, t)
        if self.shooting_stars_enabled and self.theme == 'space':
            self.draw_shooting_stars(p, w, h, t)

    def draw_rain(self, p: QPainter, w: int, h: int, t: float) -> None:
        scale = min(w, h) / 900
        p.save()
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(171, 218, 255, 125), max(1, scale*1.5)))
        for x, y, speed, phase in self.rain_drops:
            drop_x = (x*w + math.sin(t*.7 + phase)*12*scale) % w
            drop_y = (y*h + t*(170 + speed*100)*scale) % h
            p.drawLine(QPointF(drop_x, drop_y), QPointF(drop_x - 5*scale, drop_y + 19*scale))
        p.restore()

    def draw_snowfall(self, p: QPainter, w: int, h: int, t: float) -> None:
        scale = min(w, h) / 900
        p.save()
        p.setPen(Qt.PenStyle.NoPen)
        for x, y, size, speed, phase in self.snowflakes:
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
        for offset, period, x in self.lightning_events:
            phase = (t + offset) % period
            if phase < .2:
                flashes.append((x, 1 - phase/.2))
        if not flashes:
            return
        p.save()
        p.setPen(Qt.PenStyle.NoPen)
        for x, intensity in flashes:
            alpha = round(72*intensity)
            p.fillRect(QRectF(0, 0, w, h), QColor(207, 224, 255, alpha))
            points = [
                QPointF(w*x, 0),
                QPointF(w*(x-.035), h*.18),
                QPointF(w*(x+.012), h*.17),
                QPointF(w*(x-.055), h*.40),
                QPointF(w*(x+.004), h*.27),
                QPointF(w*(x-.012), h*.28),
                QPointF(w*x, 0),
            ]
            p.setBrush(QColor(231, 241, 255, round(230*intensity)))
            p.drawPolygon(QPolygonF(points))
        p.restore()

    def draw_shooting_stars(self, p: QPainter, w: int, h: int, t: float) -> None:
        scale = min(w, h) / 900
        p.save()
        for offset, period, x, y in self.shooting_star_events:
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

    def bob(self, p, w, h, t, bobos_status: BobOSStatus | None = None):
        bobos_status = bobos_status or BobOSStatus(BobOSPhase.EXPLORING, 0.0)
        bobos_phase = bobos_status.phase
        phase = t % 32.0
        mood = 'curious' if 10 <= phase < 15 else 'happy' if 15 <= phase < 22 else 'sleepy' if phase >= 22 else 'idle'
        pose_time = t - (phase - 22.0) if mood == 'sleepy' else t
        x = w*.5 + math.sin(pose_time*.36)*min(w*.075, 85)
        y = h*.56 + math.sin(pose_time*1.45)*9
        scale = min(w/1250, h/800, 1.35)

        p.save()
        p.translate(x, y)
        p.scale(scale, scale)
        p.rotate(math.sin(pose_time*.72)*2.4)
        p.setPen(Qt.PenStyle.NoPen)

        if self.ai_backpack_enabled:
            self.draw_ai_backpack(p, bobos_phase, t)
        if bobos_phase in (BobOSPhase.CONNECTING, BobOSPhase.ACTIVE, BobOSPhase.PACKING_UP):
            self.draw_bobos_device(p, bobos_phase, bobos_status.phase_elapsed_seconds, t)

        # Big floating glow behind the head.
        halo = QRadialGradient(QPointF(0, 2), 185)
        halo.setColorAt(0, QColor(41, 212, 255, 78))
        halo.setColorAt(.55, QColor(41, 212, 255, 20))
        halo.setColorAt(1, QColor(41, 212, 255, 0))
        p.setBrush(halo)
        p.drawEllipse(QPointF(0, 0), 186, 186)

        # Tiny hover ring under the head to hint floating, not a body.
        p.setBrush(QColor(120, 220, 255, 28))
        p.drawEllipse(QPointF(0, 92), 34, 9)

        # Antenna.
        p.setPen(QPen(QColor('#66dfff'), 5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(0, -96, 0, -124)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor('#b2f9ff'))
        p.drawEllipse(QPointF(0, -130), 8, 8)

        # Side modules / ears.
        p.setBrush(QColor('#1f5482'))
        p.drawRoundedRect(QRectF(-87, -28, 16, 42), 7, 7)
        p.drawRoundedRect(QRectF(71, -28, 16, 42), 7, 7)

        # Outer head shell.
        p.setPen(QPen(QColor('#73dcff'), 4))
        p.setBrush(QColor('#12355f'))
        p.drawRoundedRect(QRectF(-76, -96, 152, 144), 32, 32)

        # Inner face plate.
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor('#081b3c'))
        p.drawRoundedRect(QRectF(-63, -76, 126, 102), 24, 24)

        # Top shine.
        p.setBrush(QColor(102, 217, 255, 26))
        p.drawRoundedRect(QRectF(-52, -68, 104, 20), 10, 10)

        eyes = QColor('#6bf6ff')
        blink = math.sin(t*1.55) > .988 or mood == 'sleepy'
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(eyes)
        if blink:
            p.setPen(QPen(eyes, 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(-35, -22, -12, -22)
            p.drawLine(12, -22, 35, -22)
        elif mood == 'curious':
            p.drawEllipse(QPointF(-24, -18), 11, 16)
            p.drawEllipse(QPointF(24, -18), 11, 16)
        elif mood == 'happy':
            p.drawRoundedRect(QRectF(-39, -32, 28, 22), 10, 10)
            p.drawRoundedRect(QRectF(11, -32, 28, 22), 10, 10)
        else:
            p.drawRoundedRect(QRectF(-37, -30, 26, 20), 9, 9)
            p.drawRoundedRect(QRectF(11, -30, 26, 20), 9, 9)

        # Mouth / expression.
        p.setPen(QPen(eyes, 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        if mood == 'curious':
            p.drawEllipse(QPointF(0, 6), 5, 7)
        elif mood == 'sleepy':
            p.drawLine(-11, 6, 11, 6)
        elif mood == 'happy':
            p.drawArc(QRectF(-20, -3, 40, 28), 190*16, 160*16)
        else:
            p.drawArc(QRectF(-16, 0, 32, 18), 180*16, 180*16)

        # Cheek lights.
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(107, 246, 255, 40))
        p.drawEllipse(QPointF(-44, 5), 5, 5)
        p.drawEllipse(QPointF(44, 5), 5, 5)

        p.restore()

        if mood == 'sleepy':
            p.setPen(QColor('#c3efff'))
            p.setFont(QFont('Sans Serif', 19, QFont.Weight.Bold))
            for i in range(3):
                p.drawText(QPointF(x + scale*(96 + i*25), y - scale*(72 + i*28) - 5*math.sin(pose_time + i)), 'Z')
        return mood

    @staticmethod
    def draw_ai_backpack(p: QPainter, phase: BobOSPhase, t: float) -> None:
        """Draw Bob's fictional wearable pack behind the head."""
        p.save()
        p.setPen(QPen(QColor('#60bde3'), 3))
        p.setBrush(QColor('#15344f'))
        p.drawRoundedRect(QRectF(55, -8, 51, 83), 14, 14)
        p.setPen(QPen(QColor('#417c9f'), 2))
        p.setBrush(QColor('#214d6c'))
        p.drawRoundedRect(QRectF(62, 31, 37, 32), 8, 8)
        p.setPen(QColor('#b8edff'))
        p.setFont(QFont('Sans Serif', 10, QFont.Weight.Bold))
        p.drawText(QRectF(64, 36, 33, 18), Qt.AlignmentFlag.AlignCenter, 'AI')
        p.setPen(QPen(QColor('#6ce6ff'), 3))
        p.drawLine(QPointF(61, 1), QPointF(79, 9 + math.sin(t*2)*2))
        if phase in (BobOSPhase.CONNECTING, BobOSPhase.ACTIVE):
            glow = 110 if phase is BobOSPhase.ACTIVE else round(75 + 40*(.5 + .5*math.sin(t*5)))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(93, 230, 255, glow))
            p.drawEllipse(QPointF(80, 28), 5, 5)
        p.restore()

    @staticmethod
    def draw_bobos_device(p: QPainter, phase: BobOSPhase, phase_elapsed: float, t: float) -> None:
        """Render a tiny fictional laptop and BobOS desktop without real I/O."""
        p.save()
        if phase is BobOSPhase.PACKING_UP:
            progress = min(1.0, phase_elapsed / 6.0)
            p.setPen(QPen(QColor('#83e8ff'), 2))
            p.setBrush(QColor('#173a53'))
            device_x = 92 - progress*22
            device_y = 67 - progress*45
            p.drawRoundedRect(QRectF(device_x, device_y, 50, 8), 4, 4)
            p.setPen(QPen(QColor('#9cecff'), 2))
            p.drawLine(QPointF(device_x + 4, device_y + 3), QPointF(device_x + 46, device_y + 3))
            p.restore()
            return
        p.setPen(QPen(QColor('#83e8ff'), 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.setBrush(QColor('#10273d'))
        p.drawRoundedRect(QRectF(58, 23, 83, 66), 7, 7)
        screen = QLinearGradient(60, 25, 139, 87)
        screen.setColorAt(0, QColor('#132c54'))
        screen.setColorAt(1, QColor('#241e54'))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(screen)
        p.drawRoundedRect(QRectF(64, 29, 71, 53), 4, 4)
        p.setPen(QColor('#d9f8ff'))
        p.setFont(QFont('Sans Serif', 7, QFont.Weight.Bold))
        p.drawText(QRectF(68, 32, 63, 11), Qt.AlignmentFlag.AlignCenter, 'BobOS 1.0')
        p.setPen(Qt.PenStyle.NoPen)
        app_colors = (QColor('#5ee7ff'), QColor('#a78bfa'), QColor('#64e6a2'))
        for index, color in enumerate(app_colors):
            p.setBrush(color)
            p.drawRoundedRect(QRectF(72 + index*18, 48, 13, 13), 3, 3)
            p.setBrush(QColor(224, 245, 255, 150))
            p.drawRoundedRect(QRectF(70 + index*18, 67, 16, 3), 1, 1)
        if phase is BobOSPhase.CONNECTING:
            p.setPen(QColor('#a8efff'))
            p.setFont(QFont('Sans Serif', 6, QFont.Weight.DemiBold))
            p.drawText(QRectF(68, 80, 64, 9), Qt.AlignmentFlag.AlignCenter,
                       'CONNECTING' if int(t*2) % 2 == 0 else 'CONNECTING…')
        p.setPen(QPen(QColor('#9cecff'), 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(54, 91), QPointF(145, 91))
        p.drawLine(QPointF(54, 91), QPointF(62, 97))
        p.drawLine(QPointF(145, 91), QPointF(137, 97))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor('#68d9f4'))
        p.drawRoundedRect(QRectF(62, 95, 75, 5), 2, 2)
        p.restore()

    def caption(self, p, w, h, t, bobos_phase: BobOSPhase = BobOSPhase.EXPLORING):
        mood = 'curious' if 10 <= (t % 32) < 15 else 'happy' if 15 <= (t % 32) < 22 else 'sleepy' if (t % 32) >= 22 else 'idle'
        words = {
            'space': {
                'idle': 'Bob is exploring the stars…',
                'curious': 'Bob spotted something interesting!',
                'happy': 'Bob loves the galaxy!',
                'sleepy': 'Bob is dreaming among the stars…'
            },
            'mountains': {
                'idle': 'Bob is exploring the mountains…',
                'curious': 'What is beyond that peak?',
                'happy': 'Bob loves the mountain air!',
                'sleepy': 'Bob is resting under the moon…'
            },
            'snow': {
                'idle': 'Bob is watching the snowfall…',
                'curious': 'Where do the snowflakes go?',
                'happy': 'Bob loves snowy mountains!',
                'sleepy': 'Bob is dreaming in the snow…'
            },
            'forest': {
                'idle': 'Bob is exploring the forest…',
                'curious': 'Did something move behind that tree?',
                'happy': 'Bob found glowing fireflies!',
                'sleepy': 'Bob is resting among the trees…'
            },
            'city': {
                'idle': 'Bob is exploring the neon city…',
                'curious': 'What is that glowing light?',
                'happy': 'Bob loves the city lights!',
                'sleepy': 'Bob is dreaming of electric skies…'
            }
        }
        if bobos_phase is BobOSPhase.CONNECTING:
            caption = 'Bob is connecting to BobOS…'
        elif bobos_phase is BobOSPhase.ACTIVE:
            caption = 'BobOS 1.0 is open — Bob is exploring!'
        elif bobos_phase is BobOSPhase.PACKING_UP:
            caption = 'Bob is closing BobOS and packing up…'
        else:
            caption = words[self.theme][mood]
        p.setPen(QColor('#dcecff'))
        p.setFont(QFont('Sans Serif', max(13, min(22, w//72))))
        p.drawText(QRectF(0, h*.79, w, 39), Qt.AlignmentFlag.AlignCenter, caption)
        p.setPen(QColor('#92adc8'))
        p.setFont(QFont('Sans Serif', 12))
        p.drawText(QRectF(0, h-55, w, 30), Qt.AlignmentFlag.AlignCenter,
                   'Move the mouse or press a key to exit')

    @staticmethod
    def countdown_color(progress):
        """Interpolate a continuously changing green-to-red countdown color.

        Stops: 0%=green, 25%=yellow, 50%=orange, 75%=red,
        then hold red for the final quarter. Works for every duration.
        """
        progress = max(0.0, min(1.0, progress))
        stops = [
            (0.00, (45, 230, 105)),
            (0.25, (252, 220, 43)),
            (0.50, (255, 138, 33)),
            (0.75, (255, 53, 70)),
            (1.00, (255, 53, 70)),
        ]
        for (at_a, ca), (at_b, cb) in zip(stops, stops[1:]):
            if progress <= at_b:
                blend = (progress - at_a) / (at_b - at_a)
                # Smoothstep eases transitions, with no sudden jumps.
                blend = blend * blend * (3.0 - 2.0 * blend)
                return QColor(*(round(a + (b - a)*blend) for a, b in zip(ca, cb)))
        return QColor(*stops[-1][1])

    def countdown(self, p, w, h, t):
        left = max(0, math.ceil(self.lock_seconds - t))
        label = (f"KDE locks in {left // 60:02d}:{left % 60:02d}"
                 if not self.lock_error else "Could not contact KDE screen locker — retrying")
        color = self.countdown_color(t / self.lock_seconds)
        p.save()
        p.setPen(color)
        p.setFont(QFont('Sans Serif', max(17, min(29, w//55)), QFont.Weight.Bold))
        p.drawText(QRectF(0, h * .86, w, 42), Qt.AlignmentFlag.AlignCenter, label)
        # Progress bar: the entire bar uses the same continuous color.
        bar_width = min(380, w*.46)
        bar_left = (w - bar_width) / 2
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(215, 232, 255, 45))
        p.drawRoundedRect(QRectF(bar_left, h*.915, bar_width, 6), 3, 3)
        p.setBrush(color)
        p.drawRoundedRect(QRectF(bar_left, h*.915, bar_width * max(0, 1-t/self.lock_seconds), 6), 3, 3)
        p.restore()

    def request_kde_lock(self):
        if self.lock_attempted:
            return
        self.lock_attempted = True
        try:
            result = subprocess.run([
                'dbus-send', '--session', '--print-reply',
                '--dest=org.freedesktop.ScreenSaver', '/ScreenSaver',
                'org.freedesktop.ScreenSaver.Lock'
            ], timeout=4, capture_output=True, check=False)
            if result.returncode == 0:
                QApplication.quit()
                return
        except (OSError, subprocess.TimeoutExpired):
            pass
        self.lock_error = True
        self.lock_attempted = False
        self.update()

    def mouseMoveEvent(self, event):
        pos = event.position()
        if self.old_mouse is not None and time.monotonic() - self.start_time > 1.5:
            d = pos - self.old_mouse
            if abs(d.x()) + abs(d.y()) > 5:
                QApplication.quit()
        self.old_mouse = pos

    def mousePressEvent(self, event):
        QApplication.quit()

    def keyPressEvent(self, event):
        QApplication.quit()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    saver = Saver()
    saver.showFullScreen()
    saver.activateWindow()
    sys.exit(app.exec())
