from collections.abc import Callable
from typing import Final

from screenbot.themes import aurora, desert, ocean, underwater
from screenbot.themes.city import CityTheme
from screenbot.themes.forest import ForestTheme
from screenbot.themes.mountains import MountainsTheme
from screenbot.themes.snow import SnowTheme
from screenbot.themes.space import SpaceTheme

ThemeRenderer = Callable[..., None]
THEME_RENDERERS: Final[dict[str, ThemeRenderer]] = {
    'space': lambda scene, painter, width, height, _elapsed: SpaceTheme.space_background(
        scene, painter, width, height
    ),
    'mountains': MountainsTheme.mountains_background,
    'snow': SnowTheme.snow_background,
    'forest': ForestTheme.forest_background,
    'city': CityTheme.city,
    'aurora': lambda scene, painter, width, height, elapsed: aurora.draw_background(
        painter, scene.theme_frame(width, height, elapsed)
    ),
    'ocean': lambda scene, painter, width, height, elapsed: ocean.draw_background(
        painter, scene.theme_frame(width, height, elapsed)
    ),
    'desert': lambda scene, painter, width, height, elapsed: desert.draw_background(
        painter, scene.theme_frame(width, height, elapsed)
    ),
    'underwater': lambda scene, painter, width, height, elapsed: underwater.draw_background(
        painter, scene.theme_frame(width, height, elapsed)
    ),
}

THEME_MOTION_RENDERERS: Final[dict[str, Callable[..., None]]] = {
    'aurora': lambda scene, painter, width, height, elapsed: aurora.draw_motion(
        painter, scene.theme_frame(width, height, elapsed)
    ),
    'ocean': lambda scene, painter, width, height, elapsed: ocean.draw_motion(
        painter, scene.theme_frame(width, height, elapsed)
    ),
    'desert': lambda scene, painter, width, height, elapsed: desert.draw_motion(
        painter, scene.theme_frame(width, height, elapsed)
    ),
    'underwater': lambda scene, painter, width, height, elapsed: underwater.draw_motion(
        painter, scene.theme_frame(width, height, elapsed)
    ),
}
