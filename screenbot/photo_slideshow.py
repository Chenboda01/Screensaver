"""Animated presentation state for the local-only ``My photos`` theme."""
from __future__ import annotations

import math
from pathlib import Path
import time
from typing import Callable

from PyQt6.QtCore import Qt, QSize, QRectF
from PyQt6.QtGui import QColor, QFont, QImage, QPainter, QPixmap
from PyQt6.QtWidgets import QGraphicsBlurEffect, QGraphicsPixmapItem, QGraphicsScene

from screenbot.photos import EMPTY_LIBRARY_MESSAGE, PhotoLibrary, default_photo_folder


CROSSFADE_SECONDS = 2.0
ZOOM_START = 1.015
ZOOM_END = 1.10


class PhotoSlideshowRenderer:
    """Sequence local images with bounded prefetch, cross-fades, and Ken Burns motion."""

    def __init__(
        self,
        owner,
        *,
        folder: str | Path,
        include_subfolders: bool,
        interval_seconds: int,
        order: str,
        fit: str,
        enabled: bool,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.owner = owner
        self.clock = clock
        self.interval_seconds = max(5, min(120, int(interval_seconds)))
        self.fit = fit if fit in ('fill', 'fit-blur') else 'fill'
        self.folder = Path(folder).expanduser()
        self.paths: list[Path] = []
        self.message = 'Loading photos…'
        self._current_path: Path | None = None
        self._next_path: Path | None = None
        self._current_image: QImage | None = None
        self._next_image: QImage | None = None
        self._current_started_at: float | None = None
        self._next_ready_at: float | None = None
        self._current_index = -1
        self._requested: set[str] = set()
        self._unreadable: set[str] = set()
        self._decode_size = QSize(1, 1)
        self._closed = False
        self._blurred_backdrops: dict[tuple[int, int, int], QImage] = {}

        self.library = PhotoLibrary(
            self.folder,
            include_subfolders=include_subfolders,
            order=order,
            enabled=enabled,
            parent=owner,
        )
        self.library.scan_finished.connect(self._scan_finished)
        self.library.scan_failed.connect(self._scan_failed)
        self.library.photo_ready.connect(self._photo_ready)
        self.library.photo_failed.connect(self._photo_failed)
        if enabled:
            self.library.start_scan()

    @classmethod
    def from_settings(cls, owner, settings, theme: str) -> PhotoSlideshowRenderer | None:
        """Build the photo reader only after the user explicitly selects it."""
        if theme != 'photos':
            return None
        folder = settings.get('Screensaver', 'photo_folder', fallback=str(default_photo_folder())).strip()
        try:
            interval = settings.getint('Screensaver', 'photo_interval_seconds', fallback=15)
        except ValueError:
            interval = 15
        order = settings.get('Screensaver', 'photo_order', fallback='name').strip().lower()
        fit = settings.get('Screensaver', 'photo_fit', fallback='fill').strip().lower()
        return cls(
            owner,
            folder=folder or default_photo_folder(),
            include_subfolders=settings.getboolean('Screensaver', 'photo_include_subfolders', fallback=False),
            interval_seconds=interval,
            order=order,
            fit=fit,
            enabled=True,
        )

    def _scan_finished(self, paths: object) -> None:
        self.paths = list(paths)
        if not self.paths:
            self.message = EMPTY_LIBRARY_MESSAGE
            self.owner.update()
            return
        self.message = 'Loading photos…'
        self._current_index = 0
        self._current_path = self.paths[0]

    def _scan_failed(self, _error: str) -> None:
        self.paths = []
        self.message = EMPTY_LIBRARY_MESSAGE
        self.owner.update()

    def _photo_failed(self, path: str, error: str) -> None:
        # A damaged or unsupported file is skipped; one bad item must not stop
        # the slideshow or expose its filesystem details on the screen.
        self._requested.discard(path)
        self._unreadable.add(path)
        if self._current_path is not None and str(self._current_path) == path:
            self._advance_unreadable()
        elif self._next_path is not None and str(self._next_path) == path:
            self._next_path = None
            self._next_image = None
            self._next_ready_at = None
            self._request_next()
        self.owner.update()

    def _advance_unreadable(self) -> None:
        if not self.paths:
            return
        next_index = self._next_readable_index(self._current_index)
        if next_index is None:
            self._current_path = None
            self._current_image = None
            self._next_path = None
            self._next_image = None
            self._current_started_at = None
            self.message = 'No readable photos were found.'
            return
        self._current_index = next_index
        self._current_path = self.paths[self._current_index]
        self._current_image = None
        self._current_started_at = None
        self._next_path = None
        self._next_image = None
        self._next_ready_at = None
        self._request(self._current_path)

    def _next_readable_index(self, after: int) -> int | None:
        for step in range(1, len(self.paths) + 1):
            index = (after + step) % len(self.paths)
            if str(self.paths[index]) not in self._unreadable:
                return index
        return None

    def _request(self, path: Path | None) -> None:
        if path is None or self._closed:
            return
        key = str(path)
        if key in self._requested:
            return
        self._requested.add(key)
        if not self.library.request_photo(path, self._decode_size):
            self._requested.discard(key)

    def _photo_ready(self, path: str, image: object) -> None:
        self._requested.discard(path)
        if self._closed or not isinstance(image, QImage):
            return
        if self._current_path is not None and path == str(self._current_path):
            self._current_image = image
            if self._current_started_at is None:
                self._current_started_at = self.clock()
            self.message = ''
            self._request_next()
        elif self._next_path is not None and path == str(self._next_path):
            self._next_image = image
            if self._next_ready_at is None:
                self._next_ready_at = self.clock()
        self.owner.update()

    def _request_next(self) -> None:
        if len(self.paths) < 2 or self._current_index < 0:
            return
        index = self._next_readable_index(self._current_index)
        if index is None or index == self._current_index:
            return
        self._next_path = self.paths[index]
        self._next_image = None
        self._next_ready_at = None
        self._request(self._next_path)

    def _promote_next(self, fade_started: float) -> None:
        if self._next_image is None or self._next_path is None:
            return
        self._current_index = self.paths.index(self._next_path)
        self._current_path = self._next_path
        self._current_image = self._next_image
        self._current_started_at = fade_started + CROSSFADE_SECONDS
        self._next_path = None
        self._next_image = None
        self._next_ready_at = None
        self._request_next()

    def draw(self, painter: QPainter, width: int, height: int, elapsed: float) -> None:
        """Draw an animated photo or a scenic, friendly fallback behind overlays."""
        self._decode_size = QSize(max(1, round(width * 1.12)), max(1, round(height * 1.12)))
        if self._current_image is None:
            if self.paths and self._current_path is not None:
                self._request(self._current_path)
                self._draw_fallback(painter, width, height, elapsed, 'Loading photos…')
            else:
                self._draw_fallback(painter, width, height, elapsed, self.message or EMPTY_LIBRARY_MESSAGE)
            return

        now = self.clock()
        started = self._current_started_at if self._current_started_at is not None else now
        nominal_fade_at = started + self.interval_seconds - CROSSFADE_SECONDS
        fade_at = max(nominal_fade_at, self._next_ready_at or nominal_fade_at)
        if self._next_image is not None and now >= fade_at:
            amount = min(1.0, max(0.0, (now - fade_at) / CROSSFADE_SECONDS))
            current_phase = min(1.0, max(0.0, (now - started) / self.interval_seconds))
            self._draw_photo(painter, self._current_image, self._current_path, width, height, current_phase, 1.0)
            self._draw_photo(painter, self._next_image, self._next_path, width, height, 0.0, amount)
            if amount >= 1.0:
                self._promote_next(fade_at)
            return

        phase = min(1.0, max(0.0, (now - started) / self.interval_seconds))
        self._draw_photo(painter, self._current_image, self._current_path, width, height, phase, 1.0)

    def _draw_photo(self, painter: QPainter, image: QImage, path: Path | None, width: int, height: int,
                    phase: float, opacity: float) -> None:
        painter.save()
        painter.setClipRect(QRectF(0, 0, width, height))
        painter.setOpacity(opacity)
        if self.fit == 'fit-blur':
            backdrop = self._blurred_backdrop(image, width, height)
            painter.drawImage(QRectF(0, 0, width, height), backdrop)
            painter.fillRect(QRectF(0, 0, width, height), QColor(0, 0, 0, 42))
            # Keep the complete foreground photo visible for the full interval.
            scale = min(width / max(1, image.width()), height / max(1, image.height()))
            dest_w, dest_h = image.width() * scale, image.height() * scale
            x = (width - dest_w) / 2
            y = (height - dest_h) / 2
            painter.drawImage(QRectF(x, y, dest_w, dest_h), image)
        else:
            zoom = ZOOM_START + (ZOOM_END - ZOOM_START) * phase
            travel = (zoom - 1.0) * .38
            seed = sum(str(path or '').encode('utf-8')) % 97
            pan_x = math.sin(phase * math.pi + seed) * travel
            pan_y = math.cos(phase * math.pi + seed * .7) * travel
            scale = max(width / max(1, image.width()), height / max(1, image.height())) * zoom
            dest_w, dest_h = image.width() * scale, image.height() * scale
            x = (width - dest_w) / 2 + pan_x * max(0.0, dest_w - width)
            y = (height - dest_h) / 2 + pan_y * max(0.0, dest_h - height)
            painter.drawImage(QRectF(x, y, dest_w, dest_h), image)
        painter.restore()

    def _blurred_backdrop(self, image: QImage, width: int, height: int) -> QImage:
        """Render a smooth, real blur, retaining at most two transition frames."""
        key = (int(image.cacheKey()), width, height)
        cached = self._blurred_backdrops.get(key)
        if cached is not None:
            return cached
        source = image.scaled(QSize(width, height), Qt.AspectRatioMode.IgnoreAspectRatio,
                              Qt.TransformationMode.SmoothTransformation)
        pixmap_item = QGraphicsPixmapItem()
        pixmap_item.setPixmap(QPixmap.fromImage(source))
        blur = QGraphicsBlurEffect()
        blur.setBlurRadius(max(18.0, min(width, height) * .055))
        blur.setBlurHints(QGraphicsBlurEffect.BlurHint.QualityHint)
        pixmap_item.setGraphicsEffect(blur)
        scene = QGraphicsScene()
        scene.setSceneRect(QRectF(0, 0, width, height))
        scene.addItem(pixmap_item)
        output = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
        output.fill(Qt.GlobalColor.black)
        target = QPainter(output)
        scene.render(target, QRectF(0, 0, width, height), QRectF(0, 0, width, height),
                     Qt.AspectRatioMode.IgnoreAspectRatio)
        target.end()
        self._blurred_backdrops[key] = output
        while len(self._blurred_backdrops) > 2:
            self._blurred_backdrops.pop(next(iter(self._blurred_backdrops)))
        return output

    def _draw_fallback(self, painter: QPainter, width: int, height: int,
                       elapsed: float, message: str) -> None:
        # Keep the regular landscape/Bob/clock layers alive when the library is
        # empty or unavailable, while making the reason visible to the user.
        self.owner._draw_photo_fallback_landscape(painter, width, height, elapsed)
        painter.save()
        box_height = 72
        box = QRectF(width * .12, max(18, height * .05), width * .76, box_height)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(4, 14, 27, 205))
        painter.drawRoundedRect(box, 18, 18)
        painter.setPen(QColor('#f1f8ff'))
        painter.setFont(QFont('Sans Serif', max(13, min(24, width // 60)), QFont.Weight.DemiBold))
        painter.drawText(box.adjusted(16, 8, -16, -8),
                         Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                         message or EMPTY_LIBRARY_MESSAGE)
        painter.restore()

    def close(self) -> None:
        self._closed = True
        self.library.close()
