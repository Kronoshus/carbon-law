import { h } from 'preact';
import { useEffect, useState } from 'preact/hooks';
import { t, lang } from '../../core/i18n';
import type { I18nKey } from '../../core/i18n-keys';
import { apiFetch } from '../../core/api';
import { navigate } from '../../core/router';
import './datos.css';

type Q = { id: string; asked_after: string; text: string; status: 'open' | 'answered' | 'skipped'; answer: string | null };
const GROUPS = ['will', 'trust', 'ahcd', 'poa', 'resumen'];

/** Day 4: everything the client has told us, by document, each answer correctable; then the documents are confirmed. */
export function Resumen() {
  const [qs, setQs] = useState<Q[]>([]);
  const [docs, setDocs] = useState<string[]>([]);
  const [editing, setEditing] = useState<{ id: string; text: string } | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [failed, setFailed] = useState(false);
  const load = async () => {
    setQs((await (await apiFetch(`/datos?lang=${lang.value}`)).json()).questions);
    const j = await (await apiFetch('/journey')).json();
    setDocs(j.documents.tentative.length ? j.documents.tentative : ['will', 'trust', 'poa', 'ahcd']);
  };
  useEffect(() => { void load(); }, []);
  const save = async (e: Event) => {
    e.preventDefault();
    if (!editing?.text.trim()) return;
    const r = await apiFetch(`/datos/${editing.id}`, { method: 'PUT', json: { answer: editing.text.trim() } }).catch(() => null);
    if (!r?.ok) { setFailed(true); return; }
    setEditing(null); setFailed(false); await load();
  };
  const confirm = async () => {
    const r = await apiFetch('/journey/events', { method: 'POST', json: { type: 'documents_confirmed', payload: { codes: docs } } }).catch(() => null);
    if (r?.ok) setConfirmed(true); else setFailed(true);
  };
  const gaps = qs.filter((q) => q.status === 'open').length;
  const row = (q: Q) => h('li', { key: q.id, class: 'answer-row' },
    h('p', { class: 'question' }, q.text),
    editing?.id === q.id
      ? h('form', { class: 'composer', onSubmit: save },
          h('label', { class: 'visually-hidden', for: `edit-${q.id}` }, q.text),
          h('textarea', { id: `edit-${q.id}`, rows: 2, value: editing.text, onInput: (e: Event) => setEditing({ id: q.id, text: (e.currentTarget as HTMLTextAreaElement).value }) }),
          h('div', { class: 'composer-actions' },
            h('button', { class: 'btn secondary', type: 'button', onClick: () => setEditing(null) }, t('resumen.cancel')),
            h('button', { class: 'btn', type: 'submit' }, t('resumen.save'))))
      : h('div', { class: 'answer' },
          q.status === 'answered' ? h('p', null, q.answer) : h('p', { class: `status ${q.status}` }, t(q.status === 'skipped' ? 'resumen.skipped' : 'resumen.open')),
          h('button', { class: 'link-btn', type: 'button', 'aria-label': `${t('resumen.edit')}: ${q.text}`,
            onClick: () => setEditing({ id: q.id, text: q.answer ?? '' }) }, t('resumen.edit'))));
  return h('section', { class: 'screen datos-page' },
    h('h1', null, t('resumen.title')),
    h('p', null, t('resumen.body')),
    GROUPS.filter((g) => qs.some((q) => q.asked_after === g)).map((g) => h('section', { key: g, class: 'card answer-group' },
      h('h2', null, t(`resumen.group.${g}` as I18nKey)),
      h('ul', null, qs.filter((q) => q.asked_after === g).map(row)))),
    gaps ? h('p', { class: 'gaps' }, t('resumen.gaps', { n: gaps })) : null,
    failed ? h('p', { class: 'gate-error', role: 'alert' }, t('datos.error')) : null,
    confirmed ? h('p', { class: 'confirmed', role: 'status' }, t('resumen.confirmed')) : null,
    h('div', { class: 'resumen-actions' },
      gaps ? h('button', { class: 'btn secondary', type: 'button', onClick: () => navigate('/datos/resumen') }, t('resumen.complete')) : null,
      confirmed ? null : h('button', { class: 'btn', type: 'button', onClick: () => void confirm() }, t('resumen.confirm'))));
}
