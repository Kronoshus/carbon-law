/* global URL */

// Renders the app icon from its SVG sources (aprende/icon-src/) to every PNG the web app and the Chrome extension use.
// Run after changing an SVG: node scripts/render-icons.mjs (PW_CHROMIUM may point at a Chromium binary).
import { readFileSync } from 'node:fs';
import { chromium } from '@playwright/test';

const SRC = new URL('../icon-src/', import.meta.url);
const OUT = new URL('../public/icons/', import.meta.url);

// [source, file, size, transparent padding]
const PNGS = [
  ['icon.svg', 'app-192.png', 192, 0],
  ['icon.svg', 'app-512.png', 512, 0],
  ['icon-maskable.svg', 'app-maskable-512.png', 512, 0],   // full bleed, the mark inside the safe circle
  ['icon-maskable.svg', 'apple-touch-icon.png', 180, 0],   // iOS rounds the corners itself
  ['icon.svg', 'icon-128.png', 128, 16],                   // the Chrome Web Store asks for 96 px of art in 128
  ['icon-small.svg', 'icon-48.png', 48, 0],                // heavier lines that hold up at toolbar sizes
  ['icon-small.svg', 'icon-16.png', 16, 0],
];

const browser = await chromium.launch({ executablePath: process.env.PW_CHROMIUM || undefined });
for (const [src, file, size, pad] of PNGS) {
  const page = await browser.newPage({ viewport: { width: size, height: size }, deviceScaleFactor: 1 });
  const svg = readFileSync(new URL(src, SRC)).toString('base64');
  const art = size - 2 * pad;
  await page.setContent(`<style>html,body{margin:0;background:transparent}</style>
    <img src="data:image/svg+xml;base64,${svg}" style="position:absolute;left:${pad}px;top:${pad}px;width:${art}px;height:${art}px">`);
  await page.locator('img').evaluate((img) => img.decode());
  await page.screenshot({ path: new URL(file, OUT).pathname, omitBackground: true });
  await page.close();
}
await browser.close();
