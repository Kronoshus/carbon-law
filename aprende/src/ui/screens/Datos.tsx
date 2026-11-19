import { h } from 'preact';
import { useEffect, useRef, useState } from 'preact/hooks';
import { t, lang } from '../../core/i18n';
import { apiFetch } from '../../core/api';
import { navigate } from '../../core/router';
import { CharacterStage } from '../CharacterStage';
import type { CharacterEngine } from '../../core/character/engine';
import './lesson.css';

const CHAR: Record<string, 'calavera' | 'oso'> = { will: 'calavera', trust: 'calavera', poa: 'calavera', ahcd: 'oso', resumen: 'calavera' };

interface Q { id: string; asked_after: string; text: string; status: string; answer: string | null }
interface ChatResp { text: string; history: string; reasoning: string | null; next_question: { id: string; text: string } | null }

interface Msg { role: 'user' | 'assistant'; content: string; question_id?: string; reasoning_content?: string | null }

export function Datos({ group }: { group: string }) {
  const character = (CHAR[group] ?? 'calavera') as 'calavera' | 'oso';
  const storageKey = `aprende.datos.${group}`;
  const [questions, setQuestions] = useState<Q[]>([]);
  const [msgs, setMsgs] = useState<Msg[]>(() => {
    try { const s = sessionStorage.getItem(storageKey); return s ? JSON.parse(s) : []; } catch { return []; }
  });
  const [next, setNext] = useState<{ id: string; text: string } | null>(null);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<'wait' | 'error' | null>(null);
  const [done, setDone] = useState(false);
  const engine = useRef<CharacterEngine | null>(null);
  const l = lang.value;

  const total = questions.filter((q) => q.asked_after === group).length || 1;
  const answeredSkipped = questions.filter((q) => q.asked_after === group && (q.status === 'answered' || q.status === 'skipped')).length;
  const n = Math.min(answeredSkipped + 1, total);

  const persist = (m: Msg[]) => { try { sessionStorage.setItem(storageKey, JSON.stringify(m)); } catch { /* ignore */ } };

  const speak = (text: string) => { engine.current?.cancel(); void engine.current?.speak(text, l); };

  const chat = async (messages: Msg[]) => {
    setBusy(true); setErr(null);
    try {
      const res = await apiFetch('/chat', { method: 'POST', json: { mode: 'intake', character, group, lang: l, messages } });
      if (res.status === 409) { setErr('wait'); return; }
      if (!res.ok) { setErr('error'); return; }
      const data = (await res.json()) as ChatResp;
      const assistant: Msg = { role: 'assistant', content: data.history ?? data.text, reasoning_content: data.reasoning };
      const nextMsgs = [...messages, assistant];
      setMsgs(nextMsgs); persist(nextMsgs);
      if (data.text) speak(data.text);
      if (data.next_question) setNext(data.next_question);
      else { setNext(null); setDone(true); }
    } catch { setErr('error'); }
    finally { setBusy(false); }
  };

  useEffect(() => {
    (async () => {
      const r = await apiFetch(`/datos?lang=${l}`);
      if (r.status === 409) { setErr('wait'); return; }
      if (r.status === 409) { setErr('wait'); return; }
      if (!r.ok) { setErr('error'); return; }
      const d = (await r.json()) as { questions: Q[] };
      setQuestions(d.questions as Q[]);
      // initial chat if no transcript
      if (msgs.length === 0) {
        await chat([]);
      } else {
        // restore next from last? re-ask? keep done if last assistant had no next. We'll set next unknown; call chat? 
      }
    })();
  }, []);

  const send = async () => {
    if (!input.trim() || !next || busy) return;
    const text = input.trim();
    setInput('');
    const userMsg: Msg = { role: 'user', content: text, question_id: next.id };
    const nextMsgs = [...msgs, userMsg];
    setMsgs(nextMsgs); persist(nextMsgs);
    await chat(nextMsgs);
  };

  const skip = async () => {
    if (!next || busy) return;
    try { await apiFetch(`/datos/${next.id}`, { method: 'PUT', json: { skipped: true } }); } catch { /* ignore */ }
    await chat(msgs);
  };

  if (err === 'wait') return h('p', { role: 'alert' }, t('datos.wait'));
  if (err === 'error') return h('p', { role: 'alert' }, t('datos.error'));

  if (done && !next) {
    return h('div', null,
      h('h1', null, t('datos.done.title')),
      h('button', { class: 'btn', type: 'button', onClick: () => navigate('/aprender') }, t('datos.done.back')));
  }

  return h('div', { class: 'datos' },
    h('h1', null, t('datos.title')),
    h('div', { class: 'stage-wrap' }, h(CharacterStage, { character, onEngine: (e: CharacterEngine) => { engine.current = e; } })),
    h('p', { class: 'datos-progress' }, t('datos.progress', { n, total })),
    h('p', null, 'DEBUG msgs=' + msgs.length + ' qs=' + questions.length),
    h('div', { class: 'transcript' },
      msgs.map((m, i) => m.role === 'assistant'
        ? h('p', { class: 'bubble', key: i }, m.content)
        : h('p', { class: 'bubble you', key: i }, h('span', { class: 'you-label' }, t('datos.you')), ' ', m.content))),
    !done && h('form', { onSubmit: (e: Event) => { e.preventDefault(); void send(); } },
      h('label', { for: 'datos-input' }, t('datos.label')),
      h('textarea', { id: 'datos-input', value: input, onInput: (e: Event) => setInput((e.currentTarget as HTMLTextAreaElement).value), 'aria-label': t('datos.label') }),
      h('button', { type: 'submit', disabled: busy }, t('datos.send'))),
    !done && h('button', { type: 'button', onClick: () => void skip(), disabled: busy }, t('datos.skip')),
    h('button', { type: 'button', onClick: () => navigate('/aprender') }, t('datos.later')));
}
