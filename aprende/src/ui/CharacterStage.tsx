import { h } from 'preact';
import { useEffect, useRef, useState } from 'preact/hooks';
import type { CharacterEngine } from '../core/character/engine';
import type { CharacterState, Costume } from '../core/character/states';
import { t } from '../core/i18n';
import type { I18nKey } from '../core/i18n-keys';
import './character-stage.css';

export interface CharacterStageProps {
  character: 'calavera' | 'pinata' | 'oso';
  state?: CharacterState;
  costume?: Costume | null;
  onEngine?: (engine: CharacterEngine) => void;
}

const BASE = import.meta.env.BASE_URL;

/** A character on its night backdrop (the GLB carries the backdrop). Without WebGL: the still image on the JPEG backdrop.
 *  The label "AI program, not the attorney" is always on the stage. */
export function CharacterStage({ character, state = 'idle', costume = null, onEngine }: CharacterStageProps) {
  const [fallback, setFallback] = useState(false);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const engineRef = useRef<CharacterEngine | null>(null);

  useEffect(() => {
    let cancelled = false;
    let idleId: number | null = null;
    let io: IntersectionObserver | null = null;
    let onVis: (() => void) | null = null;
    let onInput: (() => void) | null = null;
    let resumeId = 0;
    const run = async () => {
      const { CharacterEngine } = await import('../core/character/engine');
      if (cancelled || !canvasRef.current) return;
      const eng = new CharacterEngine(character);
      engineRef.current = eng;
      const ok = await eng.mount(canvasRef.current).catch(() => false);
      if (cancelled) return;
      if (!ok) setFallback(true);
      else {
        eng.setState(state); eng.setCostume(costume); onEngine?.(eng);
        const canvas = canvasRef.current;
        if (canvas) {
          io = new IntersectionObserver((entries) => {
            if (entries[0]?.isIntersecting) eng.resumeRendering?.(); else eng.pauseRendering?.();
          }, { threshold: 0 });
          io.observe(canvas);
          onVis = () => { if (document.hidden) eng.pauseRendering?.(); else eng.resumeRendering?.(); };
          document.addEventListener('visibilitychange', onVis);
          // a tap gets the main thread: the character holds still for a moment while the answer is checked (INP)
          onInput = () => {
            eng.pauseRendering();
            window.clearTimeout(resumeId);
            resumeId = window.setTimeout(() => { if (!document.hidden) eng.resumeRendering(); }, 300);
          };
          document.addEventListener('pointerdown', onInput, { capture: true });
          document.addEventListener('keydown', onInput, { capture: true });
        }
      }
    };
    // after the first paint, when the main thread is free (at most 1.5 s later): the lesson's text is usable first
    const idle = typeof requestIdleCallback === 'function';
    const rafId = requestAnimationFrame(() => {
      idleId = idle ? requestIdleCallback(() => void run(), { timeout: 1500 }) : window.setTimeout(() => void run(), 0);
    });
    return () => {
      cancelled = true;
      cancelAnimationFrame(rafId);
      if (idleId !== null) { if (idle) cancelIdleCallback(idleId); else window.clearTimeout(idleId); }
      if (io) io.disconnect();
      if (onVis) document.removeEventListener('visibilitychange', onVis);
      if (onInput) { document.removeEventListener('pointerdown', onInput, { capture: true }); document.removeEventListener('keydown', onInput, { capture: true }); }
      window.clearTimeout(resumeId);
      engineRef.current?.unmount(); engineRef.current = null;
    };
  }, [character]);

  useEffect(() => { engineRef.current?.setState(state); }, [state]);
  useEffect(() => { engineRef.current?.setCostume(costume); }, [costume]);

  const name = t(`character.${character}.name` as I18nKey);
  return h('figure', { class: 'character-stage', 'aria-label': t('character.stageLabel', { name }) },
    fallback
      ? h('div', { class: 'character-still', style: { backgroundImage: `url(${BASE}characters/${character}-bg.jpg)` } },
          h('img', { src: `${BASE}characters/${character}.png`, alt: '', width: 240, height: 240, loading: 'lazy' }))
      : h('canvas', { ref: canvasRef, class: 'character-canvas' }),
    h('figcaption', { class: 'character-label' }, t('character.aiLabel')),
  );
}
