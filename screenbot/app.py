import configparser
import math
import random
import subprocess
import time
from pathlib import Path

from PyQt6.QtCore import QRectF, Qt, QTimer
from PyQt6.QtGui import QColor, QCursor, QPainter, QShowEvent
from PyQt6.QtWidgets import QApplication, QWidget
from live_sky_network import LiveWeather
from live_sky_render import SpaceSky
from bobos import BobOSPhase, BobOSStatus, BobOSTimeline, bobos_may_run
from screenbot.appearance import BobAppearance
from screenbot.bob import BobRenderer
from screenbot.burnin import burn_in_dim_alpha, burn_in_scene_scale, burn_in_scene_shift, normalize_burn_in_mode
from screenbot.clock import ClockRenderer
from screenbot.effects import WeatherEffects
from screenbot.phone.apps import PhoneAppsRenderer
from screenbot.phone.frame import PhoneFrameRenderer
from screenbot.runtime import battery_powered, frame_interval_ms
from screenbot.scene import SceneRenderer
from screenbot.settings import CLOCK_POSITIONS, PHONE_UI_PHASES, read_settings, selected_theme
from screenbot.themes.city import CityTheme
from screenbot.themes.forest import ForestTheme
from screenbot.themes.mountains import MountainsTheme
from screenbot.themes.snow import SnowTheme
from screenbot.themes.space import SpaceTheme


