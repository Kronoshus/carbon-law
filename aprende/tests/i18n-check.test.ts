import { execFileSync } from 'node:child_process';
import { mkdtempSync, mkdirSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { describe, it, expect } from 'vitest';

const script = resolve(__dirname, '../scripts/i18n-check.mjs');

function catalog(es: object, en: object, dts?: string): string {
  const dir = mkdtempSync(join(tmpdir(), 'i18n-'));
  mkdirSync(join(dir, 'i18n'));
  mkdirSync(join(dir, 'src', 'core'), { recursive: true });
  writeFileSync(join(dir, 'i18n', 'es.json'), JSON.stringify(es));
  writeFileSync(join(dir, 'i18n', 'en.json'), JSON.stringify(en));
  if (dts !== undefined) writeFileSync(join(dir, 'src', 'core', 'i18n-keys.d.ts'), dts);
  return dir;
}

function check(dir: string, ...args: string[]): { ok: boolean; out: string } {
  try {
    return { ok: true, out: execFileSync('node', [script, '--dir', dir, ...args], { encoding: 'utf8', stdio: 'pipe' }) };
  } catch (e) {
    return { ok: false, out: String((e as { stderr?: string }).stderr) };
  }
}

describe('i18n-check script', () => {
  it('fails when a key is missing in one language', () => {
    const r = check(catalog({ a: 'x', b: 'y' }, { a: 'x' }));
    expect(r.ok).toBe(false);
    expect(r.out).toContain('Missing in en.json: b');
  });

  it('fails on a stale generated types file and passes after --write', () => {
    const dir = catalog({ a: 'x' }, { a: 'x' }, 'export type I18nKey = "old";\n');
    expect(check(dir).ok).toBe(false);
    expect(check(dir, '--write').ok).toBe(true);
    expect(check(dir).ok).toBe(true);
  });
});
