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

## Christmas season

From **Thanksgiving evening (4th Thursday of November) through 26 December**,
the generator picks a random curated Christmas recipe instead of a normal mood:

`christmas_classic`, `candy_cane`, `snowfall`, `tree_lights`, `gingerbread`,
`silent_night`, `evergreen_glitter`, `santas_sleigh`.

Each recipe keeps the family structure — apex twinkles, peaks sparkle, fronts
drip or fall snow, sides chase or flow, garage stays calm — and still gives
every segment its own palette and tint. Recipes prefer Eaveglow's custom ★
palettes (Peppermint, Grinch, Candy Corn) where installed, falling back to
built-in palettes otherwise. The 20–40 minute cadence and 23:00 cutoff are
unchanged.

Test the season boundaries without waiting for December:

```
python3 /config/scripts/wled_random_look.py --dry-run --date 2026-11-25   # normal
python3 /config/scripts/wled_random_look.py --dry-run --date 2026-11-26   # Christmas
python3 /config/scripts/wled_random_look.py --dry-run --force-christmas    # any date
python3 /config/scripts/wled_random_look.py --dry-run --no-christmas       # force off
```

### Using Eaveglow's real Christmas looks (A + B)

`looks/christmas.json` is generated from Eaveglow's `src/engine/library.json`
by `node_modules/.bin/vite-node scripts/export-christmas-looks.ts`. It contains
all 28 Christmas looks in two forms:

- **Adapted style** — effect, palette and colours, mapped onto the current zone
  families by the generator (`--adapt-only`)
- **Exact look** — the WLED state Eaveglow compiles for that look against your
  segment layout, posted verbatim (`--exact-only`)

By default Christmas mode alternates the two at random. Exact mode is guarded
by a layout fingerprint: if you change your zones, regenerate the bundle or it
automatically falls back to adapted styles.

Install the bundle on HA alongside the script:

```
cp -R ~/Documents/Git/Eaveglow-Web/homeassistant/looks /config/looks/
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
