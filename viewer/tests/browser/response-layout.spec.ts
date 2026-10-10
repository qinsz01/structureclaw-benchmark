import { test, expect } from '@playwright/test';
test('one response view at a time, persistent controls and compact mobile layout', async ({
  page,
}) => {
  await page.goto('/#/case/re-truss-complex-trap-construction');
  await expect(page.getByRole('heading', { name: '结构响应', exact: true })).toBeVisible();
  await expect(page.locator('.reference-table')).not.toHaveAttribute('open', '');
  await expect(page.locator('.calculation-panel')).not.toHaveAttribute('open', '');
  await page.getByLabel('曲线放大倍数').fill('100');
  await page.getByRole('button', { name: '冻结值与着色', exact: true }).click();
  await expect(page.locator('.response-curves')).toBeHidden();
  await page.getByLabel('着色指标').selectOption('norm');
  await page.getByRole('button', { name: '变形与构件曲线', exact: true }).click();
  await expect(page.getByLabel('曲线放大倍数')).toHaveValue('100');
  await page.locator('.result-lab').screenshot({ path: 'test-results/response-clean-desktop.png' });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.locator('.result-lab').screenshot({ path: 'test-results/response-clean-mobile.png' });
  await page.getByRole('button', { name: 'EN', exact: true }).click();
  await expect(
    page.getByRole('heading', { name: 'Structural response', exact: true }),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Frozen values & color', exact: true }).click();
  await expect(page.getByLabel('Color metric')).toHaveValue('norm');
});
