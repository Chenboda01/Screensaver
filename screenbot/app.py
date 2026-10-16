import configparser
from datetime import datetime
import math
import random
import subprocess
import time
from pathlib import Path

from PyQt6.QtCore import QRectF, Qt, QTimer
from PyQt6.QtGui import QColor, QCursor, QFont, QPainter, QPen, QShowEvent
from PyQt6.QtWidgets import QApplication, QWidget
from live_sky_network import LiveWeather
from live_sky_render import SpaceSky
from bobos import BobOSPhase, BobOSStatus, BobOSTimeline
from screenbot.appearance import BobAppearance
from screenbot.bob import BobRenderer
from screenbot.bobos_status import BobOSStatusMixin
from screenbot.agent_status import AgentBadgePhase, AgentStatusSnapshot, AgentStatusWorker, HIDDEN_SNAPSHOT
from screenbot.burnin import burn_in_dim_alpha, burn_in_scene_scale, burn_in_scene_shift, normalize_burn_in_mode
from screenbot.ambient.mixin import AmbientSoundMixin
from screenbot.clock import ClockRenderer
from screenbot.mpris import HIDDEN as NO_MEDIA
from screenbot.media_overlay import MediaOverlayMixin
from screenbot.fact_overlay import FactOverlayMixin, FactPreferences
from screenbot.effects import WeatherEffects
from screenbot.phone.apps import PhoneAppsRenderer
from screenbot.phone.camera_pet import CameraState
from screenbot.phone.frame import PhoneFrameRenderer
from screenbot.photo_slideshow import PhotoSlideshowRenderer
from screenbot.runtime import battery_powered, frame_interval_ms
from screenbot.scene import SceneRenderer
from screenbot.settings import CLOCK_POSITIONS, PHONE_UI_PHASES, read_settings, selected_theme
from screenbot.seasonal_renderer import SeasonalSession
from screenbot.themes.city import CityTheme
from screenbot.themes.forest import ForestTheme
from screenbot.themes.mountains import MountainsTheme
from screenbot.themes.snow import SnowTheme
from screenbot.themes.space import SpaceTheme
from screenbot.weather_accessories import WeatherPreview
from screenbot.weather_accessory_renderer import WeatherAccessoryAnimator, WeatherAccessoryRenderer

