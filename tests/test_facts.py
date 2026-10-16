"""Offline fact catalog and no-repeat selection behavior."""
import random
import unittest

from screenbot.facts import FactCycler, category_for_scene, load_catalog


class FactCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
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

    def test_scene_and_live_sky_matching(self):
        cases = (
            (("Space", "clear", False), "space"),
            (("Mountains", "clear", False), "mountain_weather"),
            (("Snow", "snow", False), "mountain_weather"),
            (("Forest", "clear", False), "forest"),
            (("City", "clear", False), "technology"),
            (("Forest", "rain", False), "water_cycle"),
            (("Space", "thunderstorm", False), "water_cycle"),
            (("City", "clear", True), "moon"),
            (("Mountains", "rain", True), "moon"),
        )
        for args, expected in cases:
            with self.subTest(args=args):
                self.assertEqual(category_for_scene(*args), expected)

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

    def test_weather_category_also_cycles_without_repeats(self):
        cycler = FactCycler(self.catalog, random.Random(2))
        count = len(self.catalog["water_cycle"])
        chosen = [cycler.next("Forest", weather="rain") for _ in range(count)]
        self.assertEqual(len({fact["id"] for fact in chosen}), count)
        self.assertTrue(all(fact["category"] == "water_cycle" for fact in chosen))


if __name__ == "__main__":
    unittest.main()
