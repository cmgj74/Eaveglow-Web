"""Unit tests for the HA random look generator (stdlib unittest, no controller needed)."""

from __future__ import annotations

import random
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import wled_random_look as w  # type: ignore[import-not-found]  # noqa: E402


EFFECTS = ["Solid", "Breathe", "Fade", "Twinklefox", "Sparkle", "Drip", "Rain", "Colorwaves"]
PALETTES = ["Default", "C9", "C9 New", "Forest", "Autumn", "Cloud", "Breeze",
            "Sunset 2", "Ocean", "Candy", "Vintage", "Rivendell", "Semi Blue",
            "Landscape", "Orangery", "Sunset"]
STATE = {
    "seg": [
        {"id": 0, "n": "Lower Side"},
        {"id": 1, "n": "Lower Front 1"},
        {"id": 2, "n": "Garage Peak Left"},
        {"id": 3, "n": "Garage Apex Right"},
        {"id": 4, "n": "Garage"},
    ]
}


class SeasonTests(unittest.TestCase):
    def test_thanksgiving_is_fourth_thursday(self):
        self.assertEqual(w.thanksgiving(2025), date(2025, 11, 27))
        self.assertEqual(w.thanksgiving(2026), date(2026, 11, 26))
        self.assertEqual(w.thanksgiving(2027), date(2027, 11, 25))

    def test_window_starts_thanksgiving_and_ends_dec_26(self):
        self.assertFalse(w.in_christmas_season(date(2026, 11, 25)))
        self.assertTrue(w.in_christmas_season(date(2026, 11, 26)))
        self.assertTrue(w.in_christmas_season(date(2026, 12, 25)))
        self.assertTrue(w.in_christmas_season(date(2026, 12, 26)))
        self.assertFalse(w.in_christmas_season(date(2026, 12, 27)))


class BuildLookTests(unittest.TestCase):
    def test_christmas_mode_picks_a_curated_recipe(self):
        updates, summary = w.build_look(STATE, EFFECTS, PALETTES, random.Random(1), True)
        name = summary.split()[0].split("=")[1]
        self.assertTrue(summary.startswith("recipe="))
        self.assertIn(name, [r["name"] for r in w.CHRISTMAS_RECIPES])
        self.assertEqual(len(updates), len(STATE["seg"]))

    def test_christmas_mode_can_reach_every_recipe(self):
        seen = set()
        for seed in range(200):
            _, summary = w.build_look(STATE, EFFECTS, PALETTES, random.Random(seed), True)
            seen.add(summary.split()[0].split("=")[1])
        self.assertEqual(seen, {r["name"] for r in w.CHRISTMAS_RECIPES})

    def test_family_effects_are_deduped_and_valid(self):
        updates, _ = w.build_look(STATE, EFFECTS, PALETTES, random.Random(7), True)
        fx = [s["fx"] for s in updates]
        self.assertEqual(len(fx), 5)
        self.assertEqual(len(set(fx)), 5)  # one distinct effect per family
        for seg in updates:
            self.assertLess(seg["fx"], len(EFFECTS))
            self.assertLess(seg["pal"], len(PALETTES))
            self.assertEqual(len(seg["col"]), 3)

    def test_segments_get_distinct_palettes_and_tints(self):
        updates, _ = w.build_look(STATE, EFFECTS, PALETTES, random.Random(9), True)
        combos = {(s["pal"], tuple(tuple(c) for c in s["col"])) for s in updates}
        self.assertEqual(len(combos), len(updates))

    def test_normal_mode_still_uses_moods(self):
        _, summary = w.build_look(STATE, EFFECTS, PALETTES, random.Random(3), False)
        self.assertTrue(summary.startswith("mood="))

    def test_star_palette_resolves_with_or_without_marker(self):
        names = ["Default", "Peppermint@2"]
        self.assertEqual(w.resolve_palette(names, "★ Peppermint"), 1)
        self.assertEqual(w.resolve_palette(names, "Peppermint"), 1)
        self.assertIsNone(w.resolve_palette(names, "★ Grinch"))
        self.assertEqual(w.stops_for("★ Peppermint")[0], [255, 0, 0])


if __name__ == "__main__":
    unittest.main()
