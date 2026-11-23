// Copies the HA randomiser into the app bundle so Eaveglow serves it from the
// controller. HA's shell command downloads it on every run — no manual copying.
import { copyFileSync, mkdirSync } from 'node:fs';

mkdirSync('dist', { recursive: true });
copyFileSync('homeassistant/scripts/wled_random_look.py', 'dist/eaveglow-ha.py');
console.log('Wrote dist/eaveglow-ha.py');
