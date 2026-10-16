"""Seeded adventures, lock boundaries, and real Camera/Pet rendering."""
from collections.abc import Iterator
import itertools
import os
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest
from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtWidgets import QApplication

from bobos import APP_PHASES, NORMAL_SEQUENCE, PREVIEW_SEQUENCE, BobOSPhase, BobOSStatus, BobOSTimeline
from screensaver import Saver


@pytest.fixture(scope='module')
def application() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture
def saver(tmp_path: Path, application: QApplication) -> Iterator[Saver]:
    config = tmp_path / 'settings.ini'
    config.write_text('[Screensaver]\ntheme=forest\nlive_sky_enabled=false\n', encoding='utf-8')
    window = Saver(preview_bobos=True, config_path=config)
    window.resize(1280, 720)
    yield window
    window.close()


def render(saver: Saver, phase: BobOSPhase, elapsed: float, width: int = 900) -> QImage:
    image = QImage(width, round(width * 520 / 900), QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    saver.draw_phone_canvas(painter, QRectF(0, 0, image.width(), image.height()),
                            BobOSStatus(phase, elapsed), 100 + elapsed)
    painter.end()
    evidence = os.environ.get('SCREENBOT_BOBOS_EVIDENCE')
    if evidence:
        target = Path(evidence) / f'{saver.theme}-{phase.value}-{elapsed:g}-{width}.png'
        target.parent.mkdir(parents=True, exist_ok=True)
        assert image.save(str(target))
    return image


def test_seed_replays_same_adventures_independent_of_query_order() -> None:
    first = BobOSTimeline(60, True, random_seed=28)
    second = BobOSTimeline(60, True, random_seed=28)

    sequences = list(itertools.islice(first.sequences(), 12))

    assert sequences == list(itertools.islice(second.sequences(), 12))
    assert sequences != list(itertools.islice(BobOSTimeline(60, True, random_seed=29).sequences(), 12))
    for elapsed in (940, 60, 120, 4000, 0):
        assert first.status_at(elapsed) == second.status_at(elapsed)


def test_thousands_of_adventures_have_distinct_consecutive_subsets() -> None:
    timeline = BobOSTimeline(60, True, random_seed=28)

    sequences = list(itertools.islice(timeline.sequences(), 5000))

    previous = frozenset()
    counts = set()
    for sequence in sequences:
        apps = [phase for phase, _ in sequence if phase in APP_PHASES]
        assert 4 <= len(apps) <= 6
        assert len(apps) == len(set(apps))
        assert frozenset(apps) != previous
        assert sequence[:6] == NORMAL_SEQUENCE[:6]
        assert sequence[-3:] == NORMAL_SEQUENCE[-3:]
        previous = frozenset(apps)
        counts.add(len(apps))
    assert counts == {4, 5, 6}


def test_every_phase_boundary_and_cooldown_follows_selected_durations() -> None:
    timeline = BobOSTimeline(60, True, first_adventure_offset_seconds=7,
                             cooldown_offset_seconds=23, random_seed=28)
    cursor = 67

    sequences = list(itertools.islice(timeline.sequences(), 8))

    for sequence in sequences:
        for phase, duration in sequence:
            assert timeline.status_at(cursor) == BobOSStatus(phase, 0)
            assert timeline.phase_at(cursor + duration - .001) == phase
            cursor += duration
        assert timeline.phase_at(cursor) == BobOSPhase.EXPLORING
        assert timeline.phase_at(cursor + timeline.cooldown_seconds - .001) == BobOSPhase.EXPLORING
        cursor += timeline.cooldown_seconds
    assert len({sum(duration for _, duration in sequence) for sequence in sequences}) > 1


@pytest.mark.parametrize('wifi', [False, True])
def test_adventure_must_finish_before_kde_lock_deadline(wifi: bool) -> None:
    timeline = BobOSTimeline(60, wifi, random_seed=28)
    end = 60 + timeline.sequence_duration_seconds

    blocked = timeline.status_at(60, lock_deadline_seconds=end)
    allowed = timeline.status_at(60, lock_deadline_seconds=end + .001)

    assert blocked.phase == BobOSPhase.EXPLORING
    assert allowed.phase == BobOSPhase.CURIOUS
    assert timeline.status_at(end, lock_deadline_seconds=end).phase == BobOSPhase.EXPLORING
    assert timeline.status_at(60, lock_deadline_seconds=59).phase == BobOSPhase.EXPLORING


def test_later_adventure_checks_its_own_duration_before_starting() -> None:
    timeline = BobOSTimeline(60, True, random_seed=28)
    sequences = list(itertools.islice(timeline.sequences(), 2))
    second_start = 60 + sum(duration for _, duration in sequences[0]) + timeline.cooldown_seconds
    second_end = second_start + sum(duration for _, duration in sequences[1])

    status = timeline.status_at(second_start, lock_deadline_seconds=second_end)

    assert status.phase == BobOSPhase.EXPLORING
    assert timeline.status_at(second_start, lock_deadline_seconds=second_end + 1).phase == BobOSPhase.CURIOUS


def test_saver_passes_real_lock_deadline_and_preview_bypasses_it(saver: Saver) -> None:
    saver.bobos_timeline = BobOSTimeline(60, True, random_seed=28)
    saver.lock_seconds = 60 + saver.bobos_timeline.sequence_duration_seconds
    saver.password_lock = True

    status = saver.bobos_status(60)

    assert status.phase == BobOSPhase.EXPLORING
    saver.password_lock = False
    assert saver.bobos_status(60).phase == BobOSPhase.CURIOUS


def test_preview_retains_every_app_and_notification(saver: Saver) -> None:
    phases = {phase for phase, _ in saver.bobos_timeline.adventure_sequence}

    for phase, duration in PREVIEW_SEQUENCE:
        image = render(saver, phase, duration / 2)
        assert not image.isNull()

    assert set(APP_PHASES) <= phases
    assert BobOSPhase.NOTIFICATION in phases
    assert saver.bobos_timeline.sequence_duration_seconds < 60


@pytest.mark.parametrize('phase', [BobOSPhase.CAMERA, BobOSPhase.PET])
@pytest.mark.parametrize('width', [390, 1440])
def test_new_apps_render_distinct_motion_frames(saver: Saver, phase: BobOSPhase, width: int) -> None:
    before = render(saver, phase, .2, width)

    middle = render(saver, phase, 1.55, width)
    after = render(saver, phase, 2.8, width)

    assert before != middle
    assert middle != after
    assert before != after


def test_camera_uses_current_scene_and_live_sky(saver: Saver) -> None:
    forest = render(saver, BobOSPhase.CAMERA, .2)
    saver.theme = 'mountains'

    mountains = render(saver, BobOSPhase.CAMERA, .2)
    saver.live_sky_enabled = True
    saver.bobos_camera.refresh_key = None
    live_sky = render(saver, BobOSPhase.CAMERA, .4)

    assert forest != mountains
    assert mountains != live_sky
    assert saver.bobos_camera.frame.size().width() == 480
    assert saver.bobos_camera.frame.size().height() == 200


def test_camera_refresh_is_bounded_and_photo_appears_in_files(saver: Saver) -> None:
    files_before = render(saver, BobOSPhase.FILES, 0)
    render(saver, BobOSPhase.CAMERA, .2)
    first_frame = saver.bobos_camera.frame
    with patch.object(saver, 'draw_scenery', wraps=saver.draw_scenery) as draw:
        render(saver, BobOSPhase.CAMERA, .21)
        assert draw.call_count == 0
    assert saver.bobos_camera.frame is first_frame

    render(saver, BobOSPhase.CAMERA, 1.55)
    captured = saver.bobos_camera.photo.copy()
    render(saver, BobOSPhase.CAMERA, 2.8)
    files_after = render(saver, BobOSPhase.FILES, 0)

    assert saver.bobos_camera.photo == captured
    assert files_before != files_after
    assert saver.bobos_camera.photo.size().width() == 480
    assert saver.bobos_camera.photo.size().height() == 200


def test_pet_has_no_saved_state(saver: Saver, tmp_path: Path) -> None:
    existing = set(tmp_path.rglob('*'))

    render(saver, BobOSPhase.PET, 0)
    render(saver, BobOSPhase.PET, 2.8)

    assert set(tmp_path.rglob('*')) == existing
