import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';

describe('three is dynamically imported', () => {
  it('engine uses dynamic import only', () => {
    const src = readFileSync('src/core/character/engine.ts', 'utf8');
    expect(src).not.toMatch(/from\s+['"]three['"]/);
    expect(src).toMatch(/await import\(['"]three['"]\)/);
  });
  it('CharacterStage does not import three', () => {
    const src = readFileSync('src/ui/CharacterStage.tsx', 'utf8');
    expect(src).not.toMatch(/three/);
  });
});
