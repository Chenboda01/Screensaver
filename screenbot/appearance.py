"""Validated, user-configurable appearance values for Bob."""
from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata
from typing import Final

Rgb: type = tuple[int, int, int]

# These exact values are the original renderer's cyan design. Keep this mapping
# explicit so an unset/legacy configuration remains pixel-identical.
DEFAULT_PALETTE: Final[dict[str, Rgb]] = {
    'glow': (41, 212, 255),
    'outline': (102, 223, 255),
    'face_outline': (115, 220, 255),
    'eyes': (107, 246, 255),
    'halo_detail': (120, 220, 255),
    'antenna': (178, 249, 255),
    'ear_piece': (31, 84, 130),
    'face': (18, 53, 95),
    'face_inset': (8, 27, 60),
    'screen_glint': (102, 217, 255),
    'cheek': (107, 246, 255),
}

PRESET_COLORS: Final[dict[str, str]] = {
    'cyan': '#6bf6ff',
    'green': '#72f59a',
    'purple': '#c692ff',
    'orange': '#ffac57',
    'pink': '#ff83c7',
    'gold': '#ffd15c',
}
ACCESSORIES: Final[frozenset[str]] = frozenset({
    'none', 'cap', 'bow-tie', 'headphones', 'flower', 'crown', 'antenna-ball',
})
CUSTOM_COLOR_RE: Final[re.Pattern[str]] = re.compile(r'^#[0-9a-fA-F]{6}$')
MAX_NAME_GRAPHEMES: Final[int] = 16


def _is_variation_selector(char: str) -> bool:
    value = ord(char)
    return 0xFE00 <= value <= 0xFE0F or 0xE0100 <= value <= 0xE01EF


def _is_emoji_modifier(char: str) -> bool:
    return 0x1F3FB <= ord(char) <= 0x1F3FF


def _is_regional_indicator(char: str) -> bool:
    return 0x1F1E6 <= ord(char) <= 0x1F1FF


def _graphemes(text: str) -> list[str]:
    """Group combining marks, emoji joins/modifiers, and flag pairs safely."""
    clusters: list[str] = []
    for char in text:
        if (unicodedata.category(char).startswith('M') or _is_variation_selector(char)
                or _is_emoji_modifier(char) or char == '\u200d'):
            if clusters and len(clusters[-1]) < 16:
                clusters[-1] += char
            elif char != '\u200d':
                clusters.append(char)
        elif clusters and clusters[-1].endswith('\u200d'):
            if len(clusters[-1]) < 16:
                clusters[-1] += char
            else:
                clusters.append(char)
        elif _is_regional_indicator(char) and clusters and len(clusters[-1]) == 1 and _is_regional_indicator(clusters[-1]):
            clusters[-1] += char
        else:
            clusters.append(char)
    return clusters


def sanitize_bob_name(value: object) -> str:
    """Return short plain text, removing controls and directional overrides."""
    raw = (str(value) if value is not None else '')[:1024]
    safe: list[str] = []
    for char in raw:
        category = unicodedata.category(char)
        if char in '\r\n\t':
            safe.append(' ')
        elif char == '\u200d':
            safe.append(char)
        elif category in ('Cc', 'Cf', 'Cs'):
            continue
        else:
            safe.append(char)
    normalized = ' '.join(''.join(safe).split()).strip()
    clusters = _graphemes(normalized)
    result = ''.join(clusters[:MAX_NAME_GRAPHEMES]).strip()
    return result or 'Bob'


def _validated_rgb(value: object) -> Rgb | None:
    if not isinstance(value, str) or not CUSTOM_COLOR_RE.fullmatch(value.strip()):
        return None
    text = value.strip()
    return tuple(int(text[index:index + 2], 16) for index in (1, 3, 5))  # type: ignore[return-value]


def _accessible_rgb(rgb: Rgb) -> Rgb:
    """Raise very dark colors to a legible lightness without changing their hue."""
    red, green, blue = rgb
    brightness = max(red, green, blue)
    if brightness >= 150:
        return rgb
    factor = 150 / max(brightness, 1)
    return tuple(min(255, round(channel * factor)) for channel in rgb)  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class BobAppearance:
    name: str = 'Bob'
    color_preset: str = 'cyan'
    custom_color: str = '#6bf6ff'
    accessory: str = 'none'

    @classmethod
    def from_settings(cls, settings) -> 'BobAppearance':
        """Read known settings defensively; unknown values use original defaults."""
        section = 'Screensaver'
        name = sanitize_bob_name(settings.get(section, 'bob_name', fallback='Bob'))
        preset = settings.get(section, 'bob_color_preset', fallback='cyan').strip().lower()
        if preset not in {*PRESET_COLORS, 'custom'}:
            preset = 'cyan'
        custom = settings.get(section, 'bob_custom_color', fallback=PRESET_COLORS['cyan']).strip()
        if _validated_rgb(custom) is None:
            custom = PRESET_COLORS['cyan']
        accessory = settings.get(section, 'bob_accessory', fallback='none').strip().lower()
        if accessory not in ACCESSORIES:
            accessory = 'none'
        return cls(name=name, color_preset=preset, custom_color=custom.lower(), accessory=accessory)

    def accent_rgb(self) -> Rgb:
        color = self.custom_color if self.color_preset == 'custom' else PRESET_COLORS[self.color_preset]
        return _accessible_rgb(_validated_rgb(color) or _validated_rgb(PRESET_COLORS['cyan']))

    def palette(self) -> dict[str, Rgb]:
        """Resolve all related highlights while preserving original cyan pixels."""
        if self.color_preset == 'cyan':
            return dict(DEFAULT_PALETTE)
        red, green, blue = self.accent_rgb()
        # Slightly brighten outline/eyes while maintaining one consistent hue.
        outline = tuple(min(255, round(channel * 1.05 + 8)) for channel in (red, green, blue))
        eyes = tuple(min(255, round(channel * 1.1 + 8)) for channel in (red, green, blue))
        return {
            **DEFAULT_PALETTE,
            'glow': (red, green, blue),
            'outline': outline, 'face_outline': outline, 'eyes': eyes,
            'halo_detail': tuple(round(channel * .8 + 255 * .2) for channel in (red, green, blue)),
            'antenna': tuple(round(channel * .65 + 255 * .35) for channel in (red, green, blue)),
            'screen_glint': (red, green, blue), 'cheek': eyes,
        }
