import { describe, it, expect } from 'vitest';
import { startAt, clear, retryLater, finished } from '../src/core/lesson/queue';

const steps = [['a', 'b'], ['c', 'd', 'e']];

describe('lesson queue', () => {
  it('plays every item in order and crosses steps', () => {
    let s = startAt(steps);
    const seen: string[] = [];
    while (!finished(s)) { seen.push(s.queue[0]); s = clear(s, steps); }
    expect(seen).toEqual(['a', 'b', 'c', 'd', 'e']);
    expect(s.cleared).toBe(5);
  });
  it('a wrong answer comes back at the end of its step, not in the next step', () => {
    let s = startAt(steps);
    s = retryLater(s);                       // a wrong
    expect(s.queue).toEqual(['b', 'a']);
    s = clear(s, steps);                      // b right
    expect(s.queue).toEqual(['a']);
    s = clear(s, steps);                      // a right on the second try
    expect(s.step).toBe(1);
    expect(s.queue[0]).toBe('c');
  });
  it('resumes at a saved item', () => {
    const s = startAt(steps, 1, 'd');
    expect(s.queue).toEqual(['d', 'e']);
    expect(s.cleared).toBe(3);
  });
  it('a saved position that no longer exists starts the step', () => {
    expect(startAt(steps, 1, 'gone').queue).toEqual(['c', 'd', 'e']);
    expect(startAt(steps, 9).step).toBe(1);
  });
});
