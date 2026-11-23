# Home Assistant "coherent look" randomizer (actual installed setup)

This is the HA side that complements Eaveglow's coherent generator. It is not
the older `docs/home-assistant-random-look.yaml` package (which uses the WLED
HA integration and a fixed 30-minute schedule).

## What it does

At sunset HA starts a loop that applies a new curated look to the WLED
controller, then waits a **random 20–40 minutes** before applying another.
The loop stops before 23:00 so the controller's existing `Eaveglow: Lights Off`
timer (preset 249, scheduled by WLED) stays in control. It never turns the
lights back on after that timer fires.

Each generated look follows Eaveglow's coherent rules:

- Reads WLED's current segments (`GET /json`) and their labels (`seg.n`).
- Classifies segments by label: `apex`, `peak`, `front`/`soffit`, `side`,
  `garage`, fallback.
- Chooses **one effect per family** (random, deduped, from a calm list — no
  Fireworks, Strobe, Blink, Plasma or Scanner). All peaks share an effect, all
  soffits share another, and so on.
- Chooses one coordinated **mood** (`warm`, `cool`, `nature`, `festive`), then a
  **different palette for every individual segment** from that mood, so each
  peak/soffit/side/apex has its own colors even though its effect matches its
  family.
- Blends each family's traditional colors with its zone's palette and applies a
  per-zone tint. Sends three colors per segment.
- Keeps speed 75–110 and intensity 120–160 with small per-segment jitter.
- Preserves the existing segment layout — only `fx`, `sx`, `ix`, `pal` and
  `col` are sent.
- Re-rolls up to 12 times if it would repeat the current look.

## Christmas season

From **Thanksgiving evening through 26 December** the same machinery picks a
random curated Christmas recipe instead of a normal mood — `christmas_classic`,
`candy_cane`, `snowfall`, `tree_lights`, `gingerbread`, `silent_night`,
`evergreen_glitter` or `santas_sleigh`. Each keeps the zone-family structure
(apex twinkle, peak sparkle, front drip/snow, side chase/flow, garage calm)
while giving every segment its own palette and tint. Custom ★ Christmas
palettes are preferred when installed on the controller, with built-in
fallbacks. Cadence (20–40 min) and the 23:00 cutoff are unchanged.

Use `--date`, `--force-christmas` or `--no-christmas` with `--dry-run` to test
either side of the window without changing the lights.

Eaveglow's 28 real Christmas looks are bundled in `homeassistant/looks/christmas.json`,
generated from `src/engine/library.json` by
`node_modules/.bin/vite-node scripts/export-christmas-looks.ts`. The HA script
uses them two ways: it either adapts a look's effect/colours to the zone
families (`--adapt-only`) or posts the exact compiled WLED state for that look
against your current segment layout (`--exact-only`). By default it alternates
the two. Exact payloads are guarded by a layout fingerprint — regenerate the
bundle after changing zones.

## Files (HA container paths)

| File | Purpose |
| --- | --- |
| `/config/scripts/wled_random_look.py` | Python 3 generator (stdlib only) |
| `/config/shell_commands.yaml` | `wled_random_look: python3 /config/scripts/wled_random_look.py` |
| `/config/automations.yaml` | `wled_sunset_random_look` automation |

Copies are versioned in this repo under [`homeassistant/`](../homeassistant/README.md): the Python script is verbatim, and the two YAML files contain only the relevant entries (merge them into your existing HA files — they are not full replacements).

The WLED address is `192.168.1.230` (`WLED_HOST` near the top of the script);
`WLED_URL` overrides it for testing.

## Automation

```yaml
- id: wled_sunset_random_look
  alias: "WLED - Random look every 20-40 min until 23:00"
  trigger:
    - platform: sun
      event: sunset
  condition: []
  action:
    - repeat:
        while:
          - condition: template
            value_template: "{{ now() < today_at('23:00') }}"
        sequence:
          - action: shell_command.wled_random_look
          - delay:
              minutes: "{{ range(20, 41) | random }}"
  mode: single
```

Note: the automation entity ID remains
`automation.wled_random_look_every_30_60_min_until_23_00` because HA keeps the
original ID when only the display name changes.

## Operating it

- Dry run (no light change):
  `python3 /config/scripts/wled_random_look.py --dry-run`
- Apply one look: Developer Tools → Actions → `shell_command.wled_random_look`
- Run the **automation** manually to start a fresh 20–40 min loop; the shell
  command applies only a single look.
- Editing `automations.yaml` or restarting HA stops a running loop. It resumes
  at the next sunset, or can be started manually as above.
- Applying any look from Eaveglow overwrites the current HA-generated look
  until the next 20–40 minute cycle.
