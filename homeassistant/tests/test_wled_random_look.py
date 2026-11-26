"""Unit tests for the HA random look generator (stdlib unittest, no HA needed)."""

from __future__ import annotations

import json
import random
import sys
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "homeassistant" / "scripts"))

import wled_random_look as w  # type: ignore[import-not-found]  # noqa: E402


EFFECTS = ["Solid", "Breathe", "Fade", "Twinklefox", "Sparkle", "Drip", "Rain", "Colorwaves"]
PALETTES = ["Default", "C9", "C9 New", "Forest", "Autumn", "Cloud", "Breeze",
            "Sunset 2", "Ocean", "Candy", "Vintage", "Rivendell", "Semi Blue",
            "Landscape", "Orangery", "Sunset"]
STATE = {"seg": [
    {"id": 0, "n": "Lower Side"}, {"id": 1, "n": "Lower Front 1"},
    {"id": 2, "n": "Garage Peak Left"}, {"id": 3, "n": "Garage Apex Right"},
    {"id": 4, "n": "Garage"},
]}
RAW_LIBRARY = json.loads((ROOT / "src" / "engine" / "library.json").read_text())
HOLIDAYS = w.holidays_from_library(RAW_LIBRARY, {"customLooks": []})
GOLDEN = json.loads((Path(__file__).parent / "fixtures_compiled.json").read_text())


class DateRuleTests(unittest.TestCase):
    def test_eaveglow_date_rules(self):
        self.assertEqual(w.holiday_date("fixed:7-4", 2026), date(2026, 7, 4))
        self.assertEqual(w.holiday_date("easter:0", 2026), date(2026, 4, 5))
        self.assertEqual(w.holiday_date("easter:-47", 2026), date(2026, 2, 17))
        self.assertEqual(w.holiday_date("last:5:1", 2026), date(2026, 5, 25))
        self.assertEqual(w.holiday_date("nth:11:4:4", 2026), date(2026, 11, 26))
        self.assertEqual(w.holiday_date("dates:2026-11-08,2027-10-29", 2026), date(2026, 11, 8))
        self.assertIsNone(w.holiday_date("dates:2027-10-29", 2026))

    def test_calendar_covers_all_library_holidays(self):
        self.assertEqual(len(HOLIDAYS), 14)
        for holiday in HOLIDAYS:
            self.assertTrue(holiday["rule"])
            self.assertTrue(holiday["looks"])


class HolidaySelectionTests(unittest.TestCase):
    def setUp(self):
        self.seasons = [
            {"holidayId": hid, "daysBefore": before, "daysAfter": after,
             "enabled": True, "lookIds": []}
            for hid, before, after in [
                ("valentines", 7, 0), ("easter", 7, 0), ("july_4th", 7, 1),
                ("halloween", 30, 0), ("thanksgiving", 7, 0), ("christmas", 30, 7),
            ]
        ]

    def settings(self, hidden=None):
        return {"autopilot": {"enabled": True, "seasons": self.seasons, "dates": []},
                "hiddenLooks": hidden or []}

    def test_halloween_and_christmas_from_autopilot(self):
        self.assertEqual(w.active_holiday(date(2026, 10, 25), HOLIDAYS, self.settings())["id"], "halloween")
        self.assertEqual(w.active_holiday(date(2026, 11, 30), HOLIDAYS, self.settings())["id"], "christmas")

    def test_shorter_season_wins(self):
        self.assertEqual(w.active_holiday(date(2026, 11, 20), HOLIDAYS, self.settings())["id"], "thanksgiving")

    def test_no_holiday_falls_back(self):
        self.assertIsNone(w.active_holiday(date(2026, 9, 1), HOLIDAYS, self.settings()))

    def test_autopilot_off_falls_back(self):
        settings = {"autopilot": {"enabled": False, "seasons": self.seasons}}
        self.assertIsNone(w.active_holiday(date(2026, 10, 25), HOLIDAYS, settings))

    def test_hidden_looks(self):
        halloween = next(h for h in HOLIDAYS if h["id"] == "halloween")
        hidden = [look["id"] for look in halloween["looks"]]
        self.assertIsNone(w.active_holiday(date(2026, 10, 25), HOLIDAYS, self.settings(hidden)))
        partial = self.settings([hidden[0]])
        result = w.active_holiday(date(2026, 10, 25), HOLIDAYS, partial)
        self.assertEqual(len(result["looks"]), len(halloween["looks"]) - 1)


