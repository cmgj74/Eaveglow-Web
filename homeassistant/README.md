# Home Assistant files (copied from the running setup)

These are copies of the files currently installed in the HA container, kept
here so they are versioned alongside Eaveglow. They are **snippets**, not a
drop-in replacement for your whole HA config.

| File in this repo | Installed at | Notes |
| --- | --- | --- |
| `scripts/wled_random_look.py` | `/config/scripts/wled_random_look.py` | Copied verbatim (SHA-256 `b0a54fc8…`). Python 3 stdlib only. |
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
