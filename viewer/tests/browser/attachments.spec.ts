import { test, expect } from '@playwright/test';
import fs from 'node:fs';

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('research-locale', 'en'));
});

test('a complete CAD drawing and a complete raster remain inspectable and downloadable', async ({
  page,
}) => {
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto('/#/case/MM-082');
  await expect(page.locator('.research-attachment')).toHaveCount(1);
  await expect(page.locator('.research-attachment')).toHaveAttribute('data-name', 'drawing.dxf');
  const drawing = page.locator('.dxf-svg');
  await expect(drawing).toBeVisible();
  const initial = await drawing.getAttribute('viewBox');
  await page.getByRole('button', { name: 'Zoom in drawing', exact: true }).click();
  await expect(drawing).not.toHaveAttribute('viewBox', initial!);
  await page.getByRole('button', { name: 'Fit', exact: true }).click();
  await expect(drawing).toHaveAttribute('viewBox', initial!);
  const entities = await drawing.locator('line,text,circle,path,polyline').count();
  await page.getByRole('button', { name: 'Layers', exact: true }).click();
  const layers = page.locator('.drawing-layers input');
  expect(await layers.count()).toBeGreaterThan(1);
  for (const layer of await layers.all()) await layer.uncheck();
  await expect(drawing.locator('line,text,circle,path,polyline')).toHaveCount(0);
  for (const layer of await layers.all()) await layer.check();
  await expect(drawing.locator('line,text,circle,path,polyline')).toHaveCount(entities);
  await page.getByRole('button', { name: 'Expand', exact: true }).click();
  await expect(page.getByRole('dialog', { name: 'DXF drawing preview' })).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.locator('.expanded-drawing')).toHaveCount(0);
  const detail = JSON.parse(fs.readFileSync('public/data/cases/MM-082.json', 'utf8'));
  const pendingDrawing = page.waitForEvent('download');
  await page.locator('.research-attachment-heading a[download]').click();
  const downloadedDrawing = await pendingDrawing;
  expect(downloadedDrawing.suggestedFilename()).toBe('drawing.dxf');
  expect(fs.readFileSync((await downloadedDrawing.path())!)).toEqual(
    fs.readFileSync(`public/data/${detail.turns[0].attachments[0].path}`),
  );
  const pendingInput = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Download public input JSON' }).click();
  const input = JSON.parse(fs.readFileSync((await (await pendingInput).path())!, 'utf8'));
  expect(input).toEqual({
    caseId: 'MM-082',
    turnId: 't1',
    instruction: detail.turns[0].instruction,
    attachments: [
      {
        name: 'drawing.dxf',
        path: 'drawing.dxf',
        mimeType: detail.turns[0].attachments[0].mimeType,
      },
    ],
  });
  await page.getByRole('tab', { name: 'Benchmark reference' }).click();
  await expect(page.locator('.reference-caption')).toContainText('YJK');
  await expect(page.locator('.scene-canvas canvas')).toBeVisible();
  await page.screenshot({ path: 'test-results/research-yjk-reference.png', fullPage: true });
  await page.goto('/#/case/MM-001');
  await expect(page.locator('.research-attachment')).toHaveCount(1);
  await page.getByRole('button', { name: 'Enlarge drawing.png', exact: true }).click();
  await expect(
    page.getByRole('dialog', { name: 'drawing.png', exact: true }).locator('img'),
  ).toBeVisible();
  await page.keyboard.press('Escape');
  expect(errors).toEqual([]);
});

test('frozen data, self-contained SVG/PNG and geometry exports retain current case and turn', async ({
  page,
}) => {
  await page.goto('/#/case/INT-097?turn=t2&state=1&tab=reference');
  await expect(page.locator('.research-response-figure svg')).toBeVisible();
  await page.getByRole('button', { name: 'Maintainer mode', exact: true }).click();
  for (const [label, suffix] of [
    ['Export response SVG', 'svg'],
    ['Export response PNG', 'png'],
    ['Export plotted data JSON', 'json'],
  ]) {
    const pending = page.waitForEvent('download');
    await page.getByRole('button', { name: label, exact: true }).click();
    const download = await pending;
    expect(download.suggestedFilename()).toMatch(new RegExp(`^INT-097-t2-s1.*\\.${suffix}$`));
    await download.saveAs(`test-results/research-response.${suffix}`);
  }
  const svg = fs.readFileSync('test-results/research-response.svg', 'utf8');
  expect(svg).toContain('INT-097');
  expect(svg).toContain('t2');
  expect(svg).toContain('mm');
  expect(svg).not.toMatch(/(?:href|src)="https?:/);
  const png = fs.readFileSync('test-results/research-response.png');
  expect(png.readUInt32BE(16)).toBe(2880);
  expect(png.readUInt32BE(20)).toBe(1920);
  const data = JSON.parse(fs.readFileSync('test-results/research-response.json', 'utf8'));
  expect(data.caseId).toBe('INT-097');
  expect(data.turnId).toBe('t2');
  expect(data.state).toBe(1);
  expect(data.unit).toBe('mm');
  expect(data.referenceSource.sha256).toMatch(/^[a-f0-9]{64}$/);
  await page.locator('.research-quantity-details > summary').click();
  const complete = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Download complete turn reference JSON' }).click();
  await (await complete).saveAs('test-results/research-current-turn.json');
  const current = JSON.parse(fs.readFileSync('test-results/research-current-turn.json', 'utf8'));
  expect(current.quantities).toHaveLength(2);
  expect(current.quantities.every((q: { unit: string }) => q.unit === 'mm')).toBe(true);
  const model = page.waitForEvent('download');
  await page.getByRole('link', { name: 'Download model JSON' }).click();
  expect((await model).suggestedFilename()).toBe('INT-097-s1-model.json');
  await page.getByRole('button', { name: 'Labels', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Labels', exact: true })).toHaveAttribute(
    'aria-pressed',
    'true',
  );
  const image = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Export image', exact: false }).click();
  expect((await image).suggestedFilename()).toContain('INT-097-s1');
});

test('catalogue, public drawing, review diagnostics and 3D/results remain usable on a narrow screen', async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  for (const [url, image] of [
    ['/', 'catalogue'],
    ['/#/case/MM-082', 'drawing'],
    ['/#/case/MM-082?tab=reference', 'reference'],
    ['/#/case/STD-089?tab=review', 'review'],
  ]) {
    await page.goto(url);
    if (image === 'review') {
      await page.getByRole('button', { name: 'Maintainer mode', exact: true }).click();
      await page.getByRole('tab', { name: 'Review & provenance' }).click();
    }
    await expect(page.locator('.research-loading')).toHaveCount(0);
    await expect
      .poll(() => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth))
      .toBe(true);
    await page.screenshot({ path: `test-results/research-${image}-mobile.png`, fullPage: true });
  }
  await page.goto('/#/case/MM-082?tab=reference');
  await expect(page.locator('.scene-canvas canvas')).toBeVisible();
  await expect(page.getByRole('combobox', { name: 'Result component' })).toBeVisible();
  await page.locator('.research-quantity-details > summary').click();
  await expect
    .poll(() => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth))
    .toBe(true);
});