class Saver(QWidget, SceneRenderer, SpaceTheme, MountainsTheme, SnowTheme, ForestTheme, CityTheme, WeatherEffects, WeatherAccessoryRenderer, BobRenderer, ClockRenderer, PhoneFrameRenderer, PhoneAppsRenderer, MediaOverlayMixin, AmbientSoundMixin, BobOSStatusMixin, FactOverlayMixin):
    def __init__(self, *, preview: bool = False, config_path: Path | None = None,
                 preview_bobos: bool = False, preview_wifi_animation: bool | None = None,
                 preview_weather: WeatherPreview | None = None,
                 forced_preview_datetime: datetime | None = None):
        super().__init__()
        self.setWindowTitle('ScreenBot Screensaver')
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.BlankCursor)
        self.quick_preview, self.is_preview = preview, preview or preview_bobos
        settings = read_settings(config_path)
        self.seasonal_session = SeasonalSession.from_settings(settings, is_preview=self.is_preview, forced_preview_datetime=forced_preview_datetime)
        self.init_fact_overlay(FactPreferences.from_settings(settings))
        self.bob_appearance = BobAppearance.from_settings(settings)
        self.bob_weather_enabled = settings.getboolean('Screensaver', 'bob_weather_enabled', fallback=True)
        self.preview_weather_override = preview_weather
        self.weather_accessory_animator = WeatherAccessoryAnimator()
        self.theme = selected_theme(settings)
        self.random_theme = settings.get('Screensaver', 'theme', fallback='random') == 'random'
        self.photo_slideshow = PhotoSlideshowRenderer.from_settings(self, settings, self.theme)
        self.show_clock = settings.getboolean('Screensaver', 'show_clock', fallback=True)
        self.now_playing_enabled = settings.getboolean('Screensaver', 'now_playing_enabled', fallback=False)
        self.init_ambient_sound(settings)
        self.now_playing = NO_MEDIA
        self.media_worker = None
        self._mpris_playing = False
        self._closing = False
        self.init_media_worker()
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
        self.bobos_camera = CameraState()
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
        self.agent_status_enabled = settings.getboolean('Screensaver', 'agent_status_enabled', fallback=True)
        self.agent_status = HIDDEN_SNAPSHOT
        self.agent_status_worker = None
        self._agent_celebration_pending = False
        self._agent_celebration_started_at: float | None = None
        if self.agent_status_enabled and not self.is_preview:
            self.agent_status_worker = AgentStatusWorker(self)
            self.agent_status_worker.status_changed.connect(self.set_agent_status)
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
        self.update_ambient_sound()
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
        """Pause hidden facts while preserving BobOS timing and KDE lock priority."""
        status = BobOSStatusMixin.bobos_status(self, elapsed_seconds)
        return self.pause_facts_for_bobos_status(status, elapsed_seconds)

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
        self.draw_now_playing(p)
        bobos_status = self.bobos_status(t)
        phase = bobos_status.phase
        if phase not in PHONE_UI_PHASES:
            celebration_elapsed = self._agent_celebration_elapsed(phase)
            self.bob(p, w, h, t, bobos_status, celebration_elapsed=celebration_elapsed)
            self.caption(p, w, h, t, phase)
            self.draw_fact_overlay(p, w, h, t, phase)
        if phase in PHONE_UI_PHASES:
            self.draw_phone_os(p, w, h, bobos_status, t)
        elif phase in (BobOSPhase.ZOOM_IN, BobOSPhase.ZOOM_OUT):
            self.draw_phone_zoom(p, w, h, bobos_status, t)
        self.draw_agent_status(p, w, h)
        if self.show_timer:
            self.countdown(p, w, h, t)
        if self.quick_preview:
            self.preview_hint(p, w, h, t)
        if self.photo_slideshow is not None:
            self.photo_slideshow.draw_notice(p, w, h, t)
        if protection != 'off':
            p.restore()
        dim_alpha = burn_in_dim_alpha(protection, t)
        if dim_alpha:
            p.fillRect(QRectF(0, 0, w, h), QColor(0, 0, 0, dim_alpha))
        p.end()

    def set_agent_status(self, snapshot: AgentStatusSnapshot) -> None:
        """Accept only the status worker's privacy-safe state and clock values."""
        previous_phase = self.agent_status.phase
        self.agent_status = snapshot
        if snapshot.phase is AgentBadgePhase.FINISHED and previous_phase is not AgentBadgePhase.FINISHED:
            self._agent_celebration_pending = True
        elif snapshot.phase is AgentBadgePhase.WORKING:
            self._agent_celebration_pending = False
            self._agent_celebration_started_at = None
        elif snapshot.phase is AgentBadgePhase.HIDDEN:
            self._agent_celebration_pending = False
            self._agent_celebration_started_at = None
        self.update()

    def start_agent_status_worker(self) -> None:
        """Start optional polling only for the real primary screensaver session."""
        if (self.agent_status_worker is not None
                and not self.is_preview
                and not self.agent_status_worker.isRunning()):
            self.agent_status_worker.start()

    def stop_agent_status_worker(self) -> None:
        """Join the worker after QApplication exits, when no screen is blocked."""
        if self.agent_status_worker is not None and self.agent_status_worker.isRunning():
            self.agent_status_worker.stop()

    def _agent_celebration_elapsed(self, phase: BobOSPhase) -> float | None:
        """Start one brief celebration when Bob is visible after a confirmed finish."""
        if phase in PHONE_UI_PHASES:
            return None
        if self._agent_celebration_pending:
            self._agent_celebration_pending = False
            self._agent_celebration_started_at = time.monotonic()
        if self._agent_celebration_started_at is None:
            return None
        elapsed = time.monotonic() - self._agent_celebration_started_at
        if elapsed >= 4.5:
            self._agent_celebration_started_at = None
            return None
        return elapsed

    def draw_agent_status(self, painter: QPainter, width: int, height: int) -> None:
        """Paint only the safe working/finished label on the primary Saver window."""
        if not self.agent_status_enabled or self.agent_status.phase is AgentBadgePhase.HIDDEN:
            return
        compact = width < 280
        if self.agent_status.phase is AgentBadgePhase.WORKING:
            started_at = self.agent_status.started_at
            elapsed = max(0, int(time.monotonic() - started_at)) if started_at is not None else 0
            if compact:
                duration = f'{elapsed // 60}m' if elapsed >= 60 else f'{elapsed}s'
            else:
                duration = f'{elapsed // 60} min' if elapsed >= 60 else f'{elapsed} sec'
            text = f'Working · {duration}' if compact else f'AI agent working · {duration}'
            accent = QColor('#63d9ff')
        else:
            finished_at = self.agent_status.finished_at
            if finished_at is None:
                return
            local_time = datetime.fromtimestamp(finished_at).strftime('%H:%M')
            text = f'Finished · {local_time}' if compact else f'AI agent finished · {local_time}'
            accent = QColor('#77e4a0')
        badge_width = min(370, max(180, width - 24))
        badge_height = 44
        x = width - badge_width - 18
        y = height - badge_height - 18
        painter.save()
        painter.setPen(QPen(QColor(accent.red(), accent.green(), accent.blue(), 190), 1.5))
        painter.setBrush(QColor(8, 19, 35, 226))
        painter.drawRoundedRect(QRectF(x, y, badge_width, badge_height), 15, 15)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(accent)
        painter.drawRoundedRect(QRectF(x + 12, y + 12, 20, 20), 6, 6)
        painter.setPen(QColor('#061421'))
        painter.setFont(QFont('Sans Serif', 9, QFont.Weight.Bold))
        painter.drawText(QRectF(x + 12, y + 12, 20, 20), Qt.AlignmentFlag.AlignCenter, 'AI')
        painter.setPen(QColor('#eff8ff'))
        painter.setFont(QFont('Sans Serif', max(10, min(14, width // 72)), QFont.Weight.DemiBold))
        painter.drawText(QRectF(x + 42, y + 4, badge_width - 52, badge_height - 8),
                         Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)
        painter.restore()

    def closeEvent(self, event) -> None:
        """Request polling shutdown without delaying the screensaver close animation."""
        if self.photo_slideshow is not None:
            self.photo_slideshow.close()
        self.close_media_overlay()
        self.stop_ambient_sound()
        if self.agent_status_worker is not None and self.agent_status_worker.isRunning():
            self.agent_status_worker.request_stop()
        super().closeEvent(event)

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

    def mousePressEvent(self, event): QApplication.quit()

    def keyPressEvent(self, event): QApplication.quit()
