import { defineConfig } from '@playwright/test';

const executablePath = process.env.PW_CHROMIUM;

export default defineConfig({
  timeout: 60000,
  projects: [
    {
      // the web app against a real backend (T2-11): Vite proxies the API, so the browser stays same-origin
      name: 'web',
      testDir: './e2e',
      use: { baseURL: 'http://127.0.0.1:5173', browserName: 'chromium', launchOptions: executablePath ? { executablePath } : undefined },
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
      url: 'http://127.0.0.1:8011/health',
      env: { PYTHON: process.env.PYTHON || 'python' },
      reuseExistingServer: !process.env.CI,
      timeout: 120000,
    },
    {
      command: 'npm run dev',
      url: 'http://127.0.0.1:5173',
      reuseExistingServer: !process.env.CI,
      timeout: 120000,
    },
  ],
});
