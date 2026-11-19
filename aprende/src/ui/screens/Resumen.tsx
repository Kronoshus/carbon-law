import { h } from 'preact';
import { useEffect, useState } from 'preact/hooks';
import { t } from '../../core/i18n';
import type { I18nKey } from '../../core/i18n-keys';
import { apiFetch } from '../../core/api';
import { navigate } from '../../core/router';

interface Q { id: string; asked_after: string; text: string; status: string; answer: string | null }

const GROUP_LABEL: Record<string, I18nKey> = { will: 'resumen.group.will', trust: 'resumen.group.trust', ahcd: 'resumen.group.ahcd', poa: 'resumen.group.poa', resumen: 'resumen.group.resumen' };

export function Resumen() {
  const [questions, setQuestions] = useState<Q[]>([]);
  const [editing, setEditing] = useState<string | null>(null);
  const [draft, setDraft] = useState('');
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);

  const load = async () => {
    const r = await apiFetch('/datos');
    if (r.ok) setQuestions(((await r.json()) as { questions: Q[] }).questions);
  };

  useEffect(() => { void load(); }, []);

  const startEdit = (q: Q) => { setEditing(q.id); setDraft(q.answer ?? ''); };
  const cancelEdit = () => { setEditing(null); setDraft(''); };
  const saveEdit = async (id: string) => {
    setBusy(true);
    try {
      await apiFetch(`/datos/${id}`, { method: 'PUT', json: { answer: draft } });
      setEditing(null); setDraft('');
      await load();
    } finally { setBusy(false); }
  };

  const gaps = questions.filter((q) => q.status === 'open').length;

  const groups = Array.from(new Set(questions.map((q) => q.asked_after)));

  const confirm = async () => {
    setBusy(true);
    try {
      const jr = await apiFetch('/journey');
      const j = jr.ok ? await jr.json() as { documents: { tentative: string[] } } : null;
      const codes = (j?.documents?.tentative?.length ? j.documents.tentative : ['will', 'trust', 'poa', 'ahcd']);
      const r = await apiFetch('/journey/events', { method: 'POST', json: { type: 'documents_confirmed', payload: { codes } } });
      if (r.ok) setConfirmed(true);
    } finally { setBusy(false); }
  };

  return h('div', null,
    h('h1', null, t('resumen.title')),
    h('p', null, t('resumen.body')),
    groups.map((g) => h('section', { key: g },
      h('h2', null, t(GROUP_LABEL[g])),
      questions.filter((q) => q.asked_after === g).map((q) => h('div', { key: q.id, class: 'resumen-row' },
        h('p', null, q.text),
        editing === q.id
          ? h('div', null,
              h('textarea', { value: draft, onInput: (e: Event) => setDraft((e.currentTarget as HTMLTextAreaElement).value) }),
              h('button', { type: 'button', onClick: () => void saveEdit(q.id), disabled: busy }, t('resumen.save')),
              h('button', { type: 'button', onClick: cancelEdit }, t('resumen.cancel')))
          : h('div', null,
              h('p', null, q.status === 'skipped' ? t('resumen.skipped') : q.status === 'open' ? t('resumen.open') : (q.answer ?? '')),
              h('button', { type: 'button', onClick: () => startEdit(q) }, t('resumen.edit'))))))),
    h('p', null, t('resumen.gaps', { n: gaps })),
    h('button', { type: 'button', onClick: () => navigate('/datos/resumen') }, t('resumen.complete')),
    h('button', { type: 'button', onClick: () => void confirm(), disabled: busy }, t('resumen.confirm')),
    confirmed && h('p', null, t('resumen.confirmed')));
}
