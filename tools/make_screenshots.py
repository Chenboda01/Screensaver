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
import tempfile
import time
from typing import Final
from unittest.mock import patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"
ROOT: Final = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image, ImageDraw
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


def make_saver(theme: str, *, bobos: bool = False, photo_folder: Path | None = None,
               photo_fit: str = "fill") -> Saver:
    """Use isolated settings with networking, locking, and the clock disabled."""
    settings = configparser.ConfigParser()
    settings["Screensaver"] = {
        "theme": theme, "show_clock": "false", "password_lock": "false",
        "live_sky_enabled": "false", "bobos_enabled": "false",
    }
    if photo_folder is not None:
        settings["Screensaver"]["photo_folder"] = str(photo_folder)
    settings["Screensaver"]["photo_fit"] = photo_fit
    with patch("screenbot.app.read_settings", return_value=settings), \
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


def create_demo_photos(folder: Path) -> None:
    """Create non-private local sample images for the gallery capture."""
    palette = ((239, 137, 89), (183, 112, 73), (98, 155, 143))
    for index, sky in enumerate(palette):
        image = Image.new("RGB", (1200, 800))
        pixels = image.load()
        for y in range(image.height):
            amount = y / max(1, image.height - 1)
            if index == 0 and y >= 440:
                sea = (34, 109, 142)
                amount_sea = (y - 440) / 360
                color = tuple(round(channel * (1 - amount_sea * .5) + 10 * amount_sea * .5)
                              for channel in sea)
            else:
                color = tuple(round(channel * (1 - amount * .45) + 22 * amount * .45) for channel in sky)
            for x in range(image.width):
                pixels[x, y] = color
        draw = ImageDraw.Draw(image)
        if index == 0:
            draw.ellipse((835, 210, 1015, 390), fill=(255, 226, 159))
            for row in range(10):
                y = 480 + row * 28
                draw.line((90 + row * 12, y, 1120 - row * 16, y),
                          fill=(74, 148 + row * 4, 159 + row * 3), width=4)
            draw.polygon([(0, 660), (210, 620), (410, 690), (650, 642),
                          (850, 705), (1200, 650), (1200, 800), (0, 800)],
                         fill=(19, 55, 66))
        elif index == 1:
            draw.ellipse((900, 120, 1040, 260), fill=(255, 219, 156))
            draw.polygon([(0, 540), (250, 400), (500, 525), (770, 365),
                          (1040, 515), (1200, 430), (1200, 800), (0, 800)],
                         fill=(141, 79, 55))
            draw.polygon([(0, 655), (310, 520), (620, 700), (940, 510),
                          (1200, 650), (1200, 800), (0, 800)], fill=(199, 128, 77))
        else:
            draw.ellipse((880, 105, 1010, 235), fill=(255, 230, 186))
            draw.rectangle((0, 520, 1200, 800), fill=(35, 82, 88))
            for tree_x, tree_height in ((120, 330), (330, 250), (890, 310), (1080, 370)):
                draw.rectangle((tree_x, 520 - tree_height // 3, tree_x + 22, 720), fill=(23, 55, 58))
                draw.ellipse((tree_x - 90, 520 - tree_height, tree_x + 115, 560), fill=(30, 91, 78))
        image.save(folder / f"sample-{index + 1}.jpg", quality=90)


def main() -> None:
    """Regenerate every README gallery image from the current source tree."""
    app = QApplication([])
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for theme in ("space", "mountains", "snow", "forest", "city", "aurora", "ocean", "desert", "underwater"):
        saver = make_saver(theme)
        if theme == "aurora":
            set_sky(saver, "2024-03-10T03:00:00")
        capture(saver, 5).save(OUTPUT / f"{theme}.webp", lossless=True)
        saver.close()

    with tempfile.TemporaryDirectory(prefix="screenbot-gallery-photos-") as temporary:
        folder = Path(temporary)
        create_demo_photos(folder)
        saver = make_saver("photos", photo_folder=folder)
        deadline = time.monotonic() + 5
        while (saver.photo_slideshow is not None
               and saver.photo_slideshow._current_image is None
               and time.monotonic() < deadline):
            app.processEvents()
            saver.update()
            time.sleep(.005)
        if saver.photo_slideshow is None or saver.photo_slideshow._current_image is None:
            raise RuntimeError("The local demo photos did not decode for the gallery capture.")
        capture(saver, 5).save(OUTPUT / "my-photos.webp", lossless=True)
        saver.close()

        portrait_folder = folder / "portrait"
        portrait_folder.mkdir()
        portrait = Image.new("RGB", (800, 1200), (30, 90, 130))
        portrait_draw = ImageDraw.Draw(portrait)
        portrait_draw.rectangle((0, 0, 799, 250), fill=(245, 157, 103))
        portrait_draw.ellipse((510, 105, 670, 265), fill=(255, 226, 159))
        portrait_draw.polygon([(0, 770), (180, 560), (380, 790), (580, 510),
                               (800, 740), (800, 1200), (0, 1200)], fill=(25, 65, 75))
        portrait_draw.polygon([(0, 920), (240, 740), (450, 980), (650, 720),
                               (800, 900), (800, 1200), (0, 1200)], fill=(40, 115, 120))
        portrait.save(portrait_folder / "portrait.jpg", quality=94)
        saver = make_saver("photos", photo_folder=portrait_folder, photo_fit="fit-blur")
        deadline = time.monotonic() + 5
        while (saver.photo_slideshow is not None
               and saver.photo_slideshow._current_image is None
               and time.monotonic() < deadline):
            app.processEvents()
            saver.update()
            time.sleep(.005)
        if saver.photo_slideshow is None or saver.photo_slideshow._current_image is None:
            raise RuntimeError("The local portrait did not decode for the fit gallery capture.")
        capture(saver, 5).save(OUTPUT / "my-photos-fit.webp", lossless=True)
        saver.close()

        missing_folder = folder / "missing-user-folder"
        saver = make_saver("photos", photo_folder=missing_folder)
        deadline = time.monotonic() + 5
        while (saver.photo_slideshow is not None
               and saver.photo_slideshow.message == "Loading photos…"
               and time.monotonic() < deadline):
            app.processEvents()
            saver.update()
            time.sleep(.005)
        capture(saver, 5).save(OUTPUT / "my-photos-fallback.webp", lossless=True)
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
