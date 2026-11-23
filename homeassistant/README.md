# Home Assistant integration

Eaveglow publishes everything HA needs to the controller at build/install
time. HA's shell command downloads the generator on **every run**, so there is
no hand-installed bundle and no regeneration step:

| Controller file | Source | Contents |
| --- | --- | --- |
| `/eaveglow-ha.py` | `homeassistant/scripts/wled_random_look.py` | The generator (Python 3 stdlib only) |
| `/eaveglow-library.json` | `scripts/build-ha-library.mjs` | Trimmed look library: 171 looks, 14 holidays, 48 palettes (40 KB) |

`npm run build` creates both files in `dist/`; `npm run install-to -- <host>`
uploads them with the app.

## Install to HA (once)

Open Eaveglow on the controller and tap **🏡 Install to HA**. The page generates
the exact `shell_commands.yaml` line and `automations.yaml` block using the
controller's real address — copy them into HA and restart. After that, nothing
else needs manual updating: changing a look in Eaveglow changes HA's next look.

The shell command is a bootstrap:

```yaml
wled_random_look: "curl -fsSL http://<controller>/eaveglow-ha.py -o /tmp/eaveglow-ha.py && WLED_URL=http://<controller> python3 /tmp/eaveglow-ha.py"
```

## What is read live each run

- `/json` — segments (names/ranges), effects, palettes, brightness, `maxseg`
- `/json/fxdata` — effect metadata (optional)
- `/eaveglow.json` — autopilot seasons, special dates, hidden looks, transition
- `/eaveglow-library.json` — look definitions, holiday date rules, palette stops

The generator compiles the chosen Eaveglow look against the **current**
segments in Python (a port of `compileLook`, golden-tested against the
TypeScript original in `homeassistant/tests/fixtures_compiled.json`), so exact
mode always matches your present layout. There is no fingerprint and no
stale-layout fallback any more.

## Behaviour

At sunset HA applies a new look and repeats every random 20–40 minutes until
23:00. Every holiday — **Christmas included** — follows Eaveglow's autopilot
calendar: season windows (`daysBefore`/`daysAfter`), enabled flags, special
dates first, shorter season wins. If autopilot is off, no holiday is active,
or all of a holiday's looks are hidden, the normal mood look is used.

### Letting HA be the only automation

Eaveglow's autopilot also writes WLED timers with dated season presets. With
**Schedule ON**, WLED applies those itself and fights HA. Keep **Schedule OFF**
and **Autopilot ON**: the seasons stay in `/eaveglow.json` as a calendar, but
WLED's timers stay off, so only HA changes the look. To reach that state, enable
both and Save, then turn Schedule off and Save again.

## Testing

```
python3 -m unittest discover -s homeassistant/tests -v
```

Dry runs against the controller (change nothing):

```
curl -fsSL http://<controller>/eaveglow-ha.py -o /tmp/eaveglow-ha.py
python3 /tmp/eaveglow-ha.py --dry-run --date 2026-10-25    # Halloween
python3 /tmp/eaveglow-ha.py --dry-run --date 2026-11-30    # Christmas
python3 /tmp/eaveglow-ha.py --dry-run --force-christmas    # override
python3 /tmp/eaveglow-ha.py --dry-run --no-christmas       # normal look
```

See `docs/home-assistant-coherent-look.md` for the full description.
