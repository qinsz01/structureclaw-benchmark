import { defineConfig } from '@playwright/test';
const port = Number(process.env.BENCH_VIEWER_PORT || 4173);
if (!Number.isInteger(port) || port < 1024 || port > 65535)
  throw new Error('BENCH_VIEWER_PORT must be an integer from 1024 to 65535');
export default defineConfig({
  testDir: './tests/browser',
  timeout: 90000,
  workers: 1,
  use: {
    baseURL: `http://127.0.0.1:${port}`,
    viewport: { width: 1440, height: 1000 },
    launchOptions: { args: ['--enable-unsafe-swiftshader'] },
    screenshot: 'only-on-failure',
  },
  webServer: {
    command: `npm run preview -- --port ${port} --strictPort`,
    url: `http://127.0.0.1:${port}`,
    reuseExistingServer: true,
  },
  reporter: 'list',
});
