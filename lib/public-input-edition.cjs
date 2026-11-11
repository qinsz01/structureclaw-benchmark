'use strict';

// One canonical public input changes delivered presentation, never authored/native source identity.
// The bundle is deliberately a closed schema, not an arbitrary record overlay.
const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const EDITION = 'current';
const PUBLIC_INPUT_ROOT = 'corpora/research-300/public-inputs';
const VALIDATORS = Object.freeze(['scripts/research300/public_input_clean.py', 'scripts/research300/public_input_visual.py', 'scripts/research300/render_public_visual.cjs', 'scripts/research300/public_input_editorial.py']);
const HASH = /^[a-f0-9]{64}$/;
const checkedContent = new Set();
const provider = () => require('./corpus-provider.cjs');
const digest = value => provider().sha256(Buffer.from(JSON.stringify(value), 'utf8'));
const canonical = value => Array.isArray(value) ? value.map(canonical)
  : value && typeof value === 'object' ? Object.fromEntries(Object.keys(value).sort().map(key => [key, canonical(value[key])])) : value;
const fail = message => { throw new Error(`Public input edition: ${message}`); };

function fields(value, names, context) {
  if (!value || typeof value !== 'object' || Array.isArray(value)
      || Object.keys(value).some(key => !names.includes(key)) || names.some(key => !Object.hasOwn(value, key))) fail(`invalid ${context} fields`);
}
function hash(value, context) { if (typeof value !== 'string' || !HASH.test(value)) fail(`invalid ${context} hash`); }
function read(root, relative) {
  const file = provider().resolveCaseFile(root, relative);
  const bytes = fs.readFileSync(file);
  return { file, bytes, sha256: provider().sha256(bytes) };
}
function parse(bytes, context) {
  try { return JSON.parse(bytes.toString('utf8')); } catch (_) { fail(`invalid ${context} JSON`); }
}

function getFrozenPublicBinding(record) {
  const { resolveCaseFile, sha256, getResponseContract } = provider();
  const fileHash = name => sha256(fs.readFileSync(resolveCaseFile(record.caseDir, name)));
  const sourcePaths = [...new Set(['contract.json', 'prompt.txt', 'reference-requests.json', ...record.contract.modelStates, ...record.contract.attachments])]
    .sort((a, b) => Buffer.compare(Buffer.from(a), Buffer.from(b)));
  const sourceHash = digest({ schemaVersion: 1, files: sourcePaths.map(name => ({ path: name, sha256: fileHash(name) })) });
  const publicFiles = [...new Set(['prompt.txt', ...record.contract.attachments])].sort().map(name => {
    const bytes = fs.readFileSync(resolveCaseFile(record.caseDir, name));
    return { path: name, sha256: sha256(bytes), bytes: bytes.length };
  });
  const turns = record.contract.turns.map((turn, index) => ({ id: turn.id, instruction: turn.instruction,
    attachments: turn.attachments, responseContract: getResponseContract(record, index) }));
  return { sourceHash, publicSha256: digest({ files: publicFiles, turns }) };
}

function checkCorrespondence(record, contentHash, validatorSha256, checker) {
  // All bytes and base hashes are verified afresh before using this cache. No
  // mtime/size or mutable manifest property substitutes for content identity.
  const key = `${validatorSha256}:${contentHash}`;
  if (checkedContent.has(key)) return;
  const result = spawnSync('python3', [checker, '--check', '--case', record.id, '--root', record.root], {
    encoding: 'utf8', timeout: 30000, maxBuffer: 1024 * 1024,
  });
  if (result.error || result.status !== 0) fail(`deterministic editorial correspondence check failed${result.error ? `: ${result.error.code || result.error.message}` : ''}`);
  let verdict;
  try { verdict = JSON.parse(result.stdout); } catch (_) { fail('editorial checker returned an invalid verdict'); }
  if (verdict.valid !== true) fail('deterministic editorial correspondence check did not validate this edition');
  if (checkedContent.size >= 1024) checkedContent.clear();
  checkedContent.add(key);
}

