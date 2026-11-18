import { describe, it, expect } from 'vitest';
import { toggle } from '../src/ui/exercises/Match';
import { move } from '../src/ui/exercises/Order';

describe('match pairing', () => {
  it('pairs a left tile with a right tile', () => {
    let s = toggle({}, '0', null);
    expect(s).toEqual({ pairs: {}, pending: '0' });
    s = toggle(s.pairs, s.pending, '2');
    expect(s).toEqual({ pairs: { '0': '2' }, pending: null });
  });
  it('choosing a paired tile undoes its pair', () => {
    expect(toggle({ '0': '2' }, '0', null).pairs).toEqual({});
    expect(toggle({ '0': '2', '1': '0' }, null, '2').pairs).toEqual({ '1': '0' });
  });
  it('a right tile alone does nothing', () => {
    expect(toggle({}, null, '1')).toEqual({ pairs: {}, pending: null });
  });
});

describe('order moves', () => {
  it('moves a step up and down, never past the ends', () => {
    expect(move(['a', 'b', 'c'], 1, -1)).toEqual(['b', 'a', 'c']);
    expect(move(['a', 'b', 'c'], 1, 1)).toEqual(['a', 'c', 'b']);
    expect(move(['a', 'b', 'c'], 0, -1)).toEqual(['a', 'b', 'c']);
    expect(move(['a', 'b', 'c'], 2, 1)).toEqual(['a', 'b', 'c']);
  });
});
