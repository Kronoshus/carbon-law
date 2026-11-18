import { describe, it, expect } from 'vitest';
import { pairsToAnswer } from '../src/ui/exercises/Match';
import { orderToAnswer } from '../src/ui/exercises/Order';

describe('exercise answer builders', () => {
  it('pairsToAnswer builds left->right map', () => {
    expect(pairsToAnswer([{ leftKey: '0', rightKey: '2' }, { leftKey: '1', rightKey: '0' }])).toEqual({ '0': '2', '1': '0' });
  });
  it('orderToAnswer returns a copy of the chosen order', () => {
    const keys = ['2', '0', '1'];
    const out = orderToAnswer(keys);
    expect(out).toEqual(['2', '0', '1']);
    expect(out).not.toBe(keys);
  });
});
