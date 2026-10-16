"""Opt-in, read-only now-playing snapshots for a future screensaver overlay."""
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from threading import Event, RLock
import time
from typing import Final, Protocol

from PyQt6.QtCore import QObject, QThread, pyqtSignal


class Playback(StrEnum):
    PLAYING = 'Playing'
    PAUSED = 'Paused'
    STOPPED = 'Stopped'


@dataclass(frozen=True, slots=True)
class Track:
    """The only media information permitted to leave the reader."""

    player: str
    title: str
    artist: str = ''
    album: str = ''


@dataclass(frozen=True, slots=True)
class PlayerSample:
    """An internal player observation; service is only used to track recency."""

    service: str
    playback: Playback
    track: Track


@dataclass(frozen=True, slots=True)
class NowPlaying:
    """A display snapshot; paused_at allows the view to fade before hiding."""

    track: Track | None = None
    paused_at: float | None = None


HIDDEN: Final = NowPlaying()
POLL_SECONDS: Final = 2.0
PAUSE_GRACE_SECONDS: Final = 3.0


class MetadataReader(Protocol):
    def read(self) -> tuple[PlayerSample, ...]:
        """Return bounded, sanitized samples; absence or failure returns empty."""
        ...


class NowPlayingTracker:
    """Mutable in-memory recency and pause tracking, with no persistence."""

    def __init__(self) -> None:
        self._previous: dict[str, PlayerSample] = {}
        self._changed: dict[str, float] = {}
        self._paused: dict[str, float] = {}

    def observe(self, samples: tuple[PlayerSample, ...], now: float) -> NowPlaying:
        """Prefer playing media, then the most recently changed player."""
        current = {sample.service: sample for sample in samples if sample.track.title}
        self._changed = {key: stamp for key, stamp in self._changed.items() if key in current}
        self._paused = {key: stamp for key, stamp in self._paused.items() if key in current}
        for key, sample in current.items():
            if sample != self._previous.get(key):
                self._changed[key] = now
            if sample.playback is Playback.PLAYING:
                self._paused.pop(key, None)
            else:
                self._paused.setdefault(key, now)
        self._previous = current
        if not current:
            return HIDDEN
        selected = max(current.values(), key=lambda sample: (
            sample.playback is Playback.PLAYING, self._changed[sample.service], sample.service,
        ))
        paused_at = self._paused.get(selected.service)
        if paused_at is not None and now - paused_at >= PAUSE_GRACE_SECONDS:
            return HIDDEN
        return NowPlaying(selected.track, paused_at)


def _session_reader() -> MetadataReader:
    """Load the optional bus adapter only after the worker has been enabled."""
    from screenbot.mpris_bus import SessionBusReader
    return SessionBusReader(enabled=True)


class MprisWorker(QThread):
    """Poll only after explicit opt-in; never query the bus from paintEvent."""

    changed = pyqtSignal(object)

    def __init__(self, parent: QObject | None = None, *, enabled: bool = False,
                 reader_factory: Callable[[], MetadataReader] = _session_reader) -> None:
        super().__init__(parent)
        self._enabled = enabled
        self._reader_factory = reader_factory
        self._stop = Event()
        self._publication_lock = RLock()

    def request_stop(self) -> None:
        """Clear displayed metadata immediately and stop without blocking the UI."""
        with self._publication_lock:
            self._stop.set()
            self.requestInterruption()
            self.changed.emit(HIDDEN)

    def stop(self) -> None:
        """Join this worker after its view has closed; never terminate a thread."""
        self.request_stop()
        self.wait()

    def run(self) -> None:
        """Create the transport on this thread and publish only sanitized values."""
        if not self._enabled or self._stop.is_set():
            self.changed.emit(HIDDEN)
            return
        reader = self._reader_factory()
        tracker = NowPlayingTracker()
        previous = HIDDEN
        while not self._stop.is_set() and not self.isInterruptionRequested():
            started = time.monotonic()
            snapshot = tracker.observe(reader.read(), time.monotonic())
            with self._publication_lock:
                if self._stop.is_set() or self.isInterruptionRequested():
                    break
                if snapshot != previous:
                    self.changed.emit(snapshot)
                    previous = snapshot
            self._stop.wait(max(0.0, POLL_SECONDS - (time.monotonic() - started)))
