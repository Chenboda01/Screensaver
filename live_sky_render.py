"""Layered landscape skies and a cached, atmosphere-free orbital scene."""
from datetime import datetime, timezone
import math
from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QImage, QLinearGradient, QPainter, QPainterPath, QPen, QRadialGradient
from live_sky import SkyPosition, Weather, sky_position


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
    p.setBrush(color)
    p.drawPath(_phase_path(center, radius, phase))


def _phase_path(center: QPointF, radius: float, phase: float) -> QPainterPath:
    """Project the illuminated portion of a sphere onto a circular disc."""
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
    return path


def earth_phase(altitude: float, morning: bool) -> float:
    """Place the disc center on the local day/night side of the terminator.

    The visible lit fraction is (1 + sin(sun altitude)) / 2: a half-disc
    at the horizon, fully lit at the zenith, and dark at the nadir.
    """
    phase = .25 + altitude / 360
    return phase if morning else 1 - phase


class SpaceSky:
    """Mutable single-frame cache, rebuilt once a minute or on location/size change."""

    def __init__(self) -> None:
        self._key: tuple[int, int, tuple[float, float] | None] | None = None
        self._image = QImage()

    def draw(self, p: QPainter, w: int, h: int, now: float,
             coordinates: tuple[float, float] | None) -> None:
        """Draw Earth and the Moon behind Bob; unknown locations stay half-lit."""
        radius = max(1, round(min(w, h) * .12))
        key = (radius, math.floor(now / 60), coordinates)
        if key != self._key:
            sky = sky_position(datetime.fromtimestamp(now, timezone.utc), *(coordinates or (0., 0.)))
            phase = earth_phase(sky.sun_altitude, sky.morning) if coordinates is not None else .25
            self._image = self._render(radius, phase, sky.moon_phase)
            self._key = key
        p.drawImage(QPointF(w * .19 - radius * 1.15, h * .43 - radius * 1.7), self._image)

    @staticmethod
    def _render(radius: int, phase: float, moon_phase: float) -> QImage:
        """Rasterize the decorative continents, night lights, and phase masks."""
        image = QImage(radius * 4, radius * 3, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.transparent)
        p = QPainter(image)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        center = QPointF(radius * 1.15, radius * 1.7)
        _glow(p, center, radius * 1.14, QColor(80, 169, 247, 100))
        disc = QPainterPath()
        disc.addEllipse(center, radius, radius)
        continents = QPainterPath()
        for outline in (
            ((-.84,-.56),(-.54,-.79),(-.2,-.65),(-.12,-.39),(-.31,-.18),(-.23,.02),(-.39,.13),(-.57,-.1),(-.8,-.19)),
            ((-.35,.13),(-.1,.18),(.02,.37),(-.17,.71),(-.32,.85),(-.4,.46)),
            ((.06,-.55),(.29,-.72),(.69,-.55),(.88,-.25),(.64,-.04),(.4,-.16),(.29,.06),(.08,-.07),(-.03,-.32)),
            ((.1,-.04),(.4,.02),(.48,.26),(.25,.59),(.1,.4),(-.02,.15)),
            ((.59,.42),(.84,.37),(.9,.59),(.64,.68),(.51,.56)),
        ):
            continents.moveTo(center + QPointF(outline[0][0]*radius, outline[0][1]*radius))
            for x, y in outline[1:]:
                continents.lineTo(center + QPointF(x*radius, y*radius))
            continents.closeSubpath()
        p.setClipPath(disc)
        p.fillPath(disc, QColor('#081529'))
        p.fillPath(continents, QColor('#112836'))
        p.setBrush(QColor('#ffce80'))
        for index in range(300):
            point = center + QPointF((((index*.618033989)%1)*2-1)*radius,
                                     (((index*.414213562)%1)*2-1)*radius)
            if continents.contains(point):
                p.drawEllipse(point, max(.6, radius*.006), max(.6, radius*.006))
        p.save()
        p.setClipPath(_phase_path(center, radius, phase), Qt.ClipOperation.IntersectClip)
        p.fillPath(disc, QColor('#287fc0'))
        p.fillPath(continents, QColor('#69a788'))
        p.setBrush(QColor('#d6e9ed'))
        p.drawEllipse(center + QPointF(0, -radius), radius*.48, radius*.12)
        p.drawEllipse(center + QPointF(0, radius), radius*.48, radius*.09)
        p.restore()
        rim = QRadialGradient(center, radius)
        rim.setColorAt(0, QColor(0, 10, 30, 0))
        rim.setColorAt(.72, QColor(0, 10, 30, 0))
        rim.setColorAt(1, QColor(0, 10, 30, 160))
        p.fillPath(disc, rim)
        terminator = QPainterPath()
        side = 1 if phase < .5 else -1
        for index in range(65):
            y = -1 + index / 32
            x = side * math.cos(phase*math.tau) * math.sqrt(max(0., 1-y*y))
            point = center + QPointF(x*radius, y*radius)
            if index == 0:
                terminator.moveTo(point)
            else:
                terminator.lineTo(point)
        warmth = max(0., 1 - abs(math.cos(phase*math.tau))*4)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(255, 169, 91, round(150*warmth)), max(1., radius*.025)))
        p.drawPath(terminator)
        p.setClipping(False)
        p.setPen(QPen(QColor(104, 187, 245, 160), max(1., radius*.012)))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(disc)
        moon = QPointF(radius*2.9, radius*.8)
        moon_radius = radius*.3
        illumination = (1-math.cos(moon_phase*math.tau))/2
        p.setPen(Qt.PenStyle.NoPen)
        _glow(p, moon, moon_radius*1.7, QColor(193, 217, 244, round(45*illumination)))
        p.setPen(QPen(QColor('#65728c'), max(.7, radius*.006)))
        p.setBrush(QColor('#182136'))
        p.drawEllipse(moon, moon_radius, moon_radius)
        p.setPen(Qt.PenStyle.NoPen)
        _moon(p, moon, moon_radius, moon_phase, QColor('#dce5ef'))
        p.setClipPath(_phase_path(moon, moon_radius, moon_phase))
        p.setBrush(QColor(82, 101, 129, 55))
        for x, y, size in ((-.4,-.3,.22), (.3,.2,.27), (-.2,.5,.14)):
            p.drawEllipse(moon+QPointF(x*moon_radius, y*moon_radius), size*moon_radius, size*moon_radius)
        p.end()
        return image
