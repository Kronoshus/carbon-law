import { describe, it, expect, beforeAll } from 'vitest';
import { spawnSync } from 'node:child_process';
import { readFileSync, writeFileSync, mkdtempSync, mkdirSync, readdirSync, existsSync } from 'node:fs';
import { inflateRawSync } from 'node:zlib';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';

// T8-02 acceptance (Opus, p8-tests): the Chrome Web Store package and its static checks. Nothing is uploaded.
// `npm run pack:ext` builds the extension and writes dist/aprende-extension.zip; `node scripts/check-extension.mjs <zip|dir>`
// exits 0 when the package passes and 1 (naming the file and the rule) when it does not.
const ZIP = 'dist/aprende-extension.zip';
const ORIGIN = 'https://carbon-law.onrender.com';                 // the default API_ORIGIN of the extension build

/** The entries of a zip file (stored or deflated), read with node:zlib only. */
function unzip(path: string): Map<string, Buffer> {
  const buf = readFileSync(path);
  let eocd = buf.length - 22;
  while (eocd >= 0 && buf.readUInt32LE(eocd) !== 0x06054b50) eocd--;
  expect(eocd, 'end of central directory').toBeGreaterThanOrEqual(0);
  const count = buf.readUInt16LE(eocd + 10);
  let p = buf.readUInt32LE(eocd + 16);
  const out = new Map<string, Buffer>();
  for (let i = 0; i < count; i++) {
    const method = buf.readUInt16LE(p + 10), size = buf.readUInt32LE(p + 20);
    const nameLen = buf.readUInt16LE(p + 28), extraLen = buf.readUInt16LE(p + 30), commentLen = buf.readUInt16LE(p + 32);
    const local = buf.readUInt32LE(p + 42);
    const name = buf.subarray(p + 46, p + 46 + nameLen).toString('utf8');
    const start = local + 30 + buf.readUInt16LE(local + 26) + buf.readUInt16LE(local + 28);
    const data = buf.subarray(start, start + size);
    if (!name.endsWith('/')) out.set(name, method === 8 ? inflateRawSync(data) : Buffer.from(data));
    p += 46 + nameLen + extraLen + commentLen;
  }
  return out;
}

const pngSize = (b: Buffer) => ({ png: b.subarray(1, 4).toString() === 'PNG', w: b.readUInt32BE(16), h: b.readUInt32BE(20) });

function check(target: string) {
  const r = spawnSync('node', ['scripts/check-extension.mjs', target], { encoding: 'utf8' });
  return { code: r.status, out: `${r.stdout}\n${r.stderr}` };
}

/** A copy of the packaged extension in a folder, with one defect planted by `plant`. */
function planted(plant: (dir: string) => void): string {
  const dir = mkdtempSync(join(tmpdir(), 'cl-t8-02-'));
  for (const [name, data] of unzip(ZIP)) {
    mkdirSync(dirname(join(dir, name)), { recursive: true });
    writeFileSync(join(dir, name), data);
  }
  plant(dir);
  return dir;
}
const append = (dir: string, file: string, code: string) => writeFileSync(join(dir, file), readFileSync(join(dir, file), 'utf8') + '\n' + code);
const editManifest = (dir: string, edit: (m: Record<string, unknown>) => void) => {
  const m = JSON.parse(readFileSync(join(dir, 'manifest.json'), 'utf8'));
  edit(m);
  writeFileSync(join(dir, 'manifest.json'), JSON.stringify(m));
};

