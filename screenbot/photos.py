"""Private, bounded photo discovery and decoding for the optional slideshow.

Nothing in this module touches the filesystem until ``PhotoLibrary`` is
explicitly enabled and ``start_scan`` is called.  Discovery and decoding run
off the GUI thread; decoded images are scaled before delivery and retained in
a small LRU cache.
"""
from __future__ import annotations

from collections import OrderedDict
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
import os
from pathlib import Path
import random
import threading
from typing import Final

from PyQt6.QtCore import Qt, QObject, QSize, pyqtSignal
from PyQt6.QtGui import QImage, QImageReader


PHOTO_EXTENSIONS: Final[frozenset[str]] = frozenset({
    '.avif', '.bmp', '.gif', '.heic', '.heif', '.jpeg', '.jpg', '.png',
    '.tif', '.tiff', '.webp',
})
PHOTO_ORDERS: Final[frozenset[str]] = frozenset({'name', 'date', 'random'})
MAX_DECODED_IMAGES: Final[int] = 3
MAX_PENDING_DECODES: Final[int] = 2
MAX_IMAGE_WIDTH: Final[int] = 3840
MAX_IMAGE_HEIGHT: Final[int] = 2160
MAX_IMAGE_PIXELS: Final[int] = 8_294_400
EMPTY_LIBRARY_MESSAGE: Final[str] = 'No photos found in this folder.'


def default_photo_folder() -> Path:
    """Return the conventional local folder without checking or scanning it."""
    return Path.home() / 'Pictures'


def _is_hidden_relative(path: Path) -> bool:
    return any(part.startswith('.') for part in path.parts if part not in ('.', '..'))


def discover_photos(
    folder: str | os.PathLike[str] | None = None,
    *,
    include_subfolders: bool = False,
    order: str = 'name',
    random_seed: int | None = None,
) -> list[Path]:
    """List supported local images, skipping hidden entries and symlinks.

    ``date`` means newest filesystem modification time first.  Random order is
    stable when a seed is supplied, which makes previews and tests repeatable.
    The returned paths are metadata only; no image contents are opened here.
    """
    if order not in PHOTO_ORDERS:
        raise ValueError(f'Unsupported photo order: {order!r}')
    root = Path(folder).expanduser() if folder is not None else default_photo_folder()
    try:
        root = root.resolve(strict=True)
        if not root.is_dir():
            return []
    except (OSError, RuntimeError):
        return []

    found: list[Path] = []
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    # Do not follow symlinks, including symlinked directories.
                    if entry.is_symlink() or entry.name.startswith('.'):
                        continue
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            if include_subfolders:
                                stack.append(Path(entry.path))
                        elif (entry.is_file(follow_symlinks=False)
                              and Path(entry.name).suffix.casefold() in PHOTO_EXTENSIONS):
                            found.append(Path(entry.path))
                    except OSError:
                        # Files can disappear or become unreadable during a scan.
                        continue
        except OSError:
            continue

    if order == 'name':
        found.sort(key=lambda item: (item.name.casefold(), str(item).casefold()))
    elif order == 'date':
        def modified(path: Path) -> tuple[float, str]:
            try:
                return (-path.stat(follow_symlinks=False).st_mtime, str(path).casefold())
            except OSError:
                return (0.0, str(path).casefold())
        found.sort(key=modified)
    else:
        random.Random(random_seed).shuffle(found)
    return found


def _bounded_size(target: QSize) -> QSize:
    width = max(1, min(target.width(), MAX_IMAGE_WIDTH))
    height = max(1, min(target.height(), MAX_IMAGE_HEIGHT))
    ratio = min(1.0, MAX_IMAGE_WIDTH / width, MAX_IMAGE_HEIGHT / height,
                (MAX_IMAGE_PIXELS / (width * height)) ** 0.5)
    return QSize(max(1, round(width * ratio)), max(1, round(height * ratio)))


def decode_photo(path: str | os.PathLike[str], target_size: QSize) -> QImage:
    """Decode a photo to a bounded screen-sized QImage with EXIF transforms."""
    reader = QImageReader(str(path))
    reader.setDecideFormatFromContent(True)
    reader.setAutoTransform(True)
    source = reader.size()
    target = _bounded_size(target_size)
    if source.isValid() and source.width() > 0 and source.height() > 0:
        scale = min(1.0, target.width() / source.width(), target.height() / source.height())
        reader.setScaledSize(QSize(max(1, round(source.width() * scale)),
                                   max(1, round(source.height() * scale))))
    image = reader.read()
    if image.isNull():
        raise ValueError(reader.errorString() or 'The image could not be decoded.')
    if image.width() > target.width() or image.height() > target.height():
        image = image.scaled(target, Qt.AspectRatioMode.KeepAspectRatio,
                             Qt.TransformationMode.SmoothTransformation)
    return image


@dataclass(frozen=True)
class _CacheKey:
    path: str
    width: int
    height: int


