import { h } from 'preact';
import { useEffect, useState } from 'preact/hooks';
import { t, lang } from '../../core/i18n';
import { apiFetch } from '../../core/api';
import './datos.css';

export function Acuerdo() {
  const [data, setData] = useState<any>(null);
  const [status, setStatus] = useState<number | null>(null);
  const [name, setName] = useState('');
  const [accept, setAccept] = useState(false);
  const [busy, setBusy] = useState(false);
  const [changed, setChanged] = useState(false);

  const load = async () => {
    const r = await apiFetch(`/engagement?lang=${lang.value}`);
    setStatus(r.status);
    if (r.ok) setData(await r.json());
    else setData(await r.json().catch(() => null));
  };
  useEffect(() => { void load(); }, []);

  const sign = async (e: Event) => {
    e.preventDefault();
    if (!name.trim() || !accept || !data) return;
    setBusy(true);
    const r = await apiFetch('/engagement/sign', { method: 'POST', json: { name: name.trim(), accept, sha256: data.sha256 } });
    setBusy(false);
    if (r.status === 409) { setChanged(true); await load(); return; }
    if (r.ok) await load();
  };

  const download = async () => {
    const r = await apiFetch('/engagement/pdf');
    if (!r.ok) return;
    const blob = await r.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'acuerdo.pdf'; a.click();
    URL.revokeObjectURL(url);
  };

  if (status === 409 && data?.error === 'gate') {
    return h('section', null, h('h1', null, t('acuerdo.title')), h('p', null, t('acuerdo.wait')));
  }
  if (status === 409 && data?.error === 'not_ready') {
    return h('section', null, h('h1', null, t('acuerdo.title')), h('p', null, t('acuerdo.wait')));
  }
  if (!data) return h('section', null, h('p', null, '…'));

  const signed = !!data.client_signed_at;
  const both = !!data.attorney_signed_at;

  return h('section', { class: 'acuerdo' },
    h('h1', null, t('acuerdo.title')),
    h('p', null, t('acuerdo.intro')),
    h('div', { class: 'letter' }, data.text),
    changed ? h('p', null, t('acuerdo.changed')) : null,
    signed
      ? both
        ? h('div', null,
            h('p', null, t('acuerdo.both')),
            h('button', { onClick: download }, t('acuerdo.download')),
            h('button', { onClick: () => (window.location.hash = '#/pagar') }, t('acuerdo.pay')))
        : h('p', null, t('acuerdo.signed'))
      : h('form', { onSubmit: sign },
          h('label', null, t('acuerdo.name'),
            h('input', { value: name, onInput: (e: any) => setName(e.currentTarget.value) })),
          h('label', null,
            h('input', { type: 'checkbox', checked: accept, onChange: (e: any) => setAccept(e.currentTarget.checked) }),
            t('acuerdo.accept')),
          h('button', { type: 'submit', disabled: busy || !name.trim() || !accept }, t('acuerdo.sign'))),
    both ? h('button', { onClick: download }, t('acuerdo.download')) : null,
  );
}