class Saver(QWidget, SceneRenderer, SpaceTheme, MountainsTheme, SnowTheme, ForestTheme, CityTheme, WeatherEffects, BobRenderer, ClockRenderer, PhoneFrameRenderer, PhoneAppsRenderer):
    def __init__(self, *, preview: bool = False, config_path: Path | None = None,
                 preview_bobos: bool = False, preview_wifi_animation: bool | None = None):
        super().__init__()
        self.setWindowTitle('ScreenBot Screensaver')
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.BlankCursor)
        self.quick_preview = preview
        self.is_preview = preview or preview_bobos
        settings = read_settings(config_path)
        self.bob_appearance = BobAppearance.from_settings(settings)
        self.theme = selected_theme(settings)
        self.random_theme = settings.get('Screensaver', 'theme', fallback='random') == 'random'
        self.show_clock = settings.getboolean('Screensaver', 'show_clock', fallback=True)
        self.clock_format = settings.get('Screensaver', 'clock_format', fallback='12h').strip()
        if self.clock_format not in ('12h', '24h'):
            self.clock_format = '12h'
        self.show_date = settings.getboolean('Screensaver', 'show_date', fallback=False)
        clock_position = settings.get('Screensaver', 'clock_position', fallback='top-center').strip()
        self.clock_position = clock_position if clock_position in CLOCK_POSITIONS else 'top-center'
        self.burn_in_protection = normalize_burn_in_mode(
            settings.get('Screensaver', 'burn_in_protection', fallback='standard'))
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
        self.live_sky_enabled = settings.getboolean('Screensaver', 'live_sky_enabled', fallback=False)
        self.live_sky_conditions = settings.getboolean('Screensaver', 'live_sky_conditions', fallback=True)
        self.live_sky_units = settings.get('Screensaver', 'live_sky_units', fallback='c')
        try:
            interval = settings.getint('Screensaver', 'live_sky_interval', fallback=30)
        except ValueError:
            interval = 30
        self.live_sky_location = settings.get('Screensaver', 'live_sky_location', fallback='').strip()
        try:
            coordinates = (settings.getfloat('Screensaver', 'live_sky_latitude'),
                           settings.getfloat('Screensaver', 'live_sky_longitude'))
        except (ValueError, configparser.Error):
            coordinates = None
        self.live_sky_sample_time = 0.
        self.live_sky_position = None
        self.space_sky = SpaceSky()
        self.live_weather = LiveWeather(self, enabled=self.live_sky_enabled,
                                       location=self.live_sky_location, interval=interval,
                                       coordinates=coordinates,
                                       timezone_name=settings.get('Screensaver', 'live_sky_timezone', fallback=''),
                                       config_path=None if self.is_preview else Path.home() / '.config' / 'screenbot-screensaver.ini')

        self.password_lock = not self.is_preview and settings.getboolean('Screensaver', 'password_lock', fallback=False)
        try:
            minutes = settings.getint('Screensaver', 'lock_minutes', fallback=2)
        except ValueError:
            minutes = 2
        self.lock_seconds = max(1, min(60, minutes)) * 60
        self.show_timer = self.password_lock and settings.getboolean('Screensaver', 'show_timer', fallback=False)
        self.preview_bobos = preview_bobos
        if settings.has_option('Screensaver', 'bob_phone_enabled'):
            configured_phone = settings.getboolean('Screensaver', 'bob_phone_enabled')
        else:
            configured_phone = settings.getboolean('Screensaver', 'ai_backpack_enabled', fallback=True)
        self.phone_enabled = preview_bobos or configured_phone
        self.bobos_enabled = settings.getboolean('Screensaver', 'bobos_enabled', fallback=True)
        if preview_bobos:
            self.bobos_enabled = True
        if preview:
            self.bobos_enabled = False
        try:
            bobos_delay_minutes = settings.getint('Screensaver', 'bobos_activation_delay', fallback=3)
        except ValueError:
            bobos_delay_minutes = 3
        self.bobos_activation_delay_seconds = max(1, min(30, bobos_delay_minutes)) * 60
        self.show_wifi_animation = (
            preview_wifi_animation
            if preview_wifi_animation is not None
            else settings.getboolean('Screensaver', 'show_wifi_animation', fallback=True)
        )
        self.performance_mode = settings.get('Screensaver', 'performance_mode', fallback='balanced').strip().lower()
        if self.performance_mode not in ('smooth', 'balanced', 'battery-saver'):
            self.performance_mode = 'balanced'
        self.reduce_motion = settings.getboolean('Screensaver', 'reduce_motion', fallback=False)
        self.on_battery = battery_powered()
        self._last_power_check = time.monotonic()
        self._scenery_cache = None
        self._scenery_cache_key = None
        self._scenery_cache_time = 0.0
        self._space_foreground_cache = None
        self._space_foreground_key = None
        schedule_random = random.Random()
        self.bobos_timeline = BobOSTimeline(
            activation_delay_seconds=self.bobos_activation_delay_seconds,
            show_connection_animation=self.show_wifi_animation,
            first_adventure_offset_seconds=0 if preview_bobos else schedule_random.randint(0, 90),
            cooldown_offset_seconds=schedule_random.randint(60, 180),
            preview_mode=preview_bobos,
        )
        self.lock_attempted = False
        self.next_lock_attempt = 0.0
        self.lock_error = False
        self.start_time = time.monotonic()
        self.session_started = False
        self.old_mouse = None
        r = random.Random()
        self.particles = [(r.random(), r.random(), r.uniform(.65, 2.6), r.random()*math.tau) for _ in range(110)]
        self.rain_drops = [(r.random(), r.random(), r.uniform(.8, 1.8), r.random()) for _ in range(150)]
        self.snowflakes = [(r.random(), r.random(), r.uniform(1.2, 4.0), r.uniform(.5, 1.6), r.random()*math.tau) for _ in range(110)]
        self.lightning_events = [(r.uniform(0, 20), r.uniform(12, 24), r.uniform(.15, .85)) for _ in range(4)]
        self.shooting_star_events = [(r.uniform(0, 24), r.uniform(10, 22), r.uniform(.1, .8), r.uniform(.08, .35)) for _ in range(5)]
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.lock_timer = QTimer(self)
        self.lock_timer.setInterval(1000)
        self.lock_timer.timeout.connect(self.check_password_lock)
        if self.password_lock:
            self.lock_timer.start()

    def animate(self) -> None:
        """Advance animation with power and unattended-time aware pacing."""
        elapsed = max(0.0, time.monotonic() - self.start_time)
        now = time.monotonic()
        if now - self._last_power_check >= 30:
            self.on_battery = battery_powered()
            self._last_power_check = now
        interval = frame_interval_ms(self.performance_mode, self.on_battery, elapsed)
        if self.timer.interval() != interval:
            self.timer.setInterval(interval)
        self.update()

    def check_password_lock(self) -> None:
        """Keep KDE's real lock deadline independent of paint visibility/FPS."""
        if not self.password_lock:
            return
        elapsed = max(0.0, time.monotonic() - self.start_time)
        if elapsed >= self.lock_seconds and elapsed >= self.next_lock_attempt:
            self.next_lock_attempt = elapsed + 5
            QTimer.singleShot(0, self.request_kde_lock)

    def showEvent(self, event: QShowEvent) -> None:
        """Start all screensaver-relative timers when Bob first becomes visible."""
        if not self.session_started:
            self.start_time = time.monotonic()
            self.session_started = True
        if not self.timer.isActive():
            self.timer.start(frame_interval_ms(self.performance_mode, self.on_battery,
                                                time.monotonic() - self.start_time))
        if self.password_lock and not self.lock_timer.isActive():
            self.lock_timer.start()
        self.preview_mouse_origin = QCursor.pos()
        super().showEvent(event)

    def hideEvent(self, event) -> None:
        """Pause animated painting while retaining the independent lock guard."""
        self.timer.stop()
        super().hideEvent(event)

    def bobos_status(self, elapsed_seconds: float) -> BobOSStatus:
        """Keep BobOS out of disabled states and yield before the real KDE lock."""
        enabled = bobos_may_run(
            phone_enabled=self.phone_enabled,
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
        protection = self.burn_in_protection
        scene_offset = burn_in_scene_shift(protection, t)
        scene_scale = burn_in_scene_scale(w, h) if protection != 'off' else 1.0
        if protection != 'off':
            p.save()
            p.translate(w * .5 + scene_offset[0], h * .5 + scene_offset[1])
            p.scale(scene_scale, scene_scale)
            p.translate(-w * .5, -h * .5)
        self.draw_scenery(p, w, h, t)
        if self.show_clock:
            self.clock(p, w, h, protection, t, scene_offset, scene_scale)
        bobos_status = self.bobos_status(t)
        phase = bobos_status.phase
        if phase not in PHONE_UI_PHASES:
            self.bob(p, w, h, t, bobos_status)
            self.caption(p, w, h, t, phase)
        if phase in PHONE_UI_PHASES:
            self.draw_phone_os(p, w, h, bobos_status, t)
        elif phase in (BobOSPhase.ZOOM_IN, BobOSPhase.ZOOM_OUT):
            self.draw_phone_zoom(p, w, h, bobos_status, t)
        if self.show_timer:
            self.countdown(p, w, h, t)
        if self.quick_preview:
            self.preview_hint(p, w, h, t)
        if protection != 'off':
            p.restore()
        dim_alpha = burn_in_dim_alpha(protection, t)
        if dim_alpha:
            p.fillRect(QRectF(0, 0, w, h), QColor(0, 0, 0, dim_alpha))
        p.end()

    def request_kde_lock(self):
        if self.is_preview or self.lock_attempted:
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
        if self.is_preview:
            if event.globalPosition().toPoint() != self.preview_mouse_origin:
                QApplication.quit()
            return
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
