import { test, expect } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('research-locale', 'en'));
});

test('diversity overview shows all current results and filters exactly eight failures', async ({
  page,
}) => {
  await page.goto('/');
  const overview = page.getByRole('region', { name: 'Codex trial results' });
  await expect(overview).toContainText('292');
  await expect(overview).toContainText('412');
  await expect(overview).toContainText('146');
  await expect(overview).toContainText('26/300');
  await overview.getByRole('button', { name: /Not passed/ }).click();
  await expect(page.locator('.result-count')).toContainText('8 / 300');
  await expect(page).toHaveURL(/trial=not-passed/);
  await expect(page.locator('.research-case-card')).toHaveCount(8);
  await page.reload();
  await expect(page.locator('.research-case-card')).toHaveCount(8);
});

test('original and repaired INT056 answers stay separate across all turns and deep links', async ({
  page,
}) => {
  await page.goto('/#/case/INT-056?turn=t2&tab=codex&trialVersion=historical');
  const panel = page.locator('.trial-panel');
  await expect(panel.locator('.trial-question')).toContainText(
    'Increase the crane load by 20% and give the revised response.',
  );
  await expect(panel.locator('.trial-turn-heading')).toContainText('not passed');
  await page.getByLabel('Answer version').selectOption('repair');
  await expect(panel.locator('.trial-question')).toContainText('not yet been decided');
  await expect(panel.locator('.trial-answer')).toContainText('Both components');
  await expect(panel.locator('.trial-turn-heading')).toContainText('passed');
  await expect(page).toHaveURL(/trialVersion=repair/);
  await page.reload();
  await expect(page.getByLabel('Answer version')).toHaveValue('repair');
  await expect(panel.locator('.trial-answer')).toContainText('Both components');
  await page.locator('[data-turn-id="t3"]').click();
  await expect(panel.locator('.trial-answer')).toContainText('117.6');
  await expect(page.getByRole('tab', { name: 'Codex answer & evaluation' })).toHaveAttribute(
    'aria-selected',
    'true',
  );
  await page.locator('[data-turn-id="t2"]').click();
  await expect(panel.locator('.trial-answer')).toContainText('Both components');
});

test('drawing, original signed table, candidate figures and scoring failure are inspectable', async ({
  page,
}) => {
  await page.goto('/#/case/MM-090?tab=codex');
  await expect(page.locator('.trial-input-image')).toBeVisible();
  await expect(page.locator('.trial-answer table')).toBeVisible();
  await expect(page.locator('.trial-gallery img').first()).toBeVisible();
  await expect(page.locator('.gate-fail')).not.toHaveCount(0);
  const broken = await page
    .locator('.trial-panel img')
    .evaluateAll(
      (images) =>
        images.filter(
          (image) =>
            !(image as HTMLImageElement).complete || !(image as HTMLImageElement).naturalWidth,
        ).length,
    );
  expect(broken).toBe(0);
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.locator('.trial-answer')).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(
    true,
  );
});

test('PKPM repair is labeled as an adapter regression and linked reports remain historical failures', async ({
  page,
}) => {
  await page.goto('/#/case/STD-080?tab=codex&trialVersion=historical');
  await expect(page.locator('.trial-repair-note')).toContainText('396');
  await expect(page.locator('.trial-turn-heading')).toContainText('not passed');
  await page.goto('/#/case/STD-088?tab=codex&trialVersion=historical');
  const report = page.locator('.trial-answer a', { hasText: 'complete engineering report' });
  await expect(report).toHaveAttribute('href', /data\/trials\/historical\/files\/[a-f0-9]+\.md$/);
  expect((await page.request.get((await report.getAttribute('href'))!)).ok()).toBe(true);
  await expect(page.locator('.trial-turn-heading')).toContainText('not passed');
});

test('candidate answer markup cannot execute HTML or create unverified external links', async ({
  page,
}) => {
  await page.route('**/data/trials/cases/STD-001.json', async (route) => {
    const response = await route.fetch();
    const data = await response.json();
    data.turns[0].answer =
      '<img src=x onerror="window.answerInjected=true">\n\n[external](https://example.invalid/) [script](javascript:alert(1))';
    await route.fulfill({ response, json: data });
  });
  await page.goto('/#/case/STD-001?tab=codex');
  await expect(page.locator('.trial-answer')).toContainText('<img');
  await expect(
    page.locator('.trial-answer a, .trial-answer img, .trial-answer script'),
  ).toHaveCount(0);
  expect(
    await page.evaluate(() => (window as unknown as { answerInjected?: boolean }).answerInjected),
  ).toBeUndefined();
});

test('source-corrected edition and baseline remain distinct in direct links and downloads', async ({
  page,
}) => {
  await page.goto('/#/case/STD-039?tab=codex');
  const panel = page.locator('.trial-panel');
  await expect(page.getByLabel('Answer version')).toHaveValue('current');
  await expect(panel.locator('.trial-question')).toContainText('0.0161472');
  await expect(panel.locator('.trial-turn-heading')).toContainText('passed');
  const answer = await panel.locator('.trial-answer').innerText();
  await page.getByLabel('Answer version').selectOption('historical');
  await expect(panel.locator('.trial-question')).toContainText('0.012');
  await expect(panel.locator('.trial-answer')).not.toHaveText(answer);
  await expect(page).toHaveURL(/trialVersion=historical/);
  await page.reload();
  await expect(page.getByLabel('Answer version')).toHaveValue('historical');
  await page.getByLabel('Answer version').selectOption('current');
  await expect(panel.locator('.trial-question')).toContainText('0.0161472');
});
