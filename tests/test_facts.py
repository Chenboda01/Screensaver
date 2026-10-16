"""Offline fact catalog and no-repeat selection behavior."""
import os
import random
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt6.QtWidgets import QApplication

from screenbot.fact_overlay import FactPreferences, fact_card_rect, fact_font_size, wrap_complete_text
from screenbot.facts import FactCycler, category_for_scene, load_catalog, load_quotes, localized_labels
from PyQt6.QtGui import QFont


class FactCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.catalog = load_catalog()

    def test_every_scene_category_has_at_least_thirty_sourced_short_facts(self):
        self.assertEqual(set(self.catalog), {
            "space", "moon", "mountain_weather", "forest", "technology", "water_cycle",
        })
        for category, facts in self.catalog.items():
            with self.subTest(category=category):
                self.assertGreaterEqual(len(facts), 30)
                self.assertEqual(len({fact["id"] for fact in facts}), len(facts))
                self.assertTrue(all(fact["source"].startswith("https://") for fact in facts))
                self.assertTrue(all(len(fact["text"]) <= 150 for fact in facts))
        quotes = load_quotes()
        self.assertGreaterEqual(len(quotes), 30)
        self.assertTrue(all("original character line" in quote["source"] for quote in quotes))

    def test_scene_and_live_sky_matching(self):
        cases = (
            (("Space", "clear", False), "space"),
            (("Mountains", "clear", False), "mountain_weather"),
            (("Snow", "snow", False), "mountain_weather"),
            (("Forest", "clear", False), "forest"),
            (("City", "clear", False), "technology"),
            (("Forest", "rain", False), "water_cycle"),
            (("Space", "thunderstorm", False), "space"),
            (("City", "clear", True), "moon"),
            (("Mountains", "rain", True), "moon"),
        )
        for args, expected in cases:
            with self.subTest(args=args):
                self.assertEqual(category_for_scene(*args), expected)
        self.assertEqual(category_for_scene("Space", "rain"), "space")
        self.assertEqual(category_for_scene("Aurora"), "space")
        self.assertEqual(category_for_scene("Underwater"), "water_cycle")

    def test_deterministic_seed_produces_identical_per_category_order(self):
        first = FactCycler(self.catalog, random.Random(4815))
        second = FactCycler(self.catalog, random.Random(4815))
        themes = ["Space", "Forest", "City", "Snow", "Mountains"] * 8
        left = [first.next(theme)["id"] for theme in themes]
        right = [second.next(theme)["id"] for theme in themes]
        self.assertEqual(left, right)

    def test_no_fact_repeats_until_its_category_is_exhausted(self):
        for theme, category in (("Space", "space"), ("Forest", "forest"),
                                ("City", "technology"), ("Mountains", "mountain_weather"),
                                ("Snow", "mountain_weather"), ("Space", "moon")):
            cycler = FactCycler(self.catalog, random.Random(91))
            if category == "moon":
                chosen = [cycler.next(theme, full_moon=True) for _ in self.catalog[category]]
                following = cycler.next(theme, full_moon=True)
            else:
                chosen = [cycler.next(theme) for _ in self.catalog[category]]
                following = cycler.next(theme)
            ids = [fact["id"] for fact in chosen]
            with self.subTest(category=category, theme=theme):
                self.assertEqual(len(set(ids)), len(ids))
                self.assertEqual({fact["category"] for fact in chosen}, {category})
                self.assertIn(following["id"], ids)
                self.assertNotEqual(following["id"], chosen[-1]["id"])

    def test_weather_category_also_cycles_without_repeats(self):
        cycler = FactCycler(self.catalog, random.Random(2))
        count = len(self.catalog["water_cycle"])
        chosen = [cycler.next("Forest", weather="rain") for _ in range(count)]
        self.assertEqual(len({fact["id"] for fact in chosen}), count)
        self.assertTrue(all(fact["category"] == "water_cycle" for fact in chosen))

    def test_quotes_and_both_modes_use_distinct_no_repeat_decks(self):
        cycler = FactCycler(self.catalog, random.Random(123))
        quotes = [cycler.next("Forest", content_mode="quotes") for _ in load_quotes()]
        self.assertEqual(len({quote["id"] for quote in quotes}), len(load_quotes()))
        self.assertNotEqual(cycler.next("Forest", content_mode="quotes")["id"], quotes[-1]["id"])
        self.assertTrue(all(quote["kind"] == "quote" and quote["category"] == "forest" for quote in quotes))
        both = [cycler.next("Forest", content_mode="both") for _ in range(4)]
        self.assertEqual([entry["kind"] for entry in both], ["fact", "quote", "fact", "quote"])

    def test_fact_preferences_clamp_malformed_values_safely(self):
        import configparser
        settings = configparser.ConfigParser()
        settings.read_string("[Screensaver]\nfacts_enabled=no\nfacts_interval_minutes=99\nfacts_content_mode=INVALID\n")
        self.assertEqual(FactPreferences.from_settings(settings), FactPreferences(False, 5, "facts"))
        empty = configparser.ConfigParser()
        self.assertEqual(FactPreferences.from_settings(empty), FactPreferences(True, 3, "facts"))

    def test_fact_and_quote_text_use_locale_sidecar_with_english_fallback(self):
        english = self.catalog["space"][0]
        spanish = load_catalog(locale="es-MX")["space"][0]
        self.assertNotEqual(spanish["text"], english["text"])
        self.assertEqual(spanish["id"], english["id"])
        self.assertEqual(spanish["source"], english["source"])
        spanish_quote = load_quotes(locale="es-ES")[0]
        english_quote = load_quotes()[0]
        self.assertNotEqual(spanish_quote["text"], english_quote["text"])
        self.assertEqual(spanish_quote["source"], english_quote["source"])
        self.assertEqual(load_catalog(locale="fr-FR")["space"][0]["text"], english["text"])

    def test_card_headings_are_localized_with_english_fallback(self):
        self.assertEqual(localized_labels("es-MX"), {
            "did_you_know": "¿Sabías que?", "bob_says": "BOB DICE",
        })
        self.assertEqual(localized_labels("fr-FR"), {
            "did_you_know": "DID YOU KNOW?", "bob_says": "BOB SAYS",
        })

    def test_layout_avoids_obstacles_and_suppresses_when_every_safe_slot_is_blocked(self):
        from PyQt6.QtCore import QRectF
        rect = fact_card_rect(1280, 720, (QRectF(0, 0, 1280, 200),),
                              "This card avoids every visible element safely.")
        self.assertIsNotNone(rect)
        self.assertFalse(rect.intersects(QRectF(0, 0, 1280, 200)))
        all_blocked = (QRectF(0, 0, 1280, 720),)
        self.assertIsNone(fact_card_rect(1280, 720, all_blocked, "No safe room remains."))

    def test_every_english_and_spanish_fact_fits_without_losing_words_at_supported_sizes(self):
        sizes = ((800, 600), (1280, 720), (1920, 1080))
        for locale in ("en", "es"):
            catalog = load_catalog(locale=locale)
            for width, height in sizes:
                for category, records in catalog.items():
                    for record in records:
                        with self.subTest(locale=locale, size=(width, height), fact=record["id"]):
                            rect = fact_card_rect(width, height, text=record["text"])
                            self.assertIsNotNone(rect)
                            font = QFont("Sans Serif", fact_font_size(rect.width()))
                            lines = wrap_complete_text(record["text"], font, rect.width() - 28)
                            self.assertEqual(" ".join(lines), " ".join(record["text"].split()))
                            metrics = __import__("PyQt6.QtGui", fromlist=["QFontMetricsF"]).QFontMetricsF(font)
                            self.assertTrue(all(metrics.horizontalAdvance(line) <= rect.width() - 28
                                                for line in lines))
                for quote in load_quotes(locale=locale):
                    rect = fact_card_rect(width, height, text=quote["text"])
                    self.assertIsNotNone(rect, (locale, width, quote["id"]))
                    font = QFont("Sans Serif", fact_font_size(rect.width()))
                    lines = wrap_complete_text(quote["text"], font, rect.width() - 28)
                    self.assertEqual(" ".join(lines), " ".join(quote["text"].split()))

    def test_electric_vote_recorder_and_phonograph_claims_match_patent_records(self):
        technology = {fact["id"]: fact for fact in self.catalog["technology"]}
        vote = technology["tech-19"]
        self.assertIn("90,646", vote["text"])
        self.assertIn("June 1, 1869", vote["text"])
        self.assertEqual(vote["source"], "https://edison.rutgers.edu/life-of-edison/inventions?catid=91&id=543&view=article")
        phonograph = technology["tech-21"]
        self.assertIn("filed", phonograph["text"])
        self.assertIn("February 19, 1878", phonograph["text"])
        self.assertEqual(phonograph["source"], "https://patents.google.com/patent/US200521A/en")
        developed = technology["tech-20"]
        self.assertIn("developed", developed["text"])
        self.assertEqual(developed["source"], "https://americanhistory.si.edu/lighting/scripts/s19b.htm")

        spanish = load_catalog(locale="es")
        translated = {fact["id"]: fact["text"] for fact in spanish["technology"]}
        self.assertIn("90.646", translated["tech-19"])
        self.assertIn("1869", translated["tech-19"])
        self.assertIn("19 de febrero de 1878", translated["tech-21"])
        self.assertIn("desarrolló", translated["tech-20"])

    def test_forest_index_claims_link_to_the_specific_supporting_pages(self):
        forest = {fact["id"]: fact for fact in self.catalog["forest"]}
        self.assertEqual(forest["forest-29"]["source"], "https://www.nps.gov/subjects/fungi/index.htm")
        self.assertEqual(forest["forest-30"]["source"], "https://www.nps.gov/subjects/pollinators/index.htm")


if __name__ == "__main__":
    unittest.main()
