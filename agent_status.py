"""Privacy-safe status transitions for the optional screensaver agent badge."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Final, assert_never

from PyQt6.QtCore import QThread, pyqtSignal

from agent_prompt import DetectionResult, terminal_agent_status


class AgentBadgePhase(StrEnum):
    """Only the three states that may be shown on the public screensaver."""

    HIDDEN = "hidden"
    WORKING = "working"
    FINISHED = "finished"


@dataclass(frozen=True, slots=True)
class AgentStatusSnapshot:
    """A UI-safe status value; deliberately contains no process or agent data."""

    phase: AgentBadgePhase
    started_at: float | None = None
    finished_at: float | None = None


HIDDEN_SNAPSHOT: Final[AgentStatusSnapshot] = AgentStatusSnapshot(AgentBadgePhase.HIDDEN)


class AgentStatusTracker:
    """Derive visible states only from confirmed transitions."""

    def __init__(self) -> None:
        self._last_detection = DetectionResult.UNKNOWN
        self._working_started_at: float | None = None
        self._finished_snapshot: AgentStatusSnapshot | None = None

    def observe(self, detection: DetectionResult, monotonic_now: float,
                wall_time_now: float) -> AgentStatusSnapshot:
        """Consume a status result and return only safe state and timing data."""
        match detection:
            case DetectionResult.ACTIVE:
                if self._last_detection is not DetectionResult.ACTIVE:
                    self._working_started_at = monotonic_now
                self._finished_snapshot = None
                self._last_detection = DetectionResult.ACTIVE
                return AgentStatusSnapshot(
                    AgentBadgePhase.WORKING,
                    started_at=self._working_started_at,
                )
            case DetectionResult.INACTIVE:
                was_working = self._last_detection is DetectionResult.ACTIVE
                self._last_detection = DetectionResult.INACTIVE
                if was_working:
                    self._finished_snapshot = AgentStatusSnapshot(
                        AgentBadgePhase.FINISHED,
                        started_at=self._working_started_at,
                        finished_at=wall_time_now,
                    )
                if self._finished_snapshot is not None:
                    return self._finished_snapshot
                self._working_started_at = None
                return HIDDEN_SNAPSHOT
            case DetectionResult.UNKNOWN:
                self._last_detection = DetectionResult.UNKNOWN
                self._working_started_at = None
                self._finished_snapshot = None
                return HIDDEN_SNAPSHOT
            case unreachable:
                assert_never(unreachable)


POLL_INTERVAL_SECONDS: Final[float] = 7.5


class AgentStatusWorker(QThread):
    """Poll detection away from the UI thread and emit only safe snapshots."""

    status_changed = pyqtSignal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._tracker = AgentStatusTracker()
        self._stopping = False

    def stop(self) -> None:
        """Request an orderly exit; the bounded wait is at most one poll period."""
        self._stopping = True
        self.requestInterruption()
        self.wait(round((POLL_INTERVAL_SECONDS + 2) * 1000))

    def run(self) -> None:
        """Scan immediately, then wait between scans without blocking the UI."""
        while not self._stopping and not self.isInterruptionRequested():
            snapshot = self._tracker.observe(
                terminal_agent_status(),
                self._monotonic_time(),
                self._wall_time(),
            )
            self.status_changed.emit(snapshot)
            if self._wait_for_next_scan():
                break

    @staticmethod
    def _monotonic_time() -> float:
        """Provide an overridable monotonic clock for deterministic worker tests."""
        import time

        return time.monotonic()

    @staticmethod
    def _wall_time() -> float:
        """Provide an overridable wall clock for the visible completion time."""
        import time

        return time.time()

    def _wait_for_next_scan(self) -> bool:
        """Wait using Qt's interruption-aware thread sleep."""
        remaining_ms = round(POLL_INTERVAL_SECONDS * 1000)
        while remaining_ms > 0 and not self._stopping and not self.isInterruptionRequested():
            step_ms = min(remaining_ms, 250)
            self.msleep(step_ms)
            remaining_ms -= step_ms
        return self._stopping or self.isInterruptionRequested()
