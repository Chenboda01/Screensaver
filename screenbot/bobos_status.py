"""Screensaver-level BobOS eligibility and timeline status helpers."""
from bobos import BobOSStatus, bobos_may_run


class BobOSStatusMixin:
    """Keep phone adventures out of disabled states and before the real lock."""

    def bobos_status(self, elapsed_seconds: float) -> BobOSStatus:
        enabled = bobos_may_run(
            phone_enabled=self.phone_enabled,
            bobos_enabled=self.bobos_enabled,
            password_lock_enabled=self.password_lock,
            elapsed_seconds=elapsed_seconds,
            lock_seconds=self.lock_seconds,
        )
        return self.bobos_timeline.status_at(
            elapsed_seconds, enabled=enabled,
            lock_deadline_seconds=self.lock_seconds if self.password_lock else None,
        )
