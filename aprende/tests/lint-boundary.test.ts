import { describe, it, expect } from 'vitest';
import { Linter } from 'eslint';
import { readFileSync } from 'node:fs';

describe('import boundary', () => {
  it('flags bad-import.ts', () => {
    const linter = new Linter();
    const code = readFileSync('tests/fixtures/bad-import.ts', 'utf8');
    const messages = linter.verify(code, {
      rules: { 'no-restricted-imports': ['error', { patterns: [{ group: ['**/targets/**'] }] }] },
      languageOptions: { parserOptions: { ecmaVersion: 2022, sourceType: 'module' } },
    });
    const restricted = messages.filter(m => m.ruleId === 'no-restricted-imports');
    expect(restricted.length).toBe(1);
  });
});
