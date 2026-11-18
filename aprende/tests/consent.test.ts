import { describe, it, expect } from 'vitest';
import { classifyConsent } from '../src/core/consent';
import phrases from '../../tests/fixtures/consent_phrases.json';

const expected = { yes: 'yes', no: 'no', unclear: null } as const;

describe('consent phrase table (shared with the backend)', () => {
  for (const [kind, texts] of Object.entries(phrases) as [keyof typeof expected, string[]][]) {
    for (const text of texts) {
      it(`${kind}: ${JSON.stringify(text)}`, () => expect(classifyConsent(text)).toBe(expected[kind]));
    }
  }
});
