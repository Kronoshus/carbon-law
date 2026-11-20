import { describe, it, expect, beforeAll } from 'vitest';
import { execSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { gzipSync } from 'node:zlib';

// T8-05 acceptance (Opus, p8-tests): spec 13's budget, "JS < 170 KB compressed before the character engine". Initial JS
// is the entry chunk plus every chunk it imports statically (what the browser must fetch and run before the first
// screen); dynamic imports (the character engine, three.js, GLTFLoader) are not counted, and must not be preloaded.
const BUDGET = 170_000;                        // bytes, gzip level 9 (kB as Vite prints them)
type Chunk = { file: string; imports?: string[]; dynamicImports?: string[]; isEntry?: boolean; src?: string };

function initial(dir: string, entry: (k: string, c: Chunk) => boolean) {
  const manifest = JSON.parse(readFileSync(`${dir}/.vite/manifest.json`, 'utf8')) as Record<string, Chunk>;
  const start = Object.keys(manifest).filter((k) => entry(k, manifest[k]));
  expect(start.length).toBeGreaterThan(0);
  const seen = new Set<string>();
  const walk = (k: string) => { if (seen.has(k)) return; seen.add(k); for (const i of manifest[k].imports ?? []) walk(i); };
  start.forEach(walk);
  const files = [...seen].map((k) => manifest[k].file).filter((f) => f.endsWith('.js'));
  const bytes = files.reduce((n, f) => n + gzipSync(readFileSync(`${dir}/${f}`), { level: 9 }).length, 0);
  return { files, bytes, manifest };
}

describe('T8-05 initial JS budget', () => {
  beforeAll(() => {
    execSync('npm run build:web', { stdio: 'ignore' });
    execSync('npm run build:ext', { stdio: 'ignore' });
  }, 240000);

  it('the web app: initial JS is at most 170 KB gzip and holds no three.js', () => {
    const { files, bytes } = initial('dist/web', (k, c) => !!c.isEntry && k.endsWith('index.html'));
    expect(bytes, files.join(', ')).toBeLessThanOrEqual(BUDGET);
    for (const f of files) expect(readFileSync(`dist/web/${f}`, 'utf8'), f).not.toContain('WebGLRenderer');
  });

  it('the web app: index.html preloads nothing of the character engine', () => {
    const html = readFileSync('dist/web/index.html', 'utf8');
    const { manifest } = initial('dist/web', (k, c) => !!c.isEntry && k.endsWith('index.html'));
    const lazy = Object.values(manifest).filter((c) => /three|GLTFLoader|engine/.test(c.file)).map((c) => c.file);
    expect(lazy.length).toBeGreaterThan(0);                                       // three.js is still built, as its own chunk
    for (const f of lazy) expect(html, f).not.toContain(f);
  });

  it('the side panel: initial JS is at most 170 KB gzip and holds no three.js', () => {
    const { files, bytes } = initial('dist/extension', (k, c) => !!c.isEntry && k.endsWith('sidepanel.html'));
    expect(bytes, files.join(', ')).toBeLessThanOrEqual(BUDGET);
    for (const f of files) expect(readFileSync(`dist/extension/${f}`, 'utf8'), f).not.toContain('WebGLRenderer');
  });

});
