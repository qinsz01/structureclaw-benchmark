import { test, expect } from '@playwright/test';
import fs from 'node:fs';

test('DXF layers, zoom, dimensions, property card and publication export', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto('/#/case/re-arch-frame-complex-2s2b');
  const drawing = page.locator('.dxf-svg');
  await expect(drawing).toBeVisible();
  await expect(drawing.locator('line')).toHaveCount(61);
  await expect(drawing.locator('text')).toHaveCount(12);
  const view = await drawing.getAttribute('viewBox');
  await page.getByRole('button', { name: '放大图纸', exact: true }).click();
  await expect(drawing).not.toHaveAttribute('viewBox', view!);
  await page.getByRole('button', { name: '适配', exact: true }).click();
  await expect(drawing).toHaveAttribute('viewBox', view!);
  await page.getByRole('button', { name: '图层', exact: true }).click();
  const layer = page.locator('.drawing-layers input').first();
  await layer.uncheck();
  expect(await drawing.locator('line,text,polyline,circle').count()).toBeLessThan(74);
  await layer.check();
  await page.getByRole('button', { name: '图层', exact: true }).click();
  await page.getByRole('button', { name: '放大查看', exact: true }).click();
  await expect(page.getByRole('dialog', { name: 'DXF 图纸预览' })).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.locator('.expanded-drawing')).toHaveCount(0);
  await page.getByRole('button', { name: '尺寸', exact: true }).click();
  await expect(page.getByRole('button', { name: '尺寸', exact: true })).toHaveAttribute(
    'aria-pressed',
    'true',
  );
  await expect(page.locator('.answer-summary')).toContainText('模型规模');
  await page.getByRole('button', { name: '出图模式', exact: true }).click();
  await page.getByRole('slider', { name: '出图字号' }).fill('1.5');
  await page.getByRole('slider', { name: '出图线宽' }).fill('1.5');
  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: '导出原图 + 结构图', exact: true }).click();
  const file = await download;
  await file.saveAs('test-results/dxf-comparison-figure.png');
  const buffer = fs.readFileSync('test-results/dxf-comparison-figure.png');
  expect(buffer.readUInt32BE(16)).toBe(2800);
  expect(buffer.readUInt32BE(20)).toBe(1500);
  await page.screenshot({ path: 'test-results/dxf-improved.png', fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect
    .poll(() => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth))
    .toBe(true);
  await page.screenshot({ path: 'test-results/dxf-improved-mobile.png', fullPage: true });
  expect(errors).toEqual([]);
});

test('camera survives display changes and a shared link restores the turn and load', async ({
  page,
  context,
}) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  await page.goto('/#/case/beam-multi-turn-incomplete');
  await page.locator('.turn-tabs button').nth(1).click();
  await page.getByRole('button', { name: '轴测', exact: true }).click();
  const canvas = page.locator('.scene-canvas canvas');
  await expect(canvas).toBeVisible();
  const box = (await canvas.boundingBox())!;
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width / 2 + 90, box.y + box.height / 2 + 20, { steps: 10 });
  await page.mouse.up();
  const before = await canvas.getAttribute('data-camera');
  const expectSameCamera = async () => {
    await expect
      .poll(async () => {
        const values = (await canvas.getAttribute('data-camera'))!.split(',').map(Number);
        return Math.max(...before!.split(',').map((n, i) => Math.abs(Number(n) - values[i])));
      })
      .toBeLessThan(1e-8);
  };
  await page.getByRole('button', { name: '编号', exact: true }).click();
  await expectSameCamera();
  await page.getByRole('button', { name: '荷载', exact: true }).click();
  await expectSameCamera();
  await page.getByRole('button', { name: 'EN', exact: true }).click();
  await expectSameCamera();
  await page.getByRole('button', { name: 'Share this view' }).click();
  const url = await page.evaluate(() => navigator.clipboard.readText());
  expect(url).toContain('turn=1');
  expect(url).toContain('load=LC1');
  const second = await context.newPage();
  await second.goto(url);
  await expect(second.locator('.turn-tabs button').nth(1)).toHaveAttribute('aria-pressed', 'true');
  await expect(second.locator('.scene-bottom select')).toHaveValue('LC1');
  await expect(second.getByRole('button', { name: 'Labels', exact: true })).toHaveAttribute(
    'aria-pressed',
    'true',
  );
  await expect(second.getByRole('button', { name: 'Loads', exact: true })).toHaveAttribute(
    'aria-pressed',
    'false',
  );
  const restored = (await second.locator('canvas').getAttribute('data-camera'))!
    .split(',')
    .map(Number);
  before!
    .split(',')
    .map(Number)
    .forEach((value, i) => expect(restored[i]).toBeCloseTo(value, 5));
  await second.close();
});

test('image composition exports without DXF and every referenced drawing has a complete preview', async ({
  page,
}) => {
  const index = await (await page.request.get('/data/index.json')).json();
  for (const c of index.cases.filter((c: { modality: string }) => c.modality === 'dxf')) {
    const detail = await (await page.request.get(`/data/cases/${c.id}.json`)).json();
    for (const a of detail.scenario.attachments) {
      const drawing = await (await page.request.get(`/data/${a.relPath}.json`)).json();
      expect(drawing.unsupported).toEqual([]);
      expect(drawing.entities.length).toBeGreaterThan(0);
    }
  }
  await page.goto('/#/case/image-frame-sketch');
  await page.getByRole('button', { name: '出图模式', exact: true }).click();
  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: '导出原图 + 结构图', exact: true }).click();
  await (await download).saveAs('test-results/image-comparison-figure.png');
  await page.goto('/#/case/frame-2story-1bay-static');
  await page.locator('.scene-bottom select').selectOption({ index: 0 });
});