class CompileTests(unittest.TestCase):
    """Golden tests: Python compiler must match Eaveglow's TypeScript compiler."""

    @staticmethod
    def normalize(rows):
        keys = ("id", "start", "stop", "grp", "spc", "on", "col", "fx", "sx", "ix", "pal", "rev")
        return [{k: row.get(k) for k in keys if k in row} for row in rows]

    def test_matches_typescript_output(self):
        segments = GOLDEN["segments"]
        total = max(s["stop"] for s in segments)
        for case in GOLDEN["cases"]:
            with self.subTest(look=case["id"]):
                payload = w.compile_look(case["look"], segments, GOLDEN["effects"],
                                         GOLDEN["palettes"], GOLDEN["fxdata"],
                                         32, total, 128, 7)
                self.assertEqual(self.normalize(payload["seg"]),
                                 self.normalize(case["seg"]))


class AdaptedModeTests(unittest.TestCase):
    def test_family_effect_mapping(self):
        recipe = w.recipe_from_look({"id": "builtin.test", "effect": "Drip",
                                     "palette": "", "colors": [[255, 255, 255]]})
        self.assertIn("Drip", recipe["effects"]["front"])
        self.assertNotIn("Drip", recipe["effects"]["side"])

    def test_build_look_uses_look_ids_and_varied_tints(self):
        recipes = [w.recipe_from_look(l) for h in HOLIDAYS for l in h["looks"][:3]]
        updates, summary = w.build_look(STATE, EFFECTS, PALETTES, random.Random(4), True, recipes)
        self.assertTrue(summary.startswith("recipe=builtin."), summary)
        combos = {(s["pal"], tuple(tuple(c) for c in s["col"])) for s in updates}
        self.assertEqual(len(combos), len(updates))

    def test_star_palette_resolves_with_or_without_marker(self):
        names = ["Default", "Peppermint@2"]
        self.assertEqual(w.resolve_palette(names, "★ Peppermint"), 1)
        self.assertEqual(w.resolve_palette(names, "Peppermint"), 1)
        self.assertIsNone(w.resolve_palette(names, "★ Grinch"))
        self.assertEqual(w.stops_for("★ Peppermint")[0], [255, 0, 0])

    def test_holiday_palettes_override_generic_ones(self):
        installed = set(w.PALETTES) | {"C9", "C9 New", "Candy"}
        recipe = w.recipe_from_look(
            {"id": "builtin.xm_candy_twinkle", "effect": "Twinklefox",
             "palette": "★ Peppermint", "colors": [[255, 0, 0]]},
            installed, "christmas",
        )
        self.assertEqual(recipe["palettes"][0], "C9")
        self.assertNotIn("Ocean", recipe["palettes"])
        self.assertNotIn("Beach", recipe["palettes"])

    def test_palette_slots_by_version(self):
        self.assertEqual(w.palette_slots({"ver": "0.15.0", "arch": "esp8266"}), (255, 10))
        self.assertEqual(w.palette_slots({"ver": "16.0.1", "arch": "esp32"}), (200, 129))
        self.assertEqual(w.palette_slots({"ver": "16.0.1", "arch": "esp8266"}), (200, 10))

    def test_custom_palette_file_format(self):
        payload = json.loads(w.custom_palette_file({
            "wled": "★ Peppermint",
            "stops": [[255, 0, 0], [255, 255, 255], [255, 0, 0]],
        }))
        self.assertEqual(payload["n"], "★ Peppermint")
        self.assertEqual(payload["palette"], [0, "FF0000", 128, "FFFFFF", 255, "FF0000"])

    def test_ensure_custom_palettes_installs_missing(self):
        library = {"palettes": [{"wled": "★ Peppermint", "stops": [[255, 0, 0]],
                                 "positions": [0]}]}
        original_scan, original_read, original_upload = (
            w.scan_custom_palettes, w.read_optional_json, w.upload_file)
        uploaded = []
        try:
            w.scan_custom_palettes = lambda info: (
                {"★ Peppermint": 200} if uploaded else {})
            w.read_optional_json = lambda path: None
            w.upload_file = lambda path, content, **kw: uploaded.append((path, content))
            ids = w.ensure_custom_palettes(["★ Peppermint"], library, {"ver": "16.0.1"})
            self.assertEqual(ids, {"★ Peppermint": 200})
            self.assertEqual(uploaded[0][0], "/palette0.json")
        finally:
            w.scan_custom_palettes, w.read_optional_json, w.upload_file = (
                original_scan, original_read, original_upload)
            w.CUSTOM_PALETTE_IDS = {}

    def test_saved_layout_segments(self):
        settings = {"layout": {
            "totalPixels": 12, "spacing": {"lit": 2, "skip": 1},
            "zones": [
                {"id": "a", "name": "Front", "start": 0, "length": 5},
                {"id": "b", "name": "Apex", "start": 5, "length": 1, "reversed": True},
            ],
        }}
        segs = w.saved_layout_segments(settings)
        self.assertEqual(len(segs), 2)
        self.assertEqual(segs[0], {
            "id": 0, "start": 0, "stop": 5, "grp": 2, "spc": 1, "on": True,
            "bri": 255, "col": [], "fx": 0, "sx": 128, "ix": 128, "pal": 0,
            "rev": False, "n": "Front",
        })
        self.assertEqual((segs[1]["start"], segs[1]["stop"], segs[1]["rev"]), (5, 6, True))

    def test_layout_signature_ignores_names_reverse_and_effects(self):
        a = [{"id": 0, "start": 0, "stop": 5, "grp": 1, "spc": 0,
              "rev": False, "n": "Front", "fx": 3}]
        b = [{"id": 0, "start": 0, "stop": 5, "grp": 1, "spc": 0,
              "rev": True, "n": "Renamed in WLED", "fx": 9}]
        self.assertEqual(w.layout_signature(a), w.layout_signature(b))
        b[0]["stop"] = 6
        self.assertNotEqual(w.layout_signature(a), w.layout_signature(b))

    def test_ensure_saved_layout_dry_run_substitutes_segments(self):
        settings = {"layout": {"zones": [{"name": "Front", "start": 0, "length": 5}],
                               "spacing": {"lit": 1, "skip": 0}}}
        snapshot = {"state": {"on": True, "seg": [{"id": 0, "start": 0, "stop": 5, "n": None}]},
                    "info": {}}
        out = w.ensure_saved_layout(settings, snapshot, dry_run=True)
        self.assertEqual(out["state"]["seg"][0]["n"], "Front")
        self.assertEqual(len(snapshot["state"]["seg"]), 1)  # original untouched

    def test_ensure_saved_layout_noop_when_geometry_matches(self):
        settings = {"layout": {"zones": [{"name": "Front", "start": 0, "length": 5}],
                               "spacing": {"lit": 1, "skip": 0}}}
        snapshot = {"state": {"on": True, "seg": [{"id": 0, "start": 0, "stop": 5,
                                                   "grp": 1, "spc": 0, "rev": True,
                                                   "n": "Different name"}]}, "info": {}}
        self.assertIs(w.ensure_saved_layout(settings, snapshot, dry_run=True), snapshot)

    def test_playback_settings(self):
        bri, tr = w.playback_settings({"bri": 88}, {"transition": 12})
        self.assertEqual((bri, tr), (88, 12))
        self.assertEqual(w.playback_settings({}, None), (128, 7))


if __name__ == "__main__":
    unittest.main()
