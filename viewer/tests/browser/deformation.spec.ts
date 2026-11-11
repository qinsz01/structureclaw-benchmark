import { test, expect } from '@playwright/test';
import fs from 'node:fs';
test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('research-locale', 'en'));
});
for (const [id, turnId] of [
  ['STD-001', 't1'],
  ['MM-001', 't1'],
  ['INT-040', 't2'],
  ['INT-079', 't2'],
  ['INT-081', 't2'],
]) {
  test(`${id} displays every verified native node and member independently of requested rows`, async ({
    page,
  }) => {
    await page.goto(`/#/case/${id}?turn=${turnId}&tab=reference`);
    await expect(page.locator('.research-state')).toHaveAttribute('data-state', '1');
    const toggle = page.getByRole('checkbox', { name: 'Discrete NODE deformation' });
    await expect(toggle).toBeEnabled();
    await toggle.check();
    const data = await page.locator('.research-response-figure metadata').textContent();
    const evidence = JSON.parse(data!);
    const coverage = evidence.deformation.field.coverage;
    expect(coverage.completeNodes).toBe(coverage.totalNodes);
    expect(coverage.completeElements).toBe(coverage.totalElements);
    await expect(page.locator('.research-deformed-node')).toHaveCount(coverage.totalNodes);
    await expect(page.locator('.research-deformed-member')).toHaveCount(coverage.totalElements);
    expect(evidence.deformation.nodes).toHaveLength(coverage.totalNodes);
    expect(evidence.deformation.quantities).toHaveLength(coverage.totalNodes * 3);
    expect(
      Number(await page.getByRole('spinbutton', { name: 'Deformation scale' }).inputValue()),
    ).toBeGreaterThan(0);
    const moved = await page
      .locator('.research-deformed-node')
      .evaluateAll((nodes) => nodes.some((n) => n.getAttribute('data-displaced') === 'true'));
    expect(moved).toBe(true);
    // The lazy 3D scene can change the page height while an element screenshot scrolls.
    await expect(page.locator('.scene-canvas canvas')).toBeVisible();
    await page
      .locator('.research-response-figure')
      .screenshot({ path: `test-results/deformation-${id}.png` });
  });
}
test('exports include the full native field without adding extra scoring rows', async ({
  page,
}) => {
  await page.goto('/#/case/STD-001?turn=t1&tab=reference');
  await expect(page.locator('.research-quantity-details tbody tr')).toHaveCount(7);
  await page.getByRole('checkbox', { name: 'Discrete NODE deformation' }).check();
  await expect(page.locator('.research-quantity-details tbody tr')).toHaveCount(7);
  await page.getByRole('spinbutton', { name: 'Deformation scale' }).fill('250');
  const metadata = JSON.parse(
    (await page.locator('.research-response-figure metadata').textContent())!,
  );
  expect(metadata.deformation.scale).toBe(250);
  await page.getByRole('button', { name: 'Maintainer mode', exact: true }).click();
  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Export plotted data JSON' }).click();
  const payload = JSON.parse(fs.readFileSync((await (await download).path())!, 'utf8'));
  expect(payload.deformation.quantities.length).toBe(9);
  expect(payload.deformation.field.engine).toBe('OpenSees');
  await page.getByRole('button', { name: 'Auto scale', exact: true }).click();
  expect(
    Number(await page.getByRole('spinbutton', { name: 'Deformation scale' }).inputValue()),
  ).not.toBe(250);
});

test('SVG and PNG carry the same complete source evidence as the displayed deformation', async ({
  page,
}) => {
  await page.goto('/#/case/MM-001?turn=t1&tab=reference');
  await page.getByRole('button', { name: 'Maintainer mode', exact: true }).click();
  await page.getByRole('checkbox', { name: 'Discrete NODE deformation' }).check();
  const current = JSON.parse(
    (await page.locator('.research-response-figure metadata').textContent())!,
  );
  for (const format of ['SVG', 'PNG']) {
    const pending = page.waitForEvent('download');
    await page.getByRole('button', { name: `Export response ${format}`, exact: true }).click();
    const bytes = fs.readFileSync((await (await pending).path())!);
    let metadata = '';
    if (format === 'SVG')
      metadata = await page.evaluate(
        (text) =>
          new DOMParser().parseFromString(text, 'image/svg+xml').querySelector('metadata')!
            .textContent!,
        bytes.toString('utf8'),
      );
    else
      for (let offset = 8; offset < bytes.length;) {
        const length = bytes.readUInt32BE(offset);
        if (bytes.toString('ascii', offset + 4, offset + 8) === 'iTXt')
          metadata = bytes
            .subarray(offset + 8 + 'research300'.length + 5, offset + 8 + length)
            .toString('utf8');
        offset += length + 12;
      }
    expect(JSON.parse(metadata)).toEqual(current);
  }
});

for (const id of ['INT-079', 'INT-081']) {
  test(`${id} clarification cannot expose native deformation through a crafted state URL`, async ({
    page,
  }) => {
    await page.goto(`/#/case/${id}?turn=t1&state=1&tab=reference`);
    await expect(page.locator('.task-text')).toBeVisible();
    await expect(page.locator('.clarification-notice')).toHaveCount(0);
    await expect(page.getByRole('tab', { name: 'Benchmark reference' })).toBeDisabled();
    await expect(
      page.locator('.research-state, .research-results, .research-deformed-node'),
    ).toHaveCount(0);
    await expect(page).not.toHaveURL(/state=1/);
  });
}
