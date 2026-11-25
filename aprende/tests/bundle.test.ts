import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';

describe('three is not in the initial bundle', () => {
  it('excludes three from the entry chunks of the web build (built in tests/build-once.ts)', () => {
    const manifest = JSON.parse(readFileSync('dist/web/.vite/manifest.json', 'utf8'));
    const entry = Object.values(manifest).find((v) => (v as { isEntry?: boolean }).isEntry) as { file: string; imports?: string[] };
    const chunks = [entry.file, ...(entry.imports || [])];
    for (const c of chunks) {
      const src = readFileSync(`dist/web/${c}`, 'utf8');
      expect(src).not.toContain('WebGLRenderer');
    }
  });
});
