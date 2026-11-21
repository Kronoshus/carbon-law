import { defineConfig } from '@playwright/test';

const executablePath = process.env.PW_CHROMIUM;
// Several worktrees test at once on one machine: each run may pick its own ports (E2E_WEB_PORT, E2E_API_PORT).
const web = process.env.E2E_WEB_PORT || '5173';
const api = process.env.E2E_API_PORT || '8011';
const adminPort = process.env.E2E_ADMIN_PORT || '5174';
const fakePort = process.env.E2E_FAKE_PORT || '8291';
// The release tests (T8-06) move the backend's one clock forward: they run after every other test, one at a time.
const RELEASE = /release[^/]*\.spec\.ts$/;

export default defineConfig({
  // Each page renders the 3D character in software; more than a few at once starves a desktop CPU (local runs only).
  workers: process.env.CI ? undefined : 4,
  timeout: 60000,
  projects: [
    {
      // the web app against a real backend (T2-11): Vite proxies the API, so the browser stays same-origin
      name: 'web',
      testDir: './e2e',
      testIgnore: RELEASE,
      use: { baseURL: `http://127.0.0.1:${web}`, browserName: 'chromium', launchOptions: executablePath ? { executablePath } : undefined },
    },
    {
      // the built extension (T2-12); these tests launch their own persistent context with the unpacked extension
      name: 'extension',
      testDir: './tests/e2e',
      testIgnore: RELEASE,
    },
    {
      // the release criteria end to end, on a fake clock (brief s.5): the phone journey, then the same in the side panel
      name: 'release',
      testDir: '.',
      testMatch: RELEASE,
      dependencies: ['web', 'extension'],
      workers: 1,
      timeout: 45 * 60_000,                                             // five lessons and two weeks of steps, one browser
      // without WebGL the characters are their still images (the app's own fallback): the journey, not the 3D, is tested here
      use: { trace: 'retain-on-failure', screenshot: 'only-on-failure', baseURL: `http://127.0.0.1:${web}`, browserName: 'chromium',
        launchOptions: { args: ['--disable-webgl'], ...(executablePath ? { executablePath } : {}) } },
    },
  ],
  webServer: [
    {
      // the fake model and the fake Stripe (scripts/e2e-fakes.py): tests never reach a real model or Stripe
      command: `${process.env.PYTHON || 'python'} ../scripts/e2e-fakes.py`,
      env: { E2E_FAKE_PORT: fakePort, E2E_API_PORT: api, STRIPE_WEBHOOK_SECRET: 'whsec_e2e' },
      url: `http://127.0.0.1:${fakePort}/health`,
      reuseExistingServer: !process.env.CI,
      timeout: 30000,
    },
    {
      command: 'bash ../scripts/start-e2e-backend.sh',
      url: `http://127.0.0.1:${api}/health`,
      env: { PYTHON: process.env.PYTHON || 'python', PORT: api, E2E_FAKE_PORT: fakePort, E2E_WEB_PORT: web },
      reuseExistingServer: !process.env.CI,
      timeout: 120000,
    },
    {
      command: `npm run dev -- --port ${web} --strictPort`,
      env: { E2E_API_PORT: api },
      url: `http://127.0.0.1:${web}`,
      reuseExistingServer: !process.env.CI,
      timeout: 120000,
    },
    {
      command: `python3 -m http.server ${adminPort} -d ../web --bind 127.0.0.1`,
      url: `http://127.0.0.1:${adminPort}`,
      reuseExistingServer: !process.env.CI,
      timeout: 30000,
    },
  ],
});
