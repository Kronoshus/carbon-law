import { h, type ComponentChildren } from 'preact';
import { useEffect, useMemo, useRef, useState } from 'preact/hooks';
import { t, lang } from '../../core/i18n';
import { apiFetch } from '../../core/api';
import { platform } from '../../platform';
import { navigate } from '../../core/router';
import { startAt, clear, retryLater, finished, type QueueState } from '../../core/lesson/queue';
import type { CharacterEngine } from '../../core/character/engine';
import type { CharacterState } from '../../core/character/states';
import { CharacterStage } from '../CharacterStage';
import { MatchExercise } from '../exercises/Match';
import { OrderExercise } from '../exercises/Order';
import { ListenExercise } from '../exercises/Listen';
import { Icon } from '../Icons';
import './lesson.css';

type Character = 'calavera' | 'pinata' | 'oso';
interface Item {
  id: string; kind: string; character?: Character; sensitive?: boolean;
  text?: string; story?: string; prompt?: string; statement?: string; options?: string[];
  say?: string; left?: { key: string; text: string }[]; right?: { key: string; text: string }[];
  steps?: { key: string; text: string }[];
}
interface Lesson { id: string; title: string; character: Character; sensitive: boolean; steps: { id: string; title: string; items: Item[] }[] }
interface Feedback { correct: boolean; explain: string | null; source: { kind: string; cite: string; url: string } | null; petals: number }

const SUPPORTED = new Set(['explain', 'choice', 'scenario', 'truefalse', 'match', 'order', 'listen']);
const posKey = (id: string) => `aprende.lesson.${id}`;

/** What the character says for an item: the explanation, or the question. */
const spoken = (it: Item) => it.say ?? it.text ?? it.statement ?? it.prompt ?? '';

