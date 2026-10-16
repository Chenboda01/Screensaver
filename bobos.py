"""Deterministic timing for Bob's entirely fictional phone adventure."""
from dataclasses import dataclass
from enum import StrEnum
from typing import Final


class BobOSPhase(StrEnum):
    EXPLORING = "exploring"
    CURIOUS = "curious"
    PHONE_ACTIVATION = "phone-activation"
    WIFI_CONNECTING = "wifi-connecting"
    BOOTING = "booting"
    ZOOM_IN = "zoom-in"
    HOME = "home"
    BROWSER = "browser"
    NOTIFICATION = "notification"
    FILES = "files"
    TERMINAL = "terminal"
    GAMES = "games"
    SETTINGS = "settings"
    CHAT = "chat"
    MAPS = "maps"
    WEATHER = "weather"
    CALENDAR = "calendar"
    APP_STORE = "app-store"
    SHUTDOWN = "shutdown"
    ZOOM_OUT = "zoom-out"
    RETURN = "return"


MIN_COOLDOWN_SECONDS: Final[int] = 5 * 60
NORMAL_SEQUENCE: Final[tuple[tuple[BobOSPhase, int], ...]] = (
    (BobOSPhase.CURIOUS, 4),
    (BobOSPhase.PHONE_ACTIVATION, 5),
    (BobOSPhase.WIFI_CONNECTING, 8),
    (BobOSPhase.BOOTING, 8),
    (BobOSPhase.ZOOM_IN, 5),
    (BobOSPhase.HOME, 26),
    (BobOSPhase.BROWSER, 32),
    (BobOSPhase.NOTIFICATION, 6),
    (BobOSPhase.FILES, 24),
    (BobOSPhase.TERMINAL, 32),
    (BobOSPhase.GAMES, 36),
    (BobOSPhase.SETTINGS, 24),
    (BobOSPhase.CHAT, 16),
    (BobOSPhase.MAPS, 16),
    (BobOSPhase.WEATHER, 12),
    (BobOSPhase.CALENDAR, 12),
    (BobOSPhase.APP_STORE, 18),
    (BobOSPhase.SHUTDOWN, 8),
    (BobOSPhase.ZOOM_OUT, 5),
    (BobOSPhase.RETURN, 3),
)
PREVIEW_SEQUENCE: Final[tuple[tuple[BobOSPhase, int], ...]] = (
    (BobOSPhase.CURIOUS, 1),
    (BobOSPhase.PHONE_ACTIVATION, 1),
    (BobOSPhase.WIFI_CONNECTING, 2),
    (BobOSPhase.BOOTING, 2),
    (BobOSPhase.ZOOM_IN, 2),
    (BobOSPhase.HOME, 3),
    (BobOSPhase.BROWSER, 4),
    (BobOSPhase.NOTIFICATION, 1),
    (BobOSPhase.FILES, 3),
    (BobOSPhase.TERMINAL, 4),
    (BobOSPhase.GAMES, 4),
    (BobOSPhase.SETTINGS, 3),
    (BobOSPhase.CHAT, 2),
    (BobOSPhase.MAPS, 2),
    (BobOSPhase.WEATHER, 2),
    (BobOSPhase.CALENDAR, 2),
    (BobOSPhase.APP_STORE, 2),
    (BobOSPhase.SHUTDOWN, 2),
    (BobOSPhase.ZOOM_OUT, 2),
    (BobOSPhase.RETURN, 1),
)


@dataclass(frozen=True, slots=True)
class BobOSStatus:
    phase: BobOSPhase
    phase_elapsed_seconds: float


@dataclass(frozen=True, slots=True)
class BobOSTimeline:
    """Schedule adventures from the screensaver's first visible frame."""

    activation_delay_seconds: int
    show_connection_animation: bool
    first_adventure_offset_seconds: int = 0
    cooldown_offset_seconds: int = 0
    preview_mode: bool = False

    @property
    def adventure_sequence(self) -> tuple[tuple[BobOSPhase, int], ...]:
        """Return the full fictional activity, omitting only optional Wi-Fi."""
        sequence = PREVIEW_SEQUENCE if self.preview_mode else NORMAL_SEQUENCE
        if self.show_connection_animation:
            return sequence
        return tuple(item for item in sequence if item[0] is not BobOSPhase.WIFI_CONNECTING)

    @property
    def sequence_duration_seconds(self) -> int:
        return sum(duration for _, duration in self.adventure_sequence)

    def phase_at(self, elapsed_seconds: float, *, enabled: bool = True) -> BobOSPhase:
        """Return the phase at an elapsed screen time without performing real I/O."""
        return self.status_at(elapsed_seconds, enabled=enabled).phase

    def status_at(self, elapsed_seconds: float, *, enabled: bool = True) -> BobOSStatus:
        """Return the current phase and its elapsed time for animation drawing."""
        if not enabled or elapsed_seconds < 0:
            return BobOSStatus(BobOSPhase.EXPLORING, 0.0)

        delay = 0 if self.preview_mode else max(0, self.activation_delay_seconds)
        first_start = delay + (0 if self.preview_mode else max(0, self.first_adventure_offset_seconds))
        sequence = self.adventure_sequence
        cycle_offset = 0
        last_completed_at = 0.0
        while True:
            sequence_start = first_start + cycle_offset
            if elapsed_seconds < sequence_start:
                return BobOSStatus(BobOSPhase.EXPLORING, elapsed_seconds - last_completed_at)

            cursor = sequence_start
            for phase, duration in sequence:
                phase_end = cursor + duration
                if elapsed_seconds < phase_end:
                    return BobOSStatus(phase, elapsed_seconds - cursor)
                cursor = phase_end

            completed_at = cursor
            next_start = completed_at + self.cooldown_seconds
            if elapsed_seconds < next_start:
                return BobOSStatus(BobOSPhase.EXPLORING, elapsed_seconds - completed_at)
            last_completed_at = completed_at
            cycle_offset += self.sequence_duration_seconds + self.cooldown_seconds

    @property
    def cooldown_seconds(self) -> int:
        """Return a cooldown that is always at least five minutes."""
        return MIN_COOLDOWN_SECONDS + max(0, self.cooldown_offset_seconds)


def bobos_may_run(
    *,
    phone_enabled: bool,
    bobos_enabled: bool,
    password_lock_enabled: bool,
    elapsed_seconds: float,
    lock_seconds: float,
) -> bool:
    """Enforce the phone dependency and yield before KDE's real password lock."""
    if not phone_enabled or not bobos_enabled:
        return False
    if password_lock_enabled and elapsed_seconds >= lock_seconds:
        return False
    return True
