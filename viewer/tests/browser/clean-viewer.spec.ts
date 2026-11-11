import { test, expect } from '@playwright/test';
import fs from 'node:fs';

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('research-locale', 'en'));
});

for (const id of ['MM-001', 'STD-001', 'INT-002']) {
  test(`${id} defaults to the task and attachments without internal metadata or answer hints`, async ({
    page,
  }) => {
    await page.goto(`/#/case/${id}`);
    await expect(
      page.getByRole('button', { name: 'Maintainer mode', exact: true }),
    ).toHaveAttribute('aria-pressed', 'false');
    await expect(page.locator('.task-text')).toBeVisible();
    await expect(page.getByRole('tab', { name: 'Review & provenance' })).toHaveCount(0);
    await expect(
      page.locator(
        '.turn-identity, .research-input-edition, .research-attachment-source, .clarification-notice, .research-json',
      ),
    ).toHaveCount(0);
    await expect(page.locator('.research-turn-tabs small')).toHaveCount(0);
    const text = await page.locator('main').innerText();
    expect(text).not.toMatch(
      /SHA-?256|[a-f0-9]{64}|baseSourceHash|inputBinding|responseContract|unresolvedFields|expectedQuestion|forceUnit|Frozen evaluator|Public response contract|corpora\/research-300/,
    );
    const pending = page.waitForEvent('download');
    await page.getByRole('button', { name: 'Download public input JSON' }).click();
    const input = JSON.parse(fs.readFileSync((await (await pending).path())!, 'utf8'));
    expect(Object.keys(input).sort()).toEqual(['attachments', 'caseId', 'instruction', 'turnId']);
    expect(input.caseId).toBe(id);
    expect(input.turnId).toBe('t1');
    for (const attachment of input.attachments) {
      expect(Object.keys(attachment).sort()).toEqual(['mimeType', 'name', 'path']);
      expect(attachment.path).not.toMatch(/^(?:\/|[A-Za-z]:)|(?:^|\/)\.\.(?:\/|$)/);
    }
  });
}

test('review deep links need an explicit global maintainer selection and switching off closes diagnostics', async ({
  page,
}) => {
  await page.goto('/#/case/STD-089?tab=review&maintainer=true');
  await expect(page.locator('.task-text')).toBeVisible();
  await expect(page.locator('.research-review')).toHaveCount(0);
  await expect(page.getByRole('tab', { name: 'Review & provenance' })).toHaveCount(0);
  await page.getByRole('button', { name: 'Maintainer mode', exact: true }).click();
  await page.getByRole('tab', { name: 'Review & provenance' }).click();
  await expect(page.locator('[data-status="accepted"]')).toHaveAttribute('data-complete', 'false');
  await expect(page.locator('[data-status="agentNotRun"]')).toContainText('Not run');
  await expect(page.locator('.research-review')).toContainText('Case input hash');
  await page.reload();
  await expect(page.getByRole('button', { name: 'Maintainer mode', exact: true })).toHaveAttribute(
    'aria-pressed',
    'true',
  );
  await expect(page.locator('.research-review')).toBeVisible();
  await page.getByRole('button', { name: 'Maintainer mode', exact: true }).click();
  await expect(page.locator('.task-text')).toBeVisible();
  await expect(page.locator('.research-review')).toHaveCount(0);
  await page.reload();
  await expect(page.getByRole('button', { name: 'Maintainer mode', exact: true })).toHaveAttribute(
    'aria-pressed',
    'false',
  );
});

test('normal reference view preserves signed scoring values, units and deformation without visible hashes', async ({
  page,
}) => {
  await page.goto('/#/case/INT-097?turn=t2&tab=reference');
  await expect(page.locator('.research-results')).toBeVisible();
  await page.locator('.research-quantity-details > summary').click();
  await expect(
    page.getByRole('columnheader', { name: 'Absolute / relative tolerance' }),
  ).toHaveCount(0);
  const value = page.locator('tr[data-quantity-id="case-D--top--uz--mm"]');
  await expect(value.locator('[data-unit]')).toHaveAttribute('data-unit', 'mm');
  expect(Number(await value.locator('[data-value]').getAttribute('data-value'))).toBeLessThan(0);
  await page.getByRole('checkbox', { name: 'Discrete NODE deformation' }).check();
  await expect(page.locator('.research-deformed-node').first()).toBeVisible();
  const visibleText = [
    await page.locator('main').innerText(),
    ...(await page.locator('svg text').allTextContents()),
  ].join(' ');
  expect(visibleText).not.toMatch(/SHA-?256|[a-f0-9]{64}|corpora\/research-300/);
  await expect(
    page.locator(
      '.research-reference-evidence, .research-deformation-source, .research-quantity-provenance',
    ),
  ).toHaveCount(0);
  for (const name of ['Export plotted data JSON', 'Download complete turn reference JSON']) {
    const pending = page.waitForEvent('download');
    await page.getByRole('button', { name, exact: true }).click();
    const payload = JSON.parse(fs.readFileSync((await (await pending).path())!, 'utf8'));
    expect(payload.engine).toBe('OpenSees');
    expect(payload.quantities.length).toBeGreaterThan(0);
    expect(JSON.stringify(payload)).not.toMatch(
      /sha256|[a-f0-9]{64}|sourceHash|receipt|tolerance|rawTrace|corpora\/research-300/i,
    );
  }
  const pendingModel = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Download model JSON', exact: false }).click();
  const model = JSON.parse(fs.readFileSync((await (await pendingModel).path())!, 'utf8'));
  expect(model.model.nodes.length).toBeGreaterThan(0);
  expect(JSON.stringify(model)).not.toMatch(
    /sha256|[a-f0-9]{64}|sourceHash|receipt|rawTrace|corpora\/research-300/i,
  );
  await page.getByRole('button', { name: 'Maintainer mode', exact: true }).click();
  await expect(
    page.getByRole('columnheader', { name: 'Absolute / relative tolerance' }),
  ).toBeVisible();
});

test('normal catalogue and input stay clean and fit a narrow screen', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  for (const url of ['/', '/#/case/MM-021', '/#/case/STD-001', '/#/case/INT-002']) {
    await page.goto(url);
    await expect(page.locator('.research-loading')).toHaveCount(0);
    await expect(
      page.locator(
        '[data-summary="accepted"], [data-summary="agentNotRun"], .research-status-note',
      ),
    ).toHaveCount(0);
    await expect
      .poll(() => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth))
      .toBe(true);
  }
  await expect(page.getByRole('tab', { name: 'Benchmark reference' })).toBeDisabled();
  await expect(page.locator('.research-state, .research-results')).toHaveCount(0);
});
