"""Runtime wiring for safe forced-date previews and local seasonal preferences."""

import configparser
from datetime import datetime
import os
from pathlib import Path
import subprocess
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtWidgets import QApplication

from screenbot.app import Saver


@pytest.fixture(scope="module")
def app() -> QApplication:
    """Initialize Qt for offscreen runtime frames."""
    return QApplication.instance() or QApplication([])


def write_settings(path: Path, values: dict[str, str]) -> None:
    """Write an isolated ScreenBot settings file for a preview scenario."""
    config = configparser.ConfigParser()
    config["Screensaver"] = values
    with path.open("w", encoding="utf-8") as output:
        config.write(output)


def test_preview_force_date_selects_halloween_and_draws_witch_hat(app: QApplication, tmp_path: Path) -> None:
    # Given local seasonal preferences with Halloween enabled and no network location.
    config_path = tmp_path / "screenbot.ini"
    write_settings(config_path, {
        "theme": "forest",
        "seasonal_enabled": "true",
        "seasonal_halloween_enabled": "true",
        "seasonal_new_year_enabled": "false",
    })
    saver = Saver(preview=True, config_path=config_path,
                  forced_preview_datetime=datetime(2026, 10, 31, 12, 0))
    image = QImage(960, 540, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    # When drawing the explicit forced-date preview.
    saver.draw_scenery(painter, image.width(), image.height(), 0.0)
    painter.end()
    # Then Halloween decorations render and Bob receives the seasonal witch hat.
    assert saver.seasonal_bob_hat == "witch"
    assert any(image.pixelColor(x, y).alpha() > 0
               for y in range(0, image.height(), 4)
               for x in range(0, image.width(), 4))
    assert saver.is_preview and not saver.password_lock
    saver.close()


def test_regular_command_line_rejects_force_date_without_preview() -> None:
    # Given a production screensaver invocation with a forced calendar value.
    environment = {**os.environ, "QT_QPA_PLATFORM": "offscreen"}
    # When the CLI is launched without either preview mode.
    result = subprocess.run(
        [sys.executable, str(Path(__file__).parents[1] / "screensaver.py"),
         "--force-date", "2026-10-31"],
        capture_output=True, text=True, env=environment, check=False,
    )
    # Then it exits with a usage error before starting the saver.
    assert result.returncode == 2
    assert "--force-date" in result.stdout