export function Leccion({ id }: { id: string }) {
  const [lesson, setLesson] = useState<Lesson | null>(null);
  const [failure, setFailure] = useState<'locked' | 'error' | null>(null);
  const [state, setState] = useState<QueueState | null>(null);
  const [choice, setChoice] = useState<unknown>(null);
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [result, setResult] = useState<{ completed: boolean; score: number } | null>(null);
  const [streak, setStreak] = useState(0);
  const engine = useRef<CharacterEngine | null>(null);
  const [engineTick, setEngineTick] = useState(0);      // a (new) character engine is ready to speak
  const l = lang.value;

  const steps = useMemo(() => lesson?.steps.map((s) => s.items.map((it) => it.id)) ?? [], [lesson]);
  const byId = useMemo(() => new Map(lesson?.steps.flatMap((s) => s.items).map((it) => [it.id, it]) ?? []), [lesson]);
  const total = steps.reduce((n, s) => n + s.length, 0);
  const item = state && !finished(state) ? byId.get(state.queue[0]) ?? null : null;

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const res = await apiFetch(`/learn/lessons/${encodeURIComponent(id)}?lang=${l}`);
      if (cancelled) return;
      if (!res.ok) { setFailure(res.status === 409 ? 'locked' : 'error'); return; }
      const data = (await res.json()) as Lesson;
      const saved = await platform.storage.get(posKey(id));
      const pos = saved ? (JSON.parse(saved) as { step: number; item: string }) : { step: 0, item: undefined };
      if (cancelled) return;
      setLesson(data);
      setState(startAt(data.steps.map((s) => s.items.map((it) => it.id)), pos.step, pos.item));
      const p = await apiFetch('/progress');
      if (p.ok && !cancelled) setStreak(((await p.json()) as { streak: { count: number } }).streak.count);
    })();
    return () => { cancelled = true; };
  }, [id, l]);

  useEffect(() => {                               // remember where the client is
    if (state && item) void platform.storage.set(posKey(id), JSON.stringify({ step: state.step, item: item.id }));
  }, [item?.id]);

  useEffect(() => {                               // say the item aloud (once, even when the character changes)
    if (!item || !engine.current) return;
    engine.current.cancel();
    void engine.current.speak(spoken(item), l);
  }, [item?.id, engineTick]);

  useEffect(() => {
    if (!state || !finished(state) || result) return;
    (async () => {
      const res = await apiFetch(`/learn/lessons/${encodeURIComponent(id)}/complete`, { method: 'POST' });
      const r = (await res.json()) as { completed: boolean; score: number };
      if (r.completed) await platform.storage.remove(posKey(id));
      setResult(r);
    })();
  }, [state && finished(state)]);

  const next = () => {
    if (!state) return;
    setState(feedback && !feedback.correct ? retryLater(state) : clear(state, steps));
    setFeedback(null);
    setChoice(null);
  };

  const check = async () => {
    if (!item || choice === null) return;
    const res = await apiFetch('/learn/attempts', { method: 'POST', json: { item_id: item.id, answer: choice, lang: l } });
    if (res.ok) setFeedback((await res.json()) as Feedback);
  };

  if (failure) return h(Frame, { title: lesson?.title ?? '' }, h('p', { class: 'lesson-note', role: 'alert' }, t(failure === 'locked' ? 'leccion.locked' : 'leccion.error')),
    h('button', { class: 'btn', type: 'button', onClick: () => navigate('/aprender') }, t('celebration.back')));
  if (!lesson || !state) return h(Frame, { title: '' }, h('p', { class: 'lesson-note', role: 'status' }, t('leccion.loading')));

  const calm = lesson.sensitive || !!item?.sensitive;
  const character = item?.character ?? lesson.character;
  const charState: CharacterState = result ? (result.completed ? (calm ? 'comforting' : 'celebrating') : 'idle')
    : feedback ? (feedback.correct && !calm ? 'celebrating' : 'idle') : 'talking';

  const bar = h('header', { class: 'lessonbar' },
    h('button', { class: 'icon-btn', type: 'button', 'aria-label': t('leccion.exit'), onClick: () => navigate('/aprender') }, h(Icon, { name: 'cerrar' })),
    h('progress', { class: 'lesson', max: total, value: state.cleared, 'aria-label': t('leccion.progress') }),
    h('span', { class: 'chip' }, h(Icon, { name: 'vela' }), String(streak)));

  if (result) {
    return h('div', { class: 'lesson-player' }, bar, h('main', null,
      h(CharacterStage, { character: lesson.character, state: charState }),
      h('section', { class: `celebration card${calm ? ' calm' : ''}`, role: 'status' },
        result.completed
          ? [h('h1', null, t(calm ? 'celebration.calm' : 'celebration.title')),
             h('button', { class: 'btn', type: 'button', onClick: () => navigate('/aprender') }, t('celebration.back'))]
          : [h('p', null, t('result.notYet', { score: Math.round(result.score * 100) })),
             h('button', { class: 'btn', type: 'button', onClick: () => { setResult(null); setState(startAt(steps)); } }, t('result.review'))])));
  }
  if (!item) return null;

  return h('div', { class: 'lesson-player' }, bar, h('main', null,
    h('div', { class: 'stage-wrap' }, h(CharacterStage, { character, state: charState, onEngine: (e) => { engine.current = e; setEngineTick((n) => n + 1); } })),
    item.kind === 'explain'           // a question is on screen as its heading; only explanations need the bubble
      ? h('div', { class: 'talk' }, h('p', { class: 'bubble', 'aria-live': 'polite' }, spoken(item),
          h('button', { class: 'icon-btn listen', type: 'button', 'aria-label': t('leccion.replay'), onClick: () => { engine.current?.cancel(); void engine.current?.speak(spoken(item), l); } }, h(Icon, { name: 'volumen' }))))
      : null,
    !SUPPORTED.has(item.kind)
      ? h('section', { class: 'q' }, h('p', { class: 'lesson-note' }, t('leccion.soon')), h('button', { class: 'btn secondary', type: 'button', onClick: next }, t('leccion.skip')))
      : item.kind === 'explain'
        ? h('section', { class: 'q' }, h('button', { class: 'btn', type: 'button', onClick: next }, t('leccion.continue')))
        : item.kind === 'match'
        ? h(MatchExercise, { item, choice: choice as unknown as Record<string,string> | null, setChoice, locked: !!feedback, correct: feedback?.correct ?? null, onCheck: check })
        : item.kind === 'order'
        ? h(OrderExercise, { item, choice: choice as unknown as string[] | null, setChoice, locked: !!feedback, correct: feedback?.correct ?? null, onCheck: check })
        : item.kind === 'listen'
        ? h(ListenExercise, { item, choice: choice as unknown as number | null, setChoice, locked: !!feedback, correct: feedback?.correct ?? null, onCheck: check })
        : h(Question, { item, choice: choice as unknown as number | boolean | null, setChoice, locked: !!feedback, correct: feedback?.correct ?? null, onCheck: check }),
    feedback && h(FeedbackSheet, { feedback, onNext: next })));
}