describe('T8-02 the Store package', () => {
  let files: Map<string, Buffer>;
  let manifest: Record<string, any>;            // eslint-disable-line @typescript-eslint/no-explicit-any
  beforeAll(() => {                             // the zip is packed once for all test files in tests/build-once.ts
    files = unzip(ZIP);
    manifest = JSON.parse(files.get('manifest.json')!.toString('utf8'));
  });

  it('is a zip with the manifest at its root and no build leftovers', () => {
    expect(files.has('manifest.json')).toBe(true);
    const names = [...files.keys()];
    expect(names.filter((n) => n.startsWith('.vite/') || n.endsWith('.map') || n.startsWith('src/'))).toEqual([]);
    expect(names.filter((n) => n.startsWith('offscreen'))).toEqual([]);        // F-003: no microphone, no offscreen document
  });

  it('asks only for the permissions it uses, and one https host: the firm\'s API', () => {
    expect(manifest.manifest_version).toBe(3);
    expect(manifest.permissions).toEqual(['sidePanel', 'storage']);
    expect(manifest.host_permissions).toEqual([`${ORIGIN}/*`]);
    expect(manifest.optional_permissions ?? []).toEqual([]);
    expect(manifest.web_accessible_resources ?? []).toEqual([]);
    expect(manifest.externally_connectable).toBeUndefined();
  });

  it('runs no remote code: its CSP allows only its own scripts and talks only to the API', () => {
    const csp: string = manifest.content_security_policy?.extension_pages ?? '';
    const directives = Object.fromEntries(csp.split(';').map((d) => d.trim()).filter(Boolean).map((d) => {
      const [name, ...values] = d.split(/\s+/);
      return [name, values];
    }));
    expect(directives['script-src']).toEqual(["'self'"]);
    expect(directives['object-src']).toEqual(["'self'"]);
    expect(directives['connect-src']).toEqual(["'self'", ORIGIN]);
  });

  it('has the Store basics: name, short description, version and 16/48/128 PNG icons', () => {
    expect(manifest.name.length).toBeGreaterThan(0);
    expect(manifest.name.length).toBeLessThanOrEqual(75);
    expect(manifest.description.length).toBeGreaterThan(0);
    expect(manifest.description.length).toBeLessThanOrEqual(132);
    expect(manifest.version).toMatch(/^\d+(\.\d+){0,3}$/);
    for (const size of ['16', '48', '128']) {
      const file = files.get(manifest.icons?.[size]);
      expect(file, `icon ${size}`).toBeTruthy();
      expect(pngSize(file!)).toEqual({ png: true, w: Number(size), h: Number(size) });
    }
  });

  it('has the API origin built in (it never calls its own chrome-extension:// origin for the API)', () => {
    const js = [...files].filter(([n]) => n.endsWith('.js')).map(([, b]) => b.toString('utf8')).join('\n');
    expect(js).toContain(ORIGIN);
  });

  it('passes the static checks', () => {
    const r = check(ZIP);
    expect(r.out).not.toMatch(/FAIL/);
    expect(r.code).toBe(0);
  });

  const DEFECTS: [string, (dir: string) => void, RegExp][] = [
    ['a chrome.storage.local write', (d) => append(d, 'popup.js', 'chrome.storage.local.set({ a: 1 });'), /popup\.js.*storage\.local|storage\.local.*popup\.js/],
    ['a chrome.storage.sync write', (d) => append(d, 'sidepanel.js', 'chrome.storage.sync.set({ a: 1 });'), /sidepanel\.js.*storage\.sync|storage\.sync.*sidepanel\.js/],
    ['a bracketed storage["local"] write', (d) => append(d, 'background.js', "chrome.storage['local'].set({ a: 1 });"), /background\.js.*local|local.*background\.js/],
    ['a remote script tag', (d) => writeFileSync(join(d, 'sidepanel.html'), readFileSync(join(d, 'sidepanel.html'), 'utf8')
      .replace('</head>', '<script src="https://cdn.example.com/x.js"></script></head>')), /sidepanel\.html.*remote|remote.*sidepanel\.html/i],
    ['eval', (d) => append(d, 'background.js', 'eval("1");'), /background\.js.*eval|eval.*background\.js/],
    ['new Function', (d) => append(d, 'popup.js', 'new Function("return 1")();'), /popup\.js.*Function|Function.*popup\.js/],
    ['a remote import', (d) => append(d, 'background.js', 'import("https://cdn.example.com/x.js");'), /background\.js.*remote|remote.*background\.js/i],
    ['an unused permission', (d) => editManifest(d, (m) => { (m.permissions as string[]).push('history'); }), /history/],
    ['unsafe-eval in the CSP', (d) => editManifest(d, (m) => { m.content_security_policy = { extension_pages: "script-src 'self' 'unsafe-eval'; object-src 'self'" }; }), /unsafe-eval/],
    ['a missing icon', (d) => editManifest(d, (m) => { (m.icons as Record<string, string>)['128'] = 'icons/missing-128.png'; }), /missing-128\.png/],
    ['a second host', (d) => editManifest(d, (m) => { (m.host_permissions as string[]).push('https://example.com/*'); }), /example\.com/],
  ];
  for (const [name, plant, says] of DEFECTS) {
    it(`fails on ${name}`, () => {
      const r = check(planted(plant));
      expect(r.code).toBe(1);
      expect(r.out).toMatch(says);
    });
  }
});

describe('T8-02 the Store listing draft', () => {
  it('has 1 to 5 screenshots of 1280×800 and short descriptions within 132 characters', () => {
    const dir = '../docs/store/screenshots';
    expect(existsSync(dir)).toBe(true);
    const shots = readdirSync(dir).filter((f) => f.endsWith('.png'));
    expect(shots.length).toBeGreaterThanOrEqual(1);
    expect(shots.length).toBeLessThanOrEqual(5);
    for (const f of shots) expect(pngSize(readFileSync(join(dir, f))), f).toEqual({ png: true, w: 1280, h: 800 });
    const listing = readFileSync('../docs/store/listing.md', 'utf8');
    const short = [...listing.matchAll(/^Short description \((es|en)\): (.+)$/gm)].map((m) => m[2].trim());
    expect(short.length).toBe(2);
    for (const s of short) expect(s.length).toBeLessThanOrEqual(132);
  });
});
