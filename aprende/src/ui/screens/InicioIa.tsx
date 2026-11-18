import { h } from 'preact';
import { useEffect, useRef, useState } from 'preact/hooks';
import { navigate } from '../../core/router';
import { t, lang } from '../../core/i18n';
import { apiFetch } from '../../core/api';
import { CharacterStage } from '../CharacterStage';
import type { CharacterEngine } from '../../core/character/engine';

export function InicioIa() {
  const engine = useRef<CharacterEngine | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const txt = t('gate.disclosure.calavera');
    engine.current?.speak(txt, lang.value);
  }, []);

  async function onOk() {
    setBusy(true);
    try {
      await apiFetch('/journey/events', { method: 'POST', json: { type: 'ai_disclosed', payload: {} } });
      navigate('/inicio/consentimiento');
    } finally {
      setBusy(false);
    }
  }

  return h('section', { class: 'screen gate' },
    h('h1', null, t('gate.disclosure.title')),
    h(CharacterStage, { character: 'calavera', onEngine: (e: CharacterEngine) => {
      engine.current = e;
      e.speak(t('gate.disclosure.calavera'), lang.value);
    } }),
    h('p', { class: 'speech' }, t('gate.disclosure.calavera')),
    h('button', { class: 'btn', onClick: onOk, disabled: busy }, t('gate.disclosure.ok')),
  );
}
