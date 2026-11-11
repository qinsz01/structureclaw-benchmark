#!/usr/bin/env node
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const defaultProvider = require('../lib/corpus-provider.cjs');
const { toPublicTask } = require('../lib/public-task.cjs');
const ROOT = path.resolve(__dirname, '..');
const { EDITION, PUBLIC_INPUT_ROOT } = require('../lib/public-input-edition.cjs');
const README = '# Research-300 benchmark inputs\n\n'
  + 'The case list is in `index.json`. Each `cases/<id>/task.json` contains the task turns.\n\n'
  + 'Present turns in order. On each turn, supply its instruction and only the attachment files listed for that turn. Keep earlier turns in the conversation. Attachment paths are relative to the case folder.\n\n'
  + 'Provide these reporting instructions once before the task turns:\n\n'
  + 'Report every requested signed result in a Markdown table:\n\n'
  + '| selection | location | component | value | unit |\n'
  + '| --- | --- | --- | --- | --- |\n\n'
  + 'Use `case:<id>` or `combination:<id>`. Use the public node ID or `memberID@positionM:left/right` for location; positionM is in metres. Preserve selection IDs, signs and requested units. An optional descriptive label may precede selection.\n\n'
  + 'For derived results, include a fenced JSON object with a `derivedQuantities` array. Each entry supplies `value`, `unit`, `governingOperand` and `governingSelection`. Use null governing fields for sums and differences. For extrema, identify the governing public node/member, a published derived ID or an unambiguous selection key; supply `{"kind":"case","id":"<id>"}` (or kind `combination`) as governingSelection. Add `governingLocation` with kind, id and, for a member, positionM and side when needed to identify the exact station.\n\n'
  + 'Identify each derived result by its published `id` or by its `operation` and public `operands`: `{"operation":"difference","operands":["memberA","memberB"]}` means memberA minus memberB. Supported operations are difference, sum, max, min and max_abs. Bare node/member operands must identify a unique requested quantity; otherwise supply an operand object with `selection:{kind,id}`, `location:{kind,id,positionM,side}` and `component` (omit positionM/side for nodes). A single requested derived result may omit its id and operation/operands.\n';
const INDEX_FIELDS = ['id', 'family', 'language', 'engine', 'turns'];
const METADATA = /\b(?:sha256|inputBinding|responseContract|baseSourceHash|publicInputSha256)\b|[a-f0-9]{64}/i;
const SOURCE_DIRECTORIES = new Set(['corpora', 'lib', 'scripts', 'planning', 'schemas', 'scenarios', 'external', 'docs', 'viewer', 'public', 'node_modules']);

const exists = file => fs.lstatSync(file, { throwIfNoEntry: false });
const within = (parent, child) => child === parent || child.startsWith(parent + path.sep);
const json = (file, value) => fs.writeFileSync(file, JSON.stringify(value, null, 2) + '\n', { flag: 'wx', mode: 0o644 });
const closed = (value, keys) => value && typeof value === 'object' && !Array.isArray(value)
  && Object.keys(value).length === keys.length && keys.every(key => Object.hasOwn(value, key));

function noSymlinkComponents(file) {
  const absolute = path.resolve(file);
  let current = path.parse(absolute).root;
  for (const component of absolute.slice(current.length).split(path.sep).filter(Boolean)) {
    current = path.join(current, component);
    const stat = exists(current);
    if (!stat) break;
    if (stat.isSymbolicLink()) throw new Error('Symlink source or output path is forbidden');
  }
}

function noSymlinkTree(directory) {
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const file = path.join(directory, entry.name);
    if (entry.isSymbolicLink()) throw new Error('Symlink in existing output is forbidden');
    if (entry.isDirectory()) noSymlinkTree(file);
    else if (!entry.isFile()) throw new Error('Existing output contains a non-regular file');
  }
}

function publicText(text, context) {
  defaultProvider.assertPublicText(text, context);
  if (METADATA.test(text)) throw new Error(`Internal hashes or metadata in public ${context}`);
}

