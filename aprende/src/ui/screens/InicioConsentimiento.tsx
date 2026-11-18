import { h } from 'preact';
import { useState } from 'preact/hooks';
import { navigate } from '../../core/router';
import { t } from '../../core/i18n';
import { apiFetch } from '../../core/api';
import { classifyConsent } from '../../core/consent';

export function InicioConsentimiento() {
  const [text, setText] = useState('');
  const [unclearCount, setUnclearCount] = useState(0);
  const [showAgain, setShowAgain] = useState(false);
  const [busy, setBusy] = useState(false);

  async function postConsent(answer: 'yes' | 'no') {
    setBusy(true);
    try {
      await apiFetch('/journey/events', { method: 'POST', json: { type: 'consent', payload: { answer } } });
      if (answer === 'yes') navigate('/inicio/nombres');
      else navigate('/inicio/no-acepto');
    } finally {
      setBusy(false);
    }
  }

  async function onSubmit(e: Event) {
    e.preventDefault();
    const res = classifyConsent(text);
    if (res === 'yes') { await postConsent('yes'); return; }
    if (res === 'no') { await postConsent('no'); return; }
    // unclear
    if (unclearCount === 0) {
      setUnclearCount(1);
      setShowAgain(true);
    } else {
      await postConsent('no');
    }
  }

  async function onYes() { await postConsent('yes'); }
  async function onNo() { await postConsent('no'); }

  return h('section', { class: 'screen gate' },
    h('h1', null, t('gate.consent.title')),
    h('p', null, t('gate.consent.body')),
    h('form', { onSubmit },
      h('label', { class: 'field' },
        t('gate.consent.label'),
        h('input', { 'aria-label': t('gate.consent.label'), value: text, onInput: (e: Event) => setText((e.target as HTMLInputElement).value) }),
      ),
      h('button', { class: 'btn', type: 'submit', disabled: busy }, t('gate.consent.send')),
    ),
    h('div', { class: 'row' },
      h('button', { class: 'btn', onClick: onYes, disabled: busy }, t('gate.consent.yes')),
      h('button', { class: 'btn', onClick: onNo, disabled: busy }, t('gate.consent.no')),
    ),
    showAgain ? h('p', { class: 'again' }, t('gate.consent.again')) : null,
  );
}
