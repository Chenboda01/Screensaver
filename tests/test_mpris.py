"""Deterministic privacy, lifecycle, selection and bounded-polling checks."""
from dataclasses import fields
from threading import Event
import time

from PyQt6.QtCore import QCoreApplication, QEventLoop, QThread, QTimer, Qt
import pytest

from screenbot.mpris import HIDDEN, MetadataReader, MprisWorker, NowPlaying, NowPlayingTracker, Playback, PlayerSample, Track
from screenbot.mpris_bus import (
    CALL_MILLISECONDS, MAX_PLAYERS, PLAYER_INTERFACE, ROOT_INTERFACE,
    PropertyValue, SessionBusReader, TEXT_LIMIT,
)


class FakeBus:
    """Mutable mock player state and call recorder for transport-boundary tests."""

    def __init__(self) -> None:
        self.services = ['org.mpris.MediaPlayer2.browser', 'org.example.private.WindowTitles']
        self.values: dict[str, PropertyValue] = {
            'PlaybackStatus': 'Playing', 'Identity': 'Browser media',
            'Metadata': {'xesam:title': 'Song', 'xesam:artist': ['Artist'], 'xesam:album': 'Album',
                         'xesam:url': 'file:///private/file', 'mpris:artUrl': 'https://private/image'},
        }
        self.calls: list[tuple[str, str, str, int]] = []

    def names(self, timeout_ms: int) -> list[str]:
        self.calls.append(('', '', 'ListNames', timeout_ms))
        return self.services

    def get(self, service: str, interface: str, name: str, timeout_ms: int) -> PropertyValue:
        self.calls.append((service, interface, name, timeout_ms))
        return self.values[name]


def sample(service: str = 'player', title: str = 'Song',
           playback: Playback = Playback.PLAYING) -> PlayerSample:
    return PlayerSample(service, playback, Track('Player', title, 'Artist', 'Album'))


def test_disabled_reader_never_constructs_transport() -> None:
    # Given a constructor which must never run without opt-in.
    def forbidden() -> FakeBus:
        pytest.fail('disabled reader accessed the session bus')
    reader = SessionBusReader(transport_factory=forbidden)
    # When sampling the default-off reader.
    observed = reader.read()
    # Then no data or bus access occurs.
    assert observed == ()


def test_reader_returns_only_permitted_media_fields() -> None:
    # Given browser MPRIS metadata and an unrelated private service.
    bus = FakeBus()
    # When explicitly opting in.
    observed = SessionBusReader(enabled=True, transport_factory=lambda: bus).read()
    # Then only the MPRIS media fields cross the boundary.
    assert observed == (PlayerSample(bus.services[0], Playback.PLAYING,
                                    Track('Browser media', 'Song', 'Artist', 'Album')),)
    assert {field.name for field in fields(Track)} == {'player', 'title', 'artist', 'album'}
    assert {(interface, name) for _, interface, name, _ in bus.calls[1:]} == {
        (PLAYER_INTERFACE, 'PlaybackStatus'), (PLAYER_INTERFACE, 'Metadata'), (ROOT_INTERFACE, 'Identity'),
    }
    assert all(service == bus.services[0] for service, _, _, _ in bus.calls[1:])
    assert all(0 < timeout <= CALL_MILLISECONDS for _, _, _, timeout in bus.calls)


def test_playback_only_reader_never_requests_track_metadata() -> None:
    bus = FakeBus()
    reader = SessionBusReader(enabled=True, transport_factory=lambda: bus)
    assert reader.is_playing()
    assert {(interface, name) for _, interface, name, _ in bus.calls[1:]} == {
        (PLAYER_INTERFACE, 'PlaybackStatus'),
    }
    bus.values['PlaybackStatus'] = 'Paused'
    bus.calls.clear()
    assert not reader.is_playing()


@pytest.mark.parametrize('title', ['', ' \n\t', '\x00\u202e', 42, ['wrong']])
def test_empty_or_malformed_titles_hide(title: str | int | list[str]) -> None:
    bus = FakeBus()
    bus.values['Metadata'] = {'xesam:title': title}
    assert SessionBusReader(enabled=True, transport_factory=lambda: bus).read() == ()


def test_metadata_is_plain_bounded_text() -> None:
    bus = FakeBus()
    bus.values['Identity'] = 'Browser\x00\u202e'
    bus.values['Metadata'] = {'xesam:title': '界' * 1000, 'xesam:artist': ['One', 'Two'], 'xesam:album': []}
    result = SessionBusReader(enabled=True, transport_factory=lambda: bus).read()[0].track
    assert result.player == 'Browser'
    assert result.title == '界' * (TEXT_LIMIT - 1) + '…'
    assert result.artist == 'One, Two'
    assert result.album == ''


@pytest.mark.parametrize('field,value', [('PlaybackStatus', None), ('PlaybackStatus', 'Unknown'),
                                        ('Metadata', None), ('Metadata', 'invalid')])
