import { h } from 'preact';
import { useEffect, useState } from 'preact/hooks';
import { t } from '../../core/i18n';
import { apiFetch } from '../../core/api';
import './preguntas.css';

type Question = { id: string; question: string; created_at: string; answer: string | null; answered_at: string | null };

export function Preguntas() {
  const [questions, setQuestions] = useState<Question[] | null>(null);
  useEffect(() => {
    (async () => {
      const r = await apiFetch('/journey/questions');
      if (r.ok) setQuestions((await r.json()).questions ?? []);
      else setQuestions([]);
    })();
  }, []);
  return h('section', { class: 'screen preguntas' },
    h('h1', null, t('preguntas.title')),
    questions === null
      ? null
      : questions.length === 0
        ? [h('p', { key: 'n' }, t('preguntas.none')), h('a', { key: 'a', class: 'btn', href: '#/aprender' }, t('empty.today'))]
        : h('ul', { class: 'preguntas-list' }, questions.map((q) =>
            h('li', { key: q.id, class: 'card' },
              h('p', { class: 'pregunta' }, q.question),
              q.answer !== null
                ? h('p', null, h('strong', null, t('preguntas.answer')), ' ', q.answer)
                : h('p', { class: 'espera' }, t('preguntas.waiting'))))),
  );
}
