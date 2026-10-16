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
DEFAULT_QUOTES = DEFAULT_CATALOG.with_name("quotes.json")
DEFAULT_TRANSLATIONS = DEFAULT_CATALOG.parent / "translations"
VALID_CATEGORIES = frozenset({
    "space", "moon", "mountain_weather", "forest", "technology", "water_cycle",
})
CONTENT_MODES = frozenset({"facts", "quotes", "both"})
DEFAULT_LABELS = {"did_you_know": "DID YOU KNOW?", "bob_says": "BOB SAYS"}


def _localized_texts(locale: str, root: str | Path, group: str) -> dict[str, str]:
    language = str(locale or "en").replace("-", "_").split("_", 1)[0].lower()
    if not language.isalpha() or len(language) not in (2, 3):
        return {}
    translation_file = Path(root) / f"{language}.json"
    if not translation_file.is_file():
        return {}
    document = json.loads(translation_file.read_text(encoding="utf-8"))
    translations = document.get(group) if isinstance(document, dict) else None
    if isinstance(document, dict) and group not in document:
        return {}
    if not isinstance(translations, dict) or not all(
        isinstance(key, str) and isinstance(value, str) and value.strip()
        for key, value in translations.items()
    ):
        raise ValueError(f"invalid fact translations: {translation_file}")
    return translations


def load_catalog(
    path: str | Path = DEFAULT_CATALOG,
    *,
    locale: str = "en",
    translations_root: str | Path | None = None,
) -> dict[str, tuple[dict[str, str], ...]]:
    """Load and validate the local, editable JSON fact catalogue."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or set(raw) != VALID_CATEGORIES:
        raise ValueError("fact catalogue categories do not match the supported set")
    catalog: dict[str, tuple[dict[str, str], ...]] = {}
    translation_root = Path(translations_root) if translations_root is not None else Path(path).parent / "translations"
    translations = _localized_texts(locale, translation_root, "facts")
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
            display_text = translations.get(fact_id, text)
            if len(display_text) > 150:
                raise ValueError(f"{fact_id}: translated fact exceeds the 150-character display limit")
            checked.append({"id": fact_id, "text": display_text, "source": source})
        catalog[category] = tuple(checked)
    unknown_translations = set(translations) - all_ids
    if unknown_translations:
        raise ValueError(f"translations refer to unknown fact ids: {sorted(unknown_translations)[:3]}")
    return catalog


def load_quotes(
    path: str | Path = DEFAULT_QUOTES,
    *,
    locale: str = "en",
    translations_root: str | Path | None = None,
) -> tuple[dict[str, str], ...]:
    """Load original, clearly attributed, fictional Bob lines for Quotes mode."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, list) or len(raw) < 30:
        raise ValueError("quote catalogue must contain at least 30 lines")
    checked = []
    seen: set[str] = set()
    translation_root = Path(translations_root) if translations_root is not None else Path(path).parent / "translations"
    translations = _localized_texts(locale, translation_root, "quotes")
    for item in raw:
        if not isinstance(item, dict) or set(item) != {"id", "text", "source"}:
            raise ValueError("each quote needs id, text, and source")
        quote_id, text, source = item["id"], item["text"], item["source"]
        if not all(isinstance(value, str) and value.strip() for value in (quote_id, text, source)):
            raise ValueError("quote fields must be non-empty strings")
        if quote_id in seen or len(text) > 150 or source != "ScreenBot original character line: Bob":
            raise ValueError(f"invalid or duplicate quote: {quote_id}")
        seen.add(quote_id)
        display_text = translations.get(quote_id, text)
        if len(display_text) > 150:
            raise ValueError(f"{quote_id}: translated quote exceeds the 150-character display limit")
        checked.append({"id": quote_id, "text": display_text, "source": source})
    unknown_translations = set(translations) - seen
    if unknown_translations:
        raise ValueError(f"translations refer to unknown quote ids: {sorted(unknown_translations)[:3]}")
    return tuple(checked)


