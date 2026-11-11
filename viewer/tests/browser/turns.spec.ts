import { test, expect } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('research-locale', 'en'));
});

test('physical support count excludes suppressed out-of-plane degrees of freedom', async ({
  page,
}) => {
  await page.goto('/#/case/INT-005?turn=t1&tab=reference');
  await expect(page.locator('.research-geometry-summary')).toContainText('3 nodes');
  await expect(page.locator('.research-geometry-summary')).toContainText('2 physical supports');
});

test('clarification cannot reveal a future state through controls or a crafted deep link', async ({
  page,
}) => {
  await page.goto('/#/case/INT-002?turn=t1&state=1&tab=reference');
  await expect(page.locator('.task-text')).toContainText('10 with no unit');
  await expect(page.locator('.clarification-notice')).toHaveCount(0);
  await expect(page.locator('main')).not.toContainText('forceUnit');
  await expect(page.locator('.research-state, .research-results, .scene-canvas')).toHaveCount(0);
  await expect(page.getByRole('tab', { name: 'Benchmark reference' })).toBeDisabled();
  await expect(page).not.toHaveURL(/state=1/);
  await page.locator('[data-turn-id="t2"]').click();
  await expect(page.locator('[data-turn-id="t2"]')).toHaveAttribute('aria-pressed', 'true');
  await expect(page.locator('.research-attachment')).toHaveCount(0);
  await page.getByRole('tab', { name: 'Benchmark reference' }).click();
  await expect(page.locator('.scene-canvas canvas')).toBeVisible();
  await expect(page.locator('.reference-caption')).toContainText('INT-002 · state 1');
  await page.locator('[data-turn-id="t1"]').click();
  await expect(page.locator('.research-state, .research-results, .scene-canvas')).toHaveCount(0);
  await page.screenshot({ path: 'test-results/research-clarification.png', fullPage: true });
});

test('same-page deep links and late model responses retain the requested clarification turn', async ({
  page,
}) => {
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route('**/data/models/INT-002-s1.json', async (route) => {
    await gate;
    await route.continue();
  });
  const request = page.waitForRequest('**/data/models/INT-002-s1.json');
  await page.goto('/#/case/INT-002?turn=t2&tab=reference');
  await request;
  await page.evaluate(() => {
    location.hash = '/case/INT-002?turn=t1&state=1&tab=reference';
  });
  await expect(page.locator('.task-text')).toBeVisible();
  await expect(page.getByRole('tab', { name: 'Benchmark reference' })).toBeDisabled();
  const response = page.waitForResponse('**/data/models/INT-002-s1.json');
  release();
  await response;
  await expect(page.locator('[data-turn-id="t1"]')).toHaveAttribute('aria-pressed', 'true');
  await expect(page.locator('.research-state, .research-results, .scene-canvas')).toHaveCount(0);
  await expect(page).not.toHaveURL(/state=1/);
});

test('a physical edit and undo select the exact model state, including after reload', async ({
  page,
}) => {
  await page.goto('/#/case/INT-001?turn=t2&state=2&tab=reference');
  await expect(page.locator('[data-turn-id="t2"]')).toHaveAttribute('aria-pressed', 'true');
  await expect(page.locator('.research-state')).toHaveAttribute('data-state', '2');
  const modified = await page.locator('.research-state').getAttribute('data-model-sha256');
  await page.locator('[data-turn-id="t3"]').click();
  await expect(page.locator('.research-state')).toHaveAttribute('data-state', '3');
  const restored = await page.locator('.research-state').getAttribute('data-model-sha256');
  expect(restored).not.toBe(modified);
  await page.reload();
  await expect(page.locator('[data-turn-id="t3"]')).toHaveAttribute('aria-pressed', 'true');
  await expect(page.locator('.research-state')).toHaveAttribute('data-state', '3');
  await page.locator('[data-turn-id="t1"]').click();
  await expect(page.locator('.research-state')).toHaveAttribute('data-model-sha256', restored!);
});

test('query turns retain physical state and convert only their requested quantities and units', async ({
  page,
}) => {
  await page.goto('/#/case/INT-097?turn=t1&tab=reference');
  await expect(page.locator('.research-state')).toHaveAttribute('data-state', '1');
  const hash = await page.locator('.research-state').getAttribute('data-model-sha256');
  await page.locator('.research-quantity-details > summary').click();
  const first = page.locator('tr[data-quantity-id="case-D--top--uz"]');
  await expect(first).toBeVisible();
  await expect(first.locator('[data-unit]')).toHaveAttribute('data-unit', 'm');
  const m = Number(await first.locator('[data-value]').getAttribute('data-value'));
  expect(m).toBeLessThan(0);
  await expect(page.locator('tr[data-quantity-id]')).toHaveCount(2);
  await page.locator('[data-turn-id="t2"]').click();
  await expect(page.locator('.research-state')).toHaveAttribute('data-model-sha256', hash!);
  await page.locator('.research-quantity-details > summary').click();
  const second = page.locator('tr[data-quantity-id="case-D--top--uz--mm"]');
  await expect(second.locator('[data-unit]')).toHaveAttribute('data-unit', 'mm');
  const mm = Number(await second.locator('[data-value]').getAttribute('data-value'));
  expect(mm).toBeCloseTo(m * 1000, 10);
  await expect(page.locator('[data-quantity-id="case-D--top--uz"]')).toHaveCount(0);
  await expect(page.locator('tr[data-quantity-id]')).toHaveCount(2);
  await expect(page).toHaveURL(/turn=t2/);
  await expect(page).toHaveURL(/state=1/);
});

test('commercial scoring uses native PKPM precision while strict and engineering diagnostics stay distinct', async ({
  page,
}) => {
  await page.goto('/#/case/STD-089?tab=reference');
  await expect(page.locator('.reference-source')).toContainText('PKPM');
  await page.locator('.research-quantity-details > summary').click();
  const q = page.locator('tr[data-quantity-id="case-D-member-c0-0-1-s0-right-M3"]');
  await expect(q.locator('[data-value]')).toHaveAttribute('data-value', '1.693812370300293');
  await expect(q.locator('[data-unit]')).toHaveAttribute('data-unit', 'kN.m');
  await page.getByRole('button', { name: 'Maintainer mode', exact: true }).click();
  await page.getByRole('tab', { name: 'Review & provenance' }).click();
  await expect(page.locator('[data-status="nativeVerified"]')).toHaveAttribute(
    'data-complete',
    'true',
  );
  await expect(page.locator('[data-status="inputReviewed"]')).toHaveAttribute(
    'data-complete',
    'false',
  );
  await expect(page.locator('[data-status="accepted"]')).toHaveAttribute('data-complete', 'false');
  await expect(page.locator('[data-status="agentNotRun"]')).toContainText('Not run');
  await expect(page.locator('.diagnostic-summary')).toContainText('Strict');
  await expect(page.locator('.diagnostic-summary')).toContainText('Engineering');
  await expect(page.locator('.strict-differences tbody tr')).toHaveCount(2);
  await expect(page.locator('.strict-differences')).toContainText('M3');
  await expect(page.locator('.diagnostic-summary [data-engineering-failed]')).toHaveAttribute(
    'data-engineering-failed',
    '0',
  );
  await page.screenshot({ path: 'test-results/research-std089-diagnostics.png', fullPage: true });
});
