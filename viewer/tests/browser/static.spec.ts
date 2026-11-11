import { test, expect } from '@playwright/test';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('research-locale', 'en'));
});

test('production build serves public inputs and reference figures from a static subdirectory', async ({
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
    '.txt': 'text/plain',
    '.dxf': 'application/dxf',
  };
  const server = http.createServer((req, res) => {
    const pathname = decodeURIComponent(new URL(req.url || '/', 'http://localhost').pathname);
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
  page.on('response', (response) => {
    if (response.status() >= 400) failed.push(response.url());
  });
  page.on('request', (request) => {
    if (!request.url().startsWith(origin) && !request.url().startsWith('blob:'))
      failed.push(request.url());
  });
  try {
    await page.goto(`${origin}/explorer/#/case/MM-082?turn=t1`);
    await expect(page.locator('.dxf-svg')).toBeVisible();
    await expect(page.locator('.research-attachment')).toHaveCount(1);
    await expect(page.locator('.research-attachment')).toHaveAttribute('data-name', 'drawing.dxf');
    await page.getByRole('tab', { name: 'Benchmark reference' }).click();
    await expect(page.locator('.scene-canvas canvas')).toBeVisible();
    await expect(page.locator('.reference-source')).toContainText('YJK');
    await expect(page.locator('.research-response-figure svg')).toBeVisible();
    await page.getByRole('link', { name: 'Back to catalogue' }).click();
    await expect(page.locator('.case-card')).toHaveCount(12);
    await expect(page.getByRole('link', { name: 'Download tasks' })).toHaveJSProperty(
      'href',
      `${origin}/explorer/benchmark-inputs.zip`,
    );
    expect(failed).toEqual([]);
  } finally {
    await new Promise<void>((resolve, reject) =>
      server.close((error) => (error ? reject(error) : resolve())),
    );
  }
});

test('without WebGL the exact model remains visible and frozen responses still render', async ({
  page,
}) => {
  await page.addInitScript(() => {
    const original = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function (type: string, ...args: unknown[]) {
      if (type.startsWith('webgl')) return null;
      return original.apply(this, [type, ...args] as Parameters<typeof original>);
    } as typeof original;
  });
  await page.goto('/#/case/STD-001?turn=t1&tab=reference');
  await expect(page.locator('.fallback svg')).toBeVisible();
  await expect(page.locator('.fallback')).toContainText('static');
  await expect(page.locator('.research-response-figure svg')).toBeVisible();
  await expect(page.getByRole('button', { name: /Export image/ })).toBeDisabled();
  await page.locator('.research-quantity-details > summary').click();
  await expect(page.locator('[data-quantity-id]').first()).toBeVisible();
});