def localized_labels(
    locale: str = "en", *, translations_root: str | Path = DEFAULT_TRANSLATIONS,
) -> dict[str, str]:
    """Return localized overlay labels, falling back to English per label."""
    translated = _localized_texts(locale, translations_root, "labels")
    if set(translated) - set(DEFAULT_LABELS):
        raise ValueError("fact UI translations contain unknown labels")
    return {key: translated.get(key, value) for key, value in DEFAULT_LABELS.items()}


def category_for_scene(theme: str, weather: str = "clear", full_moon: bool = False) -> str:
    """Map a rendered scene to a fact category, with visible sky events first."""
    if full_moon:
        return "moon"
    theme_key = str(theme).strip().lower().replace(" ", "_")
    if theme_key == "space":
        return "space"
    weather_key = str(weather).strip().lower()
    if weather_key in {"rain", "drizzle", "thunderstorm"}:
        return "water_cycle"
    if theme_key in {"mountains", "snow"}:
        return "mountain_weather"
    if theme_key == "forest":
        return "forest"
    if theme_key == "city":
        return "technology"
    if theme_key in {"ocean", "underwater", "desert"}:
        return "water_cycle"
    if theme_key == "aurora":
        return "space"
    return "space"


class FactCycler:
    """Choose matching facts without repeats until each category is exhausted."""

    def __init__(
        self,
        catalog: Mapping[str, Iterable[Mapping[str, str]]] | None = None,
        rng: Any | None = None,
        quotes: Iterable[Mapping[str, str]] | None = None,
        locale: str = "en",
    ) -> None:
        self.catalog = dict(catalog if catalog is not None else load_catalog(locale=locale))
        self.rng = rng if rng is not None else random.Random()
        self.quotes = [dict(item) for item in (
            quotes if quotes is not None else load_quotes(locale=locale)
        )]
        self._remaining: dict[str, list[dict[str, str]]] = {}
        for category, facts in self.catalog.items():
            values = [dict(item) for item in facts]
            if values:
                self._remaining[category] = self._shuffled(values)
        self._remaining_quotes = self._shuffled(self.quotes)
        self._both_next: dict[str, str] = {}
        self._last_fact: dict[str, str] = {}
        self._last_quote_id: str | None = None

    def _shuffled(self, values: list[dict[str, str]]) -> list[dict[str, str]]:
        result = list(values)
        self.rng.shuffle(result)
        return result

    def _refill(self, values: list[dict[str, str]], last_id: str | None = None) -> list[dict[str, str]]:
        result = self._shuffled(values)
        if len(result) > 1 and last_id is not None and result[-1].get("id") == last_id:
            result[-1], result[-2] = result[-2], result[-1]
        return result

    def next(
        self,
        theme: str,
        weather: str = "clear",
        full_moon: bool = False,
        content_mode: str = "facts",
    ) -> dict[str, str]:
        category = category_for_scene(theme, weather, full_moon)
        if category not in self.catalog or not self.catalog[category]:
            raise ValueError(f"no facts available for category {category!r}")
        mode = str(content_mode).strip().lower()
        if mode not in CONTENT_MODES:
            mode = "facts"
        if mode == "both":
            mode = self._both_next.get(category, "facts")
            self._both_next[category] = "quotes" if mode == "facts" else "facts"
        if mode == "quotes":
            if not self.quotes:
                raise ValueError("no quotes are available")
            if not self._remaining_quotes:
                self._remaining_quotes = self._refill(self.quotes, self._last_quote_id)
            quote = self._remaining_quotes.pop()
            self._last_quote_id = quote["id"]
            return {**quote, "category": category, "kind": "quote"}
        remaining = self._remaining.get(category)
        if not remaining:
            remaining = self._refill(
                [dict(item) for item in self.catalog[category]], self._last_fact.get(category)
            )
            self._remaining[category] = remaining
        fact = remaining.pop()
        self._last_fact[category] = fact["id"]
        return {**fact, "category": category, "kind": "fact"}
