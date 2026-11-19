import { h } from 'preact';
import { useState } from 'preact/hooks';
import { t } from '../../core/i18n';
import type { I18nKey } from '../../core/i18n-keys';
import { apiFetch } from '../../core/api';
import { navigate } from '../../core/router';
import './datos.css';

const DOCS = ['will', 'trust', 'poa', 'ahcd'] as const;

/** Day 2: the tentative document choice, so the attorney's scope review can start (spec 6.2). */
export function Documentos() {
  const [picked, setPicked] = useState<string[]>([]);
  const [unsure, setUnsure] = useState(false);
  const [failed, setFailed] = useState(false);
  const toggle = (d: string) => { setUnsure(false); setPicked(picked.includes(d) ? picked.filter((x) => x !== d) : [...picked, d]); };
  const save = async (e: Event) => {
    e.preventDefault();
    const r = await apiFetch('/journey/events', { method: 'POST', json: { type: 'documents_tentative', payload: { codes: unsure ? [...DOCS] : picked } } }).catch(() => null);
    if (r?.ok) navigate('/aprender'); else setFailed(true);
  };
  const option = (label: string, checked: boolean, onChange: () => void) =>
    h('label', { class: 'option' }, h('input', { type: 'checkbox', checked, onChange }), label);
  return h('form', { class: 'screen datos-page', onSubmit: save },
    h('h1', null, t('docs.title')),
    h('p', null, t('docs.body')),
    h('fieldset', { class: 'choices' }, h('legend', { class: 'visually-hidden' }, t('docs.title')),
      DOCS.map((d) => option(t(`docs.${d}` as I18nKey), picked.includes(d), () => toggle(d))),
      option(t('docs.unsure'), unsure, () => { setUnsure(!unsure); setPicked([]); })),
    failed ? h('p', { class: 'gate-error', role: 'alert' }, t('datos.error')) : null,
    h('button', { class: 'btn', type: 'submit', disabled: !unsure && !picked.length }, t('docs.save')));
}
