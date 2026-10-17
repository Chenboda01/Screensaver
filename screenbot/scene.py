import math
import time
from datetime import UTC, datetime

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QImage, QLinearGradient, QPainter, QPen

from live_sky import SkyPosition, sky_position
from live_sky_render import draw_sky
from screenbot.runtime import particle_count, quality_particle_count
from screenbot.themes import THEME_MOTION_RENDERERS, THEME_RENDERERS
from screenbot.themes.environment import ThemeEnvironment, ThemeFrame


class SceneRenderer:
    def _draw_photo_fallback_landscape(self, painter: QPainter, width: int,
                                       height: int, elapsed: float) -> None:
        """Use the built-in Mountains scene behind the empty-library notice."""
        self.mountains_background(painter, width, height, elapsed)

    def draw_scenery(self, p: QPainter, w: int, h: int, t: float) -> None:
        """Render a cached static scene beneath the live weather/effect layers."""
        if self.theme == 'photos':
            # Photos change continuously and are asynchronously decoded, so
            # they bypass the static theme cache. Existing weather remains a
            # separate overlay and Bob/clock/BobOS stay in the normal layers.
            THEME_RENDERERS[self.theme](self, p, w, h, t)
            self.weather(p, w, h, t)
            return
        if self.theme in THEME_MOTION_RENDERERS:
            self._update_live_sky_position()
        cache_key = (self.theme, w, h, self.live_sky_enabled,
                     self.live_weather.weather.category if self.live_sky_enabled else '',
                     math.floor(time.time() / 60) if self.live_sky_enabled else 0)
        now = time.monotonic()
        # Live-Sky clouds and wind-affected trees move, so refresh their static
        # atmosphere once a second while retaining the expensive frame cache.
        cache_lifetime = 1.0 if self.live_sky_enabled or self.theme == 'city' else float('inf')
        if (self._scenery_cache is None or self._scenery_cache_key != cache_key
                or now - self._scenery_cache_time >= cache_lifetime):
            image = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
            image.fill(Qt.GlobalColor.transparent)
            layer = QPainter(image)
            layer.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            self._draw_static_scenery(layer, w, h, t)
            layer.end()
            self._scenery_cache = image
            self._scenery_cache_key = cache_key
            self._scenery_cache_time = now
        p.drawImage(0, 0, self._scenery_cache)
        self._draw_scenery_motion(p, w, h, t)
        if self.theme == 'space':
            self._draw_space_foreground(p, w, h)
            if self.live_sky_enabled:
                coordinates = (self.live_weather.latitude, self.live_weather.longitude) if self.live_weather.located else None
                self.space_sky.draw(p, w, h, time.time(), coordinates)
        if self.live_sky_enabled and self.theme not in ('space', 'underwater') and self.live_sky_position is not None:
            self.live_landscape_light(p, w, h, t)
        self.weather(p, w, h, t)
        latitude = self.live_weather.latitude if self.live_weather.located else None
        self.seasonal_bob_hat = self.seasonal_session.draw(p, w, h, t, self.theme, latitude, self.reduce_motion)

    def _draw_static_scenery(self, p: QPainter, w: int, h: int, t: float) -> None:
        """Render the selected theme through the central theme registry."""
        THEME_RENDERERS[self.theme](self, p, w, h, t)

    def _draw_space_foreground(self, p: QPainter, w: int, h: int) -> None:
        """Reuse costly planetary gradients, painted above the moving starfield."""
        key = (w, h, self.live_sky_enabled)
        if self._space_foreground_cache is None or self._space_foreground_key != key:
            image = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
            image.fill(Qt.GlobalColor.transparent)
            layer = QPainter(image)
            layer.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            unit = min(w, h)
            self.planet(layer, w*.77, h*.31, unit*.105, '#d78350', '#f6c678', '#56385a', ring=True)
            if not self.live_sky_enabled:
                self.planet(layer, w*.19, h*.43, unit*.047, '#347cbe', '#92e4f4', '#253e85')
            self.planet(layer, w*.81, h*.68, unit*.032, '#a85576', '#f3a3b2', '#4c397f')
            layer.end()
            self._space_foreground_cache = image
            self._space_foreground_key = key
        p.drawImage(0, 0, self._space_foreground_cache)

    def _draw_scenery_motion(self, p: QPainter, w: int, h: int, t: float) -> None:
        """Draw foreground motion over the cached static theme layer."""
        scale = 0.3 if self.reduce_motion else (0.5 if self.performance_mode == 'battery-saver' else 1.0)
        if self.theme in THEME_MOTION_RENDERERS:
            THEME_MOTION_RENDERERS[self.theme](self, p, w, h, t)
            return
        p.setPen(Qt.PenStyle.NoPen)
        if self.theme == 'space':
            for x, y, size, phase in self.particles[:particle_count(len(self.particles), scale)]:
                brightness = int(110 + 120*(.5 + .5*math.sin(t*1.4 + phase)))
                p.setBrush(QColor(177, 212, 255, brightness))
                p.drawEllipse(QPointF((x*w + t*size*1.3) % max(w, 1), y*h), size, size)
        elif self.theme == 'mountains':
            mountain_count = quality_particle_count(40, self.performance_mode)
            for x, y, radius, phase in self.particles[:particle_count(mountain_count, scale)]:
                p.setBrush(QColor(255, 231, 168, int(70 + 100*(.5 + .5*math.sin(t + phase)))))
                p.drawEllipse(QPointF(x*w, h*(.67 + y*.31)), radius, radius)
        elif self.theme == 'snow':
            if not self.live_sky_enabled:
                for x, y, size, phase in self.particles[:particle_count(len(self.particles), scale)]:
                    px=(x*w+math.sin(t*.7+phase)*14+t*(5+size*8))%max(1,w)
                    py=(y*h+t*(15+size*10))%max(1,h)
                    p.setBrush(QColor(245,251,255,165))
                    p.drawEllipse(QPointF(px,py),size+0.5,size+0.5)
        elif self.theme == 'forest':
            forest_count = quality_particle_count(75, self.performance_mode)
            for x,y,size,phase in self.particles[:particle_count(forest_count, scale)]:
                cx=x*w+math.sin(t*.6+phase)*12
                cy=(.18+y*.73)*h+math.cos(t*.55+phase)*8
                alpha=int((80+150*(.5+.5*math.sin(t*2+phase))) * (0.45 if self.reduce_motion else 1))
                p.setBrush(QColor(210,255,145,alpha))
                p.drawEllipse(QPointF(cx,cy),size+1,size+1)

    def preview_hint(self, painter: QPainter, width: int, height: int, elapsed: float) -> None:
        """Explain the temporary view, including missing Live Sky data, independently of the clock."""
        if elapsed >= 8:
            return
        theme_name = 'Futuristic City' if self.theme == 'city' else self.theme.title()
        selection = f'Random → {theme_name}' if self.random_theme else theme_name
        lines = [f'Preview: {selection} · Move the mouse or press any key to close']
        if self.live_sky_enabled:
            if not self.live_sky_location:
                lines.append('Live Sky: choose a city in Settings · showing time and moon only')
            elif not self.live_weather.located:
                lines.append('Live Sky: location loading or unavailable · showing time and moon only')
            elif self.theme != 'space' and not self.live_weather.fresh:
                lines.append('Live Sky: weather loading or unavailable · showing time and moon only')
        painter.save()
        painter.setOpacity(min(1., max(0., (8-elapsed)/2)))
        painter.setFont(QFont('Sans Serif', 12))
        bounds = QRectF(width*.05, height*.02, width*.9, 90)
        flags = Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap
        text = '\n'.join(lines)
        bounds = painter.boundingRect(bounds, flags, text).adjusted(-14, -8, 14, 8)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 190))
        painter.drawRoundedRect(bounds, 8, 8)
        painter.setPen(QColor('#ecf7ff'))
        painter.drawText(bounds, flags, text)
        painter.restore()

    def live_background(self, p: QPainter, w: int, h: int, t: float) -> None:
        self._update_live_sky_position()
        sky = self.live_sky_position
        if not self.live_weather.located and not self.quick_preview:
            sky = SkyPosition(-20, 0, -90, 0, 0, False)
        draw_sky(p, w, h, t, sky, self.live_weather.weather)
        p.setPen(Qt.PenStyle.NoPen)

    def _update_live_sky_position(self) -> None:
        """Refresh the shared astronomy snapshot at most once per second."""
        now = time.time()
        if self.live_sky_position is None or abs(now-self.live_sky_sample_time) >= 1:
            latitude, longitude = self.live_weather.latitude, self.live_weather.longitude
            if self.quick_preview and not self.live_weather.located:
                offset = datetime.now().astimezone().utcoffset()
                latitude = 0.
                longitude = offset.total_seconds()/240 if offset is not None else 0.
            self.live_sky_position = sky_position(datetime.now(UTC), latitude, longitude)
            self.live_sky_sample_time = now

    def theme_frame(self, width: int, height: int, elapsed: float) -> ThemeFrame:
        """Build one immutable theme input snapshot from live scene settings."""
        if self.live_sky_enabled:
            self._update_live_sky_position()
        motion_scale = .3 if self.reduce_motion else (
            .5 if self.performance_mode == 'battery-saver' else 1.0
        )
        weather_enabled = self.rain_enabled or self.snow_enabled or self.thunderstorms_enabled
        environment = ThemeEnvironment(
            live_sky_enabled=self.live_sky_enabled,
            sky=(SkyPosition(-20, 0, -90, 0, 0, False)
                 if self.live_sky_enabled and not self.live_weather.located and not self.quick_preview
                 else self.live_sky_position if self.live_sky_enabled else None),
            weather=self.live_weather.weather,
            manual_surface_precipitation=weather_enabled,
        )
        return ThemeFrame(width, height, elapsed, environment, motion_scale)

    def live_landscape_light(self, p: QPainter, w: int, h: int, t: float) -> None:
        sky = self.live_sky_position
        weather = self.live_weather.weather
        p.save()
        daylight = max(0., min(1., (sky.sun_altitude+6)/30))
        moonlight = (1-math.cos(sky.moon_phase*math.tau))/2 if sky.moon_altitude > 0 else 0
        tint = QColor(210, 233, 255, round(16*moonlight*(1-daylight)*(1-weather.cloud/100)+18*daylight))
        lighting = QLinearGradient(0, h*.45, 0, h)
        transparent = QColor(tint)
        transparent.setAlpha(0)
        lighting.setColorAt(0, transparent)
        lighting.setColorAt(1, tint)
        p.fillRect(QRectF(0, h*.45, w, h*.55), lighting)
        if weather.category == 'snow':
            p.fillRect(QRectF(0, h*.94, w, h*.06), QColor(231,244,255,round(min(70., t*.5)*weather.intensity)))
        if weather.category in ('rain', 'thunderstorm'):
            p.setBrush(Qt.BrushStyle.NoBrush)
            for index in range(round(4+weather.intensity*12)):
                progress = (t*.8+index*.37)%1
                p.setPen(QPen(QColor(175,218,245,round((1-progress)*80)), 1))
                p.drawEllipse(QPointF(((index*.618)%1)*w, h*(.89+(index%3)*.035)), 4+progress*20, 1+progress*4)
        p.restore()
