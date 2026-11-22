import { h, type ComponentChildren } from 'preact';
import { useEffect, useState } from 'preact/hooks';
import { t, lang } from '../../core/i18n';
import { apiFetch } from '../../core/api';
import { navigate } from '../../core/router';
import './datos.css';
import './acuerdo.css';

type Letter = { text: string; sha256: string; client_signed_at: string | null; attorney_signed_at: string | null };

/** The letter's markdown as text nodes only (headings, lists, bold): the client's name is in it, so never as HTML. */
function Markdown({ text }: { text: string }) {
  const inline = (s: string) => s.split(/\*\*(.+?)\*\*/).map((part, i) => (i % 2 ? h('strong', { key: i }, part) : part));
  const out: ComponentChildren[] = [];
  let list: ComponentChildren[] = [];
  const flush = () => { if (list.length) { out.push(h('ul', { key: out.length }, list)); list = []; } };
  text.split('\n').forEach((line, i) => {
    if (line.startsWith('- ')) { list.push(h('li', { key: i }, inline(line.slice(2)))); return; }
    flush();
    if (line.startsWith('# ')) out.push(h('h2', { key: i }, inline(line.slice(2))));
    else if (line.startsWith('## ')) out.push(h('h3', { key: i }, inline(line.slice(3))));
    else if (line.trim()) out.push(h('p', { key: i }, inline(line)));
  });
  flush();
  return h('div', { class: 'letter', tabIndex: 0, role: 'document', 'aria-label': t('acuerdo.title') }, out);
}

/** Day 5 (spec 6.1; Bus. & Prof. Code § 6148): read the letter, type a name, accept, sign; the copy comes once both signed. */
export function Acuerdo() {
  const [letter, setLetter] = useState<Letter | null>(null);
  const [waiting, setWaiting] = useState(false);
  const [name, setName] = useState('');
  const [accept, setAccept] = useState(false);
  const [note, setNote] = useState<'changed' | 'error' | null>(null);
  const load = async () => {
    const r = await apiFetch(`/engagement?lang=${lang.value}`);
    setWaiting(r.status === 409);
    if (r.ok) setLetter(await r.json());
  };
  useEffect(() => { void load(); }, []);
  const sign = async (e: Event) => {
    e.preventDefault();
    const r = await apiFetch('/engagement/sign', { method: 'POST', json: { name: name.trim(), accept, sha256: letter?.sha256 } }).catch(() => null);
    if (r?.status === 409) { setNote('changed'); setAccept(false); } else if (!r?.ok) { setNote('error'); return; } else setNote(null);
    await load();
  };
  const download = async () => {
    const r = await apiFetch('/engagement/pdf');
    if (!r.ok) { setNote('error'); return; }
    const url = URL.createObjectURL(await r.blob());
    Object.assign(document.createElement('a'), { href: url, download: 'acuerdo.pdf' }).click();
    URL.revokeObjectURL(url);
  };
  if (waiting || !letter) {
    return h('section', { class: 'screen datos-page' }, h('h1', null, t('acuerdo.title')), waiting ? h('p', null, t('acuerdo.wait')) : null);
  }
  const action = letter.attorney_signed_at
    ? h('div', { class: 'resumen-actions' },
        h('p', { class: 'confirmed', role: 'status' }, t('acuerdo.both')),
        h('button', { class: 'btn secondary', type: 'button', onClick: () => void download() }, t('acuerdo.download')),
        h('button', { class: 'btn', type: 'button', onClick: () => navigate('/pago') }, t('acuerdo.pay')))
    : letter.client_signed_at
      ? h('p', { class: 'confirmed', role: 'status' }, t('acuerdo.signed'))
      : h('form', { class: 'composer sign-form', onSubmit: sign },
          h('label', { for: 'acuerdo-name' }, t('acuerdo.name')),
          h('input', { id: 'acuerdo-name', autocomplete: 'name', value: name, onInput: (e: Event) => setName((e.currentTarget as HTMLInputElement).value) }),
          h('label', { class: 'option' }, h('input', { type: 'checkbox', checked: accept,
            onChange: (e: Event) => setAccept((e.currentTarget as HTMLInputElement).checked) }), t('acuerdo.accept')),
          h('button', { class: 'btn', type: 'submit', disabled: !name.trim() || !accept }, t('acuerdo.sign')));
  return h('section', { class: 'screen datos-page' },
    h('h1', null, t('acuerdo.title')),
    h('p', null, t('acuerdo.intro')),
    h(Markdown, { text: letter.text }),
    note ? h('p', { class: 'gate-error', role: 'alert' }, t(note === 'changed' ? 'acuerdo.changed' : 'datos.error')) : null,
    action);
}
