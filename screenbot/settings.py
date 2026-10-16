import configparser
import random
from pathlib import Path
from typing import Final

from PyQt6.QtCore import QSettings

from bobos import BobOSPhase
from live_sky_network import read_location_setting


def read_settings(config_path: Path | None = None) -> configparser.ConfigParser:
    settings = configparser.ConfigParser()
    path = config_path if config_path is not None else Path.home() / '.config' / 'screenbot-screensaver.ini'
    settings.read(path)
    if settings.has_section('Screensaver'):
        settings.set('Screensaver', 'live_sky_location', read_location_setting(QSettings(str(path), QSettings.Format.IniFormat)))
    return settings

def selected_theme(settings):
    selection = settings.get('Screensaver', 'theme', fallback='random').strip().lower()
    if selection not in ('random', 'space', 'mountains', 'snow', 'forest', 'city',
                         'aurora', 'ocean', 'desert', 'underwater'):
        selection = 'random'
    return random.choice(('space', 'mountains', 'snow', 'forest', 'city',
                          'aurora', 'ocean', 'desert', 'underwater')) if selection == 'random' else selection

CLOCK_POSITIONS: Final[frozenset[str]] = frozenset({
    'top-left', 'top-center', 'top-right',
    'center-left', 'center-center', 'center-right',
    'bottom-left', 'bottom-center', 'bottom-right',
})
PHONE_UI_PHASES: Final[frozenset[BobOSPhase]] = frozenset({
    BobOSPhase.HOME, BobOSPhase.BROWSER, BobOSPhase.NOTIFICATION,
    BobOSPhase.FILES, BobOSPhase.TERMINAL, BobOSPhase.GAMES,
    BobOSPhase.SETTINGS, BobOSPhase.CHAT, BobOSPhase.MAPS,
    BobOSPhase.WEATHER, BobOSPhase.CALENDAR, BobOSPhase.APP_STORE,
    BobOSPhase.SHUTDOWN,
})
