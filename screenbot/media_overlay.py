"""Painting and placement helpers for the optional MPRIS now-playing card."""

from __future__ import annotations

import time

from PyQt6.QtCore import QRectF, QSizeF
from PyQt6.QtGui import QPainter

from screenbot.burnin import burn_in_clock_drift, burn_in_scene_scale, burn_in_scene_shift
from screenbot.mpris import HIDDEN as NO_MEDIA, MprisWorker, NowPlaying
from screenbot.now_playing import card_opacity, card_rect, paint_card


class MediaOverlayMixin:
    """Keep the media card's geometry and paint path out of the main widget."""

    def set_now_playing(self, snapshot: NowPlaying) -> None:
        """Reject queued media after shutdown, or when privacy is not opted in."""
        if self._closing or self.is_preview:
            return
        if not self.now_playing_enabled:
            self._mpris_playing = snapshot.track is not None and snapshot.paused_at is None
            self.update_ambient_sound()
            return
        self.now_playing = snapshot
        self.update_ambient_sound()
        self.update()

    def set_mpris_playing(self, playing: bool) -> None:
        """Mute ambience from playback state without exposing track metadata."""
        if self._closing or self.is_preview:
            return
        self._mpris_playing = playing
        self.update_ambient_sound()

    def start_media_worker(self) -> None:
        """Only the primary real screensaver owns a media reader."""
        if self.media_worker is not None and not self.media_worker.isRunning() and not self._closing:
            self.media_worker.start()

    def init_media_worker(self) -> None:
        """Poll MPRIS only for the now-playing card or opted-in audio muting."""
        if (self.now_playing_enabled or self.ambient_sound_enabled) and not self.is_preview:
            self.media_worker = MprisWorker(
                self, enabled=True, playing_only=not self.now_playing_enabled,
                publish_playback=self.ambient_sound_enabled,
            )
            if self.now_playing_enabled:
                self.media_worker.changed.connect(self.set_now_playing)
            if self.ambient_sound_enabled:
                self.media_worker.playing_changed.connect(self.set_mpris_playing)

    def stop_media_worker(self) -> None:
        """Join after the application loop has exited, leaving the desktop responsive."""
        self._closing = True
        self.now_playing = NO_MEDIA
        if self.media_worker is not None:
            self.media_worker.stop()

    def close_media_overlay(self) -> None:
        """Reject queued media updates and request an immediate poller stop."""
        self._closing = True
        self.now_playing = NO_MEDIA
        if self.media_worker is not None:
            self.media_worker.request_stop()

    def media_card_rect(self) -> QRectF:
        """Place the card clear of the clock, Bob, captions, and exit hint."""
        anchor = None
        column = 'center'
        if self.show_clock:
            row, column = self.clock_position.split('-')
            x = {'left': .035, 'center': .29, 'right': .545}[column] * self.width()
            y = {'top': .08, 'center': .38, 'bottom': .65}[row] * self.height()
            conditions = self.live_sky_enabled and self.live_sky_conditions and self.theme != 'space'
            height = self.clock_font_size * (1.5 + .62 * (self.show_date + conditions))
            elapsed = time.monotonic() - self.start_time
            scene_offset = burn_in_scene_shift(self.burn_in_protection, elapsed)
            scene_scale = burn_in_scene_scale(self.width(), self.height()) if self.burn_in_protection != 'off' else 1.0
            drift_x, drift_y = burn_in_clock_drift(
                self.burn_in_protection, elapsed, self.width(), self.height(), self.clock_position,
                self.clock_font_size, self.show_date, conditions, scene_offset, scene_scale)
            anchor = QRectF(x + drift_x, y + drift_y, self.width() * .42, height)
        scale = min(self.width() / 1250, self.height() / 800, 1.35)
        sway = min(self.width() * .075, 85)
        bob_bounds = QRectF(self.width() * .5 - sway - 210 * scale,
                            self.height() * .56 - 9 - 200 * scale,
                            2 * sway + 420 * scale, 18 + 320 * scale)
        captions_top = min(self.height() * .79, self.height() - 55)
        captions = QRectF(0, captions_top, self.width(), self.height() - captions_top)
        return card_rect(QSizeF(self.size()), anchor, column, (bob_bounds, captions))

    def draw_now_playing(self, painter: QPainter) -> None:
        """Paint the cached snapshot, with no D-Bus work on the frame thread."""
        if not self.now_playing_enabled or self.is_preview or self._closing:
            return
        opacity = card_opacity(self.now_playing, time.monotonic(), self.reduce_motion)
        if opacity <= 0:
            return
        painter.save()
        painter.setOpacity(opacity)
        paint_card(painter, self.media_card_rect(), self.now_playing)
        painter.restore()
