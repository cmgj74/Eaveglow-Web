#!/usr/bin/env python3
"""Pick a new, tasteful look for the permanent lights at sunset.

Port of Eaveglow's "coherent" look generator (src/engine/lookGenerator.ts):
one coordinated mood per look, a family-appropriate effect per zone type,
and a different palette and tint for every segment. Zone types come from the
WLED segment labels (seg.n) that Eaveglow already wrote to the controller.

From Thanksgiving evening through 26 December the same machinery picks a
curated Christmas recipe instead (see CHRISTMAS_RECIPES).

Runs inside Home Assistant via shell_command. Python 3 stdlib only.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import urllib.error
import urllib.request
from datetime import date, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
WLED_HOST = "192.168.1.230"
BASE_URL = os.environ.get("WLED_URL", f"http://{WLED_HOST}")
TIMEOUT = 10


# ---------------------------------------------------------------------------
# Curated palettes — the calm built-ins from Eaveglow's library.json.
# Party / Fire / Lava / Toxic Reef / Tiamat / Traffic Light are deliberately
# excluded. Stop colours are copied from Eaveglow so colour-based effects
# match what Eaveglow would have compiled.
# ---------------------------------------------------------------------------
PALETTES: dict[str, list[list[int]]] = {
    "Sunset": [[120, 0, 0], [255, 104, 0], [167, 22, 18], [100, 0, 103], [16, 0, 130]],
    "Sunset 2": [[181, 0, 0], [255, 80, 0], [255, 198, 10], [255, 240, 160]],
    "Ocean": [[25, 25, 112], [0, 0, 139], [0, 128, 128], [0, 255, 255], [70, 130, 180]],
    "Beach": [[255, 240, 180], [255, 190, 110], [0, 200, 200], [0, 110, 180]],
    "Atlantica": [[0, 28, 112], [32, 96, 255], [0, 243, 45], [12, 95, 82], [25, 190, 95]],
    "Breeze": [[1, 6, 7], [1, 99, 111], [144, 209, 255], [0, 73, 82]],
    "Cloud": [[0, 0, 255], [135, 206, 235], [255, 255, 255], [0, 0, 139]],
    "Aurora": [[1, 5, 45], [0, 200, 23], [0, 255, 0], [0, 243, 45], [0, 135, 7]],
    "Aurora 2": [[17, 177, 13], [121, 242, 5], [25, 173, 121], [250, 77, 127], [171, 101, 221]],
    "Forest": [[0, 100, 0], [85, 107, 47], [0, 128, 0], [154, 205, 50], [144, 238, 144]],
    "Rivendell": [[1, 14, 5], [16, 36, 14], [56, 68, 30], [150, 156, 99]],
    "Landscape": [[2, 25, 1], [15, 115, 5], [126, 211, 47], [144, 182, 205], [1, 37, 192]],
    "Autumn": [[67, 4, 1], [118, 14, 1], [137, 152, 52], [113, 65, 1]],
    "Orangery": [[255, 95, 23], [255, 82, 0], [223, 13, 8], [144, 44, 2], [255, 110, 17]],
    "Vintage": [[16, 0, 1], [97, 104, 3], [255, 131, 19], [67, 9, 4]],
    "C9": [[184, 4, 0], [144, 44, 2], [4, 96, 2], [7, 7, 88]],
    "C9 New": [[255, 5, 0], [255, 135, 0], [0, 225, 5], [0, 5, 255], [255, 200, 0]],
    "Candy": [[229, 227, 1], [227, 101, 3], [40, 1, 80], [1, 0, 32]],
    "Pink Candy": [[255, 255, 255], [7, 12, 255], [227, 1, 127], [255, 255, 255], [171, 1, 190]],
    "Sakura": [[196, 19, 10], [255, 69, 45], [223, 45, 72], [255, 82, 103], [223, 13, 17]],
    "Sherbet": [[255, 33, 4], [255, 68, 25], [255, 82, 103], [255, 255, 242], [42, 255, 22]],
    "Pastel": [[10, 62, 123], [56, 130, 103], [153, 225, 85], [255, 207, 54], [239, 107, 61]],
    "April Night": [[1, 5, 45], [5, 169, 175], [45, 175, 31], [249, 150, 5], [223, 45, 72]],
    "Orange & Teal": [[0, 150, 92], [255, 72, 0]],
    "Semi Blue": [[0, 0, 0], [12, 1, 60], [53, 1, 140], [24, 107, 255]],
}

# Coordinated moods: pick one per run, then a different palette from it for
# each zone group. Groups differ, but the house still reads as one scheme.
PALETTE_MOODS = {
    "warm": ("Sunset", "Sunset 2", "Orangery", "Vintage", "C9", "Candy", "Sakura", "Autumn"),
    "cool": ("Ocean", "Beach", "Atlantica", "Breeze", "Cloud", "Semi Blue", "April Night"),
    "nature": ("Forest", "Rivendell", "Landscape", "Aurora", "Aurora 2", "Cloud", "Orange & Teal"),
    "festive": ("C9", "C9 New", "Candy", "Pink Candy", "Sherbet", "Pastel", "Sunset 2", "Sakura"),
}

# Eaveglow installs these ★ palettes on the controller when a look uses them.
# Stops copied from src/engine/library.json so colour-based effects match.
CUSTOM_PALETTES: dict[str, list[list[int]]] = {
    "Peppermint": [[255, 0, 0], [255, 0, 0], [255, 255, 255], [255, 255, 255], [255, 0, 0]],
    "Grinch": [[0, 192, 0], [102, 255, 0], [255, 0, 0], [0, 192, 0]],
    "Candy Corn": [[255, 255, 255], [255, 196, 0], [255, 106, 0], [255, 106, 0]],
}
PALETTE_STOPS = {**PALETTES, **CUSTOM_PALETTES}

# Christmas recipes. Each picks one coordinated set of palettes; effects and
# colours are per zone family, so peaks still sparkle, fronts still drip, etc.
# The whole thing mirrors Eaveglow's `christmas` group in library.json.
CHRISTMAS_RECIPES = [
    {
        "name": "christmas_classic",
        "palettes": ["★ Grinch", "C9", "Forest", "Autumn"],
        "effects": {
            "apex": ("Twinklefox", "Sparkle", "Fairytwinkle"),
            "peak": ("Sparkle", "Twinkle", "Colortwinkles"),
            "front": ("Drip", "Rain", "Drip Drop"),
            "side": ("Chase 2", "Colorwaves", "Railway"),
            "garage": ("Solid", "Breathe", "Fade"),
        },
    },
    {
        "name": "candy_cane",
        "palettes": ["★ Peppermint", "C9 New", "Sunset 2"],
        "effects": {
            "apex": ("Sparkle+", "Twinklefox", "Glitter"),
            "peak": ("Sparkle", "Glitter", "Colortwinkles"),
            "front": ("Colorwaves", "Rain", "Drip Drop"),
            "side": ("Railway", "Theater", "Chase 2"),
            "garage": ("Solid", "Fade", "Breathe"),
        },
        "colors": {"side": [[255, 40, 40], [255, 255, 255]], "front": [[255, 255, 255], [255, 90, 90]]},
    },
    {
        "name": "snowfall",
        "palettes": ["Cloud", "Breeze", "Ocean", "Semi Blue"],
        "effects": {
            "apex": ("Sparkle", "Glitter", "Twinklefox"),
            "peak": ("Sparkle Dark", "Colortwinkles", "Twinkle"),
            "front": ("Drip", "Drip Drop", "Rain"),
            "side": ("Colorwaves", "Flow", "Aurora"),
            "garage": ("Breathe", "Fade", "Solid"),
        },
        "colors": {"front": [[255, 255, 255], [200, 230, 255]], "side": [[190, 225, 255], [150, 200, 255]]},
    },
    {
        "name": "tree_lights",
        "palettes": ["C9 New", "★ Grinch", "C9", "Candy"],
        "effects": {
            "apex": ("Twinklefox", "Colortwinkles", "Sparkle"),
            "peak": ("Twinklefox", "Twinkle", "Sparkle"),
            "front": ("Colorwaves", "Chase 2", "Flow"),
            "side": ("Chase 2", "Colorwaves", "Theater"),
            "garage": ("Solid", "Breathe"),
        },
    },
    {
        "name": "gingerbread",
        "palettes": ["Autumn", "Orangery", "Vintage"],
        "effects": {
            "apex": ("Twinklefox", "Glitter", "Sparkle"),
            "peak": ("Twinklefox", "Twinkle", "Sparkle"),
            "front": ("Breathe", "Colorwaves", "Fade"),
            "side": ("Colorwaves", "Flow", "Breathe"),
            "garage": ("Solid", "Breathe"),
        },
    },
    {
        "name": "silent_night",
        "palettes": ["Breeze", "Cloud", "Semi Blue"],
        "effects": {
            "apex": ("Fairytwinkle", "Fairy", "Glitter"),
            "peak": ("Twinkle", "Sparkle", "Colortwinkles"),
            "front": ("Fade", "Breathe", "Colorwaves"),
            "side": ("Aurora", "Stream", "Colorwaves"),
            "garage": ("Solid", "Breathe", "Fade"),
        },
    },
    {
        "name": "evergreen_glitter",
        "palettes": ["Forest", "Rivendell", "Landscape"],
        "effects": {
            "apex": ("Solid Glitter", "Glitter", "Sparkle"),
            "peak": ("Glitter", "Sparkle", "Colortwinkles"),
            "front": ("Colorwaves", "Flow", "Aurora"),
            "side": ("Aurora", "Pacifica", "Colorwaves"),
            "garage": ("Fade", "Breathe", "Solid"),
        },
    },
    {
        "name": "santas_sleigh",
        "palettes": ["Sunset 2", "Sunset", "Orangery", "C9"],
        "effects": {
            "apex": ("Sparkle", "Twinklefox", "Glitter"),
            "peak": ("Meteor Smooth", "Meteor", "Sparkle"),
            "front": ("Rain", "Colorwaves", "Drip"),
            "side": ("Chase 2", "Railway", "Theater"),
            "garage": ("Breathe", "Solid"),
        },
        "colors": {"side": [[255, 30, 30], [255, 200, 60]], "front": [[255, 220, 180], [255, 120, 40]]},
    },
]

# Generated by scripts/export-christmas-looks.ts from Eaveglow's library.json.
# In HA: /config/looks/holidays.json (copy the repo's homeassistant/looks dir).
# Falls back to the old christmas.json, then to the curated recipes below.
LOOKS_FILE = Path(__file__).resolve().parent.parent / "looks" / "holidays.json"
OLD_CHRISTMAS_FILE = LOOKS_FILE.with_name("christmas.json")


def load_looks_file() -> dict | None:
    """Prefer the all-holidays bundle; fall back to the old Christmas-only one."""
    for path in (LOOKS_FILE, OLD_CHRISTMAS_FILE):
        try:
            with path.open(encoding="utf-8") as handle:
                data = json.load(handle)
            for name, stops in (data.get("paletteStops") or {}).items():
                PALETTE_STOPS.setdefault(name, stops)
            return data
        except (OSError, ValueError):
            continue
    return None


def load_settings() -> dict | None:
    """Eaveglow's live settings on the controller (autopilot, hiddenLooks…)."""
    try:
        settings = get_json("/eaveglow.json")
        return settings if isinstance(settings, dict) else None
    except (urllib.error.URLError, OSError, ValueError):
        return None


