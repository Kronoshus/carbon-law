import { defineConfig } from 'vite';
import preact from '@preact/preset-vite';
import { resolve } from 'node:path';
import { makeManifest } from './src/targets/extension/manifest';
import { mkdirSync, existsSync, writeFileSync, readdirSync, renameSync, rmSync } from 'node:fs';

export default defineConfig(({ mode }) => {
  const isExt = mode === 'extension';
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const plugins: any[] = [preact()];
  if (isExt) {
    plugins.push({
      name: 'copy-manifest',
      closeBundle() {
        const origin = process.env.API_ORIGIN || 'https://carbon-law.onrender.com';
        const manifest = makeManifest(origin);
        const out = resolve(__dirname, 'dist/extension');
        if (!existsSync(out)) mkdirSync(out, { recursive: true });
        const htmlDir = resolve(out, 'src/targets/extension');
        if (existsSync(htmlDir)) {
          for (const f of readdirSync(htmlDir)) {
            if (f.endsWith('.html')) renameSync(resolve(htmlDir, f), resolve(out, f));
          }
          try { rmSync(resolve(out, 'src'), { recursive: true, force: true }); } catch (e) { void e; }
        }
        writeFileSync(resolve(out, 'manifest.json'), JSON.stringify(manifest, null, 2) + '\n');
      }
    });
  }
  const base = process.env.VITE_BASE || '/';
  return {
    base,
    server: {
      host: '127.0.0.1',
      // dev and e2e: the API is same-origin through this proxy (production uses VITE_API_ORIGIN)
      // ('/characters' is also the folder of the character files, so only the API paths are forwarded)
      proxy: Object.fromEntries(['/auth', '/journey', '/health', '/payments', '^/characters(/[a-z_]+)?$', '/learn', '/content', '/progress', '/datos', '/chat', '/booking', '/staff']
        .map((p) => [p, 'http://127.0.0.1:8011'])),
    },
    plugins,
    esbuild: { jsx: 'automatic', jsxImportSource: 'preact' },
    resolve: { alias: { '@': resolve(__dirname, 'src') } },
    build: {
      outDir: isExt ? 'dist/extension' : 'dist/web',
      emptyOutDir: true,
      manifest: true,
      rollupOptions: {
        output: isExt ? { entryFileNames: '[name].js', chunkFileNames: 'assets/[name]-[hash].js', assetFileNames: 'assets/[name]-[hash][extname]' } : undefined,
        input: isExt
          ? {
              sidepanel: resolve(__dirname, 'src/targets/extension/sidepanel.html'),
              popup: resolve(__dirname, 'src/targets/extension/popup.html'),
              background: resolve(__dirname, 'src/targets/extension/background.ts'),
              offscreen: resolve(__dirname, 'src/targets/extension/offscreen.html'),
            }
          : resolve(__dirname, 'index.html'),
      },
    },
    test: {
      environment: 'jsdom',
      include: ['tests/**/*.test.{ts,tsx}'],
    },
  };
});
