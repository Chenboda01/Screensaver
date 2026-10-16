"""Offscreen integration and synthetic screenshot coverage for fact cards."""
import configparser
import os
from pathlib import Path
import random
import time
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtWidgets import QApplication

from bobos import BobOSPhase
from screenbot.app import Saver
from screenbot.burnin import burn_in_scene_scale, burn_in_scene_shift
from screenbot.fact_overlay import FACT_CARD_MAX_CHARS, fact_font_size, wrap_complete_text
from screenbot.facts import FactCycler, load_catalog


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

    @staticmethod
    def alpha_bounds(image: QImage) -> QRectF | None:
        xs, ys = [], []
        for y in range(image.height()):
            for x in range(image.width()):
                if image.pixelColor(x, y).alpha() > 0:
                    xs.append(x)
                    ys.append(y)
        if not xs:
            return None
        return QRectF(min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1)

    def test_real_saver_draws_complete_localized_cards_at_supported_sizes(self):
        evidence = Path(os.environ.get(
            "SCREENBOT_FACT_EVIDENCE_DIR",
            Path(__file__).resolve().parents[1] / ".omo" / "evidence" / "issue-27" / "responsive",
        ))
        evidence.mkdir(parents=True, exist_ok=True)
        for locale in ("en", "es"):
            with patch.dict(os.environ, {"LANGUAGE": locale}):
                saver = self.make_saver()
            saver.fact_cycler = FactCycler(rng=random.Random(19), locale=locale)
            catalog = load_catalog(locale=locale)
            longest = max((fact for facts in catalog.values() for fact in facts),
                          key=lambda fact: len(fact["text"]))
            for width, height in ((800, 600), (1280, 720), (1920, 1080)):
                with self.subTest(locale=locale, size=(width, height)):
                    saver.resize(width, height)
                    saver.theme = "forest"
                    saver._scenery_cache = None
                    saver._scenery_cache_key = None
                    elapsed = time.monotonic() - saver.start_time
                    displayed = {**longest, "category": "forest", "kind": "fact"}
                    saver._fact_category = "forest"
                    saver._fact_current = displayed
                    saver._fact_next = displayed
                    saver._fact_started_at = elapsed
                    saver._fact_states["forest"] = {
                        "current": displayed, "next": displayed, "phase": 0.0,
                    }
                    image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
                    image.fill(Qt.GlobalColor.transparent)
                    saver.render(image)
                    self.assertFalse(image.isNull())
                    self.assertIsNotNone(saver._fact_current)
                    fact = longest["text"]
                    self.assertLessEqual(len(fact), FACT_CARD_MAX_CHARS)
                    rect = saver.fact_card_geometry(width, height, elapsed, fact)
                    self.assertIsNotNone(rect)
                    from PyQt6.QtGui import QFont, QFontMetricsF
                    font = QFont("Sans Serif", fact_font_size(rect.width()))
                    lines = wrap_complete_text(fact, font, rect.width() - 28)
                    self.assertEqual(" ".join(lines), " ".join(fact.split()))
                    metrics = QFontMetricsF(font)
                    self.assertTrue(all(metrics.horizontalAdvance(line) <= rect.width() - 28
                                        for line in lines))
                    self.assertEqual(saver.fact_labels["did_you_know"],
                                     "¿Sabías que?" if locale == "es" else "DID YOU KNOW?")
                    self.assertTrue(image.save(str(evidence / f"{locale}-{width}x{height}.png")))
            saver.resize(1280, 720)
            for theme in THEMES:
                with self.subTest(locale=locale, theme=theme):
                    saver.theme = theme
                    saver._scenery_cache = None
                    saver._scenery_cache_key = None
                    image = QImage(1280, 720, QImage.Format.Format_ARGB32_Premultiplied)
                    image.fill(Qt.GlobalColor.transparent)
                    saver.render(image)
                    self.assertFalse(image.isNull())
                    self.assertIsNotNone(saver._fact_current)
            saver.close()

    def test_card_avoids_actual_rendered_bob_and_clock_pixels(self):
        saver = self.make_saver()
        positions = (
            "top-left", "top-center", "top-right", "center-left", "center-center",
            "center-right", "bottom-left", "bottom-center", "bottom-right",
        )
        for position in positions:
            saver.clock_position = position
            saver._advance_facts(37, "clear", False)
            rect = saver.fact_card_geometry(1280, 720, 37, saver._fact_current["text"])
            with self.subTest(position=position):
                self.assertIsNotNone(rect)
                bob_image = QImage(1280, 720, QImage.Format.Format_ARGB32_Premultiplied)
                bob_image.fill(Qt.GlobalColor.transparent)
                bob_painter = QPainter(bob_image)
                saver.bob(bob_painter, 1280, 720, 37, saver.bobos_status(37))
                bob_painter.end()
                bob_pixels = self.alpha_bounds(bob_image)
                self.assertIsNotNone(bob_pixels)
                self.assertFalse(rect.intersects(bob_pixels))

                clock_image = QImage(1280, 720, QImage.Format.Format_ARGB32_Premultiplied)
                clock_image.fill(Qt.GlobalColor.transparent)
                clock_painter = QPainter(clock_image)
                scene_offset = burn_in_scene_shift("standard", 37)
                scene_scale = burn_in_scene_scale(1280, 720)
                saver.clock(clock_painter, 1280, 720, "standard", 37,
                            scene_offset, scene_scale)
                clock_painter.end()
                clock_pixels = self.alpha_bounds(clock_image)
                self.assertIsNotNone(clock_pixels)
                self.assertFalse(rect.intersects(clock_pixels))
        saver.now_playing_enabled = True
        saver.now_playing = object()
        saver._advance_facts(37, "clear", False)
        rect = saver.fact_card_geometry(1280, 720, 37, saver._fact_current["text"])
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
        saver._fact_states.clear()
        fact_frame(90, BobOSPhase.HOME)
        self.assertIsNone(saver._fact_current)
        saver._fact_current = current
        saver.close()

    def test_category_switch_preserves_pending_fact_and_pauses_its_display_interval(self):
        saver = self.make_saver()
        saver.fact_cycler = FactCycler(rng=random.Random(4815))
        saver.facts_interval_minutes = 1
        saver.theme = "forest"
        saver._advance_facts(0, "clear", False)
        first_forest = saver._fact_current["id"]
        pending_forest = saver._fact_next["id"]
        shown = [("forest", saver._fact_current["id"])]

        saver.rain_enabled = True
        saver._advance_facts(25, "rain", False)
        first_water = saver._fact_current["id"]
        shown.append(("water_cycle", saver._fact_current["id"]))
        self.assertEqual(saver._fact_category, "water_cycle")
        saver.rain_enabled = False
        saver._advance_facts(50, "clear", False)
        self.assertEqual(saver._fact_category, "forest")
        self.assertEqual(saver._fact_current["id"], first_forest)
        self.assertEqual(saver._fact_next["id"], pending_forest)
        shown.append(("forest", saver._fact_current["id"]))
        saver.rain_enabled = True
        saver._advance_facts(85, "rain", False)
        self.assertEqual(saver._fact_current["id"], first_water)
        shown.append(("water_cycle", saver._fact_current["id"]))
        saver.rain_enabled = False
        saver._advance_facts(110, "clear", False)
        self.assertEqual(saver._fact_current["id"], pending_forest)
        shown.append(("forest", saver._fact_current["id"]))
        self.assertEqual(shown, [
            ("forest", first_forest), ("water_cycle", first_water),
            ("forest", first_forest), ("water_cycle", first_water),
            ("forest", pending_forest),
        ])
        saver.close()

    def test_hidden_bobos_minutes_do_not_consume_a_fact(self):
        saver = self.make_saver()
        saver.facts_interval_minutes = 1
        saver._advance_facts(0, "clear", False)
        first = saver._fact_current["id"]
        pending = saver._fact_next["id"]
        saver.pause_fact_overlay(15)
        saver._advance_facts(180, "clear", False, visible=False)
        saver._advance_facts(180, "clear", False, visible=True)
        self.assertEqual(saver._fact_current["id"], first)
        self.assertEqual(saver._fact_next["id"], pending)
        self.assertEqual(saver._fact_states["forest"]["phase"], 15)
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
