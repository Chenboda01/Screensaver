"""Saver lifecycle adapter for the isolated ambient sound policy and player."""
from __future__ import annotations

from configparser import ConfigParser
from datetime import datetime
from pathlib import Path

from live_sky_network import LiveWeather
from screenbot.ambient.engine import AmbientSoundEngine
from screenbot.ambient.policy import SceneSound, parse_theme, parse_weather


class AmbientSoundMixin:
    """Bridge Saver's scene snapshot and lifecycle into optional audio playback."""

    theme: str
    live_weather: LiveWeather
    live_sky_enabled: bool
    rain_enabled: bool
    snow_enabled: bool
    thunderstorms_enabled: bool
    is_preview: bool
    _mpris_playing: bool
    ambient_sound: AmbientSoundEngine
    ambient_live_sky_only: bool
    ambient_sound_enabled: bool
    ambient_quiet_hours: bool

    def init_ambient_sound(self, settings: ConfigParser) -> None:
        """Create the single player after reading validated persisted settings."""
        self.ambient_sound_enabled = settings.getboolean('Screensaver', 'ambient_sound_enabled', fallback=False)
        try:
            volume = settings.getint('Screensaver', 'ambient_sound_volume', fallback=25)
        except ValueError:
            volume = 25
        self.ambient_live_sky_only = (
            settings.get('Screensaver', 'ambient_sound_mode', fallback='always').strip() == 'live-sky'
        )
        self.ambient_quiet_hours = settings.getboolean('Screensaver', 'ambient_quiet_hours', fallback=False)
        root = Path(__file__).resolve().parents[2]
        self.ambient_sound = AmbientSoundEngine(
            self, enabled=self.ambient_sound_enabled and not self.is_preview,
            volume_percent=volume, live_sky_only=self.ambient_live_sky_only,
            quiet_hours=self.ambient_quiet_hours, asset_directory=root / 'assets' / 'audio',
        )

    def update_ambient_sound(self) -> None:
        """Send current scene and MPRIS state to the audio policy once per frame."""
        if not self.ambient_sound.available:
            return
        now = datetime.now()
        weather = self.live_weather.weather
        scene = SceneSound(
            theme=parse_theme(self.theme), weather=parse_weather(weather.category),
            live_sky_enabled=self.live_sky_enabled, live_sky_fresh=self.live_weather.fresh,
            live_sky_only=self.ambient_live_sky_only,
            rain_enabled=self.rain_enabled, snow_enabled=self.snow_enabled,
            thunder_enabled=self.thunderstorms_enabled,
            elapsed_hours=now.hour + now.minute / 60,
            rain_intensity=self.live_weather.weather.intensity,
        )
        self.ambient_sound.update_scene(scene, playing_media=self._mpris_playing)

    def stop_ambient_sound(self) -> None:
        """Synchronously silence and detach the single audio stream."""
        self.ambient_sound.close()
