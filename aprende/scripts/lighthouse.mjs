/* eslint-disable no-undef */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import puppeteer from 'puppeteer-core';
import lighthouse from 'lighthouse';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '..');

const args = process.argv.slice(2);
let url = 'http://127.0.0.1:4173/';
const ui = args.indexOf('--url');
if (ui !== -1) url = args[ui + 1];
url = url.replace(/\/?$/, '/');

const chromePath = process.env.PW_CHROMIUM || process.env.CHROME_PATH;
if (!chromePath) { console.error('Set PW_CHROMIUM or CHROME_PATH'); process.exit(2); }

const outDir = path.join(ROOT, 'lighthouse');
fs.mkdirSync(outDir, { recursive: true });

const browser = await puppeteer.launch({
  executablePath: chromePath,
  headless: true,
  args: ['--no-sandbox'],
});
const debugPort = new URL(browser.wsEndpoint()).port;

// Sign up a fictional client and seed journey events so the app is past gating.
const setupPage = await browser.newPage();
await setupPage.goto(url, { waitUntil: 'domcontentloaded' });
await setupPage.evaluate(async () => {
  const json = { 'Content-Type': 'application/json' };
  const r = await fetch('/auth/signup', { method: 'POST', headers: json, body: JSON.stringify({
    name: 'Ana Torres', email: `ana-${Date.now()}-${Math.random().toString(36).slice(2, 7)}@example.com`,
    password: 'long-secure-password', source: 'aprende', adult: true }) });
  const tok = (await r.json()).token;
  localStorage.setItem('aprende_token', tok);
  const me = (type, payload = {}) => fetch('/journey/events', { method: 'POST',
    headers: { ...json, Authorization: `Bearer ${tok}` }, body: JSON.stringify({ type, payload }) });
  await me('ai_disclosed'); await me('consent', { answer: 'yes' }); await me('names_submitted', { names: ['Ana Torres'] });
});
await setupPage.close();

const targets = [
  { name: 'map', hash: '#/aprender' },
  { name: 'lesson', hash: '#/leccion/will' },
];

const scores = {};
for (const t of targets) {
  const targetUrl = url + t.hash;
  const result = await lighthouse(targetUrl, {
    port: Number(debugPort),
    output: 'json',
    onlyCategories: ['performance'],
    chromeFlags: [],
  }, undefined);
  const lhr = result.lhr;
  const score = Math.round((lhr.categories.performance.score ?? 0) * 100);
  scores[t.name] = score;
  fs.writeFileSync(path.join(outDir, `${t.name}.json`), JSON.stringify(lhr, null, 2));
  console.log(`${t.name}: ${score}`);
}

await browser.close();

console.log(`map: ${scores.map}`);
console.log(`lesson: ${scores.lesson}`);
if (scores.map < 90 || scores.lesson < 90) process.exit(1);
