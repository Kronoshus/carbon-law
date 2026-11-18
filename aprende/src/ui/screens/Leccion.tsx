import { h } from 'preact';
import { useEffect, useRef, useState } from 'preact/hooks';
import { t } from '../../core/i18n';
import type { I18nKey } from '../../core/i18n-keys';
import { apiFetch } from '../../core/api';
import { platform } from '../../platform';
import { navigate } from '../../core/router';
import { CharacterStage } from '../CharacterStage';
import type { CharacterState } from '../../core/character/states';

interface Item {
  id: string;
  kind: string;
  character?: string;
  sensitive?: boolean;
  text?: string;
  statement?: string;
  prompt?: string;
  story?: string;
  options?: string[];
  left?: { key: string; text: string }[];
  right?: { key: string; text: string }[];
  steps?: { key: string; text: string }[];
  explain?: string;
}

interface Step { id: string; title: string; items: Item[]; }

interface Lesson { id: string; title: string; character: string; sensitive: boolean; steps: Step[]; }

interface Feedback { correct: boolean; explain: string | null; source: { kind: string; cite: string; url: string } | null; }

export function Leccion({ id }: { id: string }) {
  const [lesson, setLesson] = useState<Lesson | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [stepIndex, setStepIndex] = useState(0);
  const [queue, setQueue] = useState<Item[]>([]);
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  const [doneCount, setDoneCount] = useState(0);
  const [total, setTotal] = useState(0);
  const [completed, setCompleted] = useState(false);
  const [score, setScore] = useState<number | null>(null);
  const [wrongItems, setWrongItems] = useState<Item[]>([]);
  const [repasarMode, setRepasarMode] = useState(false);
  const engineRef = useRef<{ speak: (t: string, l: 'es' | 'en') => Promise<void> } | null>(null);
  const langVal = (document.documentElement.lang === 'en' ? 'en' : 'es') as 'es' | 'en';

  const reducedMotion = typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await apiFetch(`/learn/lessons/${encodeURIComponent(id)}?lang=${langVal}`);
        if (!res.ok) throw new Error(await res.text());
        const data = await res.json() as Lesson;
        if (cancelled) return;
        setLesson(data);
        const allItems = data.steps.flatMap((s) => s.items);
        setTotal(allItems.length);
        // resume
        const pos = await platform.storage.get(`aprende_lesson_pos_${id}`);
        let si = 0; let startItem: Item | null = null;
        if (pos) {
          try {
            const p = JSON.parse(pos);
            if (typeof p.stepIndex === 'number') si = p.stepIndex;
            if (p.itemId) startItem = allItems.find((it) => it.id === p.itemId) || null;
          } catch { /* ignore */ }
        }
        si = Math.min(si, Math.max(0, data.steps.length - 1));
        setStepIndex(si);
        const stepItems = data.steps[si]?.items || [];
        if (startItem && stepItems.some((it) => it.id === startItem!.id)) {
          // move startItem to front
          const idx = stepItems.findIndex((it) => it.id === startItem!.id);
          const q = [...stepItems];
          if (idx > 0) { const [it] = q.splice(idx, 1); q.unshift(it); }
          setQueue(q);
        } else {
          setQueue([...stepItems]);
        }
      } catch (e) {
        if (!cancelled) setError(String(e));
      }
    })();
    return () => { cancelled = true; };
  }, [id]);

  const item = queue[0] || null;
  const calm = !!(lesson?.sensitive || (lesson?.steps.flatMap((s) => s.items).some((it) => it.sensitive)));
  const charName = (item?.character || lesson?.character || 'calavera') as 'calavera' | 'pinata' | 'oso';
  const charState: CharacterState = (completed
    ? (reducedMotion ? 'idle' : (calm ? 'comforting' : 'celebrating'))
    : (item?.kind === 'explain' ? 'talking' : 'idle')) as CharacterState;

  useEffect(() => {
    if (!item || !engineRef.current) return;
    const text = item.text || item.statement || item.prompt || '';
    if (text && item.kind === 'explain') {
      void engineRef.current.speak(text, langVal);
    }
  }, [item?.id]);

  async function savePos() {
    if (!lesson || !item) return;
    await platform.storage.set(`aprende_lesson_pos_${id}`, JSON.stringify({ stepIndex, itemId: item.id }));
  }

  useEffect(() => { void savePos(); }, [stepIndex, item?.id]);

  async function submitAnswer(answer: unknown) {
    if (!item) return;
    const res = await apiFetch('/learn/attempts', { method: 'POST', json: { item_id: item.id, answer, lang: langVal } });
    if (!res.ok) { setError(await res.text()); return; }
    const data = await res.json() as Feedback;
    setFeedback(data);
    if (data.correct) {
      setDoneCount((c) => c + 1);
    } else {
      setWrongItems((prev) => (prev.some((x) => x.id === item.id) ? prev : [...prev, item]));
    }
  }

  function advanceAfterFeedback() {
    if (!item || !feedback) return;
    if (feedback.correct) {
      setQueue((q) => q.slice(1));
    } else {
      setQueue((q) => {
        const [first, ...rest] = q;
        return [...rest, first];
      });
    }
    setFeedback(null);
    setSelected(null);
  }

  function advanceExplain() {
    if (!item) return;
    setDoneCount((c) => c + 1);
    setQueue((q) => q.slice(1));
  }

  function skipItem() {
    if (!item) return;
    setDoneCount((c) => c + 1);
    setQueue((q) => q.slice(1));
  }

  // move to next step when queue empty
  useEffect(() => {
    if (!lesson) return;
    if (queue.length === 0 && stepIndex < lesson.steps.length - 1) {
      const next = stepIndex + 1;
      setStepIndex(next);
      setQueue([...(lesson.steps[next]?.items || [])]);
    } else if (queue.length === 0 && stepIndex === lesson.steps.length - 1 && total > 0 && doneCount >= total && !completed && !repasarMode) {
      // complete
      void finishLesson();
    }
  }, [queue.length, stepIndex, lesson]);

  async function finishLesson() {
    const res = await apiFetch(`/learn/lessons/${encodeURIComponent(id)}/complete`, { method: 'POST' });
    if (!res.ok) { setError(await res.text()); return; }
    const data = await res.json() as { completed: boolean; score: number };
    setCompleted(true);
    setScore(data.score);
  }

  function restartWrong() {
    if (wrongItems.length === 0) {
      // restart whole
      if (!lesson) return;
      setStepIndex(0);
      setQueue([...lesson.steps[0].items]);
      setDoneCount(0);
      setCompleted(false);
      setScore(null);
      setWrongItems([]);
      return;
    }
    const synthetic: Step = { id: 'repaso', title: '', items: [...wrongItems] };
    const newLesson = lesson ? { ...lesson, steps: [synthetic] } : null;
    if (newLesson) setLesson(newLesson);
    setStepIndex(0);
    setQueue([...wrongItems]);
    setDoneCount(0);
    setCompleted(false);
    setScore(null);
    setWrongItems([]);
    setRepasarMode(true);
  }

  if (error) return h('div', null, error);
  if (!lesson || !item && !completed) return h('div', null, '…');

  // progress value
  const progressValue = Math.min(doneCount, total || 1);

  if (completed) {
    return h('div', { class: 'lesson-player' },
      h('header', { class: 'lessonbar' },
        h('button', { class: 'icon-btn', 'aria-label': t('leccion.exit' as I18nKey), onClick: () => navigate('/aprender') }, '×'),
        h('progress', { class: 'lesson', max: total || 1, value: total }),
      ),
      h('section', { class: 'celebration' },
        h('h1', null, calm ? t('celebration.calm' as I18nKey) : t('celebration.title' as I18nKey)),
        score !== null && !calm ? h('p', null, t('result.score' as I18nKey, { score: Math.round((score || 0) * 100) })) : null,
        (!completed || (score !== null && score < 0.8))
          ? h('button', { class: 'btn', onClick: restartWrong }, t('result.repasar' as I18nKey))
          : h('button', { class: 'btn', onClick: () => navigate('/aprender') }, t('celebration.return' as I18nKey)),
      ),
    );
  }

  const kind = item.kind;
  const isUnsupported = ['match', 'order', 'listen'].includes(kind);

  return h('div', { class: 'lesson-player' },
    h('header', { class: 'lessonbar' },
      h('button', { class: 'icon-btn', 'aria-label': t('leccion.exit' as I18nKey), onClick: () => navigate('/aprender') },
        h('svg', { 'aria-hidden': 'true', width: 24, height: 24 }, h('use', { href: '#i-cerrar' })),
      ),
      h('label', { class: 'visually-hidden', for: 'avance' }, t('leccion.progress' as I18nKey)),
      h('progress', { id: 'avance', class: 'lesson', max: total || 1, value: progressValue }),
      h('span', { class: 'chip' }, h('svg', { 'aria-hidden': 'true', style: { inlineSize: '1.2rem', blockSize: '1.2rem' } }, h('use', { href: '#i-vela' })), ' 1'),
    ),
    h(CharacterStage, { character: charName, state: charState, onEngine: (e) => { engineRef.current = e as never; } }),
    h('div', { class: 'talk' },
      h('p', { class: 'bubble', 'aria-live': 'polite' },
        item.text || item.statement || item.prompt || '',
        h('button', { class: 'icon-btn listen', type: 'button', 'aria-label': t('leccion.replay' as I18nKey), onClick: () => {
          const txt = item.text || item.statement || item.prompt || '';
          void engineRef.current?.speak(txt, langVal);
        } }, h('svg', { 'aria-hidden': 'true', width: 24, height: 24 }, h('use', { href: '#i-volumen' }))),
      ),
    ),
    isUnsupported
      ? h('section', { class: 'q' },
          h('span', { class: 'kind' }, t('leccion.comingSoon' as I18nKey)),
          h('button', { class: 'btn', onClick: skipItem }, t('leccion.skip' as I18nKey)),
        )
      : (kind === 'explain'
        ? h('section', { class: 'q' },
            h('button', { class: 'btn', onClick: advanceExplain }, t('leccion.continue' as I18nKey)),
          )
        : h('form', { class: 'q', onSubmit: (e: Event) => { e.preventDefault(); } },
            h('span', { class: 'kind' }, t(`leccion.kind.${kind === 'scenario' ? 'scenario' : kind === 'truefalse' ? 'truefalse' : 'choice'}` as I18nKey)),
            kind === 'scenario' ? h('p', { class: 'story' }, item.story) : null,
            h('h1', { id: 'pregunta' }, item.prompt || item.statement || ''),
            kind === 'truefalse'
              ? h('fieldset', null,
                  h('label', { class: 'option' }, h('input', { type: 'radio', name: 'r', onChange: () => setSelected(0) }), 'Verdadero'),
                  h('label', { class: 'option' }, h('input', { type: 'radio', name: 'r', onChange: () => setSelected(1) }), 'Falso'),
                )
              : h('fieldset', null,
                  (item.options || []).map((opt, i) =>
                    h('label', { class: 'option', key: i },
                      h('input', { type: 'radio', name: 'r', onChange: () => setSelected(i) }),
                      h('span', { class: 'key' }, String.fromCharCode(65 + i)),
                      ' ', opt,
                      selected === i && feedback?.correct ? h('span', { class: 'visually-hidden' }, '(correcta)') : null,
                    ),
                  ),
                ),
            h('button', { class: 'btn', type: 'button', disabled: selected === null && kind !== 'truefalse' ? true : false,
              onClick: () => {
                if (kind === 'truefalse') {
                  const ans = selected === 0 ? true : false;
                  void submitAnswer(ans);
                } else if (selected !== null) {
                  void submitAnswer(selected);
                }
              } }, t('leccion.continue' as I18nKey)),
          )),
    feedback ? h('section', { class: `feedback ${feedback.correct ? 'correct' : 'wrong'}`, role: 'status' },
      h('h2', null, feedback.correct ? t('feedback.correct' as I18nKey) : t('feedback.wrong' as I18nKey)),
      feedback.explain ? h('p', null, feedback.explain) : null,
      feedback.source ? h('p', { class: 'source' },
        t('feedback.source' as I18nKey) + ': ',
        h('a', { href: feedback.source.url || '#', target: '_blank', rel: 'noopener' }, feedback.source.cite),
        ' · ' + t('feedback.disclaimer' as I18nKey),
      ) : h('p', { class: 'source' }, t('feedback.disclaimer' as I18nKey)),
      h('div', { style: { display: 'flex', gap: 'var(--s3)', alignItems: 'center' } },
        feedback.correct ? h('p', { class: 'gain' }, t('feedback.petals' as I18nKey)) : null,
        h('button', { class: 'btn', onClick: advanceAfterFeedback }, t('leccion.continue' as I18nKey)),
      ),
    ) : null,
  );
}