def test_failed_property_reads_hide(field: str, value: PropertyValue) -> None:
    bus = FakeBus()
    bus.values[field] = value
    assert SessionBusReader(enabled=True, transport_factory=lambda: bus).read() == ()


def test_missing_qtdbus_hides() -> None:
    def missing() -> FakeBus:
        raise ImportError('QtDBus unavailable')
    assert SessionBusReader(enabled=True, transport_factory=missing).read() == ()


def test_player_count_is_bounded() -> None:
    bus = FakeBus()
    bus.services = [f'org.mpris.MediaPlayer2.player{index}' for index in range(100)]
    observed = SessionBusReader(enabled=True, transport_factory=lambda: bus, clock=lambda: 0.0).read()
    assert len(observed) == MAX_PLAYERS
    assert len(bus.calls) == 1 + MAX_PLAYERS * 3


def test_scan_deadline_stops_more_requests() -> None:
    bus = FakeBus()
    timestamps = iter([0.0, 0.0, 0.1, 1.1])
    observed = SessionBusReader(enabled=True, transport_factory=lambda: bus,
                                clock=lambda: next(timestamps)).read()
    assert observed == ()
    assert len(bus.calls) == 2  # ListNames then PlaybackStatus; metadata is never read.


def test_track_changes_update_and_playing_takes_priority() -> None:
    tracker = NowPlayingTracker()
    tracker.observe((sample('a'), sample('b', playback=Playback.PAUSED)), 0.0)
    observed = tracker.observe((sample('a', 'Next'), sample('b', playback=Playback.PAUSED)), 2.0)
    assert observed.track == sample('a', 'Next').track
    assert observed.paused_at is None


def test_most_recently_changed_player_wins_ties() -> None:
    tracker = NowPlayingTracker()
    tracker.observe((sample('a'), sample('b')), 0.0)
    observed = tracker.observe((sample('a', 'Next'), sample('b')), 2.0)
    assert observed.track == sample('a', 'Next').track


@pytest.mark.parametrize('playback', [Playback.PAUSED, Playback.STOPPED])
def test_pause_and_stop_hide_after_grace_without_extending_deadline(playback: Playback) -> None:
    tracker = NowPlayingTracker()
    tracker.observe((sample(),), 0.0)
    paused = tracker.observe((sample(playback=playback),), 2.0)
    before_deadline = tracker.observe((sample(playback=playback),), 4.9)
    hidden = tracker.observe((sample(playback=playback),), 5.0)
    assert paused.paused_at == 2.0
    assert before_deadline == paused
    assert hidden == HIDDEN


def test_disappearance_hides_and_forgets_previous_metadata() -> None:
    tracker = NowPlayingTracker()
    tracker.observe((sample(),), 0.0)
    assert tracker.observe((), 1.0) == HIDDEN
    assert tracker.observe((sample(playback=Playback.PAUSED),), 10.0).paused_at == 10.0


def test_resume_removes_pause_deadline() -> None:
    tracker = NowPlayingTracker()
    tracker.observe((sample(playback=Playback.PAUSED),), 0.0)
    assert tracker.observe((sample(),), 10.0).paused_at is None


def test_disabled_worker_does_not_construct_reader() -> None:
    app = QCoreApplication.instance() or QCoreApplication([])
    def forbidden() -> MetadataReader:
        pytest.fail('disabled worker constructed reader')
    worker = MprisWorker(reader_factory=forbidden)
    worker.start()
    assert worker.wait(1000)
    assert app is not None


def test_blocked_reader_never_blocks_ui_and_stop_discards_result() -> None:
    app = QCoreApplication.instance() or QCoreApplication([])
    started, release = Event(), Event()
    worker_threads: list[QThread] = []
    snapshots: list[NowPlaying] = []

    class SlowReader:
        def read(self) -> tuple[PlayerSample, ...]:
            worker_threads.append(QThread.currentThread())
            started.set()
            assert release.wait(2.0)
            return (sample(),)

        def is_playing(self) -> bool:
            return True

    worker = MprisWorker(enabled=True, reader_factory=SlowReader)
    worker.changed.connect(snapshots.append, Qt.ConnectionType.DirectConnection)
    worker.start()
    ticks: list[float] = []
    timer = QTimer()
    loop = QEventLoop()
    timer.timeout.connect(lambda: ticks.append(time.monotonic()))
    try:
        assert started.wait(1.0)
        timer.start(10)
        QTimer.singleShot(150, loop.quit)
        loop.exec()
        before_stop = time.monotonic()
        worker.request_stop()
        assert time.monotonic() - before_stop < 0.05
    finally:
        timer.stop()
        release.set()
        worker.stop()
    assert len(ticks) >= 5
    assert worker_threads == [worker]
    assert snapshots and all(snapshot == HIDDEN for snapshot in snapshots)
    assert app is not None


