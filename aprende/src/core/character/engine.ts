/* eslint-disable @typescript-eslint/no-explicit-any */
import { vis, viseme, type ServerAudio } from './visemes';
import { type CharacterState, STATE_OPTIONAL_KEY } from './states';

export const SHAPE_KEYS = ['jawOpen', 'blink', 'mouthRound', 'browUp', 'headYaw', 'headPitch', 'headRoll', 'lookX'] as const;

export interface Pose { jaw: number; blink: number; round: number; brow: number; yaw: number; pitch: number; roll: number; look: number; }

const JAW_SMOOTH = 0.45;

export function reducedMotion(): boolean {
  if (typeof window === 'undefined' || !window.matchMedia) return false;
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

export class CharacterEngine {
  characterId: string;
  state: CharacterState = 'idle';
  // morph state
  mouth = 0;
  round = 0;
  jaw = 0;
  blink = 0;
  brow = 0;
  nod = 0;
  look = 0;
  lookTo = 0;
  nextBlink = 0;
  nextLook = 0;
  rnd = 0;

  // three.js (loaded dynamically)
  THREE: any = null;
  scene: any = null;
  camera: any = null;
  renderer: any = null;
  face: any = null;
  body: any = null;
  canvas: HTMLCanvasElement | null = null;
  fallback = false;
  mounted = false;
  rafId = 0;
  reduced = false;

  constructor(characterId: string) {
    this.characterId = characterId;
    this.reduced = reducedMotion();
  }

  glbUrl(): string {
    return `/characters/${this.characterId}.glb`;
  }
  pngUrl(): string {
    return `/characters/${this.characterId}.png`;
  }
  bgUrl(): string {
    return `/characters/${this.characterId}-bg.png`;
  }

  async mount(canvas: HTMLCanvasElement): Promise<boolean> {
    this.canvas = canvas;
    if (this.reduced === false && typeof WebGLRenderingContext === 'undefined') {
      this.fallback = true;
      return false;
    }
    try {
      const THREE = await import('three');
      this.THREE = THREE;
      // GLTFLoader
      const mod = await import('three/examples/jsm/loaders/GLTFLoader.js');
      const GLTFLoader = mod.GLTFLoader;
      this.renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
      const s = Math.min(canvas.clientWidth || 256, canvas.clientHeight || 256);
      this.renderer.setSize(s, s, false);
      this.scene = new THREE.Scene();
      this.camera = new THREE.PerspectiveCamera(35, 1, 0.1, 100);
      this.camera.position.z = 3;
      const loader = new GLTFLoader();
      const gltf: any = await new Promise((res, rej) => {
        loader.load(this.glbUrl(), res, undefined, rej);
      });
      const root = gltf.scene;
      this.scene.add(root);
      // find face mesh with morph targets
      root.traverse((o: any) => {
        if (o.isMesh && o.morphTargetDictionary) {
          this.face = o;
        }
        if (o.name && /body|torso|shoulder/i.test(o.name)) this.body = o;
      });
      if (!this.body) this.body = root;
      this.mounted = true;
      this.startLoop();
      return true;
    } catch {
      this.fallback = true;
      return false;
    }
  }

  unmount(): void {
    if (this.rafId) cancelAnimationFrame(this.rafId);
    this.rafId = 0;
    this.mounted = false;
  }

  startLoop(): void {
    const loop = (t: number) => {
      this.frame(t);
      if (this.mounted) this.rafId = requestAnimationFrame(loop);
    };
    this.rafId = requestAnimationFrame(loop);
  }

  setState(s: CharacterState): void {
    this.state = s;
  }

  // frame() port
  frame(t: number): void {
    if (!this.face) return;
    const canvas = this.canvas;
    if (canvas) {
      const s = Math.min(canvas.clientWidth || 256, canvas.clientHeight || 256);
      if (this.renderer && this.renderer.domElement.width !== s) this.renderer.setSize(s, s, false);
    }
    this.jaw += (this.mouth - this.jaw) * JAW_SMOOTH;
    if (t > this.nextBlink + 220) this.nextBlink = t + 2200 + Math.random() * 3800;
    const d = t - this.nextBlink;
    const blink = d < 0 ? 0 : d < 80 ? d / 80 : Math.max(0, 1 - (d - 80) / 140);
    this.rnd += (this.round - this.rnd) * 0.35;
    const listening = this.state === 'listening';
    const stressed = this.jaw > 0.3;
    this.brow += ((stressed ? 0.7 : listening ? 0.15 : 0) - this.brow) * 0.06;
    this.nod += ((listening ? 1 : 0) - this.nod) * 0.03;
    if (t > this.nextLook) {
      this.lookTo = Math.random() < 0.6 ? 0 : Math.random() * 1.2 - 0.6;
      this.nextLook = t + 900 + Math.random() * 3200;
    }
    this.look += (this.lookTo - this.look) * 0.4;

    // state-driven extras
    const extraBrow = 0;
    const extraYaw = 0;
    const extraPitch = 0;
    const extraLook = 0;
    if (this.state === 'thinking') { extraBrow = 0.4; extraLook = 0.6; }
    if (this.state === 'celebrating') { extraBrow = 0.6; }
    if (this.state === 'comforting') { extraBrow = 0.1; }

    const yaw = (this.reduced ? 0 : (Math.sin(t / 3700) * 0.45 + Math.sin(t / 1300) * 0.15)) + this.look * 0.25 + extraYaw;
    const pitch = (this.reduced ? 0 : Math.sin(t / 2900) * 0.25) - this.jaw * 0.5 - this.nod * Math.max(0, Math.sin(t / 700)) * 0.5 + extraPitch;
    const roll = this.reduced ? 0 : (Math.sin(t / 4300) * 0.35 + Math.sin(t / 1700) * 0.1);

    const poseArr = (window as any).__pose || [this.jaw, blink, this.rnd, this.brow + extraBrow, yaw, pitch, roll, this.look + extraLook];

    const M = this.face.morphTargetDictionary;
    const I = this.face.morphTargetInfluences;
    const keys = [...SHAPE_KEYS];
    keys.forEach((k, i) => {
      if (M && M[k] !== undefined) I[M[k]] = poseArr[i] || 0;
    });
    // optional keys
    const optKey = STATE_OPTIONAL_KEY[this.state];
    if (optKey && M && M[optKey] !== undefined) {
      I[M[optKey]] = 1;
    } else {
      // ensure optional keys zeroed if exist
      for (const k of ['celebrate', 'think', 'wave', 'comfort']) {
        if (M && M[k] !== undefined) I[M[k]] = 0;
      }
      if (optKey && M && M[optKey] !== undefined) I[M[optKey]] = 1;
    }

    if (this.body && !this.reduced) {
      this.body.rotation.z = Math.sin(t / 2300) * 0.006;
      this.body.rotation.y = Math.sin(t / 3100) * 0.02;
      this.body.rotation.x = Math.sin(t / 2700) * 0.005;
      this.body.position.y = -1.3 + Math.sin(t / 1600) * 0.004;
      if (this.state === 'celebrating') {
        this.body.position.y += Math.abs(Math.sin(t / 400)) * 0.05;
      }
    } else if (this.body) {
      // reduced: keep base position only, no sway/bounce
      this.body.position.y = -1.3;
    }

    if (this.renderer && this.scene && this.camera) {
      this.renderer.render(this.scene, this.camera);
    }
  }

  // speak: browser speechSynthesis path (default, no server voice)
  async speak(text: string, lang: 'es' | 'en' = 'es'): Promise<void> {
    if (!text.trim()) return;
    this.setState('talking');
    const synth = (window as any).speechSynthesis;
    if (!synth) {
      this.setState('idle');
      this.mouth = this.round = 0;
      return;
    }
    const locale = lang === 'es' ? 'es-US' : 'en-US';
    const u = new SpeechSynthesisUtterance(text);
    u.lang = locale;
    let at = 0;
    let since = performance.now();
    u.onboundary = (e: any) => { at = e.charIndex; since = performance.now(); };
    const lip = setInterval(() => {
      const [open, r] = vis(text[at + Math.floor((performance.now() - since) / 70)]);
      this.mouth = 0.42 * open;
      this.round = r;
    }, 40);
    await new Promise<void>((res) => {
      u.onend = () => res();
      u.onerror = () => res();
      // store cancel fn
      (this as any)._skip = () => { synth.cancel(); res(); };
      synth.speak(u);
    });
    clearInterval(lip);
    this.mouth = this.round = 0;
    this.setState('idle');
    await new Promise((r) => setTimeout(r, 400));
  }

  // second path: accepts server audio shape (for future voice service)
  async speakAudio(audio: ServerAudio): Promise<void> {
    if (!audio.audio_base64) return;
    this.setState('talking');
    const al = audio.alignment ?? null;
    const a = new Audio(`data:${audio.mime || 'audio/mpeg'};base64,` + audio.audio_base64);
    // analyser needs audio context; best-effort
    let ctx: any = null;
    try { ctx = new (window as any).AudioContext(); } catch { ctx = null; }
    let an: any = null;
    if (ctx) {
      an = ctx.createAnalyser(); an.fftSize = 512;
      try {
        const src = ctx.createMediaElementSource(a);
        src.connect(an); an.connect(ctx.destination);
      } catch { an = null; }
    }
    const rms = (analyser: any) => {
      if (!analyser) return 0;
      const b = new Uint8Array(analyser.fftSize); analyser.getByteTimeDomainData(b);
      return Math.sqrt(b.reduce((s: number, v: number) => s + ((v - 128) / 128) ** 2, 0) / b.length);
    };
    const lip = setInterval(() => {
      const [open, r] = viseme(al, a.currentTime);
      const level = an ? rms(an) : 0;
      this.mouth = Math.min(0.5, level * 3.2) * (0.3 + 0.7 * open);
      this.round = r;
    }, 40);
    await new Promise<void>((res) => {
      a.onended = () => res();
      a.onerror = () => res();
      (this as any)._skip = () => { a.pause(); res(); };
      a.play().catch(() => res());
    });
    clearInterval(lip);
    this.mouth = this.round = 0;
    this.setState('idle');
    await new Promise((r) => setTimeout(r, 400));
  }

  cancel(): void {
    const skip = (this as any)._skip;
    if (typeof skip === 'function') skip();
  }
}

// expose pose hook type
declare global {
  interface Window { __pose?: number[]; }
}
