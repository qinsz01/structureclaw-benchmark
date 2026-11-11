import { test, expect } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import { parsePublicText } from '../../src/public-text';

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('research-locale', 'en'));
});

test('research catalogue contains all 300 cases, opt-in accurate stages, and persistent filters', async ({
  page,
}) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Research 300', exact: true })).toBeVisible();
  await expect(page.locator('.result-count b')).toHaveText('300');
  await expect(page.locator('.case-card')).toHaveCount(12);
  await expect(page.locator('[data-summary="turns"] b')).toHaveText('420');
  await expect(page.locator('[data-summary="states"] b')).toHaveText('364');
  await expect(
    page.locator('[data-summary="nativeVerified"], [data-summary="accepted"]'),
  ).toHaveCount(0);
  await page.getByRole('button', { name: 'Maintainer mode', exact: true }).click();
  await expect(page.locator('[data-summary="nativeVerified"] b')).toHaveText('300');
  const index = JSON.parse(fs.readFileSync(path.resolve('public/data/index.json'), 'utf8'));
  expect(index.summary.inputReviewed).toBe(0);
  await expect(page.locator('[data-summary="currentInputReviewed"] b')).toHaveText(
    String(index.summary.publicInputReview.passed),
  );
  await expect(page.locator('[data-summary="accepted"] b')).toHaveText('0');
  await expect(page.locator('[data-summary="agentNotRun"] b')).toHaveText('300');
  await page.getByRole('button', { name: 'Maintainer mode', exact: true }).click();
  await page.screenshot({ path: 'test-results/research-catalogue-desktop.png', fullPage: true });
  await page
    .getByRole('combobox', { name: 'Family', exact: true })
    .selectOption('interactive_robustness');
  await expect(page.locator('.result-count b')).toHaveText('100');
  await page.getByRole('combobox', { name: 'Input language' }).selectOption('en');
  await expect(page.locator('.result-count b')).toHaveText('50');
  await page.getByRole('button', { name: 'Clear filters' }).click();
  await page.getByRole('combobox', { name: 'Engine', exact: true }).selectOption('YJK');
  await expect(page.locator('.result-count b')).toHaveText('17');
  await page.getByRole('searchbox').fill('MM-082');
  await expect(page.locator('.case-card')).toHaveCount(1);
  await page.locator('.case-card').click();
  await expect(page.locator('.research-detail')).toHaveAttribute('data-case-id', 'MM-082');
  await page.getByRole('link', { name: 'Back to catalogue' }).click();
  await expect(page.getByRole('searchbox')).toHaveValue('MM-082');
  await expect(page.getByRole('combobox', { name: 'Engine', exact: true })).toHaveValue('YJK');
  await page.getByRole('searchbox').fill('does-not-exist');
  await expect(page.locator('.research-empty')).toBeVisible();
  await page.getByRole('button', { name: 'Clear filters' }).click();
  await page.getByRole('button', { name: 'Next page' }).click();
  await expect(page).toHaveURL(/page=2/);
  await page.reload();
  await expect(page.locator('.pagination')).toContainText('2 / 25');
  await page.evaluate(() => {
    location.hash = '/?q=STD-089&engine=PKPM';
  });
  await expect(page.getByRole('searchbox')).toHaveValue('STD-089');
  await expect(page.getByRole('combobox', { name: 'Engine', exact: true })).toHaveValue('PKPM');
  await expect(page.locator('.case-card')).toHaveCount(1);
  await page.getByRole('button', { name: '中文', exact: true }).click();
  await expect(page.locator('html')).toHaveAttribute('lang', 'zh-CN');
  await expect(page.getByRole('heading', { name: '案例目录' })).toBeVisible();
  await page.screenshot({
    path: 'test-results/research-catalogue-filtered-zh.png',
    fullPage: true,
  });
});

test('all 300 research routes and all 420 public turns expose their exact inputs and state', async ({
  page,
}) => {
  test.setTimeout(600000);
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  const index = JSON.parse(fs.readFileSync(path.resolve('public/data/index.json'), 'utf8'));
  expect(index.corpusId).toBe('research-300');
  expect(index.cases).toHaveLength(300);
  let turns = 0;
  for (const c of index.cases) {
    const detail = JSON.parse(
      fs.readFileSync(path.resolve(`public/data/cases/${c.id}.json`), 'utf8'),
    );
    await page.goto(`/#/case/${c.id}`);
    await expect(page.locator('.detail-title h1')).toHaveText(c.description);
    for (const turn of detail.turns) {
      await page.locator(`.turn-tabs button[data-turn-id="${turn.id}"]`).click();
      const blocks = parsePublicText(turn.instruction);
      const visibleText = blocks
        .map((block) =>
          block.type === 'table'
            ? [...block.headers, ...block.rows.flat()].join('')
            : block.type === 'list'
              ? block.items.join('')
              : block.text,
        )
        .join('');
      await expect(page.locator('.task-text')).toHaveText(visibleText);
      await expect(page.locator(`.turn-tabs button[data-turn-id="${turn.id}"]`)).toHaveAttribute(
        'aria-pressed',
        'true',
      );
      await expect(page.locator('.turn-identity')).toHaveCount(0);
      await expect(page.locator('.research-attachment')).toHaveCount(turn.attachments.length);
      for (const attachment of turn.attachments) {
        const href = await page
          .locator(
            `.research-attachment[data-name="${attachment.name}"] > .research-attachment-heading a[download]`,
          )
          .getAttribute('href');
        expect(href).toContain(`/data/${attachment.path}`);
      }
      await expect(page.locator('.research-state')).toHaveCount(0);
      if (turn.state === null) {
        await expect(page.locator('.clarification-notice')).toHaveCount(0);
        await expect(page.getByRole('tab', { name: 'Benchmark reference' })).toBeDisabled();
      } else {
        await page.getByRole('tab', { name: 'Benchmark reference' }).click();
        await expect(page.locator('.research-state')).toHaveAttribute(
          'data-state',
          String(turn.state),
        );
        await expect(page.locator('.scene-canvas canvas, .fallback svg')).toBeVisible();
        await expect(page.locator('.research-results')).toBeVisible();
        await page.getByRole('tab', { name: 'Public input' }).click();
      }
      turns++;
    }
  }
  expect(turns).toBe(420);
  expect(errors).toEqual([]);
});

test('all 150 old cases have no catalogue links, routes, or generated artifacts', async ({
  page,
}) => {
  test.setTimeout(180000);
  const files = fs.readdirSync(path.resolve('public/data/cases'));
  expect(files).toHaveLength(300);
  expect(files.every((name) => /^(STD|INT|MM)-\d{3}\.json$/.test(name))).toBe(true);
  const scenarioRoot = path.resolve('../scenarios');
  const oldIds = fs
    .readdirSync(scenarioRoot, { recursive: true })
    .map(String)
    .filter((file) => file.endsWith('.json'))
    .map((file) => JSON.parse(fs.readFileSync(path.join(scenarioRoot, file), 'utf8')).id);
  expect(oldIds).toHaveLength(150);
  await page.goto('/');
  for (const id of oldIds) {
    await page.evaluate((caseId) => {
      location.hash = `/case/${caseId}`;
    }, id);
    await expect(page.getByRole('heading', { name: 'Case not found' })).toBeVisible();
    await expect(page.locator('.research-state, .research-results')).toHaveCount(0);
  }
  await page.goto('/');
  const ids = await page
    .locator('.case-card')
    .evaluateAll((links) => links.map((link) => link.getAttribute('href')));
  expect(ids.every((href) => /^#\/case\/(STD|INT|MM)-\d{3}/.test(href || ''))).toBe(true);
});
