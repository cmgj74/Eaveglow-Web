# Home Assistant files (copied from the running setup)

These are copies of the files currently installed in the HA container, kept
here so they are versioned alongside Eaveglow. They are **snippets**, not a
drop-in replacement for your whole HA config.

| File in this repo | Installed at | Notes |
| --- | --- | --- |
| `scripts/wled_random_look.py` | `/config/scripts/wled_random_look.py` | Python 3 stdlib only; copy when deploying. |
| `looks/christmas.json` | `/config/looks/christmas.json` | Generated from Eaveglow's `library.json`; 28 Christmas looks, adapted styles + exact payloads. |
| `shell_commands.yaml` | `/config/shell_commands.yaml` | Merge the `wled_random_look:` line into your existing file. |
| `automations.yaml` | `/config/automations.yaml` | Merge only the `wled_sunset_random_look` list item into your existing list. |

The HA config also contains unrelated automations and shell commands; those
are deliberately **not** included here.

## Behaviour

At sunset, HA applies a new curated look and repeats every random 20–40
minutes until 23:00, leaving the controller's `Eaveglow: Lights Off` WLED timer
(preset 249) in control after that. The generator follows Eaveglow's coherent
rules: one coordinated mood per run, one deduped effect per zone family, and a
different palette and tint for every segment (identified by its `seg.n` label).
Only `fx`, `sx`, `ix`, `pal` and `col` are sent, so the segment layout is
preserved.

The WLED address is `192.168.1.230`, set by `WLED_HOST` near the top of the
script. `WLED_URL` overrides it for testing.

## All Eaveglow holidays

**Every holiday, Christmas included, follows Eaveglow's autopilot calendar**
from `/eaveglow.json`: each season's `daysBefore`/`daysAfter`, its enabled
flag, and Eaveglow's overlap rule (special dates first, then the shortest
season). If autopilot is off, or no holiday would be selected, the generator
falls back to the normal mood look.

If **all** of a holiday's looks are in Eaveglow's `hiddenLooks`, that holiday
is skipped entirely. If only some are hidden, the rest are used.

`looks/holidays.json` is generated from Eaveglow's `library.json` by
`node_modules/.bin/vite-node scripts/export-christmas-looks.ts`. It contains
all 14 holidays' looks in two forms:

- **Adapted style** — effect, palette and colours mapped onto the current zone
  families (`--adapt-only`)
- **Exact look** — the WLED state Eaveglow compiles for that look against your
  segment layout (`--exact-only`)

By default the script alternates the two. Exact payloads are guarded by a
layout fingerprint: if you change your zones, regenerate the bundle or it
automatically falls back to adapted styles. `christmas.json` is kept for older
setups.

### Letting HA be the only automation

Eaveglow's autopilot also writes WLED timers with dated season presets. If
**Schedule** is on, WLED will apply those presets itself and fight with HA.
To use Eaveglow only as the holiday calendar:

1. Schedule page → turn **Automatic on & off** ON, turn **Seasonal autopilot** ON, **Save**
2. Turn **Automatic on & off** OFF again, **Save**

The seasons stay in `/eaveglow.json`, but WLED's timers are switched off, so
only HA changes the look. Check with:

```
python3 -c "import json,urllib.request; s=json.load(urllib.request.urlopen('http://192.168.1.230/eaveglow.json')); print('schedule',s['schedule']['enabled'],'autopilot',s['autopilot']['enabled'])"
```

Test the season calendar without waiting for the holiday:

```
python3 /config/scripts/wled_random_look.py --dry-run --date 2026-10-25   # Halloween
python3 /config/scripts/wled_random_look.py --dry-run --date 2026-11-30   # Christmas
python3 /config/scripts/wled_random_look.py --dry-run --force-christmas    # testing override
python3 /config/scripts/wled_random_look.py --dry-run --no-christmas       # normal look
```

Install the bundle on HA alongside the script:

```
cp -R ~/Documents/Git/Eaveglow-Web/homeassistant/looks /Volumes/config/looks/
```

Run the Python tests from the repo root:
`python3 -m unittest discover -s homeassistant/tests -v`

## Operating it

- Dry run (prints the look, changes nothing):
  `python3 /config/scripts/wled_random_look.py --dry-run`
- Apply one look: Developer Tools → Actions → `shell_command.wled_random_look`
- Run the automation manually to start a fresh loop; the shell command applies
  one look only.
- Editing `automations.yaml` or restarting HA stops a running loop.
- Applying a look from Eaveglow overrides the HA look until the next cycle.

Note: the automation's entity ID stays
`automation.wled_random_look_every_30_60_min_until_23_00` because HA keeps the
original ID when only the display name changes.

See `docs/home-assistant-coherent-look.md` for the full description.
