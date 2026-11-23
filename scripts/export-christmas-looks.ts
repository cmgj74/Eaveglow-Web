/**
 * Generate the Christmas look bundle used by the HA randomiser.
 *
 * Two things come out of this single file:
 *   - `looks[]`  — a compact manifest of Eaveglow's real Christmas looks, used
 *                  by the HA script's family/step adapter (approach A)
 *   - `payload`  — the exact WLED state Eaveglow compiles for each look against
 *                  the controller's current segment layout (approach B)
 *
 * Run: node_modules/.bin/vite-node scripts/export-christmas-looks.ts
 *      WLED_HOST=192.168.1.230 node_modules/.bin/vite-node scripts/export-christmas-looks.ts
 *
 * Re-run this whenever the segment layout changes, so the exact payloads stay
 * aligned with the controller.
 */
import { mkdirSync, writeFileSync } from 'node:fs';
import { builtinLooks } from '../src/engine/library';
import { HouseLayout } from '../src/engine/model';
import { EffectCatalog, compileLook, toStateJson } from '../src/engine/segmentCompiler';

const host = process.env.WLED_HOST ?? 'wled-dig-octa-32-8l';
const base = `http://${host}`;

async function get(path: string): Promise<any> {
  const resp = await fetch(base + path);
  if (!resp.ok) throw new Error(`${path}: HTTP ${resp.status}`);
  return resp.json();
}

async function main(): Promise<void> {
  const snapshot = await get('/json');
  const effects: string[] = await get('/json/effects');
  const palettes: string[] = await get('/json/palettes');
  const fxdata: string[] = await get('/json/fxdata');

  // Custom ★ palettes Eaveglow installed, if any.
  const extra: Record<string, number> = {};
  for (let i = 0; i < palettes.length; i++) {
    const n = palettes[i].split('@')[0].trim();
    if (n.startsWith('★ ')) extra[n] = i;
  }

  const segs = (snapshot.state?.seg ?? []).filter((s: any) => s.stop > s.start);
  if (!segs.length) throw new Error('Controller has no active segments');

  const layout: HouseLayout = {
    totalPixels: Math.max(...segs.map((s: any) => s.stop)),
    manualStarts: true,
    spacing: { lit: segs[0].grp ?? 1, skip: segs[0].spc ?? 0 },
    zones: segs.map((s: any) => ({
      id: String(s.id),
      name: s.n || `Zone ${s.id + 1}`,
      start: s.start,
      length: s.stop - s.start,
    })),
  };

  const catalog = new EffectCatalog(effects, palettes, extra, fxdata);
  const maxSegments = snapshot.info?.leds?.maxseg ?? 32;
  const christmas = builtinLooks.filter((l) => l.group === 'christmas');
  if (!christmas.length) throw new Error('No christmas looks found in library.json');

  const looks = christmas.map((look) => {
    const compiled = compileLook(layout, look, catalog, maxSegments, true);
    const first = look.layers[0];
    return {
      id: look.id,
      name: look.name,
      effect: first.effect[0],
      palette: first.palette[0] ?? '',
      colors: first.colors,
      speed: first.speed,
      intensity: first.intensity,
      layers: look.layers.length,
      payload: toStateJson(compiled, segs.length, 7),
    };
  });

  const out = {
    generatedAt: new Date().toISOString(),
    source: '../src/engine/library.json',
    host,
    segmentCount: segs.length,
    // Layout fingerprint: exact payloads are only valid while these match.
    fingerprint: segs.map((s: any) => [s.id, s.start, s.stop]),
    looks,
  };

  mkdirSync('homeassistant/looks', { recursive: true });
  const path = 'homeassistant/looks/christmas.json';
  writeFileSync(path, JSON.stringify(out, null, 1) + '\n');
  console.log(
    `Wrote ${path}: ${looks.length} looks, ${segs.length} segments, ` +
      `${(JSON.stringify(out).length / 1024).toFixed(0)} KB`
  );
  // A Solid layer legitimately compiles to fx 0, and a second alternating
  // layer often does too — only flag a single-layer effect that vanished.
  const missingFx = looks.filter(
    (l) =>
      l.layers === 1 &&
      l.effect !== 'Solid' &&
      (l.payload.seg as any[]).some((s) => s.on && s.fx === 0)
  );
  if (missingFx.length) console.log('Check effects (fell back to 0):', missingFx.map((l) => l.name).join(', '));
}

main().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
