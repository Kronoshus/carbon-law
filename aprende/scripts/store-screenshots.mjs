/* global URL */
import { chromium } from 'playwright';
import { mkdirSync } from 'node:fs';
import { resolve } from 'node:path';

const extPath = resolve(process.argv[2] || 'dist/extension');
const outDir = resolve(process.argv[3] || '../docs/store/screenshots');
mkdirSync(outDir, { recursive: true });

const context = await chromium.launchPersistentContext('', {
  headless: true,
  args: [`--disable-extensions-except=${extPath}`, `--load-extension=${extPath}`],
});
const sw = context.serviceWorkers()[0] || await context.waitForEvent('serviceworker');
const extensionId = new URL(sw.url()).host;

const shots = ['map', 'lesson', 'plan'];
for (const name of shots) {
  const page = await context.newPage();
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.setContent(`<html style="background:#0f172a;margin:0"><body style="display:flex;justify-content:center;margin:0"><iframe src="chrome-extension://${extensionId}/sidepanel.html" style="width:400px;height:800px;border:0"></iframe></body></html>`);
  await page.waitForTimeout(2000);
  await page.screenshot({ path: `${outDir}/${name}.png` });
  await page.close();
}
await context.close();
console.log('screenshots written to', outDir);
