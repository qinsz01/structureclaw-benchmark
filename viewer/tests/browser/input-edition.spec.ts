import { test, expect } from '@playwright/test';
import fs from 'node:fs';

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('research-locale', 'en'));
});

for (const [id, clause] of [
  ['MM-058', 'Ask a targeted clarification about the two column-base restraints.'],
  ['MM-072', 'Reconstruct the available information and identify the missing essential datum.'],
]) {
  test(`${id} keeps the first-turn clarification action in its task without evaluator hints`, async ({
    page,
  }) => {
    await page.goto(`/#/case/${id}?turn=t1&tab=reference`);
    await expect(page.locator('.task-text')).toContainText(clause);
    await expect(page.getByRole('tab', { name: 'Benchmark reference' })).toBeDisabled();
    await expect(
      page.locator('.research-state, .research-results, .clarification-notice'),
    ).toHaveCount(0);
    await expect(page.locator('.research-attachment')).toHaveCount(1);
    await expect(page.locator('.research-attachment')).toHaveAttribute('data-name', 'drawing.png');
  });
}

test('a single complete raster stays readable and downloadable on mobile', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/#/case/MM-094');
  const attachment = page.locator('.research-attachment[data-name="drawing.png"]');
  await expect(attachment).toBeVisible();
  await expect(page.locator('.research-attachment')).toHaveCount(1);
  await expect(attachment.locator('img').first()).toBeVisible();
  await attachment.getByRole('button', { name: 'Enlarge drawing.png', exact: true }).click();
  const dialog = page.getByRole('dialog', { name: 'drawing.png', exact: true });
  await expect(dialog).toBeVisible();
  await expect(dialog.locator('img')).toBeVisible();
  const fittedWidth = await dialog
    .locator('img')
    .evaluate((img) => img.getBoundingClientRect().width);
  await dialog.getByRole('button', { name: 'Zoom in image', exact: true }).click();
  await expect
    .poll(() => dialog.locator('img').evaluate((img) => img.getBoundingClientRect().width))
    .toBeGreaterThan(fittedWidth);
  await dialog.getByRole('button', { name: 'Actual image size', exact: true }).click();
  await expect
    .poll(() =>
      dialog
        .locator('.research-image-viewport')
        .evaluate(
          (viewport) =>
            viewport.scrollHeight > viewport.clientHeight ||
            viewport.scrollWidth > viewport.clientWidth,
        ),
    )
    .toBe(true);
  await expect
    .poll(() => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth))
    .toBe(true);
  await dialog.getByRole('button', { name: 'Fit image', exact: true }).click();
  await expect
    .poll(() => dialog.locator('img').evaluate((img) => img.getBoundingClientRect().width))
    .toBeCloseTo(fittedWidth, 0);
  await page.keyboard.press('Escape');
  await expect
    .poll(() => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth))
    .toBe(true);
  await page.screenshot({ path: 'test-results/clean-MM-094-mobile.png', fullPage: true });
});

test('clarification releases only its current drawing and public download contains no bindings or future state', async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/#/case/MM-021');
  const detail = JSON.parse(fs.readFileSync('public/data/cases/MM-021.json', 'utf8'));
  await expect(page.locator('.research-input-edition, .research-json')).toHaveCount(0);
  await expect(page.getByRole('tab', { name: 'Benchmark reference' })).toBeDisabled();
  await expect(page.locator('.research-attachment')).toHaveCount(1);
  await expect(page.locator('.research-attachment')).toHaveAttribute('data-name', 'drawing.png');
  await expect(page.locator('.research-attachment[data-name="drawing-t2.png"]')).toHaveCount(0);
  await page.locator('.turn-tabs button[data-turn-id="t2"]').click();
  await expect(page.getByRole('tab', { name: 'Benchmark reference' })).toBeEnabled();
  await expect(page.locator('.research-attachment')).toHaveCount(1);
  await expect(page.locator('.research-attachment')).toHaveAttribute('data-name', 'drawing-t2.png');
  const pending = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Download public input JSON' }).click();
  const input = JSON.parse(fs.readFileSync((await (await pending).path())!, 'utf8'));
  expect(input).toEqual({
    caseId: 'MM-021',
    turnId: 't2',
    instruction: detail.turns[1].instruction,
    attachments: [{ name: 'drawing-t2.png', path: 'drawing-t2.png', mimeType: 'image/png' }],
  });
  await expect
    .poll(() => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth))
    .toBe(true);
});

test('maintainer review keeps current input review separate from frozen benchmark acceptance', async ({
  page,
}) => {
  await page.addInitScript(() => localStorage.setItem('research-maintainer', 'true'));
  await page.goto('/#/case/MM-001?tab=review');
  const detail = JSON.parse(fs.readFileSync('public/data/cases/MM-001.json', 'utf8'));
  const review = page.locator('[data-edition-review]');
  await expect(review).toContainText('Current input independent blind review');
  await expect(review).toHaveAttribute('data-edition-review', detail.publicInputReview.status);
  await expect(review).not.toContainText('clean-v3');
  await expect(page.locator('.research-review-banner')).toContainText(
    'Frozen benchmark acceptance status',
  );
  await expect(page.locator('.research-input-diagnostics')).toContainText('Response contract');
});