function Frame({ title, children }: { title: string; children?: ComponentChildren }) {
  return h('div', { class: 'lesson-player' }, h('main', { class: 'screen' }, title ? h('h1', null, title) : null, children));
}

function Question({ item, choice, setChoice, locked, correct, onCheck }: {
  item: Item; choice: number | boolean | null; setChoice: (v: number | boolean) => void; locked: boolean; correct: boolean | null; onCheck: () => void;
}) {
  const options: [string, number | boolean][] = item.kind === 'truefalse'
    ? [[t('leccion.true'), true], [t('leccion.false'), false]]
    : (item.options ?? []).map((o, i) => [o, i]);
  const heading = item.kind === 'truefalse' ? 'leccion.kind.truefalse' : item.kind === 'scenario' ? 'leccion.kind.scenario' : 'leccion.kind.choice';
  return h('form', { class: 'q', 'aria-labelledby': `q-${item.id}`, onSubmit: (e: Event) => { e.preventDefault(); onCheck(); } },
    h('span', { class: 'kind' }, t(heading)),
    item.story ? h('p', { class: 'story' }, item.story) : null,
    h('h1', { id: `q-${item.id}` }, item.prompt ?? item.statement),
    h('fieldset', { disabled: locked },
      h('legend', { class: 'visually-hidden' }, t(heading)),
      options.map(([text, value], i) => {
        const picked = choice === value;
        const mark = locked && picked ? (correct ? ' correct' : ' wrong') : '';
        return h('label', { class: `option${mark}`, key: String(value) },
          h('input', { type: 'radio', name: `r-${item.id}`, checked: picked, onChange: () => setChoice(value) }),
          h('span', { class: 'key', 'aria-hidden': 'true' }, String.fromCharCode(65 + i)), text,
          locked && picked && correct ? h('span', { class: 'visually-hidden' }, ' ' + t('leccion.correctMark')) : null);
      })),
    locked ? null : h('button', { class: 'btn', type: 'submit', disabled: choice === null }, t('leccion.check')));
}

function FeedbackSheet({ feedback, onNext }: { feedback: Feedback; onNext: () => void }) {
  const s = feedback.source;
  return h('section', { class: `feedback ${feedback.correct ? 'correct' : 'wrong'}`, role: 'status' },
    h('h2', null, h(Icon, { name: feedback.correct ? 'check' : 'pendiente' }), t(feedback.correct ? 'feedback.correct' : 'feedback.wrong')),
    feedback.explain ? h('p', null, feedback.explain) : null,
    h('p', { class: 'source' },
      s ? [t('feedback.sourceLabel'), ' ', h('a', { href: s.url, target: '_blank', rel: 'noopener' },
        s.kind === 'probate_code' ? t('feedback.probateCode', { cite: s.cite }) : t('feedback.courts')), ' · '] : null,
      t('feedback.disclaimer')),
    h('div', { class: 'feedback-actions' },
      feedback.petals ? h('p', { class: 'gain' }, h(Icon, { name: 'petalo' }), t('feedback.petals', { n: feedback.petals })) : null,
      h('button', { class: 'btn', type: 'button', autofocus: true, onClick: onNext }, t('leccion.continue'))));
}
