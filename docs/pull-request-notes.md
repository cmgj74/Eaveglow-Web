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

Earlier commits in the same PR add the WLED segment import/sync fixes, the coherent generator with seeds, the 👀 Test on lights button with one-click restore, and the top-of-page placement of that button.

## Verification

- `npm test`: 82/82 passing (10 files).
- `npm run build`: clean; `dist/eaveglow.htm.gz` 57.4 KB against the 60 KB limit.
- Uploaded to `wled-dig-octa-32-8l` (192.168.1.230); served bundle SHA-256 matches the local build.
- Live WLED state confirmed 20 unique palette/color combinations across 20 segments, with one shared effect per family.

## Notes

- No changes to `configuration.yaml`, automations or installed files in this repository — only look generation, tests and documentation.
- The earlier `docs/home-assistant-random-look.yaml` package remains as-is; it describes a different, WLED-integration-based approach.
