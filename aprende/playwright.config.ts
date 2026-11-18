import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  timeout: 60000,
  use: {
    baseURL: 'http://127.0.0.1:5173',
    browserName: 'chromium',
    launchOptions: process.env.PW_CHROMIUM
      ? { executablePath: process.env.PW_CHROMIUM }
      : undefined,
  },
  webServer: [
    {
      command: '/home/dkkm10/work/cl-wt/T2-11/scripts/start-e2e-backend.sh',
      url: 'http://127.0.0.1:8011/health',
      reuseExistingServer: !process.env.CI,
      timeout: 120000,
    },
    {
      command: 'npm run dev',
      url: 'http://127.0.0.1:5173',
      env: { VITE_API_ORIGIN: 'http://127.0.0.1:8011' },
      reuseExistingServer: !process.env.CI,
      timeout: 120000,
    },
  ],
});
