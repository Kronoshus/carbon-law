import { h } from 'preact';
import { useEffect, useState } from 'preact/hooks';
import { t } from '../../core/i18n';
import { apiFetch } from '../../core/api';
import './datos.css';

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
        ? h('p', null, t('preguntas.none'))
        : h('ul', null, questions.map((q) =>
            h('li', { key: q.id },
              h('p', null, q.question),
              q.answer !== null
                ? h('p', null, h('strong', null, t('preguntas.answer')), ' ', q.answer)
                : h('p', null, t('preguntas.waiting'))))),
  );
}
