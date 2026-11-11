import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { writeCatalogueRelease, workbookName } from './export-research300-catalogue.mjs';

test('release checking detects either stale artifact without rewriting it, and refresh restores both', () => {
  const counts = { turns: 1, states: 1, attachmentFiles: 1, attachmentUses: 1, markdownFiles: 1, pngFiles: 0, dxfFiles: 0 };
  const values = { family: 'standard_workflow', category: 'std_boundary', structure: '梁', dimension: '2D', difficulty: 'L1', modality: 'text', engine: 'OpenSees', language: 'zh' };
  const definitions = Object.fromEntries(Object.entries(values).map(([facet, key]) => [facet, [{ key, zh: key, en: key, ...(facet === 'category' ? { family: values.family } : {}) }]]));
  const catalogue = {
    schemaVersion: 1, edition: 'current', totals: { cases: 1, ...counts }, definitions,
    breakdowns: Object.fromEntries(Object.entries(definitions).map(([facet, items]) => [facet, items.map((item) => ({ ...item, cases: 1, ...counts }))])),
    cases: [{ id: 'STD-001', title: 'Current example', ...values, ...counts, focus: '边界', difficultyReason: '直接映射', authored: true, referenceReady: true, nativeVerified: true, inputReviewStatus: 'pending', accepted: false, modelTrialStatus: 'not-run' }],
  };
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'catalogue-release-test-'));
  const jsonFile = path.join(directory, 'research300-catalogue.json'), xlsxFile = path.join(directory, workbookName);
  try {
    writeCatalogueRelease(catalogue, directory);
    const originalJson = fs.readFileSync(jsonFile), originalWorkbook = fs.readFileSync(xlsxFile);
    assert.deepEqual(JSON.parse(originalJson), catalogue);
    writeCatalogueRelease(catalogue, directory, { check: true });
    fs.writeFileSync(jsonFile, '{}');
    assert.throws(() => writeCatalogueRelease(catalogue, directory, { check: true }), /stale.*research300-catalogue\.json/);
    assert.equal(fs.readFileSync(jsonFile, 'utf8'), '{}', 'check mode cannot silently fix a stale artifact');
    fs.writeFileSync(jsonFile, originalJson);
    fs.writeFileSync(xlsxFile, 'old workbook');
    assert.throws(() => writeCatalogueRelease(catalogue, directory, { check: true }), /stale.*\.xlsx/);
    assert.equal(fs.readFileSync(xlsxFile, 'utf8'), 'old workbook');
    writeCatalogueRelease(catalogue, directory);
    assert.deepEqual(fs.readFileSync(jsonFile), originalJson);
    assert.deepEqual(fs.readFileSync(xlsxFile), originalWorkbook);
    assert.deepEqual(fs.readdirSync(directory).sort(), [workbookName, 'research300-catalogue.json'].sort());
  } finally { fs.rmSync(directory, { recursive: true, force: true }); }
});
