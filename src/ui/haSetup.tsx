import { Header } from './common';

/** Everything HA needs, generated from the controller's real address. */
export function HaSetupPage() {
  const host = location.host || 'wled-dig-octa-32-8l';
  const shell =
    `wled_random_look: "curl -fsSL http://${host}/eaveglow-ha.py -o /tmp/eaveglow-ha.py && printf '%s sha=%s ' $(date -u +%FT%TZ) $(sha256sum /tmp/eaveglow-ha.py | awk '{print $1}') >> /config/eaveglow_runs.log && WLED_URL=http://${host} python3 /tmp/eaveglow-ha.py | tee -a /config/eaveglow_runs.log"`;
  const automation = `- id: wled_sunset_random_look
  alias: "WLED - Random look every 20-40 min until 23:00"
  trigger:
    - platform: sun
      event: sunset
  action:
    - repeat:
        while:
          - condition: template
            value_template: "{{ now() < today_at('23:00') }}"
        sequence:
          - action: shell_command.wled_random_look
          - delay:
              minutes: "{{ range(20, 41) | random }}"
  mode: single`;
  const copy = (text: string) =>
    navigator.clipboard?.writeText(text).catch(() => undefined);

  return (
    <main>
      <Header title="Install to HA" back />
      <p class="hint">
        Paste these two blocks into Home Assistant once. After that, everything
        is read live from this controller — the look library and the generator
        are fetched fresh on every run, so updating Eaveglow is all you ever do.
      </p>

      <h3>1 · shell_commands.yaml</h3>
      <pre class="share-text">{shell}</pre>
      <button onClick={() => copy(shell)}>Copy shell command</button>

      <h3>2 · automations.yaml</h3>
      <pre class="share-text">{automation}</pre>
      <button onClick={() => copy(automation)}>Copy automation</button>

      <p class="hint">
        Keep Eaveglow's <b>Schedule OFF</b> and <b>Autopilot ON</b> — the
        autopilot is only the holiday calendar; HA is the automation that
        applies looks.
      </p>
      <p class="hint">
        Dry run: <code>python3 /config/scripts/wled_random_look.py --dry-run --force-christmas</code>
      </p>
    </main>
  );
}
