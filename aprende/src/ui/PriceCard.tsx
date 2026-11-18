import { h } from 'preact';
import { useEffect, useState } from 'preact/hooks';
import type { I18nKey } from '../core/i18n-keys';
import { apiFetch } from '../core/api';
import { t, formatMoney } from '../core/i18n';
import { Icon } from './Icons';
import './price-card.css';

type Discount = { event: string; amount: number };
type Item = { code: 'will' | 'trust' | 'poa' | 'ahcd'; base: number; discounts: Discount[]; price: number; placeholder: boolean };

const DOC_TITLE: Record<'will' | 'trust' | 'poa' | 'ahcd', I18nKey> = {
  will: 'doc.will',
  trust: 'doc.trust',
  poa: 'doc.poa',
  ahcd: 'doc.ahcd',
};

export function PriceCard(props: { codes: string[] }) {
  const [items, setItems] = useState<Item[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await apiFetch(`/payments/quote?codes=${props.codes.join(',')}`);
        if (!res.ok) { setLoading(false); return; }
        const data = await res.json();
        if (cancelled) return;
        setItems(data.items || []);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [props.codes.join(',')]);

  if (loading) return h('section', { class: 'card price', 'aria-busy': 'true' }, t('price.loading'));

  return h('section', { class: 'card price' },
    items.map((it) => {
      const totalDiscount = (it.discounts || []).reduce((a, d) => a + d.amount, 0);
      const earned = (it.discounts || []).length;
      const seals = Array.from({ length: 5 }, (_, i) =>
        h('span', { class: i < earned ? 'seal' : 'seal empty', key: i }, h(Icon, { name: i < earned ? 'sello' : 'sello-vacio' })));
      return h('div', { class: 'price-item', key: it.code },
        h('div', { class: 'row' },
          h('h2', null, t(DOC_TITLE[it.code])),
          h('span', { class: 'now' }, formatMoney(it.price)),
          h('s', null, formatMoney(it.base)),
        ),
        h('div', { class: 'row between' },
          h('div', { class: 'seals', role: 'img', 'aria-label': t('price.seals', { count: earned }) }, seals),
          h('p', { class: 'small' }, t('price.sum', { base: formatMoney(it.base), discount: formatMoney(totalDiscount), count: earned })),
        ),
        it.placeholder ? h('span', { class: 'example' }, t('price.placeholder')) : null,
      );
    }),
  );
}
