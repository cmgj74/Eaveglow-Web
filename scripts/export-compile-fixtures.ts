/**
 * Generates golden compile fixtures for the Python compileLook port.
 * Test-only: run once after changing the compiler, commit the JSON output.
 * Run: node_modules/.bin/vite-node scripts/export-compile-fixtures.ts
 */
import { writeFileSync } from 'node:fs';
import { builtinLooks } from '../src/engine/library';
import { HouseLayout } from '../src/engine/model';
import { EffectCatalog, compileLook, toStateJson } from '../src/engine/segmentCompiler';

async function get(path: string): Promise<any> {
  const r = await fetch('http://wled-dig-octa-32-8l' + path);
  return r.json();
}

async function main(): Promise<void> {
  const snap = await get('/json');
  const effects: string[] = await get('/json/effects');
  const palettes: string[] = await get('/json/palettes');
  const fxdata: string[] = await get('/json/fxdata');
  const segs = (snap.state.seg ?? []).filter((s: any) => s.stop > s.start);
  const layout: HouseLayout = {
    totalPixels: Math.max(...segs.map((s: any) => s.stop)),
    manualStarts: true,
    spacing: { lit: segs[0].grp ?? 1, skip: segs[0].spc ?? 0 },
    zones: segs.map((s: any) => ({
      id: String(s.id), name: s.n || `Zone ${s.id + 1}`,
      start: s.start, length: s.stop - s.start, ...(s.rev ? { reversed: true } : {}),
    })),
  };
  const catalog = new EffectCatalog(effects, palettes, {}, fxdata);
  const names = ['builtin.christmas_classic', 'builtin.xm_tree_farm', 'builtin.hw_candy_corn'];
  writeFileSync(
    'homeassistant/tests/fixtures_compiled.json',
    JSON.stringify({
      effects, palettes, fxdata,
      segments: segs.map((s: any) => ({ id: s.id, n: s.n, start: s.start, stop: s.stop, rev: !!s.rev })),
      cases: names.map((id) => {
        const look = builtinLooks.find((l) => l.id === id)!;
        return { id, name: look.name, look,
                 seg: toStateJson(compileLook(layout, look, catalog, 32, true), segs.length, 7).seg };
      }),
    }, null, 1) + '\n'
  );
  console.log(`Wrote ${names.length} golden cases for ${segs.length} segments`);
}

main().catch((e) => { console.error(e); process.exitCode = 1; });
