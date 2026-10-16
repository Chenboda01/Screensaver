"""Layered sky painting: landscape callers paint their terrain on top."""
import math
from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QRadialGradient
from live_sky import SkyPosition, Weather


def blend(a: tuple[int, int, int], b: tuple[int, int, int], amount: float) -> QColor:
    fraction = max(0., min(1., amount))
    fraction = fraction*fraction*(3-2*fraction)
    return QColor(*(round(x+(y-x)*fraction) for x, y in zip(a, b)))


def draw_sky(p: QPainter, w: int, h: int, t: float, sky: SkyPosition, weather: Weather) -> None:
    p.save()
    altitude = sky.sun_altitude
    daylight = max(0., min(1., (altitude+18)/30))
    top = blend((5, 10, 30), (38, 123, 190), daylight)
    horizon = blend((17, 27, 57), (169, 219, 241), daylight)
    warmth = max(0., 1-abs(altitude)/12)
    horizon = blend(horizon.getRgb()[:3], (244, 143, 95), warmth)
    cloudiness = max(weather.cloud/100, .96 if weather.category == 'overcast' else 0)
    top = blend(top.getRgb()[:3], (75, 87, 102), cloudiness*.65*daylight)
    horizon = blend(horizon.getRgb()[:3], (106, 119, 133), cloudiness*.8*daylight)
    gradient = QLinearGradient(0, 0, 0, h*.8)
    gradient.setColorAt(0, top)
    gradient.setColorAt(1, horizon)
    p.fillRect(QRectF(0, 0, w, h), gradient)
    p.setPen(Qt.PenStyle.NoPen)
    illumination = (1-math.cos(sky.moon_phase*math.tau))/2
    moonlight = illumination if sky.moon_altitude > 0 else 0
    star_alpha = round(210*(1-daylight)*(1-.55*moonlight)*(1-cloudiness))
    p.setBrush(QColor(232, 241, 255, star_alpha))
    for index in range(90):
        x = ((index*0.61803398875)%1)*w
        y = ((index*0.41421356237)%1)*h*.64
        radius = 1+index%3*.35
        p.drawEllipse(QPointF(x, y), radius, radius)
    if cloudiness < .9:
        if altitude > -.83:
            center = QPointF(w*(.15+.7*sky.sun_azimuth/360), h*(.7-.58*max(0., altitude)/90))
            _glow(p, center, 80, QColor(255, 221, 140, 100))
            p.setBrush(QColor('#fff0ba'))
            p.drawEllipse(center, 23, 23)
        if sky.moon_altitude > 0 and illumination > .008:
            center = QPointF(w*(.15+.7*sky.moon_azimuth/360), h*(.7-.58*sky.moon_altitude/90))
            _glow(p, center, 40+70*illumination, QColor(208, 226, 255, round((1-daylight*.75)*85*illumination)))
            _moon(p, center, 22., sky.moon_phase, QColor(229, 237, 246, round(255-daylight*90)))
    # Clouds are painted after the discs: moving opaque cores physically occlude them.
    count = round(2+cloudiness*12) if cloudiness > .1 else 0
    for index in range(count):
        speed = 7+weather.wind*.7
        x = ((index*.273*w+t*speed) % (w*1.5))-w*.25
        y = h*(.12+(index%4)*.145)
        width = w*(.14+.1*cloudiness)
        color = blend((70, 79, 100), (219, 226, 232), daylight)
        color = blend(color.getRgb()[:3], (103, 116, 132), cloudiness*.65)
        color.setAlpha(round(160+90*cloudiness))
        p.setBrush(color)
        for dx, dy, size in ((-.35, .05, .65), (0, -.07, 1), (.36, .04, .7)):
            p.drawEllipse(QPointF(x+dx*width, y+dy*width), width*size*.65, width*size*.21)
    p.restore()


def _glow(p: QPainter, center: QPointF, radius: float, color: QColor) -> None:
    glow = QRadialGradient(center, radius)
    glow.setColorAt(0, color)
    transparent = QColor(color)
    transparent.setAlpha(0)
    glow.setColorAt(1, transparent)
    p.setBrush(glow)
    p.drawEllipse(center, radius, radius)


def _moon(p: QPainter, center: QPointF, radius: float, phase: float, color: QColor) -> None:
    # A lit limb and elliptical terminator produce waxing/waning crescents/gibbous.
    waxing = phase < .5
    side = 1 if waxing else -1
    terminator = math.cos(phase*math.tau)
    path = QPainterPath()
    for index in range(65):
        y = -1+2*index/64
        x = side*math.sqrt(max(0., 1-y*y))
        point = QPointF(center.x()+x*radius, center.y()+y*radius)
        if index == 0: path.moveTo(point)
        else: path.lineTo(point)
    for index in range(64, -1, -1):
        y = -1+2*index/64
        x = side*terminator*math.sqrt(max(0., 1-y*y))
        path.lineTo(QPointF(center.x()+x*radius, center.y()+y*radius))
    path.closeSubpath()
    p.setBrush(color)
    p.drawPath(path)
