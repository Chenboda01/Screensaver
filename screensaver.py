#!/usr/bin/env python3
"""ScreenBot screensaver V22 compatibility facade and command-line entrypoint."""
import configparser
import random
import subprocess
import sys
import time
from pathlib import Path
from typing import Final

from PyQt6.QtCore import QCommandLineOption, QCommandLineParser, QDateTime, QPointF, QRect, QRectF, QSettings, Qt, QTimer
from PyQt6.QtGui import QColor, QCursor, QFont, QImage, QLinearGradient, QPainter, QPen, QPolygonF, QRadialGradient, QShowEvent
from PyQt6.QtWidgets import QApplication, QWidget

from live_sky import SkyPosition, sky_position
from live_sky_network import LiveWeather, read_location_setting
from live_sky_render import SpaceSky, draw_sky
from bobos import BobOSPhase, BobOSStatus, BobOSTimeline, bobos_may_run
from screen_session import ScreenSession
from screenbot.app import Saver
from screenbot.burnin import BURN_IN_MODES, BURN_IN_SHIFT_LIMIT, burn_in_clock_drift, burn_in_dim_alpha, burn_in_scene_scale, burn_in_scene_shift, normalize_burn_in_mode
from screenbot.runtime import battery_powered, frame_interval_ms, particle_count
from screenbot.settings import CLOCK_POSITIONS, PHONE_UI_PHASES, read_settings, selected_theme

__all__ = [
    'BURN_IN_MODES', 'BURN_IN_SHIFT_LIMIT', 'BobOSPhase', 'BobOSStatus',
    'BobOSTimeline', 'CLOCK_POSITIONS', 'Final', 'LiveWeather', 'PHONE_UI_PHASES',
    'Path', 'QApplication', 'QColor', 'QCommandLineOption', 'QCommandLineParser',
    'QCursor', 'QDateTime', 'QFont', 'QImage', 'QLinearGradient', 'QPainter',
    'QPen', 'QPointF', 'QPolygonF', 'QRadialGradient', 'QRect', 'QRectF',
    'QSettings', 'QShowEvent', 'QTimer', 'QWidget', 'Qt', 'Saver',
    'ScreenSession', 'SkyPosition', 'SpaceSky',
    'battery_powered', 'bobos_may_run', 'burn_in_clock_drift',
    'burn_in_dim_alpha', 'burn_in_scene_scale', 'burn_in_scene_shift',
    'configparser', 'draw_sky', 'frame_interval_ms', 'main', 'normalize_burn_in_mode',
    'particle_count', 'random', 'read_location_setting', 'read_settings',
    'selected_theme', 'sky_position', 'subprocess', 'sys', 'time',
]

def main(arguments: list[str] | None = None) -> int:
    """Launch the screensaver or a deliberate, lock-free settings preview."""
    command_arguments = sys.argv[1:] if arguments is None else arguments
    app = QApplication(sys.argv[:1])
    parser = QCommandLineParser()
    parser.addHelpOption()
    parser.addOptions([
        QCommandLineOption('preview', 'Preview the theme without locking or starting BobOS.'),
        QCommandLineOption('preview-bobos', 'Preview the full BobOS adventure without locking.'),
        QCommandLineOption('config', 'Read temporary settings for a preview.', 'path'),
        QCommandLineOption('screen', 'Show a preview on the named display.', 'name'),
        QCommandLineOption('wifi-animation', 'Show the BobOS connection animation.'),
        QCommandLineOption('no-wifi-animation', 'Skip the BobOS connection animation.'),
    ])
    parser.process([sys.argv[0], *command_arguments])
    preview = parser.isSet('preview')
    preview_bobos = parser.isSet('preview-bobos')
    if (preview and preview_bobos) or (parser.isSet('config') and not (preview or preview_bobos)):
        parser.showHelp(2)
    if '--wifi-animation' in command_arguments:
        wifi_override = True
    elif '--no-wifi-animation' in command_arguments:
        wifi_override = False
    else:
        wifi_override = None
    try:
        saver = Saver(
            preview=preview,
            config_path=Path(parser.value('config')) if parser.isSet('config') else None,
            preview_bobos=preview_bobos,
            preview_wifi_animation=wifi_override,
        )
    except (OSError, configparser.Error, ValueError) as error:
        print(f'Could not read ScreenBot settings: {error}', file=sys.stderr)
        return 1
    if not saver.is_preview:
        session = ScreenSession(app, saver)
        session.start()
        return app.exec()
    if parser.isSet('screen'):
        for screen in app.screens():
            if screen.name() == parser.value('screen'):
                saver.setScreen(screen)
                saver.move(screen.geometry().topLeft())
                break
    saver.showFullScreen()
    saver.activateWindow()
    return app.exec()

if __name__ == '__main__':
    sys.exit(main())
