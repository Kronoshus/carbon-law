import { describe, it, expect } from 'vitest';
import { vis, viseme } from '../src/core/character/visemes';

describe('vis', () => {
  it('maps spanish vowels', () => {
    expect(vis('a')).toEqual([1, 0]);
    expect(vis('e')).toEqual([0.65, 0]);
    expect(vis('o')).toEqual([0.7, 0.8]);
  });
  it('normalizes accents', () => {
    expect(vis('á')).toEqual([1, 0]);
    expect(vis('é')).toEqual([0.65, 0]);
  });
  it('unknown consonant fallback', () => {
    expect(vis('x')).toEqual([0.45, 0.1]);
  });
  it('space returns zero', () => {
    expect(vis(' ')).toEqual([0, 0]);
  });
});

describe('viseme', () => {
  it('null alignment returns [1,0]', () => {
    expect(viseme(null, 0)).toEqual([1, 0]);
  });
  it('spanish alignment fixture', () => {
    const al = {
      characters: ['H', 'o', 'l', 'a'],
      character_start_times_seconds: [0, 0.1, 0.2, 0.3],
    };
    expect(viseme(al, 0)).toEqual(vis('H'));
    expect(viseme(al, 0.15)).toEqual(vis('o'));
    expect(viseme(al, 0.35)).toEqual(vis('a'));
  });
  it('english alignment fixture', () => {
    const al = {
      characters: ['H', 'e', 'l', 'l', 'o'],
      character_start_times_seconds: [0, 0.05, 0.1, 0.15, 0.2],
    };
    expect(viseme(al, 0.12)).toEqual(vis('l'));
    expect(viseme(al, 1.0)).toEqual(vis('o'));
  });
});
