import { h } from 'preact';
import { useEffect, useState } from 'preact/hooks';
import { apiFetch } from '../core/api';
import { t, formatMoney } from '../core/i18n';

type Discount = { event: string; amount: number };
type Item = { code: string; base: number; discounts: Discount[]; price: number; placeholder: boolean };

export function PriceCard(props: { codes: string[] }) {
  const [items, setItems] = useState<Item[]>([]);
  const [total, setTotal] = useState<number>(0);
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
        setTotal(data.total || 0);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [props.codes.join(',')]);

  if (loading) return h('div', { class: 'price-card' }, t('price.loading'));

  return h('section', { class: 'price-card' },
    items.map((it) => h('div', { class: 'price-card__item', key: it.code },
      h('div', { class: 'price-card__code' }, t(`doc.${it.code}` as any)),
      h('div', { class: 'price-card__base' }, formatMoney(it.base)),
      (it.discounts || []).map((d, i) => h('div', { class: 'price-card__discount', key: i },
        `${formatMoney(-d.amount)} ${t('price.por')} ${t(`price.event.${d.event}` as any)}`
      )),
      h('div', { class: 'price-card__price' }, formatMoney(it.price)),
      it.placeholder ? h('span', { class: 'price-card__placeholder' }, t('price.placeholder')) : null,
    )),
    h('div', { class: 'price-card__total' }, formatMoney(total)),
  );
}
