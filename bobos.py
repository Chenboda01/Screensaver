"""Pure timing rules for Bob's fictional, screensaver-only BobOS adventures."""
from dataclasses import dataclass
from enum import StrEnum
from typing import Final


class BobOSPhase(StrEnum):
    EXPLORING = "exploring"
    CONNECTING = "connecting"
    ACTIVE = "active"
    PACKING_UP = "packing-up"


ADVENTURE_SECONDS: Final[int] = 42
CONNECTION_SECONDS: Final[int] = 8
PACK_UP_SECONDS: Final[int] = 6
MIN_COOLDOWN_SECONDS: Final[int] = 5 * 60


@dataclass(frozen=True, slots=True)
class BobOSStatus:
    phase: BobOSPhase
    phase_elapsed_seconds: float


@dataclass(frozen=True, slots=True)
class BobOSTimeline:
    """Compute BobOS phases relative to the screensaver's first visible frame."""

    activation_delay_seconds: int
    show_connection_animation: bool
    first_adventure_offset_seconds: int = 0
    cooldown_offset_seconds: int = 0

    def phase_at(self, elapsed_seconds: float, *, enabled: bool = True) -> BobOSPhase:
        """Return the fictional activity phase without starting real applications."""
        return self.status_at(elapsed_seconds, enabled=enabled).phase

    def status_at(self, elapsed_seconds: float, *, enabled: bool = True) -> BobOSStatus:
        """Return a phase and its local elapsed time for smooth visual transitions."""
        if not enabled or elapsed_seconds < 0:
            return BobOSStatus(BobOSPhase.EXPLORING, 0.0)

        first_start = self.activation_delay_seconds + max(0, self.first_adventure_offset_seconds)
        connection_seconds = CONNECTION_SECONDS if self.show_connection_animation else 0
        adventure_end = first_start + connection_seconds + ADVENTURE_SECONDS
        pack_up_end = adventure_end + PACK_UP_SECONDS

        if elapsed_seconds < first_start:
            return BobOSStatus(BobOSPhase.EXPLORING, elapsed_seconds)
        while elapsed_seconds >= first_start:
            if elapsed_seconds < first_start + connection_seconds:
                return BobOSStatus(BobOSPhase.CONNECTING, elapsed_seconds - first_start)
            if elapsed_seconds < adventure_end:
                return BobOSStatus(BobOSPhase.ACTIVE, elapsed_seconds - (first_start + connection_seconds))
            if elapsed_seconds < pack_up_end:
                return BobOSStatus(BobOSPhase.PACKING_UP, elapsed_seconds - adventure_end)
            previous_pack_up_end = pack_up_end
            first_start = pack_up_end + MIN_COOLDOWN_SECONDS + max(0, self.cooldown_offset_seconds)
            if elapsed_seconds < first_start:
                return BobOSStatus(BobOSPhase.EXPLORING, elapsed_seconds - previous_pack_up_end)
            adventure_end = first_start + connection_seconds + ADVENTURE_SECONDS
            pack_up_end = adventure_end + PACK_UP_SECONDS

        return BobOSStatus(BobOSPhase.EXPLORING, 0.0)


def bobos_may_run(
    *,
    backpack_enabled: bool,
    bobos_enabled: bool,
    password_lock_enabled: bool,
    elapsed_seconds: float,
    lock_seconds: float,
) -> bool:
    """Enforce the feature dependency and let KDE's configured lock win."""
    if not backpack_enabled or not bobos_enabled:
        return False
    if password_lock_enabled and elapsed_seconds >= lock_seconds:
        return False
    return True