class PhotoLibrary(QObject):
    """Asynchronous catalog and image cache for an explicitly enabled feature."""

    scan_finished = pyqtSignal(object)
    scan_failed = pyqtSignal(str)
    photo_ready = pyqtSignal(str, object)
    photo_failed = pyqtSignal(str, str)

    def __init__(
        self,
        folder: str | os.PathLike[str] | None = None,
        *,
        include_subfolders: bool = False,
        order: str = 'name',
        enabled: bool = False,
        random_seed: int | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        if order not in PHOTO_ORDERS:
            raise ValueError(f'Unsupported photo order: {order!r}')
        self.folder = Path(folder).expanduser() if folder is not None else default_photo_folder()
        self.include_subfolders = include_subfolders
        self.order = order
        self.enabled = enabled
        self.random_seed = random_seed
        self.photos: list[Path] = []
        self.message = EMPTY_LIBRARY_MESSAGE
        self._executor: ThreadPoolExecutor | None = None
        self._lock = threading.RLock()
        self._scan_future: Future[list[Path]] | None = None
        self._pending: dict[_CacheKey, Future[QImage]] = {}
        self._cache: OrderedDict[_CacheKey, QImage] = OrderedDict()
        self._closed = False

    def _pool(self) -> ThreadPoolExecutor:
        if self._executor is None:
            self._executor = ThreadPoolExecutor(max_workers=MAX_PENDING_DECODES + 1,
                                                thread_name_prefix='screenbot-photos')
        return self._executor

    def start_scan(self) -> bool:
        """Start metadata-only discovery; disabled libraries do no filesystem I/O."""
        if not self.enabled or self._closed:
            return False
        with self._lock:
            if self._scan_future is not None and not self._scan_future.done():
                return False
            future = self._pool().submit(
                discover_photos, self.folder,
                include_subfolders=self.include_subfolders,
                order=self.order,
                random_seed=self.random_seed,
            )
            self._scan_future = future
        future.add_done_callback(self._scan_done)
        return True

    def _scan_done(self, future: Future[list[Path]]) -> None:
        try:
            photos = future.result()
        except Exception as exc:  # defensive boundary for filesystem and worker errors
            self.scan_failed.emit(str(exc))
            return
        with self._lock:
            if self._closed:
                return
            self.photos = photos
            self.message = '' if photos else EMPTY_LIBRARY_MESSAGE
        self.scan_finished.emit(photos)

    def _allowed_path(self, path: str | os.PathLike[str]) -> Path | None:
        candidate = Path(path).expanduser()
        try:
            root = self.folder.resolve(strict=True)
            if candidate.is_symlink():
                return None
            resolved = candidate.resolve(strict=True)
            relative = resolved.relative_to(root)
            if _is_hidden_relative(relative) or not resolved.is_file():
                return None
            if not self.include_subfolders and len(relative.parts) != 1:
                return None
            if resolved.suffix.casefold() not in PHOTO_EXTENSIONS:
                return None
            return resolved
        except (OSError, RuntimeError, ValueError):
            return None

    def request_photo(self, path: str | os.PathLike[str], target_size: QSize) -> bool:
        """Queue one decode, refusing excess work and keeping at most 3 images."""
        if not self.enabled or self._closed:
            return False
        allowed = self._allowed_path(path)
        if allowed is None:
            self.photo_failed.emit(str(path), 'Photo is outside the selected folder or unavailable.')
            return False
        size = _bounded_size(target_size)
        key = _CacheKey(str(allowed), size.width(), size.height())
        with self._lock:
            cached = self._cache.get(key)
            if cached is not None:
                self._cache.move_to_end(key)
            elif key in self._pending:
                return True
            elif len(self._pending) >= MAX_PENDING_DECODES:
                return False
            else:
                future = self._pool().submit(decode_photo, allowed, size)
                self._pending[key] = future
        if cached is not None:
            self.photo_ready.emit(str(allowed), cached)
            return True
        future.add_done_callback(lambda finished, cache_key=key: self._decode_done(cache_key, finished))
        return True

    def _decode_done(self, key: _CacheKey, future: Future[QImage]) -> None:
        try:
            image = future.result()
        except Exception as exc:
            with self._lock:
                self._pending.pop(key, None)
                if self._closed:
                    return
            self.photo_failed.emit(key.path, str(exc))
            return
        with self._lock:
            self._pending.pop(key, None)
            if self._closed:
                return
            self._cache[key] = image
            self._cache.move_to_end(key)
            while len(self._cache) > MAX_DECODED_IMAGES:
                self._cache.popitem(last=False)
        self.photo_ready.emit(key.path, image)

    @property
    def cached_image_count(self) -> int:
        with self._lock:
            return len(self._cache)

    @property
    def pending_decode_count(self) -> int:
        with self._lock:
            return len(self._pending)

    def close(self) -> None:
        """Stop accepting work and let bounded in-flight tasks finish safely."""
        with self._lock:
            self._closed = True
            executor, self._executor = self._executor, None
            self._cache.clear()
            self.photos.clear()
        if executor is not None:
            executor.shutdown(wait=False, cancel_futures=True)
