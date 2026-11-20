import { h } from 'preact';
import { useEffect, useState } from 'preact/hooks';
import { t } from '../../core/i18n';
import { apiFetch } from '../../core/api';
import './datos.css';

type Doc = { id: string; name: string; filename: string; url: string };

async function downloadUrl(url: string, filename: string) {
  const res = await apiFetch(url);
  const blob = await res.blob();
  const obj = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = obj;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(obj);
}

export function Firmados() {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [hasChecklist, setHasChecklist] = useState(false);
  const [mayTakeFinal, setMayTakeFinal] = useState(false);
  useEffect(() => {
    (async () => {
      const r = await apiFetch('/signed-documents');
      if (r.ok) setDocs(await r.json());
      const c = await apiFetch('/funding-checklist');
      setHasChecklist(c.ok);
      const j = await apiFetch('/journey');
      if (j.ok) { const data = await j.json(); setMayTakeFinal(!!data?.gates?.may_take_final_lesson); }
    })();
  }, []);
  return h('section', { class: 'screen datos-page' },
    h('h1', null, t('firmados.title')),
    h('p', null, t('firmados.body')),
    docs.length === 0 ? h('p', { class: 'status locked' }, t('firmados.none')) : null,
    docs.map((d) => h('div', { key: d.id, class: 'card' },
      h('button', { class: 'btn', type: 'button', onClick: () => void downloadUrl(d.url, d.filename) }, t('firmados.download', { name: d.name })))),
    hasChecklist ? h('div', { class: 'card' },
      h('h2', null, t('firmados.funding.title')),
      h('p', null, t('firmados.funding.body')),
      h('button', { class: 'btn', type: 'button', onClick: () => void downloadUrl('/funding-checklist', 'funding-checklist.md') }, t('firmados.funding.download'))) : null,
    mayTakeFinal ? h('p', null, h('a', { class: 'link-btn', href: '#/leccion/final' }, t('firmados.final'))) : null);
}

