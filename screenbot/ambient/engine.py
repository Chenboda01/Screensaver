"""Optional QtMultimedia playback for one screensaver-wide ambience stream."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys

from PyQt6.QtCore import QObject, QTimer, QUrl

from screenbot.ambient.policy import SceneSound, choose_loop, volume_scale


class AmbientSoundEngine(QObject):
    """Own one looping stream and its fade/scene policy for the saver lifetime."""

    def __init__(self, parent: QObject, *, enabled: bool, volume_percent: int,
                 live_sky_only: bool, quiet_hours: bool, asset_directory: Path) -> None:
        super().__init__(parent)
        self.enabled = enabled
        self.volume = max(0, min(100, volume_percent)) / 100
        self.live_sky_only = live_sky_only
        self.quiet_hours = quiet_hours
        self.asset_directory = asset_directory
        self.selected_loop: str | None = None
        self._playing_media = False
        self._closed = False
        self._was_muted = True
        self._failed_assets: dict[Path, tuple[int, int] | None] = {}
        self._scene: SceneSound | None = None
        self._gain = 1.0
        self._lightning_visible = False
        self._thunder_pending = False
        self._thunder_active = False
        self._current_asset: Path | None = None
        self._fade_step = 0
        self._player = None
        self._output = None
        if not enabled:
            return
        try:
            from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
        except ImportError:
            print('ScreenBot: QtMultimedia is unavailable; ambient audio is disabled.', file=sys.stderr)
            return
        self._output = QAudioOutput(self)
        self._player = QMediaPlayer(self)
        self._player.setAudioOutput(self._output)
        self._player.setLoops(QMediaPlayer.Loops.Infinite)
        self._player.errorOccurred.connect(self._on_error)
        self._player.mediaStatusChanged.connect(self._on_media_status)
        self._output.setVolume(0.0)
        self._fade = QTimer(self)
        self._fade.setInterval(100)
        self._fade.timeout.connect(self._advance_fade)
        self._quiet_timer = QTimer(self)
        self._quiet_timer.setInterval(30_000)
        self._quiet_timer.timeout.connect(self._apply_policy)
        self._quiet_timer.timeout.connect(self._refresh_failed_assets)
        self._quiet_timer.start()

    @property
    def available(self) -> bool:
        """Return whether QtMultimedia loaded successfully."""
        return self._player is not None

    def update_scene(self, scene: SceneSound, *, playing_media: bool) -> None:
        """Switch to the current scene loop, respecting MPRIS and quiet hours."""
        if self._closed or self._player is None:
            return
        self._playing_media = playing_media
        self._scene = scene
        if scene.weather.value != 'thunderstorm' and not scene.thunder_enabled:
            self._thunder_pending = False
            if hasattr(self, '_thunder_timer'):
                self._thunder_timer.stop()
        loop = choose_loop(scene) if self.enabled else None
        self._gain = volume_scale(scene)
        if loop != self.selected_loop:
            self.selected_loop = loop
            self._thunder_active = False
            self._thunder_pending = False
            self._player.stop()
            if loop is not None:
                source = self.asset_directory / f'{loop}.ogg'
                if source in self._failed_assets:
                    self.selected_loop = None
                    self._apply_policy()
                    return
                if not source.is_file():
                    self._cache_failure(source, missing=True)
                    print(f'ScreenBot: ambient asset is missing: {source}', file=sys.stderr)
                    self.selected_loop = None
                    return
                self._player.setSource(QUrl.fromLocalFile(str(source)))
                self._current_asset = source
                self._player.play()
                self._begin_fade()
        self._apply_policy()

    def close(self) -> None:
        """Stop audio synchronously before the saver window exits."""
        if self._closed:
            return
        self._closed = True
        if hasattr(self, '_quiet_timer'):
            self._quiet_timer.stop()
            self._fade.stop()
        if self._player is not None:
            if hasattr(self, '_thunder_timer'):
                self._thunder_timer.stop()
            self._player.stop()
            self._player.setSource(QUrl())
        if self._output is not None:
            self._output.setVolume(0.0)

    def _begin_fade(self) -> None:
        self._fade_step = 0
        self._fade.start()

    def _advance_fade(self) -> None:
        if self._output is None:
            self._fade.stop()
            return
        self._fade_step = min(30, self._fade_step + 1)
        self._apply_policy(fade=self._fade_step / 30)
        if self._fade_step == 30:
            self._fade.stop()

    def _apply_policy(self, *, fade: float | None = None) -> None:
        if self._player is None or self._output is None:
            return
        quiet = self.quiet_hours and _is_quiet_now(datetime.now())
        muted = self._playing_media or quiet or not self.enabled or self.selected_loop is None
        if self._was_muted and not muted:
            self._begin_fade()
        self._was_muted = muted
        level = self._fade_step / 30 if fade is None and self._fade.isActive() else (1.0 if fade is None else fade)
        output_volume = 0.0 if muted else self.volume * self._gain * max(0.0, min(1.0, level))
        if abs(self._output.volume() - output_volume) > .005:
            self._output.setVolume(output_volume)
        if muted:
            if self._player.playbackState() != self._player.PlaybackState.StoppedState:
                self._player.stop()
        elif self._player.playbackState() != self._player.PlaybackState.PlayingState:
            self._player.play()

    def _on_error(self, *_details: object) -> None:
        """Cache a terminal playback failure so paint updates cannot retry or log-flood."""
        if self._player is None or self._closed:
            return
        source = self._current_asset
        if source is not None and source not in self._failed_assets:
            self._cache_failure(source, missing=False)
            print(f'ScreenBot: ambient playback failed for {source.name}; disabling this asset.', file=sys.stderr)
        self.selected_loop = None
        self._fade.stop()
        self._player.stop()
        if self._output is not None:
            self._output.setVolume(0.0)

    def set_lightning_visible(self, visible: bool) -> None:
        """Schedule one thunderclap only on the shared visual event's rising edge."""
        if visible and not self._lightning_visible and self.selected_loop == 'rain' and not self._closed:
            self._thunder_pending = True
            if not hasattr(self, '_thunder_timer'):
                self._thunder_timer = QTimer(self)
                self._thunder_timer.setSingleShot(True)
                self._thunder_timer.setInterval(1100)
                self._thunder_timer.timeout.connect(self._play_thunder)
            self._thunder_timer.start()
        self._lightning_visible = visible

    def _play_thunder(self) -> None:
        """Play the short rumble after a visible flash using the one existing stream."""
        if (self._player is None or self._closed or not self._thunder_pending or self._playing_media or self._was_muted
                or self.selected_loop != 'rain'):
            self._thunder_pending = False
            return
        source = self.asset_directory / 'thunder.ogg'
        if source in self._failed_assets or not source.is_file():
            if source not in self._failed_assets:
                self._cache_failure(source, missing=True)
                print(f'ScreenBot: ambient asset is missing: {source}', file=sys.stderr)
            self._thunder_pending = False
            return
        self._thunder_pending = False
        self._thunder_active = True
        self._current_asset = source
        from PyQt6.QtMultimedia import QMediaPlayer
        self._player.setLoops(QMediaPlayer.Loops.Once)
        self._player.setSource(QUrl.fromLocalFile(str(source)))
        self._player.play()

    def _cache_failure(self, source: Path, *, missing: bool) -> None:
        """Remember the asset's current fingerprint for timer-based, change-only retry."""
        if missing:
            self._failed_assets[source] = None
            return
        try:
            stat = source.stat()
            self._failed_assets[source] = (stat.st_mtime_ns, stat.st_size)
        except OSError:
            self._failed_assets[source] = None

    def _refresh_failed_assets(self) -> None:
        """Retry only after a failed asset's presence, mtime, or size changes."""
        for source, previous in tuple(self._failed_assets.items()):
            try:
                stat = source.stat()
                current = (stat.st_mtime_ns, stat.st_size)
            except OSError:
                current = None
            if current != previous:
                del self._failed_assets[source]

    def _on_media_status(self, status: object) -> None:
        """Restore the selected continuous loop after a thunderclap or silence on failure."""
        if self._player is None or not self._thunder_active:
            return
        try:
            from PyQt6.QtMultimedia import QMediaPlayer
            ended = status == QMediaPlayer.MediaStatus.EndOfMedia
        except ImportError:
            ended = False
        if not ended:
            return
        self._thunder_active = False
        if self.selected_loop is None or self._closed or self._playing_media:
            return
        base = self.asset_directory / f'{self.selected_loop}.ogg'
        self._current_asset = base
        self._player.setLoops(QMediaPlayer.Loops.Infinite)
        self._player.setSource(QUrl.fromLocalFile(str(base)))
        self._player.play()


def _is_quiet_now(now: datetime) -> bool:
    """Treat 22:00–08:00 local time as quiet hours, including midnight."""
    return now.hour >= 22 or now.hour < 8
