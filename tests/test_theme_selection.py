"""Selection and scene integration checks for every registered world."""
import configparser
from unittest.mock import patch

import pytest

from screenbot.settings import selected_theme

THEMES = ('space', 'mountains', 'snow', 'forest', 'city', 'aurora', 'ocean', 'desert', 'underwater')
SELECTABLE_THEMES = THEMES + ('photos',)


@pytest.mark.parametrize('theme', SELECTABLE_THEMES)
def test_each_theme_can_be_selected_without_being_rewritten(theme: str) -> None:
    # Given a saved preference for one supported theme.
    settings = configparser.ConfigParser()
    settings['Screensaver'] = {'theme': theme}
    # When the screensaver resolves its selected theme.
    actual = selected_theme(settings)
    # Then the exact choice remains available.
    assert actual == theme


def test_random_selection_avoids_private_photos_until_explicitly_selected() -> None:
    # Given Random mode and a deterministic choice from its candidate list.
    settings = configparser.ConfigParser()
    settings['Screensaver'] = {'theme': 'random'}
    with patch('screenbot.settings.random.choice', side_effect=lambda choices: choices[-1]) as choose:
        # When the random theme is resolved.
        actual = selected_theme(settings)
    # Then only built-in scenes participate; private photos require explicit selection.
    assert actual == 'underwater'
    assert choose.call_args.args[0] == THEMES
