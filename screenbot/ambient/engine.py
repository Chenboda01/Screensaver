"""Optional QtMultimedia playback for one screensaver-wide ambience stream."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys

from PyQt6.QtCore import QObject, QTimer, QUrl

from screenbot.ambient.policy import SceneSound, choose_loop


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
        self._output.setVolume(0.0)
        self._fade = QTimer(self)
        self._fade.setInterval(100)
        self._fade.timeout.connect(self._advance_fade)
        self._quiet_timer = QTimer(self)
        self._quiet_timer.setInterval(30_000)
        self._quiet_timer.timeout.connect(self._apply_policy)
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
        loop = choose_loop(scene) if self.enabled else None
        if loop != self.selected_loop:
            self.selected_loop = loop
            self._player.stop()
            if loop is not None:
                source = self.asset_directory / f'{loop}.ogg'
                if not source.is_file():
                    print(f'ScreenBot: ambient asset is missing: {source}', file=sys.stderr)
                    self.selected_loop = None
                    return
                self._player.setSource(QUrl.fromLocalFile(str(source)))
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
        output_volume = 0.0 if muted else self.volume * max(0.0, min(1.0, level))
        if abs(self._output.volume() - output_volume) > .005:
            self._output.setVolume(output_volume)
        if muted:
            if self._player.playbackState() != self._player.PlaybackState.StoppedState:
                self._player.stop()
        elif self._player.playbackState() != self._player.PlaybackState.PlayingState:
            self._player.play()


def _is_quiet_now(now: datetime) -> bool:
    """Treat 22:00–08:00 local time as quiet hours, including midnight."""
    return now.hour >= 22 or now.hour < 8
