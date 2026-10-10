import { test, expect } from '@playwright/test';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';

test('production build works under a static subdirectory without any external services', async ({
  page,
}) => {
  const root = path.resolve('dist');
  const mime: Record<string, string> = {
    '.js': 'text/javascript',
    '.css': 'text/css',
    '.html': 'text/html',
    '.json': 'application/json',
    '.svg': 'image/svg+xml',
    '.png': 'image/png',
  };
  const server = http.createServer((req, res) => {
    const pathname = new URL(req.url || '/', 'http://localhost').pathname;
    if (!pathname.startsWith('/explorer/')) {
      res.writeHead(404).end();
      return;
    }
    const file = path.resolve(root, pathname.slice('/explorer/'.length) || 'index.html');
    if (!file.startsWith(root + path.sep) || !fs.existsSync(file) || !fs.statSync(file).isFile()) {
      res.writeHead(404).end();
      return;
    }
    res.setHeader('Content-Type', mime[path.extname(file)] || 'application/octet-stream');
    fs.createReadStream(file).pipe(res);
  });
  await new Promise<void>((resolve) => server.listen(0, '127.0.0.1', resolve));
  const address = server.address() as { port: number };
  const origin = `http://127.0.0.1:${address.port}`;
  const failed: string[] = [];
  page.on('response', (r) => {
    if (r.status() >= 400) failed.push(r.url());
  });
  page.on('request', (r) => {
    if (!r.url().startsWith(origin)) failed.push(r.url());
  });
  try {
    await page.goto(`${origin}/explorer/#/case/beam-static-with-report`);
    await expect(page.locator('.scene-canvas canvas')).toBeVisible();
    await expect(page.locator('.numeric-meta')).toContainText('OpenSeesPy');
    await page.locator('.scene-canvas canvas').click({ position: { x: 350, y: 180 } });
    await page.getByRole('link', { name: '返回案例库' }).click();
    await expect(page.locator('.case-card')).toHaveCount(12);
    expect(failed).toEqual([]);
  } finally {
    await new Promise<void>((resolve, reject) => server.close((e) => (e ? reject(e) : resolve())));
  }
});

test('WebGL fallback still exposes the reference and its numerical answer', async ({ page }) => {
  await page.addInitScript(() => {
    const original = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function (type: string, ...args: unknown[]) {
      if (type.startsWith('webgl')) return null;
      return original.apply(this, [type, ...args] as Parameters<typeof original>);
    } as typeof original;
  });
  await page.goto('/#/case/beam-static-with-report');
  await expect(page.locator('.fallback svg')).toBeVisible();
  await expect(page.locator('.fallback')).toContainText('静态参考结构');
  await expect(page.locator('.numeric-meta')).toContainText('OpenSeesPy');
  await expect(page.getByRole('button', { name: '导出图片' })).toBeDisabled();
});
