import { describe, it, expect, vi, beforeEach } from 'vitest';

// The character's 3D library and loader, as small stand-ins: the test controls when the character file arrives.
let arrive: ((gltf: unknown) => void) | null = null;
const disposed = vi.fn();
vi.mock('three', () => {
  class Group { position = { y: 0, set() {} }; add() {} }
  return {
    WebGLRenderer: class {
      capabilities = { getMaxAnisotropy: () => 1 };
      domElement = { width: 0 };
      setClearColor() {} setPixelRatio() {} setSize() {} getPixelRatio() { return 1; }
      async compileAsync() {} initTexture() {} render() {} getContext() { return {}; }
      dispose() { disposed(); }
    },
    Scene: class { add() {} traverse() {} },
    PerspectiveCamera: class { position = { set() {} }; },
    Group,
    MeshBasicMaterial: class {},
    ClampToEdgeWrapping: 0,
    DoubleSide: 2,
  };
});
vi.mock('three/examples/jsm/loaders/GLTFLoader.js', () => ({
  GLTFLoader: class { load(_url: string, res: (g: unknown) => void) { arrive = res; } },
}));

import { CharacterEngine } from '../src/core/character/engine';

const gltf = () => ({ scene: { traverse() {}, getObjectByName: () => null } });

describe('the character on a screen the client leaves while it loads', () => {
  beforeEach(() => {
    vi.stubGlobal('WebGLRenderingContext', class {});
    vi.stubGlobal('WebGL2RenderingContext', class {});
    disposed.mockClear();
    arrive = null;
  });

  it('never starts drawing and frees its graphics memory', async () => {
    const raf = vi.spyOn(window, 'requestAnimationFrame');
    const eng = new CharacterEngine('calavera');
    const mounting = eng.mount(document.createElement('canvas'));
    await vi.waitFor(() => expect(arrive).not.toBeNull());
    eng.unmount();                                      // the client taps away before the file arrives
    arrive!(gltf());
    expect(await mounting).toBe(false);
    expect(eng.mounted).toBe(false);
    expect(raf).not.toHaveBeenCalled();
    expect(disposed).toHaveBeenCalled();
  });

  it('draws as usual when the client stays', async () => {
    const raf = vi.spyOn(window, 'requestAnimationFrame').mockImplementation(() => 1);
    const eng = new CharacterEngine('calavera');
    const mounting = eng.mount(document.createElement('canvas'));
    await vi.waitFor(() => expect(arrive).not.toBeNull());
    arrive!(gltf());
    expect(await mounting).toBe(true);
    expect(raf).toHaveBeenCalled();
    eng.unmount();
  });
});
