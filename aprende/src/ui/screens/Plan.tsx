import { h } from 'preact';
import { PriceCard } from '../PriceCard';

export function Plan() {
  return h('section', null, h(PriceCard, { codes: ['will'] }));
}
