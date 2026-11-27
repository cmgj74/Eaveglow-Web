# Pull request notes — PR #9

**PR:** https://github.com/DakotaRidgeTechnology/Eaveglow-Web/pull/9
**Title:** v1.3.2 — WLED import zones, overlap warnings, segment sync, coherent look generator, test on lights, per-zone palettes
**Base:** `DakotaRidgeTechnology/main`  ·  **Head:** `cmgj74/main`

## Summary

These changes are part of the open PR #9 (not a separate PR). They make Eaveglow's coherent generator produce a house that is uniform within each zone family but visibly different across families and individual zones.

- The `🤖 Generate from zones` button now defaults to coherent mode.
- Coherent generation emits **one layer per zone** rather than one per family group. A controller with 32 segments (e.g. 20 zones) fits without simplification.
- One effect is chosen per family, randomly and deduped, so all peaks share an effect but not a color; the same applies to fronts, sides and apex.
- One coordinated mood is chosen per look (`warm`, `cool`, `nature`, `festive`), with a different palette for every zone and a per-zone color tint blended from the family's traditional colors.
- Wild effects were removed from the coherent family keyword lists: `firework`, `scanner`, `juggle`, `blink`, `strobe`.
- Faithful-mode effect lists were reordered so apex ≠ peak and front ≠ side.
- Added `docs/home-assistant-coherent-look.md` describing the actual HA randomizer that drives the controller at sunset (20–40 minute random interval, stopping before the 23:00 WLED off timer).
- The HA generator picks a random curated Christmas recipe (8 recipes) using the same family/per-segment machinery, with `--date`, `--force-christmas` and `--no-christmas` flags for testing. Added `homeassistant/tests/test_wled_random_look.py`.
- HA now uses Eaveglow's **real looks for all 14 holidays** (Christmas included) two ways: adapted to the zone families (`--adapt-only`) or the exact Eaveglow look compiled live against the current segments (`--exact-only`). Every holiday follows Eaveglow's autopilot dates from `/eaveglow.json`; all-hidden holidays are skipped and days with no holiday fall back to the normal mood.
- Everything HA needs is published by Eaveglow to the controller (`/eaveglow-ha.py`, `/eaveglow-library.json`) and fetched at run time — no static bundle, no manual file copies, no regeneration. A **🏡 Install to HA** page generates the ready-to-paste shell command and automation using the controller's real address.
- Holiday looks now prefer **on-theme palettes** — Christmas uses C9, C9 New, Candy, Sakura, Jul and the custom ★ Christmas palettes — instead of generic warm fallbacks. The 9 warm/amber Christmas looks (Gingerbread, Twinkle Stars, etc.) are skipped in HA's rotation only; Eaveglow still has all 28. Adapted looks use each family's neutral base so the palette, not one look's orange base color, supplies the seasonal color.
- Eaveglow's custom **★ palettes** are resolved live from `/paletteN.json` (WLED ids count down from 200). If a selected look needs a ★ palette that isn't installed, HA uploads its definition from the live library into the first free slot before applying. Dry runs only scan. Verified with `★ Peppermint` (id 189) and by installing `★ Candy Corn` on the controller.
- Before each look, HA compares WLED's segment **geometry** with Eaveglow's saved `layout.zones`. A preset with no `seg` can collapse the controller to one unnamed segment; HA restores the 20 saved segments (with names) before compiling. Renamed segments and `rev` flags are left alone.
- The **Autopilot card is always editable** and saving with Schedule OFF writes only `/eaveglow.json` — it no longer calls `applySchedule`, so editing the holiday calendar never replaces WLED's on/off timers. The original sunset-on / 23:00-off timers can be restored from `/eaveglow-timers-backup.json`.
- The Python `compileLook` port is golden-tested against the TypeScript compiler (`homeassistant/tests/fixtures_compiled.json`); 21 Python tests cover date rules, season selection, hidden looks, palette resolution/install, layout repair, festive rotation and exact compilation.
- To keep HA as the only automation, Eaveglow's Schedule should be off while Autopilot stays on; otherwise WLED's dated season presets apply looks at on-times and compete with HA. With Schedule off, autopilot is purely a calendar for HA. Documented in `homeassistant/README.md`.
- Every HA run appends a timestamp, the downloaded script's SHA-256, and the applied look to `/config/eaveglow_runs.log`, so the exact generator version behind any night's looks is auditable. The generated shell command on the Install to HA page includes this.
- All HA knobs are now configurable from the **🏡 Install to HA** page and stored in `/eaveglow.json` under `ha`: controller address (used in the generated shell command), min/max look interval, cutoff hour/minute, look mode (random/exact/adapted), speed and intensity ranges, and whether warm Christmas looks are allowed. HA `command_line` sensors read the timing values live, so interval/cutoff changes take effect without editing HA. The generator reads mode, ranges and warm-look preference on every run.

Earlier commits in the same PR add the WLED segment import/sync fixes, the coherent generator with seeds, the 👀 Test on lights button with one-click restore, and the top-of-page placement of that button.

## Verification

- `npm test`: 82/82 passing (10 files).
- `npm run build`: clean; `dist/eaveglow.htm.gz` 58.2 KB against the 60 KB limit.
- `python3 -m unittest discover -s homeassistant/tests`: 21/21 passing.
- Uploaded to `wled-dig-octa-32-8l` (192.168.1.230); served bundle and HA script SHA-256 match the local build.
- Live WLED state confirmed 20 unique palette/color combinations across 20 segments, with one shared effect per family.
- Live tests confirmed `★ Peppermint` (id 189), `★ Grinch` (id 182) and `★ Candy Corn` (id 178) applied to the controller; exact Candy Cane Twinkle compiled with palette 189.
- Live self-repair verified: a collapsed 1-segment layout was restored to 20 saved zones before applying a look. Six exact-mode Christmas dry runs after the festive filter contained no warm/amber looks.
- WLED sunset-on / 23:00-off timers restored from `/eaveglow-timers-backup.json`; all other config sections verified unchanged.

## Notes

- No changes to `configuration.yaml`, automations or installed files in this repository — only look generation, tests and documentation.
- The earlier `docs/home-assistant-random-look.yaml` package remains as-is; it describes a different, WLED-integration-based approach.
