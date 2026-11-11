import { test, expect } from '@playwright/test';
import fs from 'node:fs';

test('all 105 MM turns show exactly one complete PNG or DXF drawing', async ({ page }) => {
  test.setTimeout(240000);
  await page.addInitScript(() => localStorage.setItem('research-locale', 'en'));
  const failures: string[] = [];
  page.on('pageerror', (error) => failures.push(error.message));
  page.on('response', (response) => {
    if (response.url().includes('/data/attachments/') && !response.ok())
      failures.push(response.url());
  });
  const index = JSON.parse(fs.readFileSync('public/data/index.json', 'utf8'));
  const ids = index.cases
    .map((entry: { id: string }) => entry.id)
    .filter((id: string) => /^MM-/.test(id));
  expect(ids).toHaveLength(100);
  let checkedTurns = 0;
  for (const id of ids) {
    const detail = JSON.parse(fs.readFileSync(`public/data/cases/${id}.json`, 'utf8'));
    for (const turn of detail.turns) {
      expect(turn.inputEdition, id).toBe('current');
      expect(turn.attachments, id).toHaveLength(1);
      expect(turn.attachments[0].name, id).toMatch(/^drawing(?:-t\d+)?\.(png|dxf)$/);
      await page.goto(`/#/case/${id}?turn=${turn.id}`);
      await expect(page.locator('.research-attachment')).toHaveCount(1);
      if (turn.attachments[0].name.endsWith('.png')) {
        const images = page.locator('.attachment-image img');
        await expect(images).toHaveCount(1);
        await expect
          .poll(
            () =>
              images.evaluateAll((elements) =>
                elements.every((element) => {
                  const img = element as HTMLImageElement;
                  return img.complete && img.naturalWidth > 0 && img.naturalHeight > 0;
                }),
              ),
            { message: `${id}: the complete drawing decodes in the browser` },
          )
          .toBe(true);
      } else {
        await expect(page.locator('.dxf-svg')).toBeVisible();
        expect(
          await page.locator('.dxf-svg line,.dxf-svg text,.dxf-svg path').count(),
        ).toBeGreaterThan(0);
      }
      checkedTurns++;
    }
  }
  expect(checkedTurns).toBe(105);
  expect(failures).toEqual([]);
});

test('maintainer catalogue reports clean input review and frozen acceptance independently', async ({
  page,
}) => {
  await page.addInitScript(() => {
    localStorage.setItem('research-locale', 'en');
    localStorage.setItem('research-maintainer', 'true');
  });
  const index = JSON.parse(fs.readFileSync('public/data/index.json', 'utf8'));
  const review = index.summary.publicInputReview;
  expect(review.edition).toBe('current');
  expect(review.total).toBe(300);
  expect(review.passed + review.partial + review.failed + review.pending + review.invalid).toBe(
    300,
  );
  await page.goto('/');
  await expect(page.locator('[data-summary="currentInputReviewed"] b')).toHaveText(
    String(review.passed),
  );
  await expect(page.locator('[data-summary="publicInputReview"]')).toContainText(
    `${review.total} cases`,
  );
  await expect(page.locator('[data-summary="accepted"] b')).toHaveText(
    String(index.summary.accepted),
  );
  await expect(page.locator('[data-summary="agentNotRun"] b')).toHaveText(
    String(index.summary.agentNotRun),
  );
});
