'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { fixture } = require('./research300-test-fixtures.cjs');
const provider = require('./corpus-provider.cjs');
const { buildManifest } = require('../scripts/build-research300-manifest.cjs');
const { getFrozenPublicBinding } = require('./public-input-edition.cjs');
const save = (file, value) => fs.writeFileSync(file, JSON.stringify(value, null, 2) + '\n');

function cleanFixture(t, id = 'STD-001') {
  const f = fixture(t, id);
  f.contract.turns.push({ ...f.contract.turns[0], id: 't2', instruction: 'Keep all loads; report the same displacement in mm.', attachments: [] });
  for (const output of f.contract.requiredOutputs) output.turnIds = ['t1', 't2'];
  f.save();
  save(path.join(f.root, 'corpora/research-300/manifest.json'), buildManifest({ root: f.root, allowPartial: true }));
  const result = spawnSync('python3', [path.resolve(__dirname, '../scripts/research300/public_input_clean.py'), '--root', f.root, '--case', id], { encoding: 'utf8', timeout: 60000 });
  assert.equal(result.status, 0, result.stderr || result.stdout);
  f.record = provider.loadCase(provider.loadCorpus({ corpus: 'research-300', root: f.root }), id);
  f.editionDir = path.join(f.root, 'corpora/research-300/public-inputs');
  f.bundleFile = path.join(f.editionDir, id, 'input.json');
  f.rehash = () => {
    const manifestFile = path.join(f.editionDir, 'manifest.json');
    const manifest = JSON.parse(fs.readFileSync(manifestFile));
    manifest.cases.find(row => row.id === id).sha256 = provider.sha256(fs.readFileSync(f.bundleFile));
    save(manifestFile, manifest);
  };
  return f;
}

for (const id of ['STD-001', 'INT-001']) test(`${id}: clean delivery keeps native identity and exact response requirements`, t => {
  const f = cleanFixture(t, id);
  const before = getFrozenPublicBinding(f.record);
  const input = provider.getPublicTurnInput(f.record, 0);
  assert.equal(input.inputEdition, 'current');
  assert.equal(input.attachments.length, 1);
  assert.match(input.attachments[0].name, /\.md$/);
  assert.deepEqual(input.responseContract, provider.getFrozenPublicTurnInput(f.record, 0).responseContract);
  assert.deepEqual(getFrozenPublicBinding(f.record), before);
  assert.throws(() => provider.getPublicTurnInput(f.record, 0, { edition: 'frozen' }), /selection/i);
  assert.equal(provider.getPublicTurnInput(f.record, 1).attachments.length, 0);
  assert.equal(provider.getPublicTurnInput(f.record, 1).inputEdition, 'current');
  for (const attachment of input.attachments) {
    assert.equal(provider.sha256(fs.readFileSync(attachment.path)), attachment.sha256);
    assert.doesNotMatch(fs.readFileSync(attachment.path, 'utf8'), /[a-f0-9]{64}|inputBinding|expectedQuestions/);
    assert.match(fs.readFileSync(attachment.path, 'utf8'), /x_m.*y_m.*z_m/);
  }
});

test('present broken clean input fails closed while frozen input remains inspectable', t => {
  const f = fixture(t);
  const record = provider.loadCase(provider.loadCorpus({ corpus: 'research-300', root: f.root }), f.contract.id);
  fs.mkdirSync(path.join(f.root, 'corpora/research-300/public-inputs'), { recursive: true });
  assert.throws(() => provider.getPublicTurnInput(record, 0), /edition|manifest|ENOENT/i);
  assert.throws(() => provider.getPublicTurnInput(record, 0, { edition: 'frozen' }), /selection/i);
});

test('clean edition cannot alter facts even after its editable manifest is rehashed', t => {
  const f = cleanFixture(t);
  const bundle = JSON.parse(fs.readFileSync(f.bundleFile));
  bundle.turns[0].instruction += ' Apply an additional 90 kN load.';
  save(f.bundleFile, bundle);
  f.rehash();
  assert.throws(() => provider.getPublicTurnInput(f.record, 0), /correspondence|deterministic/i);
});

test('clean edition rejects extra delivered files and omitted case coverage', t => {
  const f = cleanFixture(t);
  const bundle = JSON.parse(fs.readFileSync(f.bundleFile));
  bundle.turns[0].attachments.push({ ...bundle.turns[0].attachments[0], name: 'extra.md', path: 'extra.md' });
  fs.copyFileSync(path.join(path.dirname(f.bundleFile), bundle.turns[0].attachments[0].path), path.join(path.dirname(f.bundleFile), 'extra.md'));
  save(f.bundleFile, bundle);
  f.rehash();
  assert.throws(() => provider.getPublicTurnInput(f.record, 0), /one|single|correspondence|deterministic/i);
  const manifestFile = path.join(f.editionDir, 'manifest.json');
  const manifest = JSON.parse(fs.readFileSync(manifestFile));
  manifest.cases = [];
  save(manifestFile, manifest);
  assert.throws(() => provider.getPublicTurnInput(f.record, 0), /coverage|missing/i);
});
