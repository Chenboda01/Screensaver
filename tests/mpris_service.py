# /// script
# requires-python = ">=3.11"
# dependencies = ["PyQt6"]
# ///
# Run: dbus-run-session -- python tests/mpris_service.py
"""A local synthetic MPRIS player for isolated session-bus integration checks."""
import sys
import json
import os
from pathlib import Path
from threading import Event
from typing import Final

from PyQt6.QtCore import QCoreApplication, QObject, pyqtClassInfo, pyqtProperty
from PyQt6.QtDBus import QDBusAbstractAdaptor, QDBusConnection


def fixture_value(key: str, default: str) -> str:
    """The test alone may change this synthetic service's local fixture state."""
    state = os.environ.get('SCREENBOT_MPRIS_FIXTURE')
    return str(json.loads(Path(state).read_text()).get(key, default)) if state else default


@pyqtClassInfo('D-Bus Interface', 'org.mpris.MediaPlayer2')
class Root(QDBusAbstractAdaptor):
    @pyqtProperty(str)
    def Identity(self) -> str:
        return 'Synthetic player'


@pyqtClassInfo('D-Bus Interface', 'org.mpris.MediaPlayer2.Player')
class Player(QDBusAbstractAdaptor):
    @pyqtProperty(str)
    def PlaybackStatus(self) -> str:
        return fixture_value('status', 'Playing')

    @pyqtProperty('QVariantMap')
    def Metadata(self) -> dict[str, str | list[str]]:
        return {'xesam:title': fixture_value('title', 'Synthetic song'), 'xesam:artist': ['Synthetic artist'],
                'xesam:album': 'Synthetic album', 'xesam:url': 'file:///private/sentinel',
                'mpris:artUrl': 'https://private.invalid/sentinel'}


APP: Final = QCoreApplication(sys.argv[:1])
BUS: Final = QDBusConnection.sessionBus()
NODE: Final = QObject()
ROOT: Final = Root(NODE)
PLAYER: Final = Player(NODE)
assert BUS.registerService('org.mpris.MediaPlayer2.screenbot_test')
assert BUS.registerObject('/org/mpris/MediaPlayer2', NODE, QDBusConnection.RegisterOption.ExportAdaptors)
print('READY', flush=True)
if '--unresponsive' in sys.argv:
    Event().wait()
raise SystemExit(APP.exec())
