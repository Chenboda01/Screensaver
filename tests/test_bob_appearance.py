"""Bob appearance settings validation, Unicode handling, and caption rendering."""
import configparser
import os

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtWidgets import QApplication

from bobos import BobOSPhase
from bobos import BobOSStatus
from screenbot.appearance import (
    ACCESSORIES,
    DEFAULT_PALETTE,
    PRESET_COLORS,
    BobAppearance,
    MAX_NAME_GRAPHEMES,
    sanitize_bob_name,
)
from screenbot.bob import BobRenderer


@pytest.fixture(scope='module')
def app() -> QApplication:
    return QApplication.instance() or QApplication([])


def settings_with(**values: str) -> configparser.ConfigParser:
    settings = configparser.ConfigParser()
    settings['Screensaver'] = values
    return settings


def test_missing_settings_keep_original_default_appearance_and_do_not_mutate_config() -> None:
    settings = settings_with(theme='forest')
    before = dict(settings['Screensaver'])

    appearance = BobAppearance.from_settings(settings)

    assert appearance == BobAppearance()
    assert appearance.palette() == DEFAULT_PALETTE
    assert dict(settings['Screensaver']) == before


def test_all_color_presets_derive_consistent_highlights() -> None:
    for preset in PRESET_COLORS:
        appearance = BobAppearance(color_preset=preset)
        palette = appearance.palette()
        if preset != 'cyan':
            assert palette['glow'] == appearance.accent_rgb()
            assert max(palette['outline']) >= max(palette['glow'])
            assert max(palette['eyes']) >= max(palette['outline'])
        assert palette['face'] == DEFAULT_PALETTE['face']
        assert palette['face_inset'] == DEFAULT_PALETTE['face_inset']


def test_custom_color_is_validated_and_raised_to_visible_brightness() -> None:
    appearance = BobAppearance(color_preset='custom', custom_color='#001122')
    assert max(appearance.accent_rgb()) >= 150
    assert len(appearance.palette()['eyes']) == 3

    parsed = BobAppearance.from_settings(settings_with(
        bob_color_preset='custom', bob_custom_color='not-a-color',
        bob_accessory='unknown', bob_name='\u202e',
    ))
    assert parsed.color_preset == 'custom'
    assert parsed.custom_color == PRESET_COLORS['cyan']
    assert parsed.accessory == 'none'
    assert parsed.name == 'Bob'


def test_accessory_values_are_an_allowlisted_composable_layer() -> None:
    for accessory in ACCESSORIES:
        parsed = BobAppearance.from_settings(settings_with(bob_accessory=accessory))
        assert parsed.accessory == accessory
    assert BobAppearance.from_settings(settings_with(bob_accessory='../../command')).accessory == 'none'


def _bob_image(appearance: BobAppearance, phase: BobOSPhase) -> QImage:
    class Renderer(BobRenderer):
        def __init__(self) -> None:
            self.bob_appearance = appearance
            self.phone_enabled = False

    image = QImage(640, 360, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    renderer = Renderer()
    BobRenderer.bob(renderer, painter, 640, 360, 4.25, BobOSStatus(phase, 0.0))
    painter.end()
    return image


@pytest.mark.parametrize('phase', [
    BobOSPhase.EXPLORING, BobOSPhase.PHONE_ACTIVATION, BobOSPhase.TERMINAL,
    BobOSPhase.GAMES, BobOSPhase.RETURN,
])
def test_selected_color_changes_bob_in_representative_animation_phases(phase: BobOSPhase) -> None:
    default = _bob_image(BobAppearance(), phase)
    purple = _bob_image(BobAppearance(color_preset='purple'), phase)
    assert default != purple


@pytest.mark.parametrize('accessory', sorted(ACCESSORIES - {'none'}))
def test_custom_accessory_is_a_separate_visible_layer(accessory: str) -> None:
    default = _bob_image(BobAppearance(), BobOSPhase.EXPLORING)
    customized = _bob_image(BobAppearance(accessory=accessory), BobOSPhase.EXPLORING)
    assert customized != default


def test_name_cap_preserves_unicode_graphemes_and_removes_controls() -> None:
    astronaut = '👩\u200d🚀'
    value = (astronaut * 18) + '\u202e\n  Élodie\u0301'
    result = sanitize_bob_name(value)
    assert result == astronaut * MAX_NAME_GRAPHEMES
    assert '\u202e' not in result and '\n' not in result
    assert sanitize_bob_name('   ') == 'Bob'
    assert sanitize_bob_name('🇺🇸' * 17) == '🇺🇸' * MAX_NAME_GRAPHEMES


def test_caption_draws_sanitized_display_name_without_renaming_bobos(app, monkeypatch) -> None:
    del app
    texts: list[str] = []
    original = QPainter.drawText

    def record_text(painter, *args):
        if args and isinstance(args[-1], str):
            texts.append(args[-1])
        return original(painter, *args)

    monkeypatch.setattr(QPainter, 'drawText', record_text)
    image = QImage(640, 360, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    renderer = type('CaptionContext', (), {
        'bob_appearance': BobAppearance(name='Pixel👾'),
        'theme': 'forest',
    })()
    BobRenderer.caption(renderer, painter, 640, 360, 1.0, BobOSPhase.EXPLORING)
    BobRenderer.caption(renderer, painter, 640, 360, 1.0, BobOSPhase.PHONE_ACTIVATION)
    painter.end()

    assert 'Pixel👾 is exploring the forest…' in texts
    assert 'Pixel👾 is waking up his phone…' in texts
    assert 'BobOS' not in texts
