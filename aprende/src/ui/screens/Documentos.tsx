import { h } from 'preact';
import { useState } from 'preact/hooks';
import { t } from '../../core/i18n';
import type { I18nKey } from '../../core/i18n-keys';
import { apiFetch } from '../../core/api';
import { navigate } from '../../core/router';

const CODES = ['will', 'trust', 'poa', 'ahcd'];
const LABEL: Record<string, I18nKey> = { will: 'docs.will', trust: 'docs.trust', poa: 'docs.poa', ahcd: 'docs.ahcd' };

export function Documentos() {
  const [selected, setSelected] = useState<string[]>([]);
  const [unsure, setUnsure] = useState(false);
  const [busy, setBusy] = useState(false);

  const toggle = (code: string) => {
    if (unsure) setUnsure(false);
    setSelected((prev) => prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code]);
  };
  const toggleUnsure = () => {
    setUnsure((u) => !u);
    if (!unsure) setSelected([]);
  };

  const save = async () => {
    setBusy(true);
    const codes = unsure ? CODES : selected;
    try {
      const r = await apiFetch('/journey/events', { method: 'POST', json: { type: 'documents_tentative', payload: { codes } } });
      if (r.ok) navigate('/aprender');
    } finally { setBusy(false); }
  };

  return h('div', null,
    h('h1', null, t('docs.title')),
    h('p', null, t('docs.body')),
    CODES.map((c: string) => h('label', { key: c },
      h('input', { type: 'checkbox', checked: selected.includes(c) && !unsure, onChange: () => toggle(c), disabled: unsure }),
      t(LABEL[c]))),
    h('label', null,
      h('input', { type: 'checkbox', checked: unsure, onChange: toggleUnsure }),
      t('docs.unsure')),
    h('button', { type: 'button', onClick: () => void save(), disabled: busy }, t('docs.save')));
}
