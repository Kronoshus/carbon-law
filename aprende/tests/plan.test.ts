import { describe, it, expect } from 'vitest';
import { setLang } from '../src/core/i18n';
import { dayLabel } from '../src/core/plan';

// The map header and the extension popup count the days against the client's own plan, which a change request or a
// holiday makes longer than the usual 14 days.
describe('dayLabel', () => {
  const plan = (last: number) => [{ day: 1 }, { day: 4 }, { day: last }];
  it('counts against the usual 14-day plan', () => {
    setLang('es');
    expect(dayLabel(1, plan(14), 'map.dayOf')).toBe('Día 1 de 14');
  });
  it('counts against a plan a change made longer', () => {
    setLang('en');
    expect(dayLabel(16, plan(16), 'map.dayOf')).toBe('Day 16 of 16');
    expect(dayLabel(16, plan(16), 'popup.today')).toBe('Day 16 of 16');
  });
  it('shows only the day past the plan or before the plan loads', () => {
    setLang('en');
    expect(dayLabel(20, plan(16), 'map.dayOf')).toBe('Day 20');
    expect(dayLabel(3, undefined, 'map.dayOf')).toBe('Day 3');
  });
});
