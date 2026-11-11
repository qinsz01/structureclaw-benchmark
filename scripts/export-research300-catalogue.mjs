import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath } from 'node:url';
import { readResearchCorpus } from '../viewer/scripts/research-data.mjs';
import workbook from './export-research300-catalogue-workbook.cjs';

const repository = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
export const workbookName = 'StructureClaw_Benchmark_300题_当前版.xlsx';
const catalogueName = 'research300-catalogue.json';

/** Write an already validated projection; the viewer uses this same object. */
export function writeCatalogueRelease(catalogue, output, { check = false } = {}) {
  const staging = fs.mkdtempSync(path.join(os.tmpdir(), 'research300-catalogue-'));
  try {
    fs.writeFileSync(path.join(staging, catalogueName), JSON.stringify(catalogue, null, 2) + '\n');
    workbook.writeCatalogueWorkbook(catalogue, path.join(staging, workbookName));
    for (const name of [catalogueName, workbookName]) {
      const target = path.join(output, name), ready = path.join(staging, name);
      if (check) {
        if (!fs.existsSync(target) || !fs.readFileSync(target).equals(fs.readFileSync(ready)))
          throw new Error(`Current catalogue is stale: ${target}. Run npm run catalogue:research300.`);
      } else {
        fs.mkdirSync(output, { recursive: true });
        const adjacent = fs.mkdtempSync(path.join(output, '.catalogue-release-'));
        try {
          fs.copyFileSync(ready, path.join(adjacent, name));
          fs.renameSync(path.join(adjacent, name), target);
        } finally { fs.rmSync(adjacent, { recursive: true, force: true }); }
      }
    }
  } finally { fs.rmSync(staging, { recursive: true, force: true }); }
  console.log(`${check ? 'Checked' : 'Exported'} Research 300 catalogue: ${catalogue.totals.cases} tasks, ${catalogue.totals.turns} turns, ${catalogue.totals.states} states, ${catalogue.totals.attachmentFiles} input files.`);
  return catalogue;
}

/** Refresh the current release, retaining the original planning workbook verbatim. */
export function exportResearchCatalogue({ root = repository, output = path.join(root, 'planning/releases'), check = false } = {}) {
  return writeCatalogueRelease(readResearchCorpus(root).index.catalogue, output, { check });
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const args = process.argv.slice(2);
  if (args.some((arg) => arg !== '--check')) throw new Error('Usage: node scripts/export-research300-catalogue.mjs [--check]');
  exportResearchCatalogue({ check: args.includes('--check') });
}
