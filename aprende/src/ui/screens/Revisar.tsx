import { h } from 'preact';
import { useEffect, useState } from 'preact/hooks';
import { t, lang } from '../../core/i18n';
import type { I18nKey } from '../../core/i18n-keys';
import { apiFetch } from '../../core/api';
import { navigate } from '../../core/router';
import { documentName } from '../../core/documents';
import './datos.css';
import './revisar.css';

type Summary = { article: number; text: string };
type Doc = { id: string; name: string; version: number; content: string; decision: 'ok' | 'change' | null; summary: Summary[] };

const CHANGE_TYPES = ['Beneficiary change', 'Fiduciary change', 'Asset change', 'Guardian change', 'Distribution age change', 'Title change', 'Contact or address change', 'Appointment change', 'Document scope change'];

type CardProps = { d: Doc; editing: string | null; setEditing: (id: string) => void; changeType: string; setChangeType: (v: string) => void;
  note: string; setNote: (v: string) => void; sending: boolean; speak: (text: string) => void; decideOk: (id: string) => Promise<void>;
  sendChange: (id: string) => Promise<void> };

function DocCard({ d, editing, setEditing, changeType, setChangeType, note, setNote, sending, speak, decideOk, sendChange }: CardProps) {
  return h('section', { key: d.id, class: 'card', 'aria-label': documentName(d.name) },
    h('h2', null, documentName(d.name)),
    h('ol', { class: 'parts' }, d.summary.map((s: Summary) => h('li', { key: s.article }, h('strong', null, t('revisar.part', { n: s.article })), ' ', s.text))),
    h('button', { class: 'btn secondary', type: 'button', onClick: () => speak(d.summary.map((s: Summary) => s.text).join(' ')) }, t('revisar.listen')),
    h('details', null,
      h('summary', null, t('revisar.full')),
      h('div', { class: 'document-text' }, d.content)),
    d.decision === 'ok'
      ? h('p', { role: 'status' }, t('revisar.decided.ok'))
      : d.decision === 'change'
        ? h('p', { role: 'status' }, t('revisar.decided.change'))
        : h('div', { class: 'revisar-actions' },
            h('button', { class: 'btn', type: 'button', onClick: () => void decideOk(d.id) }, t('revisar.ok')),
            h('button', { class: 'btn secondary', type: 'button', onClick: () => setEditing(d.id) }, t('revisar.change')),
            editing === d.id ? h('form', { class: 'composer', onSubmit: (e: Event) => { e.preventDefault(); void sendChange(d.id); } },
              h('label', null, t('revisar.change.type'),
                h('select', { value: changeType, onChange: (e: Event) => setChangeType((e.currentTarget as HTMLSelectElement).value) },
                  ...CHANGE_TYPES.map((ct) => h('option', { key: ct, value: ct }, t(`change.${ct}` as I18nKey))))),
              h('label', null, t('revisar.change.note'),
                h('textarea', { value: note, onInput: (e: Event) => setNote((e.currentTarget as HTMLTextAreaElement).value) })),
              h('button', { class: 'btn', type: 'submit', disabled: sending }, t('revisar.change.send'))) : null));
}

export function Revisar() {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [loading, setLoading] = useState(true);
  const [wait, setWait] = useState(false);
  const [editing, setEditing] = useState<string | null>(null);
  const [changeType, setChangeType] = useState(CHANGE_TYPES[0]);
  const [note, setNote] = useState('');
  const [sending, setSending] = useState(false);

  const load = async () => {
    setLoading(true);
    const r = await apiFetch(`/review/documents?lang=${lang.value}`);
    if (r.status === 409) { setWait(true); setDocs([]); setLoading(false); return; }
    if (!r.ok) { setLoading(false); return; }
    const data = await r.json();
    setDocs(data.documents as Doc[]);
    setWait(false);
    setLoading(false);
  };
  useEffect(() => { void load(); }, []);

  const speak = (text: string) => {
    const synth = typeof window !== 'undefined' ? window.speechSynthesis : null;
    if (!synth) return;
    synth.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.lang = lang.value === 'en' ? 'en-US' : 'es-US';
    synth.speak(u);
  };

  const decideOk = async (id: string) => {
    const r = await apiFetch(`/review/documents/${id}`, { method: 'POST', json: { decision: 'ok' } });
    if (r.ok) setDocs((prev) => prev.map((d) => d.id === id ? { ...d, decision: 'ok' } : d));
  };

  const sendChange = async (id: string) => {
    if (!note.trim()) return;
    setSending(true);
    const r = await apiFetch(`/review/documents/${id}`, { method: 'POST', json: { decision: 'change', change_type: changeType, note: note.trim() } });
    setSending(false);
    if (r.ok) {
      setDocs((prev) => prev.map((d) => d.id === id ? { ...d, decision: 'change' } : d));
      setEditing(null);
      setNote('');
    }
  };

  if (loading) return h('p', { role: 'status' }, t('leccion.loading'));
  if (wait) return h('section', { class: 'screen' }, h('h1', null, t('revisar.title')), h('p', null, t('revisar.wait')),
    h('a', { class: 'btn', href: '#/aprender' }, t('empty.today')));

  const allOk = docs.length > 0 && docs.every((d) => d.decision === 'ok');

  return h('section', { class: 'screen datos-page' },
    h('h1', null, t('revisar.title')),
    h('p', null, t('revisar.body')),
    docs.map((d) => h(DocCard, { key: d.id, d, editing, setEditing, changeType, setChangeType, note, setNote, sending, speak, decideOk, sendChange })),
    allOk ? h('div', { class: 'revisar-all' },
      h('p', null, t('revisar.all')),
      h('button', { class: 'btn', type: 'button', onClick: () => navigate('/cita?kind=signing') }, t('revisar.book'))) : null);
}
