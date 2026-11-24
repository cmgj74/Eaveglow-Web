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

## Palettes

Holiday looks prefer **on-theme palettes** so Christmas displays use C9, C9 New,
Candy, Vintage, Autumn, Sakura and Sunset 2 instead of generic fallback palettes.
When a look's own palette is a custom **★** palette, HA reads it live from the
controller's `/paletteN.json` files (WLED ids count down from 200). If it isn't
installed, HA uploads the palette definition from `/eaveglow-library.json` into
the first free slot before applying the look — no manual palette copying. Dry
runs only scan; they never install.

## Holidays

**Every holiday, Christmas included, follows Eaveglow's autopilot calendar**
from `/eaveglow.json`: each season's `daysBefore`/`daysAfter`, its enabled
flag, and Eaveglow's overlap rule (special dates first, then the shorter
season wins). If autopilot is off, or no holiday is selected, the script falls
back to the normal mood look. A holiday whose looks are all in `hiddenLooks`
is skipped; if only some are hidden, the rest are used.

To keep HA as the only automation, leave Eaveglow's Schedule off while its
Autopilot stays on — otherwise WLED's dated season presets will apply looks
at on-times and fight with HA. `--force-christmas` is a testing override that
ignores the calendar.

Eaveglow serves its look library at `/eaveglow-library.json` and the generator
at `/eaveglow-ha.py`. The HA shell command downloads the generator **on every
run**, and the generator reads the library, segments, settings and effect
metadata live from the controller — nothing is installed by hand and there is
no bundle to regenerate. It either adapts a look's effect/colours to the zone
families (`--adapt-only`) or compiles the exact Eaveglow look against the
current segments (`--exact-only`), alternating by default.

Open Eaveglow and tap **🏡 Install to HA** for the ready-to-paste shell command
and automation.

## HA files

| HA file | Purpose |
| --- | --- |
| `/config/shell_commands.yaml` | `wled_random_look:` bootstrap (downloads and runs `/eaveglow-ha.py`, logs timestamp + SHA-256 to `/eaveglow_runs.log`) — **restart HA after changing this file** |
| `/config/automations.yaml` | `wled_sunset_random_look` automation |

The generator itself lives on the controller (`/eaveglow-ha.py`), not in HA —
updating Eaveglow updates HA's behaviour automatically. Example snippets are
versioned in [`homeassistant/`](../homeassistant/README.md).

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
