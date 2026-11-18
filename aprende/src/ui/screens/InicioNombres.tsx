import { h } from 'preact';
import { useState } from 'preact/hooks';
import { navigate } from '../../core/router';
import { t } from '../../core/i18n';
import { apiFetch } from '../../core/api';

export function InicioNombres() {
  const [names, setNames] = useState<string[]>(['']);
  const [busy, setBusy] = useState(false);

  function update(i: number, v: string) {
    const next = [...names];
    next[i] = v;
    setNames(next);
  }
  function add() { setNames([...names, '']); }
  function remove(i: number) { setNames(names.filter((_, idx) => idx !== i)); }

  async function onSubmit(e: Event) {
    e.preventDefault();
    const cleaned = names.map((n) => n.trim()).filter(Boolean);
    if (cleaned.length === 0) return;
    setBusy(true);
    try {
      await apiFetch('/journey/events', { method: 'POST', json: { type: 'names_submitted', payload: { names: cleaned } } });
      const res = await apiFetch('/journey');
      const j = await res.json();
      if (j?.conflict === 'clear') navigate('/aprender');
      else navigate('/inicio/espera');
    } finally {
      setBusy(false);
    }
  }

  return h('section', { class: 'screen gate' },
    h('h1', null, t('gate.names.title')),
    h('p', null, t('gate.names.body')),
    h('form', { onSubmit },
      names.map((n, i) =>
        h('div', { class: 'name-row', key: i },
          h('label', { class: 'field' },
            t('gate.names.label', { n: i + 1 }),
            h('input', { 'aria-label': t('gate.names.label', { n: i + 1 }), value: n, onInput: (e: Event) => update(i, (e.target as HTMLInputElement).value) }),
          ),
          i > 0 ? h('button', { type: 'button', class: 'btn small', onClick: () => remove(i) }, t('gate.names.remove', { name: n })) : null,
        ),
      ),
      h('button', { type: 'button', class: 'btn small', onClick: add }, t('gate.names.add')),
      h('button', { class: 'btn', type: 'submit', disabled: busy }, t('gate.names.send')),
    ),
  );
}
