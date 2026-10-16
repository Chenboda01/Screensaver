import math
from typing import Final

BURN_IN_MODES: Final[frozenset[str]] = frozenset({'off', 'standard', 'strong'})
BURN_IN_SHIFT_LIMIT: Final[float] = 8.0

def normalize_burn_in_mode(value: str) -> str:
    """Return a supported protection mode, defaulting safely to Standard."""
    mode = value.strip().lower()
    return mode if mode in BURN_IN_MODES else 'standard'

def burn_in_scene_shift(mode: str, elapsed_seconds: float) -> tuple[float, float]:
    """Return a smooth, time-based scene offset bounded to eight logical pixels."""
    if mode == 'off':
        return 0.0, 0.0
    elapsed = max(0.0, elapsed_seconds)
    x = 5.0 * math.sin(math.tau * elapsed / 480.0) + 3.0 * math.sin(math.tau * elapsed / 197.0)
    y = 5.0 * math.sin(math.tau * elapsed / 600.0 + .8) + 3.0 * math.sin(math.tau * elapsed / 233.0)
    return x, y

def burn_in_scene_scale(width: int, height: int) -> float:
    """Scale around the center enough to cover all edges during the pixel shift."""
    shortest = max(1, min(width, height))
    # Two pixels of rasterization slack are included beyond the maximum shift.
    return 1.0 + 2.0 * (BURN_IN_SHIFT_LIMIT + 2.0) / shortest

def burn_in_clock_drift(mode: str, elapsed_seconds: float, width: int, height: int,
                        position: str, font_size: int, show_date: bool,
                        show_conditions: bool, scene_offset: tuple[float, float] = (0.0, 0.0),
                        scene_scale: float = 1.0) -> tuple[float, float]:
    """Move the clock by up to 3% while keeping its text area on-screen."""
    if mode == 'off' or width <= 0 or height <= 0:
        return 0.0, 0.0
    columns = {'left': (width * .035, width * .42),
               'center': (width * .29, width * .42),
               'right': (width * .545, width * .42)}
    rows = {'top': height * .08, 'center': height * .38, 'bottom': height * .65}
    row, column = position.split('-')
    x, area_width = columns[column]
    y = rows[row]
    area_height = font_size * 1.5
    if show_date:
        area_height += font_size * .62
    if show_conditions:
        area_height += font_size * .62

    # The whole scene is transformed first. Limit additional clock drift
    # against that mapped rectangle so corner clocks stay on-screen.
    dx, dy = scene_offset
    tx = width * (1.0 - scene_scale) * .5 + dx
    ty = height * (1.0 - scene_scale) * .5 + dy
    mapped_x = x * scene_scale + tx
    mapped_y = y * scene_scale + ty
    mapped_width = area_width * scene_scale
    mapped_height = area_height * scene_scale
    min_x = -mapped_x / scene_scale
    max_x = (width - mapped_x - mapped_width) / scene_scale
    min_y = -mapped_y / scene_scale
    max_y = (height - mapped_y - mapped_height) / scene_scale
    if max_x < min_x or max_y < min_y:
        return 0.0, 0.0

    elapsed = max(0.0, elapsed_seconds)
    desired_x = width * .03 * math.sin(math.tau * elapsed / 900.0)
    desired_y = height * .03 * math.sin(math.tau * elapsed / 1110.0)
    return (min(max(desired_x, min_x), max_x),
            min(max(desired_y, min_y), max_y))

def burn_in_dim_alpha(mode: str, elapsed_seconds: float) -> int:
    """Fade Strong mode to black between 30 and 60 unattended minutes."""
    if mode != 'strong':
        return 0
    progress = min(1.0, max(0.0, (elapsed_seconds - 30 * 60) / (30 * 60)))
    return round(255 * progress)