test('coincident member stations remain separately selectable and export their native axes', async ({
  page,
}) => {
  await page.goto('/#/case/STD-089?turn=t1&tab=reference');
  await page.getByRole('combobox', { name: 'Result component', exact: true }).selectOption('M2');
  const markers = page.locator('.research-response-marker');
  await expect(markers).toHaveCount(20);
  const centers = await markers
    .locator('circle')
    .evaluateAll((circles) =>
      circles.map((circle) => `${circle.getAttribute('cx')},${circle.getAttribute('cy')}`),
    );
  expect(new Set(centers).size).toBe(20);
  await page
    .locator('.research-response-marker[data-quantity-id="case-D-member-c0-0-1-s0-right-M2"]')
    .click();
  await expect(page.locator('.research-quantity-table tr.selected')).toHaveAttribute(
    'data-quantity-id',
    'case-D-member-c0-0-1-s0-right-M2',
  );
  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Export response SVG', exact: true }).click();
  await (await download).saveAs('test-results/research-station-axes.svg');
  const payload = await page.locator('.research-response-figure metadata').textContent();
  const metadata = JSON.parse(payload!);
  const column = metadata.axes.members.find((member: { id: string }) => member.id === 'c0-0-1');
  expect(column.local1Global).toEqual([0, 0, 1]);
  expect(
    column.basisGlobal.map((axis: number[]) => axis.map((value) => (value === 0 ? 0 : value))),
  ).toEqual([
    [0, 0, 1],
    [0, -1, 0],
    [1, 0, 0],
  ]);
  const exported = fs.readFileSync('test-results/research-station-axes.svg', 'utf8');
  expect(exported).toMatch(/local.*axes/i);
  expect(exported).toContain('c0-0-1');
  const visibleLabels = (
    await page.locator('.research-response-figure svg text').allTextContents()
  ).join(' ');
  expect(visibleLabels).toMatch(/local.*axes/i);
  expect(visibleLabels).toContain('c0-0-1');
  await page
    .locator('.research-response-figure')
    .screenshot({ path: 'test-results/research-member-stations.png' });
});

test('deformation export carries every supporting displacement component for the complete native structure', async ({
  page,
}) => {
  await page.goto('/#/case/INT-040?turn=t2&tab=reference');
  await page.getByRole('combobox', { name: 'Result component', exact: true }).selectOption('ux');
  await page.getByRole('checkbox', { name: 'Discrete NODE deformation', exact: true }).check();
  await page.getByRole('spinbutton', { name: 'Deformation scale' }).fill('100');
  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Export plotted data JSON', exact: true }).click();
  await (await download).saveAs('test-results/research-deformation.json');
  const exported = JSON.parse(fs.readFileSync('test-results/research-deformation.json', 'utf8'));
  expect(exported.component).toBe('ux');
  expect(exported.deformation.nodes).toHaveLength(4);
  expect(
    exported.deformation.quantities
      .filter((q: { location: { id: string } }) => q.location.id === 'D')
      .map((q: { component: string }) => q.component)
      .sort(),
  ).toEqual(['ux', 'uy', 'uz']);
  const node = exported.deformation.nodes.find((n: { id: string }) => n.id === 'D');
  expect(node.id).toBe('D');
  expect(node.original).toEqual([2, 1.1547005383792515, 3]);
  expect(node.translationM).toEqual([
    0.000007754865533369525, 0.000004477273703220243, -0.000019901753707524105,
  ]);
  expect(node.deformed[0]).toBeCloseTo(2.000775486553337, 12);
  expect(node.deformed[1]).toBeCloseTo(1.1551482657495735, 12);
  expect(node.deformed[2]).toBeCloseTo(2.9980098246292477, 12);
  expect(node.quantityIds).toHaveLength(3);
  expect(exported.deformation.elements).toHaveLength(6);
});