def test_enabled_worker_publishes_metadata_then_clears_on_stop() -> None:
    app = QCoreApplication.instance() or QCoreApplication([])
    published = Event()
    snapshots: list[NowPlaying] = []

    class Reader:
        def read(self) -> tuple[PlayerSample, ...]:
            return (sample(),)

        def is_playing(self) -> bool:
            return True

    worker = MprisWorker(enabled=True, reader_factory=Reader)

    def receive(snapshot: NowPlaying) -> None:
        snapshots.append(snapshot)
        if snapshot.track is not None:
            published.set()

    worker.changed.connect(receive, Qt.ConnectionType.DirectConnection)
    worker.start()
    try:
        assert published.wait(1.0)
    finally:
        worker.stop()
    assert snapshots[0].track == sample().track
    assert snapshots[-1] == HIDDEN
    assert app is not None


def test_titleless_playing_media_mutes_ambience_without_exposing_metadata() -> None:
    """Now Playing may hide a title, but opted-in playback status still mutes audio."""
    app = QCoreApplication.instance() or QCoreApplication([])
    published = Event()
    snapshots: list[NowPlaying] = []
    playing_states: list[bool] = []

    class TitlelessReader:
        def read(self) -> tuple[PlayerSample, ...]:
            return (PlayerSample('player', Playback.PLAYING, Track('Player', '')),)

        def is_playing(self) -> bool:
            return True

    worker = MprisWorker(enabled=True, reader_factory=TitlelessReader, publish_playback=True)
    worker.changed.connect(snapshots.append)
    loop = QEventLoop()
    worker.playing_changed.connect(lambda state: (playing_states.append(state), published.set(), loop.quit()))
    worker.start()
    try:
        QTimer.singleShot(1000, loop.quit)
        loop.exec()
        assert published.is_set()
        deadline = time.monotonic() + 1.0
        while (not snapshots or snapshots[-1] != HIDDEN) and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(.005)
        app.processEvents()
        assert playing_states == [True]
        assert all(snapshot == HIDDEN for snapshot in snapshots)
    finally:
        worker.stop()
    assert app is not None


def test_titleless_playing_mutes_when_another_title_is_displayable() -> None:
    app = QCoreApplication.instance() or QCoreApplication([])
    published = Event()
    playing_states: list[bool] = []
    snapshots: list[NowPlaying] = []

    class MixedReader:
        def read(self) -> tuple[PlayerSample, ...]:
            return (sample('paused', playback=Playback.PAUSED),
                    PlayerSample('private', Playback.PLAYING, Track('Player', '')))

        def is_playing(self) -> bool:
            return True

    worker = MprisWorker(enabled=True, reader_factory=MixedReader, publish_playback=True)
    worker.changed.connect(snapshots.append)
    loop = QEventLoop()
    worker.playing_changed.connect(lambda state: (playing_states.append(state), published.set(), loop.quit()))
    worker.start()
    try:
        QTimer.singleShot(1000, loop.quit)
        loop.exec()
        assert published.is_set()
        deadline = time.monotonic() + .5
        while not snapshots and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(.005)
        assert playing_states == [True]
        assert snapshots and snapshots[-1].track == sample('paused', playback=Playback.PAUSED).track
    finally:
        worker.stop()


def test_now_playing_privacy_mode_does_not_publish_playback_metadata() -> None:
    app = QCoreApplication.instance() or QCoreApplication([])
    published: list[bool] = []

    class Reader:
        def read(self) -> tuple[PlayerSample, ...]:
            return ()

        def is_playing(self) -> bool:
            return True

    worker = MprisWorker(enabled=True, reader_factory=Reader)
    worker.playing_changed.connect(published.append)
    worker.start()
    try:
        time.sleep(.05)
        app.processEvents()
        assert published == []
    finally:
        worker.stop()


def test_playback_only_worker_publishes_status_without_metadata() -> None:
    app = QCoreApplication.instance() or QCoreApplication([])
    published = Event()
    states: list[bool] = []

    class Reader:
        def read(self) -> tuple[PlayerSample, ...]:
            pytest.fail('playback-only worker read track metadata')

        def is_playing(self) -> bool:
            return True

    worker = MprisWorker(enabled=True, reader_factory=Reader, playing_only=True)
    worker.playing_changed.connect(lambda playing: (states.append(playing), published.set()),
                                   Qt.ConnectionType.DirectConnection)
    worker.start()
    assert published.wait(1.0)
    worker.stop()
    assert states == [True, False]
    assert app is not None


def test_mock_player_track_update_and_pause_flow() -> None:
    bus = FakeBus()
    reader = SessionBusReader(enabled=True, transport_factory=lambda: bus)
    tracker = NowPlayingTracker()
    initial = tracker.observe(reader.read(), 0.0)
    assert initial.track is not None
    assert initial.track.title == 'Song'
    bus.values['Metadata'] = {'xesam:title': 'Next song'}
    assert tracker.observe(reader.read(), 2.0).track == Track('Browser media', 'Next song')
    bus.values['PlaybackStatus'] = 'Paused'
    assert tracker.observe(reader.read(), 4.0).paused_at == 4.0
    assert tracker.observe(reader.read(), 7.0) == HIDDEN
