/**
 * Generate the holiday look bundles used by the HA randomiser.
 *
 * Outputs:
 *   - `holidays.json`   — all Eaveglow holidays with looks, each carrying a
 *                         compact manifest (for the family adapter) and the
 *                         exact compiled WLED state (for approach B), plus
 *                         the date rule from library.json.
 *   - `christmas.json`  — the old Christmas-only shape, kept for setups that
 *                         still reference it directly.
 *
 * Run: node_modules/.bin/vite-node scripts/export-christmas-looks.ts
 *      WLED_HOST=192.168.1.230 node_modules/.bin/vite-node scripts/export-christmas-looks.ts
 *
 * Re-run whenever the segment layout changes, so exact payloads stay aligned.
 */
import { mkdirSync, writeFileSync } from 'node:fs';
import { builtinLooks, holidayGroups, palettePresets } from '../src/engine/library';
import { HouseLayout, Look } from '../src/engine/model';
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
  const settings = await get('/eaveglow.json').catch(() => ({}));

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

  function compile(look: Look) {
    const compiled = compileLook(layout, look, catalog, maxSegments, true);
    const first = look.layers[0] ?? { effect: ['Solid'], palette: [], colors: [], speed: 128, intensity: 128 };
    return {
      id: look.id,
      name: look.name,
      effect: first.effect[0] ?? 'Solid',
      palette: first.palette[0] ?? '',
      colors: first.colors,
      speed: first.speed,
      intensity: first.intensity,
      layers: look.layers.length,
      payload: toStateJson(compiled, segs.length, 7),
    };
  }

  const fingerprint = segs.map((s: any) => [s.id, s.start, s.stop]);
  const customLooks: Look[] = (settings.customLooks ?? []) as Look[];

  const holidays = holidayGroups
    .map((h) => {
      const looks = builtinLooks.filter((l) => l.group === h.id);
      return { id: h.id, name: h.name, emoji: h.emoji, rule: h.rule, looks: looks.map(compile) };
    })
    .filter((h) => h.looks.length > 0);

  const compiledCustom = customLooks.map(compile);
  const allLooks = holidays.flatMap((h) => h.looks).concat(compiledCustom);
  const usedPalettes = new Set(allLooks.map((l) => l.palette).filter(Boolean));
  const paletteStops: Record<string, number[][]> = {};
  for (const name of usedPalettes) {
    const preset = palettePresets.find((p) => p.wled.toLowerCase() === name.toLowerCase());
    if (preset) paletteStops[name] = preset.stops;
  }

  const out = {
    generatedAt: new Date().toISOString(),
    source: '../src/engine/library.json',
    host,
    segmentCount: segs.length,
    fingerprint,
    paletteStops,
    holidays,
    // Custom looks let HA's special dates reference user-made Eaveglow looks.
    customLooks: compiledCustom,
  };

  mkdirSync('homeassistant/looks', { recursive: true });
  writeFileSync('homeassistant/looks/holidays.json', JSON.stringify(out, null, 1) + '\n');
  const christmas = holidays.find((h) => h.id === 'christmas');
  if (christmas) {
    writeFileSync(
      'homeassistant/looks/christmas.json',
      JSON.stringify({ ...out, looks: christmas.looks }, null, 1) + '\n'
    );
  }
  const total = holidays.reduce((n, h) => n + h.looks.length, 0);
  console.log(
    `Wrote holidays.json: ${holidays.length} holidays, ${total} looks, ` +
      `${segs.length} segments, ${(JSON.stringify(out).length / 1024).toFixed(0)} KB`
  );

  const missingFx = holidays.flatMap((h) => h.looks).filter(
    (l) =>
      l.layers === 1 &&
      l.effect !== 'Solid' &&
      (l.payload.seg as any[]).some((s: any) => s.on && s.fx === 0)
  );
  if (missingFx.length) console.log('Check effects (fell back to 0):', missingFx.map((l) => l.name).join(', '));
}

main().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
