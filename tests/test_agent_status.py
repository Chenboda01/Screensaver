from __future__ import annotations

from threading import Event

from PyQt6.QtCore import QThread, Qt
from PyQt6.QtWidgets import QApplication
import pytest

import agent_prompt
from agent_status import AgentBadgePhase, AgentStatusSnapshot, AgentStatusTracker, AgentStatusWorker


@pytest.fixture(scope="module")
def app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_initial_inactive_status_stays_hidden() -> None:
    tracker = AgentStatusTracker()

    snapshot = tracker.observe(agent_prompt.DetectionResult.INACTIVE, 10.0, 1000.0)

    assert snapshot == AgentStatusSnapshot(AgentBadgePhase.HIDDEN)


def test_confirmed_active_to_inactive_transition_finishes_once() -> None:
    tracker = AgentStatusTracker()

    working = tracker.observe(agent_prompt.DetectionResult.ACTIVE, 10.0, 1000.0)
    finished = tracker.observe(agent_prompt.DetectionResult.INACTIVE, 40.0, 1030.0)
    still_finished = tracker.observe(agent_prompt.DetectionResult.INACTIVE, 50.0, 1040.0)

    assert working == AgentStatusSnapshot(AgentBadgePhase.WORKING, started_at=10.0)
    assert finished == AgentStatusSnapshot(
        AgentBadgePhase.FINISHED,
        started_at=10.0,
        finished_at=1030.0,
    )
    assert still_finished == finished


def test_unknown_hides_and_breaks_a_possible_finish_transition() -> None:
    tracker = AgentStatusTracker()
    tracker.observe(agent_prompt.DetectionResult.ACTIVE, 10.0, 1000.0)

    hidden = tracker.observe(agent_prompt.DetectionResult.UNKNOWN, 20.0, 1010.0)
    inactive_after_unknown = tracker.observe(agent_prompt.DetectionResult.INACTIVE, 30.0, 1020.0)

    assert hidden == AgentStatusSnapshot(AgentBadgePhase.HIDDEN)
    assert inactive_after_unknown == AgentStatusSnapshot(AgentBadgePhase.HIDDEN)


def test_unknown_to_active_to_inactive_reports_only_confirmed_work() -> None:
    tracker = AgentStatusTracker()
    assert tracker.observe(agent_prompt.DetectionResult.UNKNOWN, 1.0, 100.0).phase is AgentBadgePhase.HIDDEN

    working = tracker.observe(agent_prompt.DetectionResult.ACTIVE, 2.0, 101.0)
    finished = tracker.observe(agent_prompt.DetectionResult.INACTIVE, 9.0, 108.0)

    assert working.phase is AgentBadgePhase.WORKING
    assert finished == AgentStatusSnapshot(
        AgentBadgePhase.FINISHED,
        started_at=2.0,
        finished_at=108.0,
    )


def test_new_active_period_starts_new_cycle_after_finish() -> None:
    tracker = AgentStatusTracker()
    tracker.observe(agent_prompt.DetectionResult.ACTIVE, 10.0, 1000.0)
    tracker.observe(agent_prompt.DetectionResult.INACTIVE, 20.0, 1010.0)

    next_working = tracker.observe(agent_prompt.DetectionResult.ACTIVE, 30.0, 1020.0)

    assert next_working == AgentStatusSnapshot(AgentBadgePhase.WORKING, started_at=30.0)


def test_status_worker_emits_from_its_background_thread(app: QApplication, monkeypatch: pytest.MonkeyPatch) -> None:
    del app
    emitted = Event()
    observed: list[tuple[QThread, AgentStatusSnapshot]] = []
    monkeypatch.setattr(
        "agent_status.terminal_agent_status",
        lambda: agent_prompt.DetectionResult.INACTIVE,
    )
    worker = AgentStatusWorker()

    def receive(snapshot: AgentStatusSnapshot) -> None:
        observed.append((QThread.currentThread(), snapshot))
        emitted.set()

    worker.status_changed.connect(receive, Qt.ConnectionType.DirectConnection)
    worker.start()
    try:
        assert emitted.wait(2.0)
    finally:
        worker.stop()

    assert observed
    assert observed[0][0] == worker
    assert observed[0][1] == AgentStatusSnapshot(AgentBadgePhase.HIDDEN)
