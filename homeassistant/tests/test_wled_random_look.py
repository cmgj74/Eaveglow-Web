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


class ManifestTests(unittest.TestCase):
    """Tests for the A+B manifest/precompiled-look bundle."""

    def setUp(self):
        self.bundle = w.load_looks_file()
        if self.bundle is None:
            self.skipTest("homeassistant/looks/christmas.json has not been generated")

    def test_manifest_covers_the_real_christmas_looks(self):
        looks = self.bundle["looks"]
        self.assertGreaterEqual(len(looks), 20)
        for entry in looks:
            self.assertTrue(entry.get("effect"))
            self.assertTrue(entry.get("payload", {}).get("seg"))

    def test_look_recipe_maps_effect_to_the_right_family(self):
        recipe = w.recipe_from_look({
            "id": "builtin.test", "effect": "Drip", "palette": "",
            "colors": [[255, 255, 255]],
        })
        self.assertIn("Drip", recipe["effects"]["front"])
        self.assertNotIn("Drip", recipe["effects"]["side"])

    def test_fingerprint_guards_exact_payloads(self):
        fingerprint = self.bundle["fingerprint"]
        segs = [{"id": row[0], "start": row[1], "stop": row[2]} for row in fingerprint]
        self.assertTrue(w.bundle_matches_layout(self.bundle, segs))
        self.assertFalse(w.bundle_matches_layout(self.bundle, segs[:-1]))
        changed = [dict(s) for s in segs]
        changed[0] = {**changed[0], "start": 999}
        self.assertFalse(w.bundle_matches_layout(self.bundle, changed))
        self.assertIsNotNone(w.look_payload(self.bundle["looks"][0]))

    def test_adapt_mode_uses_eaveglow_look_ids(self):
        recipes = [w.recipe_from_look(e) for e in self.bundle["looks"]]
        _, summary = w.build_look(STATE, EFFECTS, PALETTES, random.Random(4), True, recipes)
        self.assertTrue(summary.startswith("recipe=builtin."), summary)


if __name__ == "__main__":
    unittest.main()