function checkDestination(root, output) {
  noSymlinkComponents(root);
  noSymlinkComponents(output);
  if (within(output, root)) throw new Error('Export destination cannot replace a source root or its ancestor');
  if (within(root, output)) {
    const first = path.relative(root, output).split(path.sep)[0];
    if (first.startsWith('.') || SOURCE_DIRECTORIES.has(first)) throw new Error('Export destination must be outside source directories');
  }
  const stat = exists(output);
  if (!stat) return false;
  if (!stat.isDirectory()) throw new Error('Existing export destination must be an owned export directory');
  noSymlinkTree(output);
  let owned = false;
  try {
    const index = JSON.parse(fs.readFileSync(path.join(output, 'index.json'), 'utf8'));
    owned = fs.readFileSync(path.join(output, 'README.md'), 'utf8') === README
      && closed(index, ['cases']) && Array.isArray(index.cases) && index.cases.length > 0
      && new Set(index.cases.map(row => row.id)).size === index.cases.length
      && index.cases.every(row => closed(row, INDEX_FIELDS) && defaultProvider.CASE_ID.test(row.id)
        && ['family', 'language', 'engine'].every(key => typeof row[key] === 'string' && row[key].trim())
        && Number.isInteger(row.turns) && row.turns > 0);
  } catch (_) { /* An unrelated directory never becomes an owned export. */ }
  if (!owned) throw new Error('Refusing to replace an existing directory not recognized as an owned input export');
  return true;
}

function privateHashes(record) {
  const allowed = new Set(['prompt.txt', ...(record.contract.attachments || [])]);
  return new Set(defaultProvider.listFiles(record.caseDir).filter(name => !allowed.has(name))
    .map(name => defaultProvider.sha256(fs.readFileSync(defaultProvider.resolveCaseFile(record.caseDir, name)))));
}

function loadBundle(root, record) {
  const relative = `${PUBLIC_INPUT_ROOT}/${record.id}`;
  const directory = defaultProvider.resolveCaseFile(root, relative, { directory: true });
  const bundleFile = defaultProvider.resolveCaseFile(directory, 'input.json');
  const bundle = JSON.parse(fs.readFileSync(bundleFile, 'utf8'));
  if (bundle.edition !== EDITION || bundle.caseId !== record.id || !Array.isArray(bundle.turns)
      || bundle.turns.length !== record.contract.turns.length) throw new Error('Clean public bundle case or turn coverage mismatch');
  return { directory, bundle };
}

function attachmentBytes(root, record, input, turnIndex, attachment, released, secrets) {
  defaultProvider.assertRelative(attachment.relPath);
  const turn = released.bundle.turns[turnIndex];
  if (turn.id !== input.turnId || turn.instruction !== input.instruction || !Array.isArray(turn.attachments)
      || turn.attachments.length !== input.attachments.length) throw new Error('Public turn differs from its bundle allowlist');
  const entries = turn.attachments.filter(entry => entry.name === attachment.name && entry.path === attachment.relPath && entry.source === attachment.source);
  if (entries.length !== 1) throw new Error('Attachment is not in the current public bundle allowlist');
  if (attachment.source !== 'edition') throw new Error('Unknown public attachment source');
  const directory = released.directory;
  if (attachment.name !== path.posix.basename(attachment.relPath)) throw new Error('Attachment name differs from its public source path');
  noSymlinkComponents(path.join(directory, attachment.relPath));
  const file = defaultProvider.assertPublicFile(directory, attachment.relPath, secrets, { allowMarkdown: true });
  if (typeof attachment.path !== 'string' || path.resolve(attachment.path) !== file) throw new Error('Attachment source path differs from its public allowlist');
  const bytes = fs.readFileSync(file);
  const digest = defaultProvider.sha256(bytes);
  for (const descriptor of [attachment, entries[0]]) {
    if (descriptor.sha256 !== undefined && (!/^[a-f0-9]{64}$/.test(descriptor.sha256) || descriptor.sha256 !== digest)) throw new Error('Public attachment hash mismatch');
  }
  if (path.extname(attachment.name).toLowerCase() !== '.png') publicText(bytes.toString('utf8'), 'attachment');
  return { bytes, file };
}

