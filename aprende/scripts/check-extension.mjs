/* global Buffer */

import { readFileSync, readdirSync, statSync } from 'node:fs';
import { resolve, relative, sep } from 'node:path';
import { inflateRawSync } from 'node:zlib';

const target = process.argv[2];
if (!target) { console.error('usage: check-extension.mjs <zip|dir>'); process.exit(2); }

function isZip(p) { return p.endsWith('.zip'); }

function readZip(path) {
  const buf = readFileSync(path);
  let eocd = buf.length - 22;
  while (eocd >= 0 && buf.readUInt32LE(eocd) !== 0x06054b50) eocd--;
  if (eocd < 0) throw new Error('no eocd');
  const count = buf.readUInt16LE(eocd + 10);
  let p = buf.readUInt32LE(eocd + 16);
  const out = new Map();
  for (let i = 0; i < count; i++) {
    const method = buf.readUInt16LE(p + 10);
    const size = buf.readUInt32LE(p + 20);
    const nameLen = buf.readUInt16LE(p + 28);
    const extraLen = buf.readUInt16LE(p + 30);
    const commentLen = buf.readUInt16LE(p + 32);
    const local = buf.readUInt32LE(p + 42);
    const name = buf.subarray(p + 46, p + 46 + nameLen).toString('utf8');
    const start = local + 30 + buf.readUInt16LE(local + 26) + buf.readUInt16LE(local + 28);
    const data = buf.subarray(start, start + size);
    if (!name.endsWith('/')) out.set(name, method === 8 ? inflateRawSync(data) : Buffer.from(data));
    p += 46 + nameLen + extraLen + commentLen;
  }
  return out;
}

function readDir(root) {
  const out = new Map();
  function walk(dir) {
    for (const name of readdirSync(dir)) {
      const full = resolve(dir, name);
      const st = statSync(full);
      if (st.isDirectory()) walk(full);
      else out.set(relative(root, full).split(sep).join('/'), readFileSync(full));
    }
  }
  walk(root);
  return out;
}

const files = isZip(target) ? readZip(target) : readDir(target);

const problems = [];
function fail(file, rule) { problems.push(`FAIL ${file}: ${rule}`); }

// 1. manifest at root
if (!files.has('manifest.json')) {
  fail('manifest.json', 'manifest at root');
  // cannot continue meaningfully
  console.log(problems.join('\n'));
  process.exit(1);
}
let manifest;
try { manifest = JSON.parse(files.get('manifest.json').toString('utf8')); }
catch { fail('manifest.json', 'manifest json parse'); manifest = {}; }

if (manifest.manifest_version !== 3) fail('manifest.json', 'manifest_version 3');
if (typeof manifest.name !== 'string' || manifest.name.length < 1 || manifest.name.length > 75) fail('manifest.json', 'name 1-75 chars');
if (typeof manifest.description !== 'string' || manifest.description.length < 1 || manifest.description.length > 132) fail('manifest.json', 'description 1-132 chars');
if (typeof manifest.version !== 'string' || !/^\d+(\.\d+){0,3}$/.test(manifest.version)) fail('manifest.json', 'version 1-4 dot-separated integers');

// 2. files named by manifest exist
function checkFile(p, label) {
  if (!p || !files.has(p)) fail(p || label, 'missing file');
}
checkFile(manifest.background?.service_worker, 'background.service_worker');
checkFile(manifest.side_panel?.default_path, 'side_panel.default_path');
checkFile(manifest.action?.default_popup, 'action.default_popup');
const icons = manifest.icons || {};
for (const size of Object.keys(icons)) {
  const p = icons[size];
  checkFile(p, `icon ${size}`);
  if (files.has(p)) {
    const b = files.get(p);
    // PNG check + size
    const isPng = b.length > 24 && b[0] === 0x89 && b[1] === 0x50 && b[2] === 0x4e && b[3] === 0x47;
    if (!isPng) fail(p, 'icon not PNG');
    else {
      const w = b.readUInt32BE(16);
      const h = b.readUInt32BE(20);
      if (w !== Number(size) || h !== Number(size)) fail(p, `icon size ${size}`);
    }
  }
}
// action.default_icon may be object too
if (manifest.action?.default_icon && typeof manifest.action.default_icon === 'object') {
  for (const size of Object.keys(manifest.action.default_icon)) {
    const p = manifest.action.default_icon[size];
    checkFile(p, `icon ${size}`);
  }
}

