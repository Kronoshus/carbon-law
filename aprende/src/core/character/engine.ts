import { vis, viseme, type ServerAudio } from './visemes';

export const SHAPE_KEYS = ['jawOpen', 'blink', 'mouthRound', 'browUp', 'headYaw', 'headPitch', 'headRoll', 'lookX'] as const;

export type Costume = null | 'glasses' | 'pen';

export type CharacterStateFull =
  | 'idle' | 'talking' | 'thinking' | 'listening' | 'celebrating' | 'comforting' | 'waving' | 'dancing';

export const STATES: CharacterStateFull[] = ['idle','talking','thinking','listening','celebrating','comforting','waving','dancing'];

const JAW_SMOOTH = 0.45;

export function reducedMotion(): boolean {
  if (typeof window === 'undefined' || !window.matchMedia) return false;
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

type THREE = typeof import('three');

export class CharacterEngine {
  characterId: string;
  state: CharacterStateFull = 'idle';
  costume: Costume = null;

  mouth = 0; round = 0; jaw = 0; blink = 0; brow = 0; nod = 0; look = 0; lookTo = 0; nextBlink = 0; nextLook = 0; rnd = 0;

  THREE: THREE | null = null;
  scene: THREE.Scene | null = null;
  camera: THREE.PerspectiveCamera | null = null;
  renderer: THREE.WebGLRenderer | null = null;
  face: THREE.Object3D | null = null;
  body: THREE.Group | null = null;
  canvas: HTMLCanvasElement | null = null;
  fallback = false;
  mounted = false;
  rafId = 0;
  reduced = false;

  // overlay key targets
  overlayTargets: Record<string, number> = {};
  overlayCurrent: Record<string, number> = {};

  constructor(characterId: string) {
    this.characterId = characterId;
    this.reduced = reducedMotion();
  }

  glbUrl(): string { return `${import.meta.env.BASE_URL}characters/${this.characterId}.glb`; }
  pngUrl(): string { return `${import.meta.env.BASE_URL}characters/${this.characterId}.png`; }
  bgUrl(): string { return `${import.meta.env.BASE_URL}characters/${this.characterId}-bg.jpg`; }

  async mount(canvas: HTMLCanvasElement): Promise<boolean> {
    this.canvas = canvas;
    if (typeof WebGLRenderingContext === 'undefined') { this.fallback = true; return false; }
    try {
      const THREE = await import('three');
      this.THREE = THREE;
      const mod = await import('three/examples/jsm/loaders/GLTFLoader.js');
      const GLTFLoader = mod.GLTFLoader;
      this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
      this.renderer.setClearColor(0x111111);
      this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));   // crisp on phones, capped for low-end GPUs
      const s = Math.min(canvas.clientWidth || 256, canvas.clientHeight || 256);
      this.renderer.setSize(s, s, false);
      this.scene = new THREE.Scene();
      this.camera = new THREE.PerspectiveCamera(30, 1, 0.1, 50);
      this.camera.position.set(0, 0.12, 3.6);
      const body = new THREE.Group();
      body.position.y = -1.3;
      this.scene.add(body);
      this.body = body;

      const loader = new GLTFLoader();
      const gltf: { scene: THREE.Group } = await new Promise((res, rej) => {
        loader.load(this.glbUrl(), res, undefined, rej);
      });
      const root = gltf.scene;
      const maxAniso = this.renderer.capabilities.getMaxAnisotropy();
      root.traverse((o: THREE.Object3D) => {
        const mesh = o as THREE.Mesh;
        if (!mesh.isMesh) return;
        const map = (mesh.material as THREE.MeshBasicMaterial | undefined)?.map;
        if (map) {
          map.anisotropy = maxAniso;
          if (mesh.name !== 'Background') { map.wrapS = THREE.ClampToEdgeWrapping; map.wrapT = THREE.ClampToEdgeWrapping; }
        }
        mesh.material = new THREE.MeshBasicMaterial({
          map: map || null,
          color: map ? 0xffffff : ((mesh.material as { color?: THREE.Color })?.color ?? 0xffffff),
          side: THREE.DoubleSide,
          transparent: mesh.name === 'Avatar' || mesh.name === 'Shadow',
          alphaTest: mesh.name === 'Avatar' ? 0.02 : 0,
          depthWrite: mesh.name !== 'Shadow',
        });
      });
      const face = root.getObjectByName('Avatar');
      if (face) {
        this.face = face;
        body.add(face);
        (face as THREE.Object3D).position.y = 1.3;
      }
      this.scene.add(root);
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

  setState(s: CharacterStateFull): void { this.state = s; }
  setCostume(c: Costume): void { this.costume = c; }

  private morphDict(): Record<string, number> | null {
    const f = this.face as { morphTargetDictionary?: Record<string, number> } | null;
    return f?.morphTargetDictionary || null;
  }
  private morphInf(): number[] | null {
    const f = this.face as { morphTargetInfluences?: number[] } | null;
    return f?.morphTargetInfluences || null;
  }

  frame(t: number): void {
    if (!this.face) return;
    const canvas = this.canvas;
    if (canvas && this.renderer) {
      const s = Math.min(canvas.clientWidth || 256, canvas.clientHeight || 256);
      if (this.renderer.domElement.width !== Math.round(s * this.renderer.getPixelRatio())) this.renderer.setSize(s, s, false);
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

    // overlay key targets based on state/costume
    const overlay: Record<string, number> = { think: 0, wave: 0, waveSwing: 0, celebrate: 0, glasses: 0, pen: 0, comfort: 0 };
    if (this.state === 'thinking') overlay.think = 1;
    if (this.state === 'celebrating' || this.state === 'dancing') overlay.celebrate = 1;
    if (this.state === 'comforting') overlay.comfort = 1;
    if (this.state === 'waving') { overlay.wave = 1; overlay.waveSwing = (Math.sin(t / (1000 / 1.6)) + 1) / 2; }
    if (this.costume === 'glasses') overlay.glasses = 1;
    if (this.costume === 'pen') overlay.pen = 1;

    // ease overlays
    for (const k of Object.keys(overlay)) {
      const cur = this.overlayCurrent[k] ?? 0;
      const tgt = overlay[k];
      this.overlayCurrent[k] = cur + (tgt - cur) * 0.25;
      this.overlayTargets[k] = this.overlayCurrent[k];
    }

    // base yaw/pitch/roll
    const reduced = this.reduced;
    let yaw = 0, pitch = 0, roll = 0;
    if (!reduced) {
      yaw = Math.sin(t / 3700) * 0.45 + Math.sin(t / 1300) * 0.15 + this.look * 0.25;
      pitch = Math.sin(t / 2900) * 0.25 - this.jaw * 0.5 - this.nod * Math.max(0, Math.sin(t / 700)) * 0.5;
      roll = Math.sin(t / 4300) * 0.35 + Math.sin(t / 1700) * 0.1;
    } else {
      yaw = this.look * 0.25;
      pitch = -this.jaw * 0.5;
      roll = 0;
    }
    if (this.state === 'thinking') { yaw += 0.1; }
    if (this.state === 'dancing' && !reduced) {
      yaw += Math.sin(t / 600) * 0.25;
    }

    const poseArr = (window as { __pose?: number[] }).__pose || [
      this.jaw, blink, this.rnd, this.brow + (this.state === 'thinking' ? 0.4 : 0), yaw, pitch, roll, this.look + (this.state === 'thinking' ? 0.6 : 0),
    ];

    const M = this.morphDict();
    const I = this.morphInf();
    if (M && I) {
      SHAPE_KEYS.forEach((k, i) => {
        if (M[k] !== undefined) I[M[k]] = poseArr[i] || 0;
      });
      // overlays
      for (const k of ['think','wave','waveSwing','celebrate','glasses','pen','comfort']) {
        if (M[k] !== undefined) I[M[k]] = this.overlayTargets[k] ?? 0;
      }
    }

    // body sway/breathe
    if (this.body) {
      if (!reduced) {
        this.body.rotation.z = Math.sin(t / 2300) * 0.006;
        this.body.rotation.y = Math.sin(t / 3100) * 0.02;
        this.body.rotation.x = Math.sin(t / 2700) * 0.005;
        this.body.position.y = -1.3 + Math.sin(t / 1600) * 0.004;
        if (this.state === 'celebrating' || this.state === 'dancing') {
          this.body.position.y += Math.abs(Math.sin(t / 400)) * 0.05;
        }
        if (this.state === 'dancing') {
          this.body.rotation.y += Math.sin(t / 600) * 0.15;
        }
      } else {
        this.body.position.y = -1.3;
        this.body.rotation.z = 0; this.body.rotation.y = 0; this.body.rotation.x = 0;
      }
    }

    if (this.renderer && this.scene && this.camera) {
      this.renderer.render(this.scene, this.camera);
    }
  }

  async speak(text: string, lang: 'es' | 'en' = 'es'): Promise<void> {
    if (!text.trim()) return;
    this.setState('talking');
    const synth = typeof window !== 'undefined' ? window.speechSynthesis : null;
    if (!synth) { this.setState('idle'); this.mouth = this.round = 0; return; }
    const locale = lang === 'es' ? 'es-US' : 'en-US';
    const u = new SpeechSynthesisUtterance(text);
    u.lang = locale;
    let at = 0; let since = performance.now();
    u.onboundary = (e: SpeechSynthesisEvent) => { at = e.charIndex; since = performance.now(); };
    const lip = setInterval(() => {
      const [open, r] = vis(text[at + Math.floor((performance.now() - since) / 70)]);
      this.mouth = 0.42 * open; this.round = r;
    }, 40);
    await new Promise<void>((res) => {
      u.onend = () => res(); u.onerror = () => res();
      (this as { _skip?: () => void })._skip = () => { synth.cancel(); res(); };
      synth.speak(u);
    });
    clearInterval(lip);
    this.mouth = this.round = 0;
    this.setState('idle');
    await new Promise((r) => setTimeout(r, 400));
  }

  async speakAudio(audio: ServerAudio): Promise<void> {
    if (!audio.audio_base64) return;
    this.setState('talking');
    const al = audio.alignment ?? null;
    const a = new Audio(`data:${audio.mime || 'audio/mpeg'};base64,` + audio.audio_base64);
    let an: AnalyserNode | null = null;
    let ctx: AudioContext | null = null;
    try { ctx = new AudioContext(); an = ctx.createAnalyser(); an.fftSize = 512; const src = ctx.createMediaElementSource(a); src.connect(an); an.connect(ctx.destination); } catch { an = null; }
    const rms = (analyser: AnalyserNode | null) => {
      if (!analyser) return 0;
      const b = new Uint8Array(analyser.fftSize); analyser.getByteTimeDomainData(b);
      return Math.sqrt(b.reduce((s, v) => s + ((v - 128) / 128) ** 2, 0) / b.length);
    };
    const lip = setInterval(() => {
      const [open, r] = viseme(al, a.currentTime);
      const level = rms(an);
      this.mouth = Math.min(0.5, level * 3.2) * (0.3 + 0.7 * open);
      this.round = r;
    }, 40);
    await new Promise<void>((res) => {
      a.onended = () => res(); a.onerror = () => res();
      (this as { _skip?: () => void })._skip = () => { a.pause(); res(); };
      a.play().catch(() => res());
    });
    clearInterval(lip);
    this.mouth = this.round = 0;
    this.setState('idle');
    await new Promise((r) => setTimeout(r, 400));
  }

  cancel(): void {
    const skip = (this as { _skip?: () => void })._skip;
    if (typeof skip === 'function') skip();
  }
}

declare global { interface Window { __pose?: number[]; } }
