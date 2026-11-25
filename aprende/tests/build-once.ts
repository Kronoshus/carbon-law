import { execSync } from 'node:child_process';

// Vitest globalSetup: build the web app and the packed extension once, before any test file runs. The test files that
// read dist/ (bundle, perf-budget, extension-store) run in parallel; when each built for itself, two `vite build`s
// emptied and wrote the same dist/web at once and one failed with ENOTEMPTY.
export default function setup() {
  execSync('npm run build:web', { stdio: 'pipe' });
  execSync('npm run pack:ext', { stdio: 'pipe', env: { ...process.env, API_ORIGIN: '' } });
}
