import { useApp } from '../app';
import { HaSettings } from '../store';
import { Header, NumberField, Toggle } from './common';

const DEFAULTS: HaSettings = {
  controllerUrl: '',
  minMinutes: 20,
  maxMinutes: 40,
  cutoffHour: 23,
  cutoffMinute: 0,
  mode: 'random',
  speedMin: 75,
  speedMax: 110,
  intensityMin: 120,
  intensityMax: 160,
  warmLooks: false,
};

/** Everything HA needs, generated from the controller's real address. */
export function HaSetupPage() {
  const { settings, store } = useApp();
  const ha = { ...DEFAULTS, ...settings.ha };
  const host = ha.controllerUrl || location.host || '192.168.1.230';
  const set = (v: HaSettings) => store.update('ha', { ...ha, ...v });
  const shell =
    `wled_random_look: "curl -fsSL http://${host}/eaveglow-ha.py -o /tmp/eaveglow-ha.py && printf '%s sha=%s ' $(date -u +%FT%TZ) $(sha256sum /tmp/eaveglow-ha.py | awk '{print $1}') >> /config/eaveglow_runs.log && WLED_URL=http://${host} python3 /tmp/eaveglow-ha.py | tee -a /config/eaveglow_runs.log"`;
  const sensors = `- sensor:
    name: Eaveglow min minutes
    command: "curl -fsSL http://${host}/eaveglow.json | python3 -c \\"import json,sys; print(json.load(sys.stdin).get('ha',{}).get('minMinutes',20))\\""
    scan_interval: 60
- sensor:
    name: Eaveglow max minutes
    command: "curl -fsSL http://${host}/eaveglow.json | python3 -c \\"import json,sys; print(json.load(sys.stdin).get('ha',{}).get('maxMinutes',40))\\""
    scan_interval: 60
- sensor:
    name: Eaveglow cutoff
    command: "curl -fsSL http://${host}/eaveglow.json | python3 -c \\"import json,sys; h=json.load(sys.stdin).get('ha',{}); print('%02d:%02d' % (h.get('cutoffHour',23), h.get('cutoffMinute',0)))\\""
    scan_interval: 60`;
  const automation = `- id: wled_sunset_random_look
  alias: "WLED - Random look every ${ha.minMinutes}-${ha.maxMinutes} min until ${String(ha.cutoffHour).padStart(2, '0')}:${String(ha.cutoffMinute).padStart(2, '0')}"
  trigger:
    - platform: sun
      event: sunset
  action:
    - repeat:
        while:
          - condition: template
            value_template: "{{ now() < today_at(states('sensor.eaveglow_cutoff') if states('sensor.eaveglow_cutoff') not in ('unknown','unavailable') else '23:00') }}"
        sequence:
          - action: shell_command.wled_random_look
          - delay:
              minutes: "{{ range(states('sensor.eaveglow_min_minutes')|int(20), states('sensor.eaveglow_max_minutes')|int(40)+1) | random }}"
  mode: single`;
  const copy = (text: string) => navigator.clipboard?.writeText(text).catch(() => undefined);

  return (
    <main>
      <Header title="Install to HA" back />
      <p class="hint">
        Paste these blocks into Home Assistant once. The generator, look library,
        timing and look behaviour are then read live from this controller every run.
      </p>

      <section class="card">
        <h3>Settings</h3>
        <label class="row">Controller address (IP)
          <input aria-label="Controller address" value={ha.controllerUrl ?? ''}
            placeholder={location.host || '192.168.1.230'}
            onInput={(e) => set({ controllerUrl: e.currentTarget.value })} />
        </label>
        <label class="row">Look mode
          <select aria-label="Look mode" value={ha.mode} onChange={(e) => set({ mode: e.currentTarget.value as HaSettings['mode'] })}>
            <option value="random">Random (exact + adapted)</option>
            <option value="exact">Exact only</option>
            <option value="adapted">Adapted only (per zone)</option>
          </select>
        </label>
        <div class="row"><NumberField value={ha.minMinutes ?? 20} min={1} ariaLabel="Minimum minutes" onChange={(n) => set({ minMinutes: n })} /><small>min delay, from</small>
          <NumberField value={ha.maxMinutes ?? 40} min={1} ariaLabel="Maximum minutes" onChange={(n) => set({ maxMinutes: n })} /><small>to minutes</small></div>
        <div class="row"><NumberField value={ha.cutoffHour ?? 23} min={0} ariaLabel="Cutoff hour" onChange={(n) => set({ cutoffHour: Math.min(n, 23) })} /><small>cutoff hour</small>
          <NumberField value={ha.cutoffMinute ?? 0} min={0} ariaLabel="Cutoff minute" onChange={(n) => set({ cutoffMinute: Math.min(n, 59) })} /><small>minute</small></div>
        <div class="row"><NumberField value={ha.speedMin ?? 75} min={1} ariaLabel="Speed minimum" onChange={(n) => set({ speedMin: n })} /><small>speed from</small>
          <NumberField value={ha.speedMax ?? 110} min={1} ariaLabel="Speed maximum" onChange={(n) => set({ speedMax: n })} /><small>to</small></div>
        <div class="row"><NumberField value={ha.intensityMin ?? 120} min={1} ariaLabel="Intensity minimum" onChange={(n) => set({ intensityMin: n })} /><small>intensity from</small>
          <NumberField value={ha.intensityMax ?? 160} min={1} ariaLabel="Intensity maximum" onChange={(n) => set({ intensityMax: n })} /><small>to</small></div>
        <Toggle label="Allow warm Christmas looks" hint="Gingerbread, Twinkle Stars and other amber looks" checked={!!ha.warmLooks} onChange={(v) => set({ warmLooks: v })} />
      </section>

      <h3>1 · command_line.yaml (sensors)</h3>
      <p class="hint">Enable <code>command_line: !include command_line.yaml</code> in configuration.yaml.</p>
      <pre class="share-text">{sensors}</pre>
      <button onClick={() => copy(sensors)}>Copy sensors</button>

      <h3>2 · shell_commands.yaml</h3>
      <pre class="share-text">{shell}</pre>
      <button onClick={() => copy(shell)}>Copy shell command</button>

      <h3>3 · automations.yaml</h3>
      <pre class="share-text">{automation}</pre>
      <button onClick={() => copy(automation)}>Copy automation</button>

      <p class="hint">
        Keep Eaveglow's <b>Schedule OFF</b> and <b>Autopilot ON</b> — autopilot is
        only the holiday calendar; HA is the automation that applies looks.
      </p>
      <p class="hint">
        Dry run: <code>python3 /tmp/eaveglow-ha.py --dry-run --force-christmas</code>
      </p>
    </main>
  );
}