def easter(year: int) -> date:
    """Anonymous Gregorian algorithm — matches src/engine/holidays.ts."""
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    return date(year, (h + l - 7 * m + 114) // 31, (h + l - 7 * m + 114) % 31 + 1)


def holiday_date(rule: str, year: int) -> date | None:
    """Port of Eaveglow's holidayDate() — fixed / easter / nth / last / dates."""
    kind, _, arg = rule.partition(":")
    try:
        if kind == "fixed":
            m, d = (int(x) for x in arg.split("-"))
            return date(year, m, d)
        if kind == "easter":
            return easter(year) + timedelta(days=int(arg))
        if kind == "nth":
            m, w, n = (int(x) for x in arg.split(":"))
            first = date(year, m, 1)
            return date(year, m, 1 + (w - first.isoweekday()) % 7 + (n - 1) * 7)
        if kind == "last":
            m, w = (int(x) for x in arg.split(":"))
            last = date(year, m + 1, 1) - timedelta(days=1) if m < 12 else date(year, 12, 31)
            return last - timedelta(days=(last.isoweekday() - w) % 7)
        if kind == "dates":
            hit = next((s for s in arg.split(",") if s.startswith(f"{year}-")), None)
            if hit:
                y, m, d = (int(x) for x in hit.split("-"))
                return date(y, m, d)
    except (ValueError, TypeError):
        return None
    return None


def season_range(rule: str, before: int, after: int, today: date) -> tuple[date, date] | None:
    """The Eaveglow season window that reaches today (daysBefore/daysAfter)."""
    for year in (today.year - 1, today.year, today.year + 1):
        day = holiday_date(rule, year)
        if day and day + timedelta(days=after) >= today:
            return day - timedelta(days=before), day + timedelta(days=after)
    return None


def usable_looks(holiday: dict | None, hidden: set[str]) -> list[dict]:
    looks = (holiday or {}).get("looks", [])
    return [l for l in looks if l.get("id") not in hidden]


def active_holiday(on_date: date, bundle: dict | None, settings: dict | None) -> dict | None:
    """Which Eaveglow holiday would be active today, with its non-hidden looks.

    Special dates win; on shared days the shorter season wins, matching
    Eaveglow's autopilot. A holiday whose looks are all ignored is skipped.
    """
    bundle = bundle or {}
    autopilot = (settings or {}).get("autopilot") or {}
    hidden = set((settings or {}).get("hiddenLooks") or [])
    by_id = {h["id"]: h for h in bundle.get("holidays", [])}
    if not autopilot.get("enabled"):
        return None

    # Special dates (game day, birthday…) beat seasons.
    pool = [l for h in by_id.values() for l in h["looks"]] + list(bundle.get("customLooks") or [])
    for special in autopilot.get("dates") or []:
        if not special.get("enabled"):
            continue
        try:
            start = date.fromisoformat(special["start"])
            end = date.fromisoformat(special.get("end") or special["start"])
        except (KeyError, ValueError):
            continue
        if special.get("everyYear"):
            span = (end - start).days
            shifted = None
            for year in (on_date.year - 1, on_date.year, on_date.year + 1):
                try:
                    candidate = start.replace(year=year)
                except ValueError:  # 29 February
                    continue
                if candidate <= on_date <= candidate + timedelta(days=span):
                    shifted = candidate
                    break
            if shifted is None:
                continue
            start, end = shifted, shifted + timedelta(days=span)
        if start <= on_date <= end:
            ids = set(special.get("lookIds") or [])
            looks = [l for l in pool if l.get("id") in ids and l.get("id") not in hidden]
            if looks:
                return {"id": special.get("id", "special"), "looks": looks}

    ranges = []
    for season in autopilot.get("seasons") or []:
        if not season.get("enabled"):
            continue
        holiday = by_id.get(season.get("holidayId"))
        if not holiday:
            continue
        window = season_range(holiday["rule"], season.get("daysBefore", 0), season.get("daysAfter", 0), on_date)
        if window:
            ranges.append((window[1] - window[0], holiday, window))
    for _, holiday, window in sorted(ranges, key=lambda r: r[0]):
        if window[0] <= on_date <= window[1]:
            looks = usable_looks(holiday, hidden)
            if looks:
                return {"id": holiday["id"], "looks": looks}
    return None


def families_for_effect(effect: str) -> set[str]:
    """Which zone families a look's effect naturally suits."""
    name = normalize(effect)
    if any(k in name for k in ("sparkle", "twinkle", "glitter", "candle", "fairy", "comet")):
        return {"apex", "peak"}
    if any(k in name for k in ("drip", "rain", "icicle", "snow")):
        return {"front"}
    if any(k in name for k in ("chase", "railway", "theater", "colorwaves", "flow",
                               "aurora", "pacifica", "stream", "meteor", "palette")):
        return {"side"}
    return {"garage"}


def recipe_from_look(entry: dict) -> dict:
    """Turn one Eaveglow Christmas look into a family/step recipe."""
    effect = entry.get("effect", "Solid")
    suited = families_for_effect(effect)
    effects = {}
    for family, base in FAMILIES.items():
        if family in suited:
            effects[family] = (effect,) + tuple(base["effects"][:2])
        else:
            effects[family] = tuple(base["effects"][:3])
    palette = entry.get("palette", "")
    palettes = ([palette] if palette else []) + [p for p in PALETTES if p != palette][:4]
    return {
        "name": entry.get("id", "eaveglow"),
        "palettes": palettes,
        "effects": effects,
        "colors": {f: entry.get("colors") or base["colors"] for f, base in FAMILIES.items()},
    }


def bundle_matches_layout(bundle: dict | None, segments: list[dict]) -> bool:
    """Exact payloads are safe only for the layout they were compiled against."""
    if not bundle:
        return False
    fingerprint = bundle.get("fingerprint") or []
    actual = [[s.get("id"), s.get("start"), s.get("stop")] for s in segments]
    return bool(fingerprint) and fingerprint == actual


def look_payload(entry: dict) -> dict | None:
    """The exact compiled WLED state for one Eaveglow Christmas look."""
    payload = entry.get("payload") or {}
    segs = payload.get("seg") or []
    if not segs:
        return None
    return {"on": True, "transition": 7, "seg": segs}


# ---------------------------------------------------------------------------
# Zone families from Eaveglow's DEFAULT_GENERATION_RULES, with the wild
# effects (Fireworks, Strobe, Blink, Plasma, Bpm, Scanner) removed.
# Order matters only for name matching; priority is explicit.
# ---------------------------------------------------------------------------
FAMILIES = {
    "apex": {
        "priority": 100,
        "keywords": ("apex",),
        "effects": ("Sparkle", "Twinklefox", "Twinkle", "Glitter", "Sparkle+",
                    "Fairytwinkle", "Colortwinkles"),
        "colors": [[255, 120, 30], [255, 200, 150]],
    },
    "peak": {
        "priority": 80,
        "keywords": ("peak",),
        "effects": ("Sparkle", "Twinkle", "Glitter", "Sparkle+", "Colortwinkles",
                    "Twinklecat"),
        "colors": [[255, 220, 50], [255, 170, 0], [255, 255, 255]],
    },
    "front": {
        "priority": 40,
        "keywords": ("front", "soffit"),
        "effects": ("Rain", "Drip", "Drip Drop", "Colorwaves", "Flow", "Aurora",
                    "Pacifica", "Lake", "Stream"),
        "colors": [[255, 255, 255], [200, 220, 255], [180, 200, 255]],
    },
    "side": {
        "priority": 35,
        "keywords": ("side",),
        "effects": ("Colorwaves", "Flow", "Aurora", "Pacifica", "Stream", "Rain"),
        "colors": [[100, 200, 255], [50, 150, 255], [0, 100, 200]],
    },
    "garage": {
        "priority": 30,
        "keywords": ("garage",),
        "effects": ("Solid", "Breathe", "Fade", "Colorloop", "Gradient"),
        "colors": [[255, 180, 120], [255, 200, 150]],
    },
    "fallback": {
        "priority": 0,
        "keywords": (),
        "effects": ("Solid", "Breathe", "Fade"),
        "colors": [[255, 200, 150]],
    },
}


def get_json(path: str):
    with urllib.request.urlopen(BASE_URL + path, timeout=TIMEOUT) as resp:
        return json.load(resp)


def post_json(path: str, payload: dict) -> str:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        BASE_URL + path,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read().decode("utf-8", "replace")


def normalize(name: str) -> str:
    """Match Eaveglow's EffectCatalog normalisation (@suffix stripped)."""
    return name.split("@")[0].strip().lower()


def resolve_id(names: list[str], candidates) -> int | None:
    lookup = {normalize(n): i for i, n in enumerate(names)}
    for candidate in candidates:
        idx = lookup.get(normalize(candidate))
        if idx is not None:
            return idx
    return None


def resolve_palette(names: list[str], name: str) -> int | None:
    """Resolve a palette name, with or without Eaveglow's ★ marker."""
    plain = name[2:] if name.startswith("★ ") else name
    for candidate in (name, plain):
        idx = resolve_id(names, [candidate])
        if idx is not None:
            return idx
    return None


def stops_for(name: str) -> list[list[int]]:
    """Approximate gradient stops for a built-in or ★ palette."""
    plain = name[2:] if name.startswith("★ ") else name
    return PALETTE_STOPS.get(plain, [[255, 170, 90], [255, 255, 255]])


def blend_colors(family_colors: list[list[int]], palette_colors: list[list[int]]) -> list[list[int]]:
    """Keep a zone family's character while tinting it with the shared palette."""
    blended = []
    for i in range(3):
        base = family_colors[min(i, len(family_colors) - 1)]
        accent = palette_colors[min(i, len(palette_colors) - 1)]
        blended.append([round(base[j] * 0.6 + accent[j] * 0.4) for j in range(3)])
    return blended


COLOR_VARIATIONS = (
    (1.0, 1.0, 1.0),
    (1.18, 0.92, 0.80),
    (0.85, 1.08, 1.18),
    (1.05, 0.80, 1.20),
    (1.20, 1.12, 0.72),
    (0.78, 1.20, 0.95),
    (0.90, 1.15, 0.85),
    (1.10, 1.05, 0.90),
    (0.95, 0.90, 1.25),
    (1.25, 0.95, 0.85),
    (0.80, 1.10, 1.10),
    (1.15, 0.85, 1.05),
    (1.00, 1.20, 0.85),
    (0.85, 0.95, 1.20),
    (1.05, 1.15, 1.00),
)


def vary_color(colors: list[list[int]], index: int) -> list[list[int]]:
    """Give each segment its own tint while keeping its family's character."""
    factor = COLOR_VARIATIONS[index % len(COLOR_VARIATIONS)]
    return [
        [min(255, round(c[0] * factor[0])),
         min(255, round(c[1] * factor[1])),
         min(255, round(c[2] * factor[2]))]
        for c in colors
    ]


def classify(segment_name: str) -> str:
    """Highest-priority family whose keyword appears in the segment label."""
    lower = segment_name.lower()
    for family in sorted(FAMILIES.values(), key=lambda f: f["priority"], reverse=True):
        if any(k in lower for k in family["keywords"]):
            return next(name for name, f in FAMILIES.items() if f is family)
    return "fallback"


def build_look(state: dict, effects: list[str], palettes: list[str], rng: random.Random,
               christmas: bool = False, recipes: list[dict] | None = None):
    """Return (updates, description) without touching the controller."""
    segments = state.get("seg", [])
    if not segments:
        raise RuntimeError("WLED reported no segments; nothing to update.")

    # Eaveglow's calm built-ins that this controller actually has installed.
    installed = [p for p in PALETTES if resolve_palette(palettes, p) is not None]
    if not installed:
        raise RuntimeError("None of the curated palettes are installed on this controller.")

    if christmas:
        # Prefer styles from Eaveglow's real Christmas looks when the generated
        # bundle is available; otherwise use the curated recipes below.
        pool = recipes if recipes else CHRISTMAS_RECIPES
        usable = [
            (r, [p for p in r["palettes"] if resolve_palette(palettes, p) is not None])
            for r in pool
        ]
        usable = [(r, p) for r, p in usable if p]
        if usable:
            recipe, scheme = rng.choice(usable)
            scheme_name = recipe["name"]
            defs: dict[str, dict] = {}
            for name, base in FAMILIES.items():
                d = dict(base)
                if name in recipe.get("effects", {}):
                    d["effects"] = recipe["effects"][name]
                if name in recipe.get("colors", {}):
                    d["colors"] = recipe["colors"][name]
                defs[name] = d
        else:
            scheme, scheme_name, defs = installed, "christmas-fallback", FAMILIES
    else:
        moods = [(name, m) for name, m in PALETTE_MOODS.items() if any(p in installed for p in m)]
        if moods:
            mood_name, mood = rng.choice(moods)
        else:
            mood_name, mood = "mixed", tuple(installed)
        scheme = [p for p in mood if p in installed]
        scheme_name, defs = mood_name, FAMILIES

    groups: dict[str, list[int]] = {}
    seg_index: dict[int, int] = {}
    for i, seg in enumerate(segments):
        family = classify(seg.get("n", ""))
        groups.setdefault(family, []).append(seg.get("id", 0))
        seg_index[seg.get("id", 0)] = i

    family_order = sorted(groups, key=lambda k: defs[k]["priority"])
    picks = rng.sample(scheme, min(len(scheme), len(family_order)))
    while len(picks) < len(family_order):
        picks.append(rng.choice(scheme))
    family_palette_names = {family: name for family, name in zip(family_order, picks)}

    # One effect per family, but a different palette and tint per segment.
    segment_palettes: dict[int, tuple[str, int]] = {}
    segment_colors: dict[int, list[list[int]]] = {}
    for family in family_order:
        base_name = family_palette_names[family]
        choices = [base_name] + [p for p in scheme if p != base_name]
        for seg_id in groups[family]:
            n = seg_index.get(seg_id, 0)
            name = choices[n % len(choices)]
            segment_palettes[seg_id] = (name, resolve_palette(palettes, name) or 0)
            stops = [c for c in stops_for(name) if any(v > 20 for v in c)][:2]
            if not stops:
                stops = [[255, 170, 90], [255, 255, 255]]
            accent = (stops + [[0, 0, 0], [0, 0, 0]])[:3]
            segment_colors[seg_id] = vary_color(
                blend_colors(defs[family]["colors"], accent), n
            )

    # Shared rhythm, kept deliberately gentle.
    speed = rng.randint(75, 110)
    intensity = rng.randint(120, 160)

    used: set[int] = set()
    assigned: dict[int, int] = {}
    chosen: dict[str, str] = {}
    for family in sorted(defs, key=lambda k: defs[k]["priority"]):
        ids = groups.get(family)
        if not ids:
            continue
        available = []
        for name in defs[family]["effects"]:
            idx = resolve_id(effects, [name])
            if idx is not None:
                available.append((idx, name))
        unused = [pair for pair in available if pair[0] not in used]
        pool = unused or available
        if pool:
            effect_id, effect_name = rng.choice(pool)
        else:
            effect_id = resolve_id(effects, ["Solid", "Fade"]) or 0
            effect_name = effects[effect_id] if effect_id < len(effects) else "Solid"
        used.add(effect_id)
        chosen[family] = effect_name
        for seg_id in ids:
            assigned[seg_id] = effect_id

    updates = []
    for seg in segments:
        seg_id = seg.get("id", 0)
        updates.append({
            "id": seg_id,
            "on": True,
            "fx": assigned.get(seg_id, 0),
            "sx": max(16, min(250, speed + rng.randint(-10, 10))),
            "ix": max(16, min(250, intensity + rng.randint(-10, 10))),
            "pal": segment_palettes.get(seg_id, ("Default", 0))[1],
            "col": segment_colors.get(
                seg_id, [[255, 170, 90], [255, 255, 255], [0, 0, 0]]
            ),
        })

    varied = len({(s["pal"], tuple(tuple(c) for c in s["col"])) for s in updates})
    label = "recipe" if christmas else "mood"
    summary = (
        f"{label}={scheme_name} speed={speed} intensity={intensity} varied={varied} "
        + " ".join(f"{k}={v}/{family_palette_names[k]}" for k, v in chosen.items())
    )
    return updates, summary


def signature(segments: list[dict]) -> tuple:
    """(palettes, effects) pair, used to avoid picking the same look twice."""
    return (
        tuple(s.get("pal") for s in segments),
        tuple(s.get("fx") for s in segments),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="print the chosen look without sending it to WLED")
    parser.add_argument("--force-christmas", action="store_true",
                        help="use a Christmas recipe regardless of date (for testing)")
    parser.add_argument("--no-christmas", action="store_true",
                        help="use the normal mood generator regardless of date")
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--exact-only", action="store_true",
                            help="Christmas: only post precompiled Eaveglow looks")
    mode_group.add_argument("--adapt-only", action="store_true",
                            help="Christmas: only adapt a look's style to the zone families")
    parser.add_argument("--date", metavar="YYYY-MM-DD",
                        help="pretend it is this date (for testing)")
    args = parser.parse_args()

    try:
        on_date = date.fromisoformat(args.date) if args.date else date.today()
    except ValueError:
        print(f"ERROR: --date must be YYYY-MM-DD, got {args.date!r}", file=sys.stderr)
        return 2
    christmas = args.force_christmas
    bundle = load_looks_file()
    settings = load_settings()
    hidden = set((settings or {}).get("hiddenLooks") or [])
    holiday = None
    if christmas:
        # Testing override: pick Christmas's looks even outside its season.
        group = next((h for h in (bundle or {}).get("holidays", []) if h["id"] == "christmas"), None)
        bundle_looks = (bundle or {}).get("looks") or []
        if not group and bundle_looks:
            group = {"id": "christmas", "looks": bundle_looks}
        looks = usable_looks(group, hidden)
        if looks:
            holiday = {"id": "christmas", "looks": looks}
    elif not args.no_christmas:
        # All holidays, Christmas included, follow Eaveglow's autopilot calendar.
        holiday = active_holiday(on_date, bundle, settings)

    if args.date or args.force_christmas or args.no_christmas or holiday:
        print(f"Season: {holiday['id'] if holiday else 'normal'} on {on_date}")

    try:
        state = get_json("/json")["state"]
        effects = get_json("/json/effects")
        palettes = get_json("/json/palettes")
    except (urllib.error.URLError, OSError, ValueError, KeyError) as exc:
        print(f"ERROR: could not read WLED state from {BASE_URL}: {exc}", file=sys.stderr)
        return 1

    segments = state.get("seg", [])
    current = signature(segments)
    rng = random.Random()

    # Eaveglow looks can be posted exactly or adapted to the zone families.
    entries = holiday["looks"] if holiday else []
    layout_ok = bundle_matches_layout(bundle, segments)
    exact = [e for e in entries if look_payload(e)] if layout_ok else []
    if entries and not layout_ok:
        print("NOTE: compiled payloads don't match this layout; using adapted styles only")
    mode = "adapt"
    if exact:
        if args.exact_only:
            mode = "exact"
        elif args.adapt_only:
            mode = "adapt"
        else:
            mode = rng.choice(("exact", "adapt"))

    if mode == "exact":
        entry = exact[0]
        payload = look_payload(entry) or {"on": True, "transition": 7, "seg": segments}
        for _ in range(12):
            entry = rng.choice(exact)
            found = look_payload(entry)
            if found is None:
                continue
            payload = found
            if signature(payload["seg"]) != current:
                break
        summary = f"exact={entry['name']} (Eaveglow look)"
    else:
        recipes = [recipe_from_look(e) for e in entries if e.get("effect")] if entries else None
        updates, summary = build_look(state, effects, palettes, rng, bool(entries), recipes)
        for _ in range(12):
            if signature(updates) != current:
                break
            updates, summary = build_look(state, effects, palettes, rng, bool(entries), recipes)
        payload = {"on": True, "transition": 7, "seg": updates}

    if args.dry_run:
        print(f"DRY RUN: {summary} [{mode}]")
        print(json.dumps(payload, indent=2))
        return 0

    try:
        post_json("/json/state", payload)
    except (urllib.error.URLError, OSError) as exc:
        print(f"ERROR: could not apply look to {BASE_URL}: {exc}", file=sys.stderr)
        return 1

    print(f"Applied new look: {summary} [{mode}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
