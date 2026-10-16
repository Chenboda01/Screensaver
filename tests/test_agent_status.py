from __future__ import annotations

from threading import Event
import time
from pathlib import Path

from PyQt6.QtCore import QEventLoop, QThread, QTimer, Qt
from PyQt6.QtGui import QColor, QImage, QPainter
from PyQt6.QtWidgets import QApplication
import pytest

import agent_prompt
from bobos import BobOSPhase, BobOSStatus
from screen_session import SceneryWindow
from screenbot.app import Saver
from screenbot.agent_status import AgentBadgePhase, AgentStatusSnapshot, AgentStatusTracker, AgentStatusWorker


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
        "screenbot.agent_status.terminal_agent_status",
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


def test_blocked_status_scan_keeps_ui_frame_timer_responsive(
    app: QApplication, monkeypatch: pytest.MonkeyPatch,
) -> None:
    scan_started = Event()
    release_scan = Event()

    def slow_status_scan() -> agent_prompt.DetectionResult:
        scan_started.set()
        release_scan.wait(2.0)
        return agent_prompt.DetectionResult.ACTIVE

    monkeypatch.setattr("screenbot.agent_status.terminal_agent_status", slow_status_scan)
    worker = AgentStatusWorker()
    worker.start()
    frame_timer = QTimer()
    try:
        assert scan_started.wait(2.0)
        frame_count = 0
        loop = QEventLoop()

        def increment_frame_count() -> None:
            nonlocal frame_count
            frame_count += 1

        frame_timer.setInterval(16)
        frame_timer.timeout.connect(increment_frame_count)
        frame_timer.start()
        start = time.monotonic()
        QTimer.singleShot(250, loop.quit)
        loop.exec()
        measured_fps = frame_count / max(0.001, time.monotonic() - start)
    finally:
        frame_timer.stop()
        release_scan.set()
        worker.stop()

    assert measured_fps >= 25.0


@pytest.mark.parametrize(
    ("scan_duration", "expected_wait", "warns"),
    [(1.5, 6.0, False), (11.0, 0.0, True)],
)
def test_status_poll_cadence_subtracts_scan_time_and_reports_slow_scans(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    scan_duration: float,
    expected_wait: float,
    warns: bool,
) -> None:
    clock = [100.0]
    waits: list[float] = []
    worker = AgentStatusWorker()

    def scan() -> agent_prompt.DetectionResult:
        clock[0] += scan_duration
        return agent_prompt.DetectionResult.INACTIVE

    monkeypatch.setattr("screenbot.agent_status.terminal_agent_status", scan)
    monkeypatch.setattr(worker, "_monotonic_time", lambda: clock[0])
    monkeypatch.setattr(worker, "_wall_time", lambda: 1000.0)
    monkeypatch.setattr(worker, "_wait_for_next_scan", lambda wait: waits.append(wait) or True)
    worker.start()

    assert worker.wait(2000)
    assert waits == pytest.approx([expected_wait])
    assert ("exceeded 10 seconds" in caplog.text) is warns


