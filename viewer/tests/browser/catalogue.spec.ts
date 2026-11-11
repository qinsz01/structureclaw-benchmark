import { test, expect } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import type { ResearchCatalogue, ResearchCatalogueRow } from '../../src/research-types';

const readCatalogue = (): ResearchCatalogue =>
  JSON.parse(fs.readFileSync(path.resolve('public/data/catalogue.json'), 'utf8'));

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('research-locale', 'en'));
});

test('all catalogue filters survive reload and case navigation, then clear together', async ({
  page,
}) => {
  const catalogue = readCatalogue();
  const row = catalogue.cases.find(
    (item) => item.family === 'multimodal_reverse_engineering' && item.language === 'en',
  )!;
  const params = new URLSearchParams({
    q: row.id,
    family: row.family,
    lang: row.language,
    engine: row.engine,
    category: row.category,
    structure: row.structure,
    dimension: row.dimension,
    difficulty: row.difficulty,
    modality: row.modality,
  });
  await page.goto(`/#/?${params}`);
  const fields: [string, keyof ResearchCatalogueRow][] = [
    ['Family', 'family'],
    ['Input language', 'language'],
    ['Engine', 'engine'],
    ['Capability subgroup', 'category'],
    ['Structure', 'structure'],
    ['Dimension', 'dimension'],
    ['Preset difficulty', 'difficulty'],
    ['Input modality', 'modality'],
  ];
  await expect(page.locator('.research-more-filters')).toHaveAttribute('open', '');
  for (const [name, key] of fields) {
    await expect(page.getByRole('combobox', { name, exact: true })).toHaveValue(String(row[key]));
  }
  await expect(page.locator('.result-count')).toHaveText('1 / 300 cases');
  await expect(page.locator('.case-card')).toHaveCount(1);
  await page
    .getByRole('combobox', { name: 'Dimension', exact: true })
    .selectOption(row.dimension === '2D' ? '3D' : '2D');
  await expect(page.locator('.result-count b')).toHaveText('0');
  await page.getByRole('combobox', { name: 'Dimension', exact: true }).selectOption(row.dimension);
  await page.reload();
  for (const [name, key] of fields) {
    await expect(page.getByRole('combobox', { name, exact: true })).toHaveValue(String(row[key]));
  }
  await page.locator('.case-card').click();
  await expect(page.locator('.research-detail')).toHaveAttribute('data-case-id', row.id);
  await page.getByRole('link', { name: '← Back to catalogue', exact: true }).click();
  await expect(page.getByRole('searchbox')).toHaveValue(row.id);
  await expect(page.getByRole('combobox', { name: 'Capability subgroup' })).toHaveValue(
    row.category,
  );
  await page.getByRole('button', { name: 'Clear filters', exact: true }).click();
  await expect(page).toHaveURL(/\/#\/$/);
  await expect(page.locator('.result-count')).toHaveText('300 / 300 cases');
  await expect(page.getByRole('searchbox')).toHaveValue('');
  for (const [name] of fields)
    await expect(page.getByRole('combobox', { name, exact: true })).toHaveValue('');
});

test('capability subgroups follow their family and changing family removes an incompatible subgroup', async ({
  page,
}) => {
  const catalogue = readCatalogue();
  const category = catalogue.definitions.category.find(
    (entry) => entry.family === 'standard_workflow',
  )!;
  const groupCases = catalogue.cases.filter((row) => row.category === category.key).length;
  await page.goto('/');
  await page.locator('.research-more-filters > summary').click();
  await page
    .getByRole('combobox', { name: 'Family', exact: true })
    .selectOption('standard_workflow');
  await page.getByRole('combobox', { name: 'Capability subgroup' }).selectOption(category.key);
  await expect(page.locator('.result-count')).toHaveText(`${groupCases} / 300 cases`);
  await page
    .getByRole('combobox', { name: 'Family', exact: true })
    .selectOption('interactive_robustness');
  await expect(page.getByRole('combobox', { name: 'Capability subgroup' })).toHaveValue('');
  await expect(page.locator('.result-count')).toHaveText('100 / 300 cases');
  await expect(
    page
      .getByRole('combobox', { name: 'Capability subgroup' })
      .locator(`option[value="${category.key}"]`),
  ).toHaveCount(0);
  await expect(page).not.toHaveURL(/category=/);
});

test('composition uses global case denominators and keeps multimodal cases separate from input files', async ({
  page,
}) => {
  const catalogue = readCatalogue();
  await page.goto('/');
  await expect(page.locator('[data-summary="attachmentFiles"] b')).toHaveText('326');
  await page.locator('.research-composition > summary').click();
  for (const [family, turns, states] of [
    ['standard_workflow', '100', '100'],
    ['interactive_robustness', '215', '164'],
    ['multimodal_reverse_engineering', '105', '100'],
  ]) {
    const row = page.locator(`.research-composition tr[data-bucket="${family}"]`);
    await expect(row.locator('[data-metric="cases"]')).toHaveText('100');
    await expect(row.locator('[data-metric="share"]')).toHaveText('33.3%');
    await expect(row.locator('[data-metric="turns"]')).toHaveText(turns);
    await expect(row.locator('[data-metric="states"]')).toHaveText(states);
  }
  await page.getByRole('combobox', { name: 'Composition dimension' }).selectOption('modality');
  const image = page.locator('.research-composition tr[data-bucket="image"]');
  await expect(image.locator('[data-metric="cases"]')).toHaveText('77');
  await expect(image.locator('[data-metric="attachmentFiles"]')).toHaveText('82');
  await expect(image.locator('[data-metric="share"]')).toHaveText('25.7%');
  const dxf = page.locator('.research-composition tr[data-bucket="dxf"]');
  await expect(dxf.locator('[data-metric="cases"]')).toHaveText('23');
  await expect(dxf.locator('[data-metric="dxfFiles"]')).toHaveText('23');
  await page.getByRole('combobox', { name: 'Composition dimension' }).selectOption('category');
  const category = catalogue.breakdowns.category[0];
  const categoryRow = page.locator(`.research-composition tr[data-bucket="${category.key}"]`);
  await expect(categoryRow.locator('th')).toContainText(category.en);
  await expect(categoryRow.locator('.research-composition-family')).toHaveText(
    catalogue.definitions.family.find((family) => family.key === category.family)!.en,
  );
  await expect(categoryRow.locator('[data-metric="cases"]')).toHaveText(String(category.cases));
  await page
    .getByRole('combobox', { name: 'Family', exact: true })
    .selectOption('standard_workflow');
  await expect(page.locator('.result-count')).toHaveText('100 / 300 cases');
  await expect(page.locator('.research-composition tfoot [data-metric="cases"]')).toHaveText('300');
});

test('catalogue JSON and Excel downloads resolve to the published catalogue artifacts', async ({
  page,
}) => {
  await page.goto('/');
  const json = page.getByRole('link', { name: 'Download catalogue JSON', exact: true });
  const excel = page.getByRole('link', { name: 'Download catalogue Excel', exact: true });
  await expect(json).toHaveAttribute('href', './data/catalogue.json');
  await expect(excel).toHaveAttribute('href', './data/benchmark-catalogue.xlsx');
  const jsonDownload = page.waitForEvent('download');
  await json.click();
  const downloaded = JSON.parse(fs.readFileSync((await (await jsonDownload).path())!, 'utf8'));
  expect(downloaded.edition).toBe('current');
  expect(downloaded.totals).toMatchObject({
    cases: 300,
    turns: 420,
    states: 364,
    attachmentFiles: 326,
    markdownFiles: 221,
    pngFiles: 82,
    dxfFiles: 23,
  });
  expect(downloaded.cases).toHaveLength(300);
  const excelDownload = page.waitForEvent('download');
  await excel.click();
  const file = fs.readFileSync((await (await excelDownload).path())!);
  expect(file.subarray(0, 4).toString('hex')).toBe('504b0304');
  expect(file.length).toBeGreaterThan(1000);
});

test('expanded composition and all filters fit a narrow screen without public audit metadata', async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await page.locator('.research-composition > summary').click();
  await page.getByRole('combobox', { name: 'Composition dimension' }).selectOption('category');
  await page.locator('.research-more-filters > summary').click();
  await expect(page.getByRole('combobox', { name: 'Preset difficulty' })).toBeVisible();
  await expect
    .poll(() => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth))
    .toBe(true);
  await expect(page.locator('main')).not.toContainText(
    /SHA-?256|[a-f0-9]{64}|Native verified|Input reviewed|Accepted|Model trials not run/,
  );
  await expect(page.locator('.research-composition-table')).toBeVisible();
});
