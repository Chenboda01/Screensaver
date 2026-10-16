"""Offline, source-attributed fact selection for the screensaver.

This module has no Qt, network, clock, or filesystem side effects beyond loading
the bundled JSON catalogue. A caller can inject a random.Random-compatible
object to make a complete fact cycle reproducible in tests.
"""
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Iterable, Mapping


DEFAULT_CATALOG = Path(__file__).resolve().parent.parent / "facts" / "facts.json"
VALID_CATEGORIES = frozenset({
    "space", "moon", "mountain_weather", "forest", "technology", "water_cycle",
})


def load_catalog(path: str | Path = DEFAULT_CATALOG) -> dict[str, tuple[dict[str, str], ...]]:
    """Load and validate the local, editable JSON fact catalogue."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or set(raw) != VALID_CATEGORIES:
        raise ValueError("fact catalogue categories do not match the supported set")
    catalog: dict[str, tuple[dict[str, str], ...]] = {}
    all_ids: set[str] = set()
    for category, records in raw.items():
        if not isinstance(records, list) or len(records) < 30:
            raise ValueError(f"{category}: expected at least 30 facts")
        checked: list[dict[str, str]] = []
        for item in records:
            if not isinstance(item, dict) or set(item) != {"id", "text", "source"}:
                raise ValueError(f"{category}: each fact needs id, text, and source")
            fact_id, text, source = item["id"], item["text"], item["source"]
            if not all(isinstance(value, str) and value.strip() for value in (fact_id, text, source)):
                raise ValueError(f"{category}: fact fields must be non-empty strings")
            if fact_id in all_ids:
                raise ValueError(f"duplicate fact id: {fact_id}")
            if len(text) > 150:
                raise ValueError(f"{fact_id}: fact exceeds the 150-character display limit")
            if not source.startswith("https://"):
                raise ValueError(f"{fact_id}: source must be an HTTPS URL")
            all_ids.add(fact_id)
            checked.append({"id": fact_id, "text": text, "source": source})
        catalog[category] = tuple(checked)
    return catalog


def category_for_scene(theme: str, weather: str = "clear", full_moon: bool = False) -> str:
    """Map a rendered scene to a fact category, with visible sky events first."""
    if full_moon:
        return "moon"
    weather_key = str(weather).strip().lower()
    if weather_key in {"rain", "drizzle", "thunderstorm"}:
        return "water_cycle"
    theme_key = str(theme).strip().lower().replace(" ", "_")
    if theme_key in {"space", "mountains", "snow", "forest", "city"}:
        return {
            "space": "space",
            "mountains": "mountain_weather",
            "snow": "mountain_weather",
            "forest": "forest",
            "city": "technology",
        }[theme_key]
    return "space"


class FactCycler:
    """Choose matching facts without repeats until each category is exhausted."""

    def __init__(
        self,
        catalog: Mapping[str, Iterable[Mapping[str, str]]] | None = None,
        rng: Any | None = None,
    ) -> None:
        self.catalog = dict(catalog if catalog is not None else load_catalog())
        self.rng = rng if rng is not None else random.Random()
        self._remaining: dict[str, list[dict[str, str]]] = {}
        for category, facts in self.catalog.items():
            values = [dict(item) for item in facts]
            if values:
                self._remaining[category] = self._shuffled(values)

    def _shuffled(self, values: list[dict[str, str]]) -> list[dict[str, str]]:
        result = list(values)
        self.rng.shuffle(result)
        return result

    def next(self, theme: str, weather: str = "clear", full_moon: bool = False) -> dict[str, str]:
        category = category_for_scene(theme, weather, full_moon)
        if category not in self.catalog or not self.catalog[category]:
            raise ValueError(f"no facts available for category {category!r}")
        remaining = self._remaining.get(category)
        if not remaining:
            remaining = self._shuffled([dict(item) for item in self.catalog[category]])
            self._remaining[category] = remaining
        fact = remaining.pop()
        return {**fact, "category": category}

