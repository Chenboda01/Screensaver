"""Share deliberate-motion detection across a preview's display windows."""
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import QPointF
from PyQt6.QtWidgets import QApplication

if TYPE_CHECKING:
    from screenbot.app import Saver


class PreviewMotion:
    """Remember the first post-grace pointer position for a preview session."""

    def __init__(self, started_at: float) -> None:
        self.started_at = started_at
        self.origin: QPointF | None = None

    def should_close(self, position: QPointF, now: float) -> bool:
        if now - self.started_at < 1.5:
            return False
        if self.origin is None:
            self.origin = position
            return False
        return (position - self.origin).manhattanLength() > 12


def session_motion(window: Saver, started_at: float) -> PreviewMotion:
    """Join an already visible preview so crossing displays retains its anchor."""
    from screenbot.app import Saver

    return next((
        other.preview_motion for other in QApplication.topLevelWidgets()
        if isinstance(other, Saver) and other is not window
        and other.is_preview and other.isVisible()
    ), PreviewMotion(started_at))
