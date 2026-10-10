import { test, expect } from '@playwright/test';
test('member curves for beam, truss and spatial frame retain honest provenance and export', async ({
  page,
}) => {
  const index = await (await page.request.get('/data/index.json')).json();
  for (const id of ['beam-simple-6m-udl20-point30', 'truss-simple-tri', 'frame3d-simple']) {
    const item = index.cases.find((c: { id: string; referenceIds: string[] }) =>
      id === 'frame3d-simple' ? c.id === 'std-frame3d-simple-gt' : c.referenceIds.includes(id),
    );
    const detail = await (await page.request.get(`/data/cases/${item.id}.json`)).json();
    const turn = detail.references.findIndex((refs: string[]) => refs.includes(id));
    await page.goto(`/#/case/${item.id}?turn=${turn}`);
    const panel = page.locator('.member-view');
    await expect(panel).toBeVisible();
    if (id.startsWith('beam')) {
      await expect(panel.locator('.note')).toContainText('检查通过');
      await panel.getByLabel('单元曲线分量').selectOption('M3');
    }
    if (id.startsWith('truss')) {
      await expect(panel.locator('.note')).toContainText('桁架不恢复弯矩');
      await panel.getByLabel('单元曲线分量').selectOption('N');
    }
    if (id.startsWith('frame3d')) {
      await expect(panel.locator('.note')).toContainText('楼板传递荷载未完整归档');
      await expect(panel.getByLabel('单元曲线分量').locator('option[value="M3"]')).toHaveCount(0);
    }
    const figure = panel.locator('.paper-figure');
    await figure.screenshot({ path: `test-results/${id}-members.png` });
    const download = page.waitForEvent('download');
    await figure.getByRole('button', { name: 'SVG ↓', exact: true }).click();
    await (await download).saveAs(`test-results/${id}-members.svg`);
    await page.setViewportSize({ width: 390, height: 844 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
      true,
    );
    await page.setViewportSize({ width: 1440, height: 1000 });
  }
  await page.getByRole('button', { name: 'EN', exact: true }).click();
  await expect(page.locator('.member-view')).toContainText(
    'Expanded floor loads were not archived',
  );
});
