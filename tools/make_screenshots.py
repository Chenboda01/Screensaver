#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["PyQt6==6.11.0", "Pillow==12.3.0"]
# ///
# ─── How to run ───
# Install uv: curl -LsSf https://astral.sh/uv/install.sh | sh
# Run: uv run tools/make_screenshots.py
# Or use Python 3 with PyQt6 and Pillow already installed.
# ──────────────────
"""Capture the production Saver widget; never launch a session or fetch weather."""
from __future__ import annotations

import configparser
from datetime import datetime, timezone
import os
from pathlib import Path
import random
import sys
from typing import Final
from unittest.mock import patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"
ROOT: Final = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image
from PIL.ImageQt import fromqimage
from PyQt6.QtCore import QDateTime, Qt
from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import QApplication

from live_sky import Weather, sky_position
from screensaver import Saver

OUTPUT: Final = ROOT / "assets" / "screenshots"
RANDOM: Final = random.Random


def seeded_random(seed: int | None = None) -> random.Random:
    """Keep production particle layouts repeatable, including explicit seeds."""
    return RANDOM(22 if seed is None else seed)


def make_saver(theme: str, *, bobos: bool = False) -> Saver:
    """Use isolated settings with networking, locking, and the clock disabled."""
    settings = configparser.ConfigParser()
    settings["Screensaver"] = {
        "theme": theme, "show_clock": "false", "password_lock": "false",
        "live_sky_enabled": "false", "bobos_enabled": "false",
    }
    with patch("screensaver.read_settings", return_value=settings), \
         patch("screensaver.random.Random", side_effect=seeded_random), \
         patch("screensaver.time.monotonic", return_value=0.):
        saver = Saver(preview_bobos=bobos)
        saver.timer.stop()
        saver.resize(1280, 720)
        saver.show()
    return saver


def capture(saver: Saver, elapsed: float) -> Image.Image:
    """Render a full production paintEvent at a specified animation time."""
    image = QImage(1280, 720, QImage.Format.Format_ARGB32)
    with patch("screensaver.time.monotonic", return_value=elapsed), \
         patch("screensaver.time.time", return_value=saver.live_sky_sample_time), \
         patch("screensaver.QDateTime.currentDateTime", return_value=QDateTime.fromString(
             "2024-03-25T19:30:00Z", Qt.DateFormat.ISODate)):
        saver.render(image)
    return fromqimage(image).convert("RGB")


def set_sky(saver: Saver, instant: str, weather: Weather = Weather()) -> None:
    """Feed calculated Boston astronomy and a fixed weather sample to the renderer."""
    now = datetime.fromisoformat(instant).replace(tzinfo=timezone.utc)
    saver.live_sky_enabled = True
    saver.live_sky_sample_time = now.timestamp()
    saver.live_sky_position = sky_position(now, 42.36, -71.06)
    saver.live_weather.latitude, saver.live_weather.longitude = 42.36, -71.06
    saver.live_weather.located = True
    saver.live_weather.observation = weather
    saver.live_weather.observed_at = now.timestamp()


def save_animation(saver: Saver, name: str, start: float) -> None:
    """Encode six seconds of actual animation at 10 fps in a looping GIF."""
    frames = [capture(saver, start + frame / 10).resize(
        (768, 432), Image.Resampling.LANCZOS) for frame in range(60)]
    frames[0].save(OUTPUT / name, save_all=True, append_images=frames[1:],
                   duration=100, loop=0, optimize=True)


def main() -> None:
    """Regenerate every README gallery image from the current source tree."""
    app = QApplication([])
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for theme in ("space", "mountains", "snow", "forest", "city"):
        saver = make_saver(theme)
        capture(saver, 5).save(OUTPUT / f"{theme}.webp", lossless=True)
        saver.close()

    saver = make_saver("mountains")
    for label, instant in (
        ("sunrise", "2024-03-25T10:40:00"),
        ("noon", "2024-03-25T16:45:00"),
        ("sunset", "2024-03-25T23:00:00"),
        ("moonlight", "2024-03-25T03:00:00"),
    ):
        set_sky(saver, instant)
        capture(saver, 5).save(OUTPUT / f"live-sky-{label}.webp", lossless=True)
    save_animation(saver, "bob-moonlight.gif", 0)
    set_sky(saver, "2024-03-25T16:45:00", Weather(63, 85, 4, 12, 9))
    capture(saver, 5).save(OUTPUT / "live-sky-rain.webp", lossless=True)
    saver.close()

    saver = make_saver("space", bobos=True)
    capture(saver, 9).save(OUTPUT / "bobos.webp", lossless=True)
    save_animation(saver, "bobos-phone.gif", 6)
    saver.close()
    app.quit()
    for path in sorted(OUTPUT.iterdir()):
        if path.suffix in (".webp", ".gif"):
            print(f"{path.relative_to(ROOT)}: {path.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
