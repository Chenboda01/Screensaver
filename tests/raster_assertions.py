"""Bounded raster comparison with diagnostic images for every failure."""
import os
from pathlib import Path

from PIL import Image, ImageChops
from PyQt6.QtGui import QImage


def _rgba(image: QImage) -> Image.Image:
    normalized = image.convertToFormat(QImage.Format.Format_RGBA8888)
    return Image.frombytes('RGBA', (image.width(), image.height()),
                           normalized.constBits().asstring(normalized.sizeInBytes()))


def assert_raster_equal(actual: QImage, expected: QImage, name: str, *, exact: bool = False) -> None:
    """Allow at most 0.5% changed pixels, all channels within 16; exact means zero."""
    assert not actual.isNull() and not expected.isNull(), name
    actual_rgba, expected_rgba = _rgba(actual), _rgba(expected)
    same_size = actual.size() == expected.size()
    canvas = Image.new('RGBA', actual_rgba.size)
    canvas.paste(expected_rgba)
    difference = ImageChops.difference(actual_rgba, canvas)
    channels = difference.tobytes()
    deltas = [max(channels[index:index + 4]) for index in range(0, len(channels), 4)]
    changed = sum(delta != 0 for delta in deltas)
    peak = max(deltas, default=0)
    allowed = 0 if exact else len(deltas) * .005
    if same_size and changed <= allowed and peak <= (0 if exact else 16) and (not exact or actual == expected):
        return
    directory = Path(os.environ.get('SCREENBOT_RASTER_ARTIFACTS', '.omo/evidence/raster-failures'))
    directory.mkdir(parents=True, exist_ok=True)
    stem = Path(name).stem
    actual_rgba.save(directory / f'{stem}-actual.png')
    expected_rgba.save(directory / f'{stem}-expected.png')
    # Make even low channel differences visible, including alpha-only differences.
    visible = Image.new('RGB', actual_rgba.size)
    visible.putdata([(min(255, delta * 16),) * 3 for delta in deltas])
    visible.save(directory / f'{stem}-diff.png')
    raise AssertionError(f'{name}: {changed}/{len(deltas)} changed pixels, max delta {peak}; '
                         f'same size={same_size}; artifacts: {directory}')
