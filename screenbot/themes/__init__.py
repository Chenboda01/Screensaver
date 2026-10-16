from typing import Callable, Final

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
}
