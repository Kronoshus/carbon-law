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
    let rafId: number | null = null;
    let io: IntersectionObserver | null = null;
    let onVis: (() => void) | null = null;
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
        }
      }
    };
    const schedule = () => { if (cancelled) return; run(); };
    const tid = window.setTimeout(schedule, 4000);
    (window as unknown as { __csTimer?: number }).__csTimer = tid;
    return () => {
      cancelled = true;
      if (idleId !== null && typeof window !== 'undefined' && 'cancelIdleCallback' in window) (window as unknown as { cancelIdleCallback: (id: number) => void }).cancelIdleCallback(idleId);
      if (rafId !== null) cancelAnimationFrame(rafId);
      if (io) io.disconnect();
      if (onVis) document.removeEventListener('visibilitychange', onVis);
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
