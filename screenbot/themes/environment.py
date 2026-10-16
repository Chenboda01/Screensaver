"""Immutable Live Sky inputs and frame dimensions for independent theme renderers."""
from dataclasses import dataclass, field
from typing import Protocol

from PyQt6.QtGui import QPainter

from live_sky import SkyPosition, Weather


@dataclass(frozen=True, slots=True)
class ThemeEnvironment:
    """Snapshot of astronomy and weather needed by one theme frame."""

    live_sky_enabled: bool = False
    sky: SkyPosition | None = None
    weather: Weather = field(default_factory=Weather)
    manual_surface_precipitation: bool = False


@dataclass(frozen=True, slots=True)
class ThemeFrame:
    """Dimensions, time, and conditions shared by one offscreen theme render."""

    width: int
    height: int
    elapsed: float
    environment: ThemeEnvironment
    motion_scale: float = 1.0

    @property
    def bounded_motion_scale(self) -> float:
        """Keep renderer work within the documented zero-to-one effect budget."""
        return min(1.0, max(0.0, self.motion_scale))


class ThemeModule(Protocol):
    """Contract shared by the isolated theme renderer modules."""

    def draw_background(self, painter: QPainter, frame: ThemeFrame) -> None: ...

    def draw_motion(self, painter: QPainter, frame: ThemeFrame) -> None: ...
