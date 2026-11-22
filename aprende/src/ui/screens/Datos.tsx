import { h } from 'preact';
import { useEffect, useRef, useState } from 'preact/hooks';
import { t, lang } from '../../core/i18n';
import { apiFetch } from '../../core/api';
import { navigate } from '../../core/router';
import { CharacterStage } from '../CharacterStage';
import type { CharacterEngine } from '../../core/character/engine';
import './lesson.css';
import './datos.css';

/** "Tus datos" (spec 6.1, 9.3): the lesson's character asks the open questions one at a time; the client types or skips. */
const CHARACTER: Record<string, 'calavera' | 'oso'> = { ahcd: 'oso' };
type Msg = { role: 'user' | 'assistant'; content: string; shown?: string; question_id?: string; reasoning_content?: string | null };
type Next = { id: string; text: string } | null;
type Saved = { msgs: Msg[]; next: Next; done: boolean };

export function Datos({ group }: { group: string }) {
  const character = CHARACTER[group] ?? 'calavera';
  const key = `aprende.datos.${group}`;
  const saved: Saved | null = (() => { try { return JSON.parse(sessionStorage.getItem(key) ?? 'null'); } catch { return null; } })();
  const [state, setState] = useState<Saved>(saved ?? { msgs: [], next: null, done: false });
  const [progress, setProgress] = useState<{ n: number; total: number } | null>(null);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<'wait' | 'error' | 'server' | null>(null);
  const [openQ, setOpenQ] = useState<string | null>(null);
  const [chatOff, setChatOff] = useState(false);
  const engine = useRef<CharacterEngine | null>(null);
  const l = lang.value;

  const keep = (s: Saved) => { setState(s); sessionStorage.setItem(key, JSON.stringify(s)); };
  const count = async () => {
    const r = await apiFetch(`/datos?lang=${l}`);
    if (r.status === 409) { setProblem('wait'); return false; }
    const qs = ((await r.json()).questions as { asked_after: string; status: string; text: string }[]).filter((q) => q.asked_after === group);
    const left = qs.filter((q) => q.status === 'open').length;
    const firstOpen = qs.find((q) => q.status === 'open');
    setOpenQ(firstOpen ? firstOpen.text : null);
    setProgress({ n: Math.min(qs.length - left + 1, qs.length), total: qs.length });
    return true;
  };
  const ask = async (msgs: Msg[]) => {
    setBusy(true); setProblem(null);
    try {
      const r = await apiFetch('/chat', { method: 'POST', json: { mode: 'intake', character, group, lang: l,
        messages: msgs.map((m) => ({ role: m.role, content: m.content, question_id: m.question_id, reasoning_content: m.reasoning_content })) } });
      if (r.status === 409) { setProblem('wait'); return; }
      if (r.status === 503) {
        const j = await r.json().catch(() => ({}));
        if (j && j.error === 'ai_chat_off') { setChatOff(true); setBusy(false); return; }
      }
      if (r.status >= 500) { setProblem('server'); setBusy(false); return; }
      if (!r.ok) throw new Error(String(r.status));
      const d = await r.json();
      let mine: Msg[] = d.text ? [...msgs, { role: 'assistant' as const, content: d.history, shown: d.text, reasoning_content: d.reasoning }] : msgs;
      const answered = [...msgs].reverse().find((m) => m.role === 'user')?.question_id;
      if (d.next_question?.text && answered && d.next_question.id !== answered) {     // on to a new question: say it (attorney-approved text)
        mine = [...mine, { role: 'assistant', content: d.next_question.text }];
      }
      keep({ msgs: mine, next: d.next_question, done: !d.next_question });
      if (d.text) { engine.current?.cancel(); void engine.current?.speak(d.text, l); }
      await count();
    } catch { setProblem('error'); } finally { setBusy(false); }
  };
  useEffect(() => { void count().then((ok) => { if (ok && !saved) void ask([]); }); }, []);

  const send = (e: Event) => {
    e.preventDefault();
    if (!input.trim() || !state.next) return;
    const msgs = [...state.msgs, { role: 'user' as const, content: input.trim(), question_id: state.next.id }];
    setInput(''); keep({ ...state, msgs });
    void ask(msgs);
  };
  const skip = async () => {
    if (!state.next) return;
    setBusy(true);
    const r = await apiFetch(`/datos/${state.next.id}`, { method: 'PUT', json: { skipped: true } }).catch(() => null);
    if (!r?.ok) { setBusy(false); setProblem('error'); return; }
    await ask(state.msgs);
  };

  if (chatOff) {
    return h('div', { class: 'datos' },
      h('section', { class: 'datos-body' },
        h('p', null, t('chat.off')),
        h('button', { class: 'btn', type: 'button', onClick: () => navigate('/aprender') }, t('datos.done.back'))));
  }

  const body = problem === 'wait'
    ? [h('p', null, t('datos.wait')), h('button', { class: 'btn', type: 'button', onClick: () => navigate('/aprender') }, t('datos.done.back'))]
    : state.done
      ? [h('h1', null, t('datos.done.title')), h('button', { class: 'btn', type: 'button', onClick: () => navigate('/aprender') }, t('datos.done.back'))]
      : [
          h('div', { class: 'datos-head' }, h('h1', null, t('datos.title')),
            progress?.total ? h('span', { class: 'chip' }, t('datos.progress', progress)) : null),
          h('ol', { class: 'transcript', 'aria-live': 'polite' }, state.msgs.map((m, i) => h('li', { key: i, class: m.role === 'user' ? 'you' : 'them' },
            m.role === 'user' ? h('span', { class: 'who' }, t('datos.you')) : null, m.role === 'user' ? m.content : (m.shown ?? m.content)))),
          problem === 'error' ? h('p', { class: 'gate-error', role: 'alert' }, t('datos.error')) : null,
          problem === 'server' ? h('p', { class: 'gate-error', role: 'alert' }, t('datos.serverError')) : null,
          problem && openQ && state.msgs.length === 0 ? h('p', { class: 'bubble' }, openQ) : null,
          problem ? h('button', { class: 'btn secondary', type: 'button', onClick: () => void ask(state.msgs) }, t('datos.retry')) : null,
          h('form', { class: 'composer', onSubmit: send },
            h('label', { for: 'datos-answer' }, t('datos.label')),
            h('textarea', { id: 'datos-answer', rows: 3, value: input, disabled: busy || !state.next,
              onInput: (e: Event) => setInput((e.currentTarget as HTMLTextAreaElement).value) }),
            h('div', { class: 'composer-actions' },
              h('button', { class: 'btn secondary', type: 'button', disabled: busy || !state.next, onClick: () => void skip() }, t('datos.skip')),
              h('button', { class: 'btn', type: 'submit', disabled: busy || !input.trim() }, t('datos.send')))),
          h('button', { class: 'link-btn', type: 'button', onClick: () => navigate('/aprender') }, t('datos.later')),
        ];
  return h('div', { class: 'datos' },
    h('div', { class: 'stage-wrap' }, h(CharacterStage, { character, onEngine: (e: CharacterEngine) => { engine.current = e; } })),
    h('section', { class: 'datos-body' }, body));
}
