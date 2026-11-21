#!/usr/bin/env python3
"""Pick a new, tasteful look for the permanent lights at sunset.

Port of Eaveglow's "coherent" look generator (src/engine/lookGenerator.ts):
one palette for the whole house, a family-appropriate effect per zone type,
and shared calm speed/intensity. Zone types come from the WLED segment
labels (seg.n) that Eaveglow already wrote to the controller.

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


def build_look(state: dict, effects: list[str], palettes: list[str], rng: random.Random):
    """Return (updates, description) without touching the controller."""
    segments = state.get("seg", [])
    if not segments:
        raise RuntimeError("WLED reported no segments; nothing to update.")

    # One palette for the whole look, chosen from Eaveglow's calm built-ins
    # that this controller actually has installed.
    installed = [p for p in PALETTES if resolve_id(palettes, [p]) is not None]
    if not installed:
        raise RuntimeError("None of the curated palettes are installed on this controller.")

    # One coordinated mood per run, a different palette from it per group.
    moods = [(name, m) for name, m in PALETTE_MOODS.items() if any(p in installed for p in m)]
    if moods:
        mood_name, mood = rng.choice(moods)
    else:
        mood_name, mood = "mixed", tuple(installed)
    mood_installed = [p for p in mood if p in installed]

    groups: dict[str, list[int]] = {}
    seg_family: dict[int, str] = {}
    for seg in segments:
        family = classify(seg.get("n", ""))
        groups.setdefault(family, []).append(seg.get("id", 0))
        seg_family[seg.get("id", 0)] = family

    family_order = sorted(groups, key=lambda k: FAMILIES[k]["priority"])
    picks = rng.sample(mood_installed, min(len(mood_installed), len(family_order)))
    while len(picks) < len(family_order):
        picks.append(rng.choice(mood_installed))
    family_palette_names = {family: name for family, name in zip(family_order, picks)}

    # Within a family the effect stays uniform, but each segment gets its own
    # palette and tint so individual peaks / soffits differ from each other.
    segment_palettes: dict[int, tuple[str, int]] = {}
    segment_colors: dict[int, list[list[int]]] = {}
    for family in family_order:
        base_name = family_palette_names[family]
        choices = [base_name] + [p for p in mood_installed if p != base_name]
        for n, seg_id in enumerate(groups[family]):
            name = choices[n % len(choices)]
            segment_palettes[seg_id] = (name, resolve_id(palettes, [name]))
            stops = [c for c in PALETTES[name] if any(v > 20 for v in c)][:2]
            if not stops:
                stops = [[255, 170, 90], [255, 255, 255]]
            accent = (stops + [[0, 0, 0], [0, 0, 0]])[:3]
            segment_colors[seg_id] = vary_color(
                blend_colors(FAMILIES[family]["colors"], accent), n
            )

    # Shared rhythm, kept deliberately gentle.
    speed = rng.randint(75, 110)
    intensity = rng.randint(120, 160)

    used: set[int] = set()
    assigned: dict[int, int] = {}
    chosen: dict[str, str] = {}
    for family in sorted(FAMILIES, key=lambda k: FAMILIES[k]["priority"]):
        ids = groups.get(family)
        if not ids:
            continue
        # Resolve every candidate this controller actually has, then choose
        # one at random. Prefer an effect no other family used this run so
        # each group looks visibly different from the others.
        available = []
        for name in FAMILIES[family]["effects"]:
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
    summary = (
        f"mood={mood_name} speed={speed} intensity={intensity} varied={varied} "
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
    args = parser.parse_args()

    try:
        state = get_json("/json")["state"]
        effects = get_json("/json/effects")
        palettes = get_json("/json/palettes")
    except (urllib.error.URLError, OSError, ValueError, KeyError) as exc:
        print(f"ERROR: could not read WLED state from {BASE_URL}: {exc}", file=sys.stderr)
        return 1

    current = signature(state.get("seg", []))
    rng = random.Random()
    updates, summary = build_look(state, effects, palettes, rng)
    for _ in range(12):
        if signature(updates) != current:
            break
        updates, summary = build_look(state, effects, palettes, rng)

    if args.dry_run:
        print(f"DRY RUN: {summary}")
        print(json.dumps({"on": True, "transition": 7, "seg": updates}, indent=2))
        return 0

    try:
        post_json("/json/state", {"on": True, "transition": 7, "seg": updates})
    except (urllib.error.URLError, OSError) as exc:
        print(f"ERROR: could not apply look to {BASE_URL}: {exc}", file=sys.stderr)
        return 1

    print(f"Applied new look: {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
