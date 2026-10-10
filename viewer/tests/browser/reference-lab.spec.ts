import { test, expect } from '@playwright/test';
import fs from 'node:fs';

test('linked values, deformation, analytical checks and publication exports', async ({ page }) => {
  await page.goto('/#/case/beam-multi-turn-incomplete?turn=1');
  await expect(page.locator('.result-lab')).toBeVisible();
  await page
    .locator('.reference-results tbody tr')
    .filter({ has: page.locator('td code', { hasText: /^2$/ }) })
    .locator('[data-component="uz"] button')
    .click();
  await expect(page.locator('.result-lab > .paper-figure svg')).toContainText(
    '2 · uz = -0.0164634 m',
  );
  await page.getByLabel('叠加节点变形').check();
  await page.getByLabel('变形倍率').fill('30');
  await expect(page.locator('.result-lab > .paper-figure svg')).toContainText('变形 ×30');
  await page.locator('.calculation-panel > summary').click();
  await expect(page.locator('.calculation-panel')).toContainText('u_z(L/2) = −5qL⁴/(384EI)');
  await expect(page.locator('.calculation-panel')).toContainText('60 kN');
  const figure = page.locator('.calculation-panel .paper-figure');
  const download = page.waitForEvent('download');
  await figure.getByRole('button', { name: 'SVG ↓', exact: true }).click();
  const d = await download;
  const file = await d.path();
  const svg = fs.readFileSync(file!, 'utf8');
  expect(svg).toContain('Source: models/beam-simple-6m.json');
  expect(svg).toContain('−5qL⁴');
  expect(svg).not.toContain('foreignObject');
  await d.saveAs('test-results/beam-calculation-zh.svg');
  const pngDownload = page.waitForEvent('download');
  await figure.getByRole('button', { name: 'PNG ×3 ↓', exact: true }).click();
  const png = await pngDownload;
  await png.saveAs('test-results/beam-calculation-zh.png');
  const bytes = fs.readFileSync((await png.path())!);
  expect(bytes.readUInt32BE(16)).toBe(3000);
  expect(bytes.readUInt32BE(20)).toBe(2610);
  await figure.screenshot({ path: 'test-results/calculation-panel.png' });
  await page.getByLabel('着色指标').selectOption('moment');
  await page.locator('.result-lab svg [role="button"]').first().click();
  await expect(page.locator('.result-lab > .paper-figure svg')).toContainText(
    'max(|n1.M|, |n2.M|)',
  );
  await page.getByRole('button', { name: 'EN', exact: true }).click();
  await expect(page.locator('.result-lab')).toContainText('Auxiliary analytical calculations');
  await page.getByLabel('Color metric').selectOption('norm');
  await page
    .locator('.result-lab > .paper-figure')
    .screenshot({ path: 'test-results/results-en.png' });
});

test('coverage, multi-turn flow and multimodal evidence figures', async ({ page }) => {
  await page.goto('/');
  await page.locator('.paper-workbench > summary').click();
  await expect(page.locator('.paper-selectors select')).toHaveCount(3);
  await page
    .locator('.paper-workbench .paper-figure')
    .screenshot({ path: 'test-results/coverage.png' });
  await page.goto('/#/case/re-arch-frame-complex-2s2b');
  await expect(page.locator('.scene-canvas canvas')).toBeVisible();
  await page.getByText('论文图版 · 建模证据链', { exact: true }).click();
  const evidence = page
    .locator('.paper-figure')
    .filter({ has: page.getByRole('heading', { name: '建模证据链', exact: true }) });
  await expect(evidence).toContainText('(d) 数值标答摘要');
  await evidence.screenshot({ path: 'test-results/frame-evidence.png' });
  const download = page.waitForEvent('download');
  await evidence.getByRole('button', { name: 'SVG ↓', exact: true }).click();
  await (await download).saveAs('test-results/frame-evidence-zh.svg');
  await page.getByText('论文图版 · 输入与预期任务流程', { exact: true }).click();
  await expect(
    page.getByRole('img', { name: '任务流程（冻结输入与评判约束）', exact: true }),
  ).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
});
