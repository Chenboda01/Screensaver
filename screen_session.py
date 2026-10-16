"""Coordinate display windows around one shared Saver scene and timeline."""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

from PyQt6.QtCore import QEvent, QObject, Qt, QTimer
from PyQt6.QtGui import QCursor, QMouseEvent, QPaintEvent, QPainter, QScreen
from PyQt6.QtWidgets import QApplication, QWidget

if TYPE_CHECKING:
    from screensaver import Saver


class SceneryWindow(QWidget):
    """Draw the owner's scenery without creating weather, BobOS, or lock state."""

    def __init__(self, scene: Saver) -> None:
        super().__init__()
        self.scene = scene
        self.setWindowTitle('ScreenBot Screensaver — Scenery')
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.BlankCursor)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.scene.draw_scenery(painter, self.width(), self.height(),
                                time.monotonic() - self.scene.start_time)
        painter.end()


class ScreenSession(QObject):
    """Own mutable display membership; one Saver owns all simulation state."""

    def __init__(self, app: QApplication, scene: Saver) -> None:
        super().__init__(app)
        self.app = app
        self.scene = scene
        self.windows: dict[QScreen, QWidget] = {}
        self.observed_screens: set[QScreen] = set()
        self.stopping = False
        self.mouse_origin = QCursor.pos()

    def start(self) -> None:
        """Cover every output, selecting its Wayland target before mapping."""
        self.app.screenAdded.connect(self.screen_added)
        self.app.screenRemoved.connect(self.screen_removed)
        self.app.primaryScreenChanged.connect(self.sync_screens)
        self.app.aboutToQuit.connect(self.stop)
        for screen in self.app.screens():
            self.observe_screen(screen)
        self.sync_screens()
        self.scene.activateWindow()

    def observe_screen(self, screen: QScreen) -> None:
        self.observed_screens.add(screen)
        screen.geometryChanged.connect(self.schedule_sync)

    def schedule_sync(self) -> None:
        """Wait for Qt to finish applying a screen geometry or scale change."""
        QTimer.singleShot(0, self.sync_screens)

    def screen_added(self, screen: QScreen) -> None:
        self.observe_screen(screen)
        self.sync_screens()

    def screen_removed(self, screen: QScreen) -> None:
        screen.geometryChanged.disconnect(self.schedule_sync)
        self.observed_screens.discard(screen)
        self.sync_screens(excluded=screen)

    def sync_screens(self, *, excluded: QScreen | None = None) -> None:
        """Keep one window per distinct screen geometry, including mirrors."""
        if self.stopping:
            return
        screens = [screen for screen in self.app.screens() if screen is not excluded]
        primary = self.app.primaryScreen()
        screens.sort(key=lambda screen: screen is not primary)
        distinct: list[QScreen] = []
        for screen in screens:
            if all(screen.geometry() != other.geometry() for other in distinct):
                distinct.append(screen)
        if not distinct:
            self.stop()
            self.app.quit()
            return
        primary = distinct[0]
        for screen, window in list(self.windows.items()):
            if screen not in distinct or (window is self.scene) != (screen is primary):
                window.removeEventFilter(self)
                del self.windows[screen]
                if window is not self.scene:
                    self.scene.timer.timeout.disconnect(window.update)
                    window.close()
                    window.deleteLater()
        for screen in distinct:
            if screen not in self.windows:
                window = self.scene if screen is primary else SceneryWindow(self.scene)
                self.windows[screen] = window
                window.installEventFilter(self)
                if window is not self.scene:
                    self.scene.timer.timeout.connect(window.update)
                window.setScreen(screen)
                window.setGeometry(screen.geometry())
                window.showFullScreen()
            else:
                window = self.windows[screen]
                if window.size() != screen.size():
                    # Remap so Wayland supplies a new fullscreen configure at the new scale.
                    window.hide()
                    window.setScreen(screen)
                    window.setGeometry(screen.geometry())
                    window.showFullScreen()
                else:
                    window.setGeometry(screen.geometry())

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if self.stopping:
            return False
        if event.type() in (QEvent.Type.KeyPress, QEvent.Type.MouseButtonPress,
                            QEvent.Type.Wheel, QEvent.Type.Close):
            self.stop()
            self.app.quit()
            return True
        if isinstance(event, QMouseEvent) and event.type() == QEvent.Type.MouseMove:
            position = event.globalPosition().toPoint()
            moved = (position - self.mouse_origin).manhattanLength() > 5
            if time.monotonic() - self.scene.start_time > 1.5 and moved:
                self.stop()
                self.app.quit()
            return True
        return super().eventFilter(watched, event)

    def stop(self) -> None:
        """Close all outputs together, also when the one lock request succeeds."""
        if self.stopping:
            return
        self.stopping = True
        self.app.screenAdded.disconnect(self.screen_added)
        self.app.screenRemoved.disconnect(self.screen_removed)
        self.app.primaryScreenChanged.disconnect(self.sync_screens)
        self.app.aboutToQuit.disconnect(self.stop)
        for screen in self.observed_screens:
            screen.geometryChanged.disconnect(self.schedule_sync)
        self.observed_screens.clear()
        self.scene.timer.stop()
        for window in self.windows.values():
            window.removeEventFilter(self)
            window.close()
