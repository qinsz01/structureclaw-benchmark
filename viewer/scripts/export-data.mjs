import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { parseDxf } from './dxf.mjs';
import { readResearchCorpus } from './research-data.mjs';
import { writePublicTaskArchive } from './public-task-archive.mjs';
import workbook from '../../scripts/export-research300-catalogue-workbook.cjs';
import { writeCatalogueRelease } from '../../scripts/export-research300-catalogue.mjs';

export const viewerRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
export const corpusRoot = path.resolve(viewerRoot, '..');
const ownedNames = [
  'cases',
  'models',
  'attachments',
  'sources',
  'fixtures',
  'index.json',
  'thumbnails.json',
  'catalogue.json',
  'benchmark-catalogue.xlsx',
  'trials',
];

// JSON.stringify normalizes -0 to 0. Preserve the frozen numeric sign in all
// source models and response rows, including local-axis metadata.
function stringify(value) {
  if (typeof value === 'number') return Object.is(value, -0) ? '-0' : JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map((item) => stringify(item ?? null)).join(',')}]`;
  if (value && typeof value === 'object')
    return `{${Object.entries(value)
      .filter(([, item]) => item !== undefined)
      .map(([key, item]) => `${JSON.stringify(key)}:${stringify(item)}`)
      .join(',')}}`;
  return JSON.stringify(value);
}

function validateDestination(output, root) {
  const destination = path.resolve(output),
    source = path.resolve(root);
  if (
    source === destination ||
    source.startsWith(destination + path.sep) ||
    (destination.startsWith(source + path.sep) &&
      destination !== path.join(source, 'viewer/public/data'))
  )
    throw new Error('Export destination must not overwrite corpus sources');
  let current = destination;
  while (current !== path.dirname(current)) {
    if (fs.existsSync(current) && fs.lstatSync(current).isSymbolicLink())
      throw new Error(`Symlink export destination: ${current}`);
    current = path.dirname(current);
  }
  return destination;
}

/** Build a read-only reviewer site; never use this data directory as model input. */
export function exportData(
  output = path.join(viewerRoot, 'public/data'),
  { root = corpusRoot, includeTaskArchive, includeCatalogueRelease } = {},
) {
  output = validateDestination(output, root);
  // All source validation finishes before touching the previously generated site.
  const { index, cases, reader } = readResearchCorpus(root);
  fs.mkdirSync(path.dirname(output), { recursive: true });
  const staging = fs.mkdtempSync(path.join(path.dirname(output), '.research-viewer-export-'));
  const write = (relative, value) => {
    const target = path.join(staging, relative);
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.writeFileSync(target, stringify(value));
  };
  const thumbnails = {};
  try {
    if (
      fs.existsSync(
        path.join(root, 'docs/implementation/reviews/codex-full300-20261027/evidence-meta.json'),
      )
    ) {
      const trial = spawnSync(
        'python3',
        [path.join(viewerRoot, 'scripts/trial-data.py'), '--root', root, '--output', staging],
        {
          encoding: 'utf8',
          timeout: 180000,
          maxBuffer: 1024 * 1024,
        },
      );
      if (trial.error || trial.status !== 0)
        throw new Error(`Sealed Codex trial export failed: ${trial.error || trial.stderr}`);
      index.codexTrial = JSON.parse(fs.readFileSync(path.join(staging, 'trials/index.json')));
      for (const item of index.cases) {
        const result = index.codexTrial.caseResults.find((row) => row.caseId === item.id);
        item.codexTrial = { status: result.status, repaired: result.repaired };
      }
    }
    for (const { detail, models } of cases) {
      for (const attachment of detail.turns.flatMap((turn) => turn.attachments)) {
        const target = path.join(staging, attachment.path);
        fs.mkdirSync(path.dirname(target), { recursive: true });
        const { bytes } = reader.bytes(attachment.source, attachment.sha256, 'public-input');
        fs.writeFileSync(target, bytes);
        if (attachment.path.toLowerCase().endsWith('.dxf'))
          write(`${attachment.path}.json`, parseDxf(bytes.toString('utf8')));
      }
      for (const model of models) {
        write(`models/${model.caseId}-s${model.state}.json`, model);
        const { nodes, elements, coordinate_system } = model.model;
        thumbnails[`${model.caseId}-s${model.state}`] = { nodes, elements, coordinate_system };
      }
      write(`cases/${detail.id}.json`, detail);
    }
    write('index.json', index);
    write('thumbnails.json', thumbnails);
    write('catalogue.json', index.catalogue);
    workbook.writeCatalogueWorkbook(
      index.catalogue,
      path.join(staging, 'benchmark-catalogue.xlsx'),
    );
    if (includeCatalogueRelease ?? output === path.join(path.resolve(root), 'viewer/public/data'))
      writeCatalogueRelease(index.catalogue, path.join(root, 'planning/releases'));
    if (
      (includeTaskArchive ?? output === path.join(path.resolve(root), 'viewer/public/data')) &&
      index.cases.length === 300 &&
      cases.every(({ detail }) => detail.turns.every((turn) => turn.inputEdition === 'current'))
    )
      writePublicTaskArchive(root, path.dirname(output));
    fs.mkdirSync(output, { recursive: true });
    // Only exporter-owned paths are removed. Preserve unrelated caller files.
    for (const name of ownedNames)
      fs.rmSync(path.join(output, name), { recursive: true, force: true });
    for (const name of fs.readdirSync(staging))
      fs.renameSync(path.join(staging, name), path.join(output, name));
  } finally {
    fs.rmSync(staging, { recursive: true, force: true });
  }
  console.log(
    `Exported research-300: ${index.cases.length} cases, ${index.summary.turns} turns, ${index.summary.states} states, ${index.sources.length} verified sources.`,
  );
  return { ...index, manifest: index.sources };
}
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url))
  exportData();
