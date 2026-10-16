"""Shared deterministic lightning event test used by both scene and audio."""
from __future__ import annotations


def is_lightning_visible(elapsed: float, events: tuple[tuple[float, float, float], ...] | list[tuple[float, float, float]],
                         *, reduce_motion: bool = False) -> bool:
    """Use the same event phase and reduced-motion cadence as the visible flash renderer."""
    for index, (offset, period, _x) in enumerate(events):
        if reduce_motion and index % 2:
            continue
        if (elapsed + offset) % period < (.12 if reduce_motion else .2):
            return True
    return False
