import { defineConfig } from '@playwright/test';

const executablePath = process.env.PW_CHROMIUM;
// Several worktrees test at once on one machine: each run may pick its own ports (E2E_WEB_PORT, E2E_API_PORT).
const web = process.env.E2E_WEB_PORT || '5173';
const api = process.env.E2E_API_PORT || '8011';

export default defineConfig({
  // Each page renders the 3D character in software; more than a few at once starves a desktop CPU (local runs only).
  workers: process.env.CI ? undefined : 4,
  timeout: 60000,
  projects: [
    {
      // the web app against a real backend (T2-11): Vite proxies the API, so the browser stays same-origin
      name: 'web',
      testDir: './e2e',
      use: { baseURL: `http://127.0.0.1:${web}`, browserName: 'chromium', launchOptions: executablePath ? { executablePath } : undefined },
    },
    {
      // the built extension (T2-12); these tests launch their own persistent context with the unpacked extension
      name: 'extension',
      testDir: './tests/e2e',
    },
  ],
  webServer: [
    {
      command: 'bash ../scripts/start-e2e-backend.sh',
      url: `http://127.0.0.1:${api}/health`,
      env: { PYTHON: process.env.PYTHON || 'python', PORT: api },
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
  ],
});
