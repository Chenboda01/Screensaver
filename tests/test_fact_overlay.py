"""Offscreen integration and synthetic screenshot coverage for fact cards."""
import configparser
import os
from pathlib import Path
import time
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtWidgets import QApplication

from bobos import BobOSPhase
from screenbot.app import Saver
from screenbot.burnin import burn_in_clock_drift, burn_in_scene_scale, burn_in_scene_shift
from screenbot.fact_overlay import FACT_CARD_MAX_CHARS


THEMES = ("space", "mountains", "snow", "forest", "city", "aurora", "ocean", "desert", "underwater")


class FactOverlayIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt_app = QApplication.instance() or QApplication([])

    @staticmethod
    def settings(theme: str = "forest"):
        settings = configparser.ConfigParser()
        settings.read_dict({"Screensaver": {
            "theme": theme,
            "facts_enabled": "true",
            "facts_interval_minutes": "2",
            "facts_content_mode": "facts",
            "live_sky_enabled": "false",
            "show_clock": "true",
            "clock_position": "top-center",
            "burn_in_protection": "standard",
            "password_lock": "false",
        }})
        return settings

    def make_saver(self, theme: str = "forest") -> Saver:
        with patch("screenbot.app.read_settings", return_value=self.settings(theme)):
            saver = Saver(preview=True)
        saver.resize(1280, 720)
        saver.start_time = time.monotonic() - 37
        saver.theme = theme
        saver._scenery_cache = None
        saver._scenery_cache_key = None
        return saver

    def test_real_saver_draws_a_safe_fact_card_for_each_theme(self):
        evidence = Path(os.environ.get(
            "SCREENBOT_FACT_EVIDENCE_DIR",
            Path(__file__).resolve().parents[1] / ".omo" / "evidence" / "issue-27" / "themes",
        ))
        evidence.mkdir(parents=True, exist_ok=True)
        saver = self.make_saver()
        for theme in THEMES:
            with self.subTest(theme=theme):
                saver.theme = theme
                saver._scenery_cache = None
                saver._scenery_cache_key = None
                image = QImage(1280, 720, QImage.Format.Format_ARGB32_Premultiplied)
                image.fill(Qt.GlobalColor.transparent)
                saver.render(image)
                self.assertFalse(image.isNull())
                self.assertIsNotNone(saver._fact_current)
                self.assertLessEqual(len(saver._fact_current["text"]), FACT_CARD_MAX_CHARS)
                rect = saver.fact_card_geometry(1280, 720, time.monotonic() - saver.start_time)
                self.assertIsNotNone(rect)
                self.assertTrue(image.save(str(evidence / f"{theme}.png")))
        saver.close()

    def test_card_avoids_every_clock_position_and_bob_bounds(self):
        saver = self.make_saver()
        positions = (
            "top-left", "top-center", "top-right", "center-left", "center-center",
            "center-right", "bottom-left", "bottom-center", "bottom-right",
        )
        for position in positions:
            saver.clock_position = position
            rect = saver.fact_card_geometry(1280, 720, 37)
            with self.subTest(position=position):
                self.assertIsNotNone(rect)
                scale = min(1280 / 1250, 720 / 800, 1.35)
                sway = min(1280 * .075, 85)
                bob = __import__("PyQt6.QtCore", fromlist=["QRectF"]).QRectF(
                    1280 * .5 - sway - 210 * scale,
                    720 * .56 - 9 - 200 * scale,
                    2 * sway + 420 * scale,
                    18 + 320 * scale,
                )
                self.assertFalse(rect.intersects(bob))
                self.assertLess(rect.bottom(), 720 * .78)
                row, column = position.split("-")
                clock_x = {"left": .035, "center": .29, "right": .545}[column] * 1280
                clock_y = {"top": .08, "center": .38, "bottom": .65}[row] * 720
                scene_offset = burn_in_scene_shift("standard", 37)
                scene_scale = burn_in_scene_scale(1280, 720)
                drift_x, drift_y = burn_in_clock_drift(
                    "standard", 37, 1280, 720, position, saver.clock_font_size,
                    saver.show_date, False, scene_offset, scene_scale,
                )
                clock = QRectF(clock_x + drift_x, clock_y + drift_y, 1280 * .42,
                               saver.clock_font_size * (1.5 + .62 * saver.show_date))
                self.assertFalse(rect.intersects(clock))
        saver.now_playing_enabled = True
        saver.now_playing = object()
        rect = saver.fact_card_geometry(1280, 720, 37)
        self.assertIsNotNone(rect)
        self.assertFalse(rect.intersects(saver.media_card_rect()))
        saver.close()

    def test_fact_card_follows_burn_in_scene_transform_and_disappears_during_bobos(self):
        saver = self.make_saver()
        saver.show_clock = False

        def fact_frame(elapsed: float, phase: BobOSPhase) -> QImage:
            width, height = 1280, 720
            image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
            image.fill(Qt.GlobalColor.transparent)
            painter = QPainter(image)
            offset = burn_in_scene_shift("standard", elapsed)
            scale = burn_in_scene_scale(width, height)
            painter.translate(width * .5 + offset[0], height * .5 + offset[1])
            painter.scale(scale, scale)
            painter.translate(-width * .5, -height * .5)
            saver.draw_fact_overlay(painter, width, height, elapsed, phase)
            painter.end()
            return image

        ordinary = fact_frame(37, BobOSPhase.EXPLORING)
        self.assertIsNotNone(saver._fact_current)
        shifted = fact_frame(73, BobOSPhase.EXPLORING)
        self.assertNotEqual(ordinary, shifted)
        current = saver._fact_current
        saver._fact_current = None
        saver._fact_next = None
        saver._fact_category = None
        saver._fact_started_at = None
        fact_frame(90, BobOSPhase.HOME)
        self.assertIsNone(saver._fact_current)
        saver._fact_current = current
        saver.close()

    def test_interval_crossfades_and_advances_without_a_boundary_flash(self):
        saver = self.make_saver()
        first = saver._advance_facts(0, "clear", False)
        self.assertEqual(first, (1.0, 0.0))
        outgoing_id = saver._fact_current["id"]
        incoming_id = saver._fact_next["id"]
        half_fade = saver.facts_interval_minutes * 60 - 1.35 / 2
        halfway = saver._advance_facts(half_fade, "clear", False)
        self.assertAlmostEqual(halfway[0], .5, places=2)
        self.assertAlmostEqual(halfway[1], .5, places=2)
        boundary = saver._advance_facts(saver.facts_interval_minutes * 60, "clear", False)
        self.assertEqual(boundary, (1.0, 0.0))
        self.assertEqual(saver._fact_current["id"], incoming_id)
        self.assertNotEqual(saver._fact_current["id"], outgoing_id)
        saver.close()

    def test_off_switch_disables_card_without_advancing_the_cycler(self):
        saver = self.make_saver()
        saver.facts_enabled = False
        image = QImage(800, 450, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        saver.draw_fact_overlay(painter, 800, 450, 10, BobOSPhase.EXPLORING)
        painter.end()
        self.assertIsNone(saver._fact_current)
        self.assertEqual(image.pixelColor(400, 200).alpha(), 0)
        saver.close()


if __name__ == "__main__":
    unittest.main()