function loadPublicInputEdition(record, options = {}) {
  if (!options || typeof options !== 'object' || Array.isArray(options) || Object.keys(options).length) fail('public input selection is unavailable; this benchmark has one current input');
  if (record.corpus !== 'research-300') return null;
  const multimodal = /^MM-\d{3}$/.test(record.id);
  const { resolveCaseFile, listFiles, sha256, assertPublicFile, assertPublicText, getResponseContract } = provider();
  const selected = EDITION;
  // Missing or broken canonical input is an error. Historical source files are
  // available only to provenance checks, never as an automatic delivery fallback.
  const editionDir = resolveCaseFile(record.root, PUBLIC_INPUT_ROOT, { directory: true });
  const manifestData = read(editionDir, 'manifest.json');
  const manifest = parse(manifestData.bytes, 'manifest');
  fields(manifest, ['schemaVersion', 'edition', 'cases'], 'manifest');
  if (manifest.schemaVersion !== 1 || manifest.edition !== selected || !Array.isArray(manifest.cases)) fail('invalid manifest edition or schema');
  const ids = new Set();
  for (const entry of manifest.cases) {
    fields(entry, ['id', 'baseSourceHash', 'basePublicSha256', 'path', 'sha256'], 'manifest case');
    const idPattern = /^(STD|INT|MM)-(00[1-9]|0[1-9][0-9]|100)$/;
    if (typeof entry.id !== 'string' || !idPattern.test(entry.id) || ids.has(entry.id)) fail('invalid or duplicate case ID');
    ids.add(entry.id);
    if (entry.path !== `${entry.id}/input.json`) fail('manifest case path must match its case ID');
    for (const key of ['baseSourceHash', 'basePublicSha256', 'sha256']) hash(entry[key], key);
  }
  const casesDir = resolveCaseFile(record.root, 'corpora/research-300/cases', { directory: true });
  const expectedIds = fs.readdirSync(casesDir).filter(id => /^(STD|INT|MM)-\d{3}$/.test(id));
  if (expectedIds.length !== ids.size || expectedIds.some(id => !ids.has(id))) fail('manifest case coverage is incomplete');
  const entry = manifest.cases.find(item => item.id === record.id);
  if (!entry) fail('case is missing from edition manifest');
  const frozen = getFrozenPublicBinding(record);
  if (entry.baseSourceHash !== frozen.sourceHash || entry.basePublicSha256 !== frozen.publicSha256) fail('frozen base source/public binding mismatch');
  const originalManifest = parse(read(record.root, 'corpora/research-300/manifest.json').bytes, 'frozen manifest');
  const originalRows = originalManifest.cases?.filter(item => item.id === record.id);
  if (originalRows?.length !== 1 || originalRows[0].sourceHash !== frozen.sourceHash || originalRows[0].publicSha256 !== frozen.publicSha256) fail('frozen manifest source/public binding mismatch');
  const bundleData = read(editionDir, entry.path);
  if (bundleData.sha256 !== entry.sha256) fail('bundle hash mismatch');
  const bundle = parse(bundleData.bytes, 'bundle');
  fields(bundle, ['schemaVersion', 'edition', 'caseId', 'baseSourceHash', 'turns'], 'bundle');
  if (bundle.schemaVersion !== 1 || bundle.edition !== selected || bundle.caseId !== record.id || bundle.baseSourceHash !== frozen.sourceHash) fail('bundle case/source/edition binding mismatch');
  if (!Array.isArray(bundle.turns) || bundle.turns.length !== record.contract.turns.length) fail('bundle turn coverage mismatch');
  const privateHashes = new Set();
  const publicNames = new Set(['prompt.txt', ...record.contract.attachments]);
  for (const name of listFiles(record.caseDir)) if (!publicNames.has(name)) privateHashes.add(sha256(fs.readFileSync(resolveCaseFile(record.caseDir, name))));
  const caseEditionDir = resolveCaseFile(editionDir, record.id, { directory: true });
  const released = new Set();
  const turns = bundle.turns.map((turn, index) => {
    fields(turn, ['id', 'instruction', 'attachments'], 'turn');
    const original = record.contract.turns[index];
    if (turn.id !== original.id || typeof turn.instruction !== 'string' || !turn.instruction.trim() || !Array.isArray(turn.attachments)) fail('turn order, ID or instruction mismatch');
    if (turn.attachments.length > 1 || (multimodal && turn.attachments.length !== 1)) fail('clean input must deliver one drawing per multimodal turn and at most one file per other turn');
    assertPublicText(turn.instruction, `edition turn ${index + 1}`);
    if (privateHashes.has(sha256(Buffer.from(turn.instruction)))) fail('instruction copies a private file');
    const names = new Set();
    const attachments = turn.attachments.map(attachment => {
      fields(attachment, ['name', 'source', 'path', 'sha256'], 'attachment');
      if (attachment.source !== 'edition' || typeof attachment.name !== 'string'
          || attachment.name !== path.posix.basename(attachment.path || '') || names.has(attachment.name)) fail('invalid or duplicate attachment name/source');
      names.add(attachment.name);
      hash(attachment.sha256, 'attachment');
      const identity = `${attachment.source}:${attachment.path}`;
      if (released.has(identity)) fail('attachment must be newly released on its original turn');
      released.add(identity);
      const permitted = multimodal ? ['.png', '.dxf'] : ['.md'];
      if (!permitted.includes(path.extname(attachment.path))) fail('public attachment format is not permitted');
      const file = assertPublicFile(caseEditionDir, attachment.path, privateHashes, { allowMarkdown: true });
      if (sha256(fs.readFileSync(file)) !== attachment.sha256) fail('attachment hash mismatch');
      return { name: attachment.name, relPath: attachment.path, path: file, source: attachment.source, sha256: attachment.sha256 };
    });
    return { id: record.id, turnId: turn.id, instruction: turn.instruction, attachments, responseContract: getResponseContract(record, index) };
  });
  const publicInputSha256 = digest(canonical({ schemaVersion: 1, caseId: record.id, inputEdition: selected,
    baseSourceHash: frozen.sourceHash, basePublicSha256: frozen.publicSha256,
    turns: turns.map(turn => ({ id: turn.turnId, instruction: turn.instruction,
      attachments: turn.attachments.map(a => ({ name: a.name, source: a.source, path: a.relPath, sha256: a.sha256 })), responseContract: turn.responseContract })) }));
  const validatorSources = VALIDATORS.map(source => ({ path: source, sha256: sha256(fs.readFileSync(path.resolve(__dirname, '..', source))) }));
  const validatorSha256 = validatorSources[0].sha256;
  // Authoring SVG/audit bytes are not model-facing attachments, but changing
  // them must invalidate an earlier successful correspondence check too.
  const inventory = listFiles(caseEditionDir).map(name => ({ path: name, sha256: read(caseEditionDir, name).sha256 }));
  const authorAuditSha256 = read(caseEditionDir, 'author-audit.json').sha256;
  checkCorrespondence(record, digest({ publicInputSha256, inventory }),
    digest(validatorSources), path.resolve(__dirname, '..', validatorSources[0].path));
  const inputBinding = { schemaVersion: 1, caseId: record.id, inputEdition: selected, publicInputSha256,
    baseSourceHash: frozen.sourceHash, basePublicSha256: frozen.publicSha256,
    editionManifestSha256: manifestData.sha256, editionBundleSha256: bundleData.sha256, editorialValidatorSha256: validatorSha256,
    validatorSources, authorAuditSha256 };
  return { inputBinding, turns: turns.map(turn => ({ ...turn, inputEdition: selected, publicInputSha256, inputBinding: { ...inputBinding } })) };
}

module.exports = { EDITION, PUBLIC_INPUT_ROOT, getFrozenPublicBinding, loadPublicInputEdition };