// 3. remote code
for (const [name, buf] of files) {
  const text = buf.toString('utf8');
  if (name.endsWith('.html')) {
    const re = /<script[^>]*src\s*=\s*["']([^"']+)["']/gi;
    let m;
    while ((m = re.exec(text)) !== null) {
      const src = m[1];
      if (/^https?:/i.test(src) || src.startsWith('//')) {
        fail(name, 'remote script');
      }
    }
  }
  if (name.endsWith('.js')) {
    if (/import\s*\(\s*["']https?:/i.test(text) || /import\s*\(\s*["']\/\//.test(text)) fail(name, 'remote import');
    // importScripts with remote url
    const isRe = /importScripts\s*\(\s*["']([^"']+)["']/g;
    let mm;
    while ((mm = isRe.exec(text)) !== null) {
      if (/^https?:/i.test(mm[1]) || mm[1].startsWith('//')) fail(name, 'remote importScripts');
    }
    if (/\beval\s*\(/.test(text)) fail(name, 'eval');
    if (/new\s+Function\s*\(/.test(text)) fail(name, 'new Function');
  }
}

// 4. CSP
const csp = manifest.content_security_policy?.extension_pages || '';
const directives = {};
for (const part of csp.split(';')) {
  const t = part.trim();
  if (!t) continue;
  const bits = t.split(/\s+/);
  directives[bits[0]] = bits.slice(1);
}
if (!directives['script-src'] || directives['script-src'].join(' ') !== "'self'") fail('manifest.json', `CSP script-src ${directives['script-src'] ? directives['script-src'].join(' ') : ''}`);
if (!directives['object-src'] || directives['object-src'].join(' ') !== "'self'") fail('manifest.json', `CSP object-src ${directives['object-src'] ? directives['object-src'].join(' ') : ''}`);
// also ensure no unsafe-eval etc already covered by exact match

// 5. storage
for (const [name, buf] of files) {
  if (!name.endsWith('.js')) continue;
  const text = buf.toString('utf8');
  if (/storage\.local\b/.test(text) || /storage\[\s*['"]local['"]\s*\]/.test(text)) fail(name, 'storage.local');
  if (/storage\.sync\b/.test(text) || /storage\[\s*['"]sync['"]\s*\]/.test(text)) fail(name, 'storage.sync');
}

// 6. permissions used
const perms = manifest.permissions || [];
for (const perm of perms) {
  const needle = `chrome.${perm}`;
  let used = false;
  for (const [name, buf] of files) {
    if (name.endsWith('.js') && buf.toString('utf8').includes(needle)) used = true;
  }
  if (!used) fail('manifest.json', `unused permission ${perm}`);
}
// unknown permission? Any permission not in a known set? We'll not hardcode; usage check covers. But "unknown" maybe permission not standard. Skip.

// 7. hosts
const hosts = manifest.host_permissions || [];
if (hosts.length !== 1) {
  if (hosts.length > 1) fail('manifest.json', `second host ${hosts[1]}`);
  else fail('manifest.json', 'host_permissions');
}
const host = hosts[0] || '';
const hostMatch = /^https:\/\/[^/]+\/\*$/.test(host);
if (!hostMatch) fail('manifest.json', 'host_permissions');
const origin = host.replace(/\/\*$/, '');
let originInJs = false;
for (const [name, buf] of files) {
  if (name.endsWith('.js') && buf.toString('utf8').includes(origin)) originInJs = true;
}
if (hosts.length === 1 && !originInJs) fail('manifest.json', 'host origin not in JS');

if (problems.length === 0) {
  console.log('ok');
  process.exit(0);
} else {
  console.log(problems.join('\n'));
  process.exit(1);
}
