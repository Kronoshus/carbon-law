import { h, type ComponentChildren } from 'preact';
import { useRef, useState } from 'preact/hooks';
import { navigate } from '../../core/router';
import { t, lang } from '../../core/i18n';
import { apiFetch } from '../../core/api';
import { classifyConsent } from '../../core/consent';
import { CharacterStage } from '../CharacterStage';
import type { CharacterEngine } from '../../core/character/engine';
import { Icon } from '../Icons';
import './gate.css';

/** Day 1 before any lesson: disclosure → consent → names (spec 6.1, steps 2-4). Full screen, no tabs: one thing at a time. */
function Gate({ title, say, children }: { title?: string; say?: string; children?: ComponentChildren }) {
  const engine = useRef<CharacterEngine | null>(null);
  const speak = () => { if (say) { engine.current?.cancel(); void engine.current?.speak(say, lang.value); } };
  return h('div', { class: 'gate' }, h('div', null,
    title ? h('h1', { class: 'gate-title' }, title) : null,
    say ? h('div', { class: 'stage-wrap' }, h(CharacterStage, { character: 'calavera', onEngine: (e: CharacterEngine) => { engine.current = e; speak(); } })) : null,
    say ? h('div', { class: 'talk' }, h('p', { class: 'bubble', 'aria-live': 'polite' }, say,
      h('button', { class: 'icon-btn listen', type: 'button', 'aria-label': t('leccion.replay'), onClick: speak }, h(Icon, { name: 'volumen' })))) : null,
    h('section', { class: 'gate-body' }, children)));
}

async function record(type: string, payload: object) {
  const r = await apiFetch('/journey/events', { method: 'POST', json: { type, payload } });
  if (!r.ok) throw new Error(String(r.status));
}

function useSave() {
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  const save = async (work: () => Promise<void>) => {
    setBusy(true); setFailed(false);
    try { await work(); } catch { setFailed(true); } finally { setBusy(false); }
  };
  const error = failed ? h('p', { class: 'gate-error', role: 'alert' }, t('gate.error')) : null;
  return { busy, save, error };
}

export function InicioIa() {
  const { busy, save, error } = useSave();
  return h(Gate, { title: t('gate.disclosure.title'), say: `${t('gate.disclosure.calavera')} ${t('gate.disclosure.human')}` },
    error,
    h('button', { class: 'btn', type: 'button', disabled: busy,
      onClick: () => save(async () => { await record('ai_disclosed', {}); navigate('/inicio/consentimiento'); }) }, t('gate.disclosure.ok')));
}

export function InicioConsentimiento() {
  const [text, setText] = useState('');
  const [askedAgain, setAskedAgain] = useState(false);
  const { busy, save, error } = useSave();
  const answer = (a: 'yes' | 'no') => save(async () => {
    await record('consent', { answer: a });
    navigate(a === 'yes' ? '/inicio/nombres' : '/inicio/no-acepto');
  });
  const submit = (e: Event) => {
    e.preventDefault();
    const a = classifyConsent(text);
    if (a) return answer(a);
    if (askedAgain) return answer('no');          // unclear twice counts as no; it can be changed later
    setAskedAgain(true); setText('');
  };
  return h(Gate, { say: askedAgain ? t('gate.consent.again') : t('gate.consent.title') },
    h('h1', { class: 'visually-hidden' }, t('gate.consent.title')),   // the bubble above asks it (and La Calavera says it); the heading names the screen
    h('p', null, t('gate.consent.body')),
    h('div', { class: 'gate-choice' },
      h('button', { class: 'btn secondary', type: 'button', disabled: busy, onClick: () => answer('yes') }, t('gate.consent.yes')),
      h('button', { class: 'btn secondary', type: 'button', disabled: busy, onClick: () => answer('no') }, t('gate.consent.no'))),
    h('form', { class: 'gate-form', onSubmit: submit },
      h('label', null, t('gate.consent.label'),
        h('input', { value: text, autocomplete: 'off', onInput: (e: Event) => setText((e.target as HTMLInputElement).value) })),
      h('button', { class: 'btn', type: 'submit', disabled: busy || !text.trim() }, t('gate.consent.send'))),
    error);
}

export function InicioNoAcepto() {
  return h(Gate, { say: t('gate.refused.title') },
    h('h1', null, t('gate.refused.title')),
    h('p', null, t('gate.refused.body')),
    h('button', { class: 'btn', type: 'button', onClick: () => navigate('/aprender') }, t('gate.refused.learn')),
    h('button', { class: 'btn secondary', type: 'button', onClick: () => navigate('/inicio/consentimiento') }, t('gate.refused.change')));
}

export function InicioNombres() {
  const [names, setNames] = useState(['']);
  const { busy, save, error } = useSave();
  const set = (i: number, v: string) => setNames(names.map((n, k) => (k === i ? v : n)));
  const submit = (e: Event) => {
    e.preventDefault();
    const clean = names.map((n) => n.trim()).filter(Boolean);
    if (!clean.length) return;
    void save(async () => {
      await record('names_submitted', { names: clean });
      const j = await (await apiFetch('/journey')).json();
      navigate(j.conflict === 'clear' ? '/aprender' : '/inicio/espera');
    });
  };
  return h(Gate, {},
    h('h1', null, t('gate.names.title')),
    h('p', null, t('gate.names.body')),
    h('form', { class: 'gate-form', onSubmit: submit },
      names.map((n, i) => h('div', { class: 'name-row', key: i },
        h('label', null, t('gate.names.label', { n: i + 1 }),
          h('input', { value: n, autocomplete: 'off', onInput: (e: Event) => set(i, (e.target as HTMLInputElement).value) })),
        i > 0 ? h('button', { class: 'icon-btn', type: 'button', 'aria-label': t('gate.names.remove', { name: n.trim() || String(i + 1) }),
          onClick: () => setNames(names.filter((_, k) => k !== i)) }, h(Icon, { name: 'cerrar' })) : null)),
      h('button', { class: 'btn secondary', type: 'button', onClick: () => setNames([...names, '']) }, t('gate.names.add')),
      h('button', { class: 'btn', type: 'submit', disabled: busy || !names.some((n) => n.trim()) }, t('gate.names.send'))),
    error);
}

export function InicioEspera() {
  return h(Gate, { say: t('gate.wait.body') },
    h('h1', null, t('gate.wait.title')),
    h('button', { class: 'btn', type: 'button', onClick: () => navigate('/aprender') }, t('gate.wait.learn')));
}