function checkCounts(cases, turns, expectedCounts) {
  if (cases !== expectedCounts.cases || (turns !== null && turns !== expectedCounts.turns)) {
    throw new Error(`Complete input export requires ${expectedCounts.cases} cases and ${expectedCounts.turns} turns`);
  }
}

// The CLI exports the complete archive for a harness. A single-case harness may
// restrict publication to an exact released turn; validation still uses the full
// canonical source, while future instructions and files are never written out.
function exportResearch300Inputs({ root = ROOT, output, provider = defaultProvider, expectedCounts = { cases: 300, turns: 420 }, throughTurn } = {}) {
  if (typeof output !== 'string' || !output.trim()) throw new Error('--output is required');
  if (throughTurn !== undefined && (typeof throughTurn !== 'string' || !throughTurn.trim())) throw new Error('Released turn must be an exact public turn ID');
  root = path.resolve(root);
  output = path.resolve(output);
  const owned = checkDestination(root, output);
  const corpus = provider.loadCorpus({ corpus: 'research-300', root });
  if (!corpus || corpus.id !== 'research-300' || !Array.isArray(corpus.cases)) throw new Error('Expected research-300 corpus');
  if (throughTurn !== undefined && corpus.cases.length !== 1) throw new Error('Released-turn export requires a single-case selection');
  checkCounts(corpus.cases.length, null, expectedCounts);
  if (new Set(corpus.cases.map(entry => entry.id)).size !== corpus.cases.length
      || corpus.cases.some(entry => !defaultProvider.CASE_ID.test(entry.id))) throw new Error('Invalid or duplicate research case id');
  fs.mkdirSync(path.dirname(output), { recursive: true });
  noSymlinkComponents(path.dirname(output));
  const stage = fs.mkdtempSync(path.join(path.dirname(output), `.${path.basename(output)}.staging-`));
  let backup;
  try {
    const rows = [];
    let turnCount = 0;
    fs.mkdirSync(path.join(stage, 'cases'));
    for (const entry of [...corpus.cases].sort((a, b) => a.id.localeCompare(b.id, 'en'))) {
      const record = provider.loadCase(corpus, entry.id);
      const caseDir = defaultProvider.resolveCaseFile(root, `corpora/research-300/cases/${entry.id}`, { directory: true });
      if (!record || record.id !== entry.id || record.caseDir !== caseDir || !Array.isArray(record.contract?.turns)) throw new Error('Case source or turn coverage mismatch');
      const lastTurn = throughTurn === undefined ? record.contract.turns.length - 1
        : record.contract.turns.findIndex(turn => turn.id === throughTurn);
      if (lastTurn < 0) throw new Error(`Unknown released turn for ${record.id}: ${throughTurn}`);
      const releasedTurns = record.contract.turns.slice(0, lastTurn + 1);
      const row = { id: record.id, family: record.contract.family, language: record.contract.language, engine: record.contract.plannedEngine, turns: releasedTurns.length };
      for (const key of ['family', 'language', 'engine']) {
        if (typeof row[key] !== 'string' || !row[key].trim()) throw new Error(`Missing public case ${key}`);
        publicText(row[key], 'case metadata');
        if (path.isAbsolute(row[key]) || /[\r\n\x00]/.test(row[key])) throw new Error('Invalid public case metadata');
      }
      const released = loadBundle(root, record);
      const secrets = privateHashes(record);
      const destination = path.join(stage, 'cases', record.id);
      fs.mkdirSync(destination);
      const copied = new Map();
      const turns = releasedTurns.map((original, index) => {
        const input = provider.getPublicTurnInput(record, index);
        if (input.inputEdition !== EDITION) throw new Error(`Standalone export requires the ${EDITION} public input edition`);
        const task = toPublicTask(input);
        if (task.id !== record.id || task.turnId !== original.id) throw new Error('Public task case or turn identity mismatch');
        publicText(task.instruction, 'instruction');
        if (secrets.has(defaultProvider.sha256(Buffer.from(task.instruction, 'utf8')))) throw new Error('Public instruction copies a private file');
        const bundleTurn = released.bundle.turns[index];
        if (bundleTurn.id !== task.turnId || bundleTurn.instruction !== task.instruction
            || !Array.isArray(bundleTurn.attachments) || bundleTurn.attachments.length !== task.attachments.length) throw new Error('Public turn differs from its bundle allowlist');
        if (task.attachments.length > 1 || (record.id.startsWith('MM-') && task.attachments.length !== 1)) throw new Error('A clean public turn may deliver only one attachment; every MM turn requires a single drawing');
        if (record.id.startsWith('MM-') && task.attachments.some(a => !['.png', '.dxf'].includes(path.extname(a.name).toLowerCase()))) throw new Error('MM input must be a single PNG or DXF drawing');
        for (const [attachmentIndex, projected] of task.attachments.entries()) {
          const { bytes, file } = attachmentBytes(root, record, input, index, input.attachments[attachmentIndex], released, secrets);
          const previous = copied.get(projected.path);
          if (previous && previous !== file) throw new Error('Different public source files share a delivery name across turns');
          if (!previous) {
            fs.writeFileSync(path.join(destination, projected.path), bytes, { flag: 'wx', mode: 0o644 });
            copied.set(projected.path, file);
          }
        }
        return { id: task.turnId, instruction: task.instruction, attachments: task.attachments.map(a => a.path) };
      });
      json(path.join(destination, 'task.json'), { caseId: record.id, turns });
      rows.push(row);
      turnCount += turns.length;
    }
    checkCounts(rows.length, turnCount, expectedCounts);
    fs.writeFileSync(path.join(stage, 'README.md'), README, { flag: 'wx', mode: 0o644 });
    json(path.join(stage, 'index.json'), { cases: rows });
    // Recheck ownership immediately before publishing. The old tree survives
    // every validation failure and can be restored if the final rename fails.
    if (checkDestination(root, output) !== owned) throw new Error('Export destination changed during preparation');
    if (owned) {
      backup = fs.mkdtempSync(path.join(path.dirname(output), `.${path.basename(output)}.previous-`));
      fs.rmdirSync(backup);
      fs.renameSync(output, backup);
    }
    try { fs.renameSync(stage, output); }
    catch (error) {
      if (backup) { fs.renameSync(backup, output); backup = undefined; }
      throw error;
    }
    if (backup) { fs.rmSync(backup, { recursive: true }); backup = undefined; }
    return { output, cases: rows.length, turns: turnCount };
  } finally {
    if (exists(stage)) fs.rmSync(stage, { recursive: true });
  }
}

function main(args = process.argv.slice(2)) {
  try {
    const options = {};
    for (let index = 0; index < args.length; index++) {
      const flag = args[index];
      if (flag === '--help') {
        process.stdout.write('Usage: node scripts/export-research300-inputs.cjs --output DIR [--root DIR]\nExport all 300 cases and 420 turns from the current public inputs.\n');
        return;
      }
      if (!['--root', '--output'].includes(flag)) throw new Error(`Unknown option: ${flag}`);
      const value = args[++index];
      if (!value || value.startsWith('--')) throw new Error(`Missing value for ${flag}`);
      options[flag.slice(2)] = value;
    }
    const result = exportResearch300Inputs(options);
    process.stdout.write(`Exported ${result.cases} cases and ${result.turns} turns to ${result.output}\n`);
  } catch (error) {
    process.stderr.write(error.message + '\n');
    process.exitCode = 1;
  }
}

if (require.main === module) main();
module.exports = { exportResearch300Inputs, main };
