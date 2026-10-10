import { test, expect } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';

test('catalog filters, bilingual interface, navigation and empty state', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('.case-card')).toHaveCount(12);
  await page.screenshot({ path: 'test-results/library-desktop.png', fullPage: true });
  await page.getByRole('button', { name: /^多轮交互/ }).click();
  await expect(page.locator('.result-count b')).toHaveText('50');
  await page.getByRole('combobox', { name: '全部语言' }).selectOption('en');
  await expect(page.locator('.result-count b')).toHaveText('25');
  await page.getByRole('searchbox').fill('zzzz-no-case');
  await expect(page.locator('.empty')).toBeVisible();
  await page.locator('.empty button').click();
  await expect(page.locator('.result-count b')).toHaveText('150');
  await page.getByRole('button', { name: 'EN', exact: true }).click();
  await expect(page.locator('html')).toHaveAttribute('lang', 'en');
  await expect(page.getByRole('heading', { name: 'Case library' })).toBeVisible();
  await page.getByRole('searchbox').fill('beam-static-with-report');
  await page.locator('.case-card').click();
  await expect(page.locator('.detail')).toBeVisible();
  await page.getByRole('link', { name: 'Back to library' }).click();
  await expect(page.getByRole('searchbox')).toHaveValue('beam-static-with-report');
  await page.screenshot({ path: 'test-results/library-en.png', fullPage: true });
});

test('multi-turn behavior does not borrow a later reference, and numerical values retain signs', async ({
  page,
}) => {
  await page.goto('/#/case/beam-multi-turn-incomplete');
  await expect(page.locator('.behavior-answer')).toBeVisible();
  await expect(page.locator('canvas')).toHaveCount(0);
  await page.screenshot({ path: 'test-results/clarification.png', fullPage: true });
  await page.locator('.turn-tabs button').nth(1).click();
  await expect(page.locator('.scene-canvas canvas')).toBeVisible();
  await expect(page.locator('.reference-caption')).toContainText('beam-simple-6m');
  const canvas = page.locator('.scene-canvas canvas');
  const canvasBox = (await canvas.boundingBox())!;
  await canvas.click({ position: { x: canvasBox.width / 2, y: canvasBox.height / 2 } });
  await expect(page.locator('.selection')).toContainText('"节点": "2"');
  await page.locator('.selection-close').click();
  const row = page.locator('tbody tr').filter({ has: page.locator('td code', { hasText: /^2$/ }) });
  await expect(row.locator('[data-component="uz"]')).toHaveText('-0.0164634');
  await expect(page.locator('th').filter({ hasText: 'uz' })).toContainText('m');
  await page.getByRole('button', { name: '编号', exact: true }).click();
  await expect(page.getByRole('button', { name: '编号', exact: true })).toHaveAttribute(
    'aria-pressed',
    'true',
  );
  await page.getByRole('button', { name: '轴测', exact: true }).click();
  await page.getByRole('button', { name: '重置', exact: true }).click();
  await page.getByRole('button', { name: '全屏', exact: true }).click();
  await expect.poll(() => page.evaluate(() => Boolean(document.fullscreenElement))).toBe(true);
  await page.getByRole('button', { name: '退出全屏', exact: true }).click();
  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: '导出图片' }).click();
  expect((await download).suggestedFilename()).toBe('beam-simple-6m-reference.png');
  await page.screenshot({ path: 'test-results/beam-reference.png', fullPage: true });
  await page.locator('.turn-tabs button').first().click();
  await expect(page.locator('canvas')).toHaveCount(0);
});

test('images, DXF, commercial reference, raw downloads and mobile layouts', async ({ page }) => {
  await page.goto('/#/case/image-frame-sketch');
  await expect(page.locator('.attachment-image img')).toBeVisible();
  await page.locator('.attachment-image').click();
  await expect(page.locator('dialog')).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.locator('dialog')).not.toBeVisible();
  await expect(page.locator('canvas')).toBeVisible();
  await page.screenshot({ path: 'test-results/image-reference.png', fullPage: true });
  const index = await (await page.request.get('/data/index.json')).json();
  const dxf = index.cases.find((c: { modality: string }) => c.modality === 'dxf');
  await page.goto(`/#/case/${dxf.id}`);
  await expect(page.locator('.drawing-icon')).toBeVisible();
  const download = page.waitForEvent('download');
  await page.locator('.attachment-label a').click();
  expect((await download).suggestedFilename()).toMatch(/\.dxf$/);
  await page.goto('/#/case/std-frame3d-simple-pkpm-en');
  await expect(page.locator('.numeric-meta')).toContainText('PKPM');
  await expect(page.locator('.floor-loads')).toContainText('F1: 10 kN/m²');
  await expect(page.locator('.floor-loads')).toContainText('F2: 10 kN/m²');
  await expect(page.locator('canvas')).toBeVisible();
  await page.screenshot({ path: 'test-results/spatial-reference.png', fullPage: true });
  await page.getByRole('button', { name: 'EN', exact: true }).click();
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.locator('.input-panel')).toBeVisible();
  await expect
    .poll(() => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth))
    .toBe(true);
  await page.screenshot({ path: 'test-results/detail-mobile.png', fullPage: true });
  await page.goto('/');
  await expect(page.locator('.case-card')).toHaveCount(12);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: 'test-results/library-mobile.png', fullPage: true });
  await page.goto('/#/case/not-a-real-case');
  await expect(page.getByRole('heading', { name: 'Case not found' })).toBeVisible();
});

test('every case and turn renders without browser errors and links to the correct reference', async ({
  page,
}) => {
  test.setTimeout(300000);
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  const index = JSON.parse(fs.readFileSync(path.resolve('public/data/index.json'), 'utf8'));
  for (const c of index.cases) {
    await page.goto(`/#/case/${c.id}`);
    await expect(page.locator('.detail-title h1')).toHaveText(c.description);
    const detail = JSON.parse(
      fs.readFileSync(path.resolve(`public/data/cases/${c.id}.json`), 'utf8'),
    );
    for (let i = 0; i < detail.turns.length; i++) {
      if (i > 0) await page.locator('.turn-tabs button').nth(i).click();
      await expect(page.locator('.task-text')).toHaveText(detail.turns[i].message);
      if (detail.references[i].length) {
        await expect(page.locator('.reference-caption code')).toHaveText(detail.references[i][0]);
        await expect(page.locator('.scene-canvas canvas')).toBeVisible();
      } else await expect(page.locator('.behavior-answer')).toBeVisible();
    }
  }
  expect(errors).toEqual([]);
});