def test_saver_renders_only_confirmed_status_and_cheers_once(
    app: QApplication, tmp_path: Path,
) -> None:
    config = tmp_path / "status.ini"
    config.write_text("[Screensaver]\nagent_status_enabled=true\n", encoding="utf-8")
    saver = Saver(preview=True, config_path=config)

    def render_badge() -> QImage:
        image = QImage(640, 360, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        saver.draw_agent_status(painter, image.width(), image.height())
        painter.end()
        return image

    hidden = render_badge()
    saver.set_agent_status(AgentStatusSnapshot(
        AgentBadgePhase.WORKING,
        started_at=time.monotonic() - 12 * 60,
    ))
    working = render_badge()
    saver.set_agent_status(AgentStatusSnapshot(
        AgentBadgePhase.FINISHED,
        started_at=time.monotonic() - 13 * 60,
        finished_at=time.time(),
    ))
    finished = render_badge()

    assert hidden.pixelColor(630, 350).alpha() == 0
    assert working.pixelColor(630, 350).alpha() == 0
    assert working.pixelColor(260, 315).alpha() > 0
    assert finished.pixelColor(260, 315).alpha() > 0
    assert saver._agent_celebration_pending
    assert saver._agent_celebration_elapsed(BobOSPhase.EXPLORING) is not None
    assert not saver._agent_celebration_pending
    assert saver._agent_celebration_elapsed(BobOSPhase.EXPLORING) is not None
    calm_bob = QImage(640, 360, QImage.Format.Format_ARGB32_Premultiplied)
    calm_bob.fill(Qt.GlobalColor.transparent)
    painter = QPainter(calm_bob)
    saver.bob(painter, 640, 360, 5.0, BobOSStatus(BobOSPhase.EXPLORING, 0.0))
    painter.end()
    cheering_bob = QImage(640, 360, QImage.Format.Format_ARGB32_Premultiplied)
    cheering_bob.fill(Qt.GlobalColor.transparent)
    painter = QPainter(cheering_bob)
    saver.bob(painter, 640, 360, 5.0, BobOSStatus(BobOSPhase.EXPLORING, 0.0), celebration_elapsed=0.4)
    painter.end()
    assert any(
        calm_bob.pixel(x, y) != cheering_bob.pixel(x, y)
        for x in range(640)
        for y in range(360)
    )
    saver.set_agent_status(AgentStatusSnapshot(AgentBadgePhase.HIDDEN))
    assert render_badge().pixelColor(260, 315).alpha() == 0
    assert saver.agent_status_worker is None
    saver.close()


def test_agent_badge_setting_off_never_renders_or_creates_worker(
    app: QApplication, tmp_path: Path,
) -> None:
    config = tmp_path / "status-off.ini"
    config.write_text("[Screensaver]\nagent_status_enabled=false\n", encoding="utf-8")
    saver = Saver(config_path=config)
    saver.set_agent_status(AgentStatusSnapshot(AgentBadgePhase.WORKING, started_at=time.monotonic()))
    image = QImage(640, 360, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    saver.draw_agent_status(painter, image.width(), image.height())
    painter.end()

    assert image.pixelColor(260, 315).alpha() == 0
    assert saver.agent_status_worker is None
    saver.close()


def test_screensaver_close_requests_worker_stop_without_waiting_on_ui(
    app: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    scan_started = Event()
    release_scan = Event()
    config = tmp_path / "close.ini"
    config.write_text("[Screensaver]\nagent_status_enabled=true\n", encoding="utf-8")

    def slow_scan() -> agent_prompt.DetectionResult:
        scan_started.set()
        release_scan.wait(2.0)
        return agent_prompt.DetectionResult.ACTIVE

    monkeypatch.setattr("screenbot.agent_status.terminal_agent_status", slow_scan)
    saver = Saver(config_path=config)
    saver.show()
    app.processEvents()
    saver.start_agent_status_worker()
    worker = saver.agent_status_worker
    assert worker is not None
    try:
        assert scan_started.wait(2.0)
        close_started = time.monotonic()
        saver.close()
        close_duration = time.monotonic() - close_started
        assert close_duration < 0.2
        assert worker.isRunning()
    finally:
        release_scan.set()
        worker.stop()


def test_full_saver_paint_shows_badge_after_confirmed_status(
    app: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = tmp_path / "paint.ini"
    config.write_text("[Screensaver]\nagent_status_enabled=true\nshow_clock=false\n", encoding="utf-8")
    saver = Saver(preview=True, config_path=config)
    monkeypatch.setattr(saver, "draw_scenery", lambda *_args: None)
    monkeypatch.setattr(
        saver,
        "bobos_status",
        lambda _elapsed: BobOSStatus(BobOSPhase.HOME, 0.0),
    )
    monkeypatch.setattr(saver, "draw_phone_os", lambda *_args: None)
    saver.resize(640, 360)
    saver.show()
    app.processEvents()
    hidden = saver.grab().toImage()

    saver.set_agent_status(AgentStatusSnapshot(
        AgentBadgePhase.WORKING,
        started_at=time.monotonic() - 12 * 60,
    ))
    app.processEvents()
    working = saver.grab().toImage()

    assert not hidden.isNull() and not working.isNull()
    assert hidden.pixelColor(260, 315) != working.pixelColor(260, 315)
    saver.close()


def test_secondary_scenery_window_does_not_draw_primary_badge(
    app: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    del app
    config = tmp_path / "secondary.ini"
    config.write_text("[Screensaver]\nagent_status_enabled=true\n", encoding="utf-8")
    saver = Saver(preview=True, config_path=config)
    saver.set_agent_status(AgentStatusSnapshot(AgentBadgePhase.WORKING, started_at=time.monotonic()))
    monkeypatch.setattr(
        saver,
        "draw_scenery",
        lambda painter, width, height, _time: painter.fillRect(0, 0, width, height, QColor("#123456")),
    )
    secondary = SceneryWindow(saver)
    secondary.resize(640, 360)
    image = QImage(640, 360, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    secondary.render(painter)
    painter.end()

    assert image.pixelColor(260, 315) == QColor("#123456")
    secondary.close()
    saver.close()
