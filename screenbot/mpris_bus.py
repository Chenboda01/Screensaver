"""Bounded session-bus MPRIS reads; no controls, artwork, URLs or disk cache."""
from collections.abc import Callable, Mapping
import time
import unicodedata
from typing import Final, Protocol, TypeAlias

from screenbot.mpris import Playback, PlayerSample, Track


BUS_PREFIX: Final = 'org.mpris.MediaPlayer2.'
PLAYER_INTERFACE: Final = 'org.mpris.MediaPlayer2.Player'
ROOT_INTERFACE: Final = 'org.mpris.MediaPlayer2'
MAX_PLAYERS: Final = 16
SCAN_SECONDS: Final = 1.0
CALL_MILLISECONDS: Final = 150
TEXT_LIMIT: Final = 160
MetadataValue: TypeAlias = str | list[str]
PropertyValue: TypeAlias = str | Mapping[str, MetadataValue] | None


class BusTransport(Protocol):
    def names(self, timeout_ms: int) -> list[str]: ...
    def get(self, service: str, interface: str, name: str, timeout_ms: int) -> PropertyValue: ...


def clean_text(value: str) -> str:
    """Bound plain text and discard control/format characters, including bidi overrides."""
    text = ' '.join(''.join(char for char in value[:4096]
                           if not unicodedata.category(char).startswith('C')).split())
    return text if len(text) <= TEXT_LIMIT else text[:TEXT_LIMIT - 1] + '…'


class QtSessionBus:
    """Transport restricted to ListNames and the three permitted MPRIS properties."""

    def __init__(self) -> None:
        from PyQt6 import QtDBus
        self._qt = QtDBus
        self._bus = QtDBus.QDBusConnection.sessionBus()

    def names(self, timeout_ms: int) -> list[str]:
        if not self._bus.isConnected():
            return []
        message = self._qt.QDBusMessage.createMethodCall(
            'org.freedesktop.DBus', '/org/freedesktop/DBus', 'org.freedesktop.DBus', 'ListNames')
        reply = self._bus.call(message, self._qt.QDBus.CallMode.Block, timeout_ms)
        values = reply.arguments()
        if reply.type() != self._qt.QDBusMessage.MessageType.ReplyMessage or len(values) != 1:
            return []
        return [name for name in values[0] if type(name) is str] if type(values[0]) is list else []

    def get(self, service: str, interface: str, name: str, timeout_ms: int) -> PropertyValue:
        if not service.startswith(BUS_PREFIX) or (interface, name) not in (
            (ROOT_INTERFACE, 'Identity'), (PLAYER_INTERFACE, 'PlaybackStatus'),
            (PLAYER_INTERFACE, 'Metadata'),
        ):
            return None
        message = self._qt.QDBusMessage.createMethodCall(
            service, '/org/mpris/MediaPlayer2', 'org.freedesktop.DBus.Properties', 'Get')
        message.setAutoStartService(False)
        message.setArguments([interface, name])
        reply = self._bus.call(message, self._qt.QDBus.CallMode.Block, timeout_ms)
        values = reply.arguments()
        if reply.type() != self._qt.QDBusMessage.MessageType.ReplyMessage or len(values) != 1:
            return None
        value = values[0]
        if type(value) is self._qt.QDBusVariant:
            value = value.variant()
        if type(value) is str:
            return value
        if type(value) is dict:
            return {key: item for key, item in value.items()
                    if key in ('xesam:title', 'xesam:artist', 'xesam:album')
                    and (type(item) is str or (type(item) is list and all(type(part) is str for part in item)))}
        return None


class SessionBusReader:
    """Explicit opt-in boundary; transport creation and reads stay on the calling worker."""

    def __init__(self, *, enabled: bool = False,
                 transport_factory: Callable[[], BusTransport] = QtSessionBus,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self._enabled = enabled
        self._factory = transport_factory
        self._clock = clock

    def read(self) -> tuple[PlayerSample, ...]:
        if not self._enabled:
            return ()
        try:
            transport = self._factory()
        except (ImportError, RuntimeError):
            return ()
        deadline = self._clock() + SCAN_SECONDS

        def remaining() -> int:
            return max(0, min(CALL_MILLISECONDS, int((deadline - self._clock()) * 1000)))

        samples: list[PlayerSample] = []
        names = sorted(name for name in transport.names(remaining()) if name.startswith(BUS_PREFIX))
        for service in names[:MAX_PLAYERS]:
            timeout = remaining()
            if not timeout:
                break
            status = transport.get(service, PLAYER_INTERFACE, 'PlaybackStatus', timeout)
            if type(status) is not str:
                continue
            try:
                playback = Playback(status)
            except ValueError:
                continue
            timeout = remaining()
            if not timeout:
                break
            metadata = transport.get(service, PLAYER_INTERFACE, 'Metadata', timeout)
            if not isinstance(metadata, Mapping):
                continue
            title = metadata.get('xesam:title', '')
            if type(title) is not str or not clean_text(title):
                continue
            timeout = remaining()
            if not timeout:
                break
            identity = transport.get(service, ROOT_INTERFACE, 'Identity', timeout)
            artist = metadata.get('xesam:artist', [])
            album = metadata.get('xesam:album', '')
            samples.append(PlayerSample(service, playback, Track(
                clean_text(identity) if type(identity) is str else '', clean_text(title),
                clean_text(', '.join(clean_text(item) for item in artist[:16])) if type(artist) is list and all(type(item) is str for item in artist) else '',
                clean_text(album) if type(album) is str else '',
            )))
        return tuple(samples)
