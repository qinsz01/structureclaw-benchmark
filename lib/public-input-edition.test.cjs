"use strict";
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { fixture, publishInputs } = require('./research300-test-fixtures.cjs');
const provider = require('./corpus-provider.cjs');
const { buildSourceBinding, runResearch300, evaluateCandidateCase, currentResponseSha256, currentActivitySha256 } = require('../scripts/run-research300.cjs');
const repo = path.resolve(__dirname, '..');
const json = file => JSON.parse(fs.readFileSync(file, 'utf8'));
const save = (file, value) => fs.writeFileSync(file, JSON.stringify(value, null, 2) + '\n');
const svg = '<svg xmlns="http://www.w3.org/2000/svg" width="300" height="120"><rect width="300" height="120" fill="white"/><line x1="20" y1="80" x2="280" y2="80" stroke="black"/><text x="120" y="50" font-size="20">6 m</text></svg>';
function canonicalFixture(t, { id = 'STD-001', twoTurns = false, clarify = false } = {}) {
  const f = fixture(t, id);
  if (id.startsWith('MM-')) {
    f.write('diagram.svg', svg); f.contract.attachments.push('diagram.svg'); f.contract.turns[0].attachments.push('diagram.svg');
  }
  if (clarify) {
    Object.assign(f.contract.turns[0], { expectation: 'clarify', state: null, instruction: 'Ask for the missing support condition.' });
    f.contract.requiredOutputs = [{ id: 'clarification', kind: 'interaction', state: null, quantityIds: [], description: 'Ask which support to use.' }];
  }
  if (twoTurns) {
    const name = id.startsWith('MM-') ? 'late.svg' : 'late.txt';
    f.write(name, id.startsWith('MM-') ? svg : 'The late span is 7 m.');
    f.contract.attachments.push(name);
    for (const output of f.contract.requiredOutputs) output.turnIds = ['t1'];
    f.contract.turns.push({ ...f.contract.turns[0], id: 't2', attachments: [name], requiredOutputIds: [], instruction: 'Use the later clarification.' });
  }
  f.save(); publishInputs(f);
  f.record = provider.loadCase(provider.loadCorpus({ corpus: 'research-300', root: f.root }), id);
  f.editionDir = path.join(f.root, 'corpora/research-300/public-inputs');
  f.manifestFile = path.join(f.editionDir, 'manifest.json');
  f.bundleFile = path.join(f.editionDir, id, 'input.json');
  f.rehash = () => { const manifest = json(f.manifestFile); manifest.cases.find(row => row.id === id).sha256 = provider.sha256(fs.readFileSync(f.bundleFile)); save(f.manifestFile, manifest); };
  return f;
}
const revised = (t, options = {}) => canonicalFixture(t, { ...options, id: 'MM-001' });
const visualFixture = t => revised(t, { twoTurns: true });

test('canonical delivery binds current public bytes and keeps original source and response identities', t => {
  const f = canonicalFixture(t), before = buildSourceBinding(f.record).sourceHash;
  const original = provider.getFrozenPublicTurnInput(f.record, 0), input = provider.getPublicTurnInput(f.record, 0);
  assert.equal(input.inputEdition, 'current');
  assert.match(input.publicInputSha256, /^[a-f0-9]{64}$/);
  assert.equal(input.inputBinding.baseSourceHash, before);
  assert.equal(input.inputBinding.caseId, f.record.id);
  assert.deepEqual(input.responseContract, original.responseContract);
  assert.deepEqual(input.attachments.map(a => a.name), ['input.md']);
  for (const a of input.attachments) assert.equal(a.sha256, provider.sha256(fs.readFileSync(a.path)));
  assert.equal(buildSourceBinding(f.record).sourceHash, before);
  assert.equal(input.inputBinding.authorAuditSha256, provider.sha256(fs.readFileSync(path.join(path.dirname(f.bundleFile), 'author-audit.json'))));
  for (const source of input.inputBinding.validatorSources) assert.equal(source.sha256, provider.sha256(fs.readFileSync(path.join(repo, source.path))));
});

test('missing or broken canonical input cannot fall back to original or historical inputs', t => {
  const f = fixture(t), record = provider.loadCase(provider.loadCorpus({ corpus: 'research-300', root: f.root }), f.contract.id);
  assert.throws(() => provider.getPublicTurnInput(record, 0), /ENOENT|directory|input/i);
  const root = path.join(f.root, 'corpora/research-300/public-inputs');
  fs.mkdirSync(path.join(root, 'visual-v2'), { recursive: true });
  assert.throws(() => provider.getPublicTurnInput(record, 0), /ENOENT|manifest/i);
  assert.equal(typeof provider.getFrozenPublicTurnInput(record, 0).instruction, 'string');
});

test('edition selectors are rejected even for current or legacy input', t => {
  const f = canonicalFixture(t);
  for (const edition of ['current', 'frozen', 'clean-v3', 'visual-v2', 'concise-v1', '../current', undefined, null, {}])
    assert.throws(() => provider.getPublicTurnInput(f.record, 0, { edition }), /selection/i);
  const legacy = { id: 'legacy', corpus: 'legacy-150', root: f.root, contract: { message: 'Legacy task', attachments: [] } };
  assert.equal(provider.getPublicTurnInput(legacy, 0).instruction, 'Legacy task');
  assert.throws(() => provider.getPublicTurnInput(legacy, 0, { edition: 'frozen' }), /selection/i);
});

test('canonical root symlink is rejected', t => {
  const f = canonicalFixture(t), moved = f.editionDir + '-moved';
  fs.renameSync(f.editionDir, moved); fs.symlinkSync(moved, f.editionDir, 'dir');
  assert.throws(() => provider.getPublicTurnInput(f.record, 0), /symlink/i);
});

for (const mutation of ['bundle', 'attachment', 'manifest-source', 'duplicate', 'missing-case', 'missing-turn', 'extra-field', 'edition-tag']) test(`canonical inputs reject ${mutation} tampering`, t => {
  const f = canonicalFixture(t), manifest = json(f.manifestFile), bundle = json(f.bundleFile);
  if (mutation === 'bundle') fs.appendFileSync(f.bundleFile, ' ');
  if (mutation === 'attachment') fs.appendFileSync(path.join(path.dirname(f.bundleFile), bundle.turns[0].attachments[0].path), '\nTampered stiffness = 0\n');
  if (mutation === 'manifest-source') { manifest.cases[0].baseSourceHash = '0'.repeat(64); save(f.manifestFile, manifest); }
  if (mutation === 'duplicate') { manifest.cases.push(manifest.cases[0]); save(f.manifestFile, manifest); }
  if (mutation === 'missing-case') { manifest.cases = []; save(f.manifestFile, manifest); }
  if (mutation === 'missing-turn') { bundle.turns = []; save(f.bundleFile, bundle); f.rehash(); }
  if (mutation === 'extra-field') { bundle.responseContract = {}; save(f.bundleFile, bundle); f.rehash(); }
  if (mutation === 'edition-tag') { bundle.edition = 'visual-v2'; save(f.bundleFile, bundle); f.rehash(); }
  assert.throws(() => provider.getPublicTurnInput(f.record, 0), /edition|binding|hash|duplicate|turn|field|coverage/i);
});

for (const mutation of ['instruction', 'material', 'audit-change', 'extra-file', 'escape', 'symlink', 'hidden-reference', 'private-copy']) test(`successful checks cannot approve rehashed ${mutation}`, t => {
  const f = canonicalFixture(t); provider.getPublicTurnInput(f.record, 0);
  const bundle = json(f.bundleFile), attachment = bundle.turns[0].attachments[0], folder = path.dirname(f.bundleFile), file = path.join(folder, attachment.path);
  if (mutation === 'instruction') bundle.turns[0].instruction = 'Analyze a 100 m cantilever with self weight enabled.';
  if (mutation === 'material') fs.writeFileSync(file, fs.readFileSync(file, 'utf8').replace('200000', '1'));
  if (mutation === 'audit-change') fs.appendFileSync(path.join(folder, 'author-audit.json'), ' ');
  if (mutation === 'extra-file') fs.writeFileSync(path.join(folder, 'unexpected.txt'), 'undeclared');
  if (mutation === 'escape') attachment.path = '../STD-001/input.md';
  if (mutation === 'symlink') { fs.unlinkSync(file); fs.symlinkSync(path.join(f.caseDir, 'model-state-1.json'), file); }
  if (mutation === 'hidden-reference') fs.writeFileSync(file, 'Read model-state-1.json for the answer.');
  if (mutation === 'private-copy') fs.copyFileSync(path.join(f.caseDir, 'model-state-1.json'), file);
  attachment.sha256 = provider.sha256(fs.readFileSync(file)); save(f.bundleFile, bundle); f.rehash();
  assert.throws(() => provider.getPublicTurnInput(f.record, 0), /correspond|deterministic|unsafe|symlink|hidden|private|edition/i);
});

test('MM delivers one raster per turn and a rebound future drawing cannot be released early', t => {
  const f = visualFixture(t), first = provider.getPublicTurnInput(f.record, 0), second = provider.getPublicTurnInput(f.record, 1);
  assert.deepEqual(first.attachments.map(a => a.name), ['drawing.png']);
  assert.deepEqual(second.attachments.map(a => a.name), ['drawing-t2.png']);
  const bundle = json(f.bundleFile); [bundle.turns[0].attachments, bundle.turns[1].attachments] = [bundle.turns[1].attachments, bundle.turns[0].attachments];
  save(f.bundleFile, bundle); f.rehash();
  assert.throws(() => provider.getPublicTurnInput(f.record, 0), /correspond|deterministic/i);
});

test('MM authoring data and raster bytes are checked after previous success', t => {
  const f = visualFixture(t); provider.getPublicTurnInput(f.record, 0);
  fs.appendFileSync(path.join(path.dirname(f.bundleFile), 'authoring/drawing.svg'), ' ');
  assert.throws(() => provider.getPublicTurnInput(f.record, 0), /correspond|deterministic/i);
});

test('runner rejects missing and stale edition binding before evaluating revised candidates', async t => {
  const f = revised(t), input = provider.getPublicTurnInput(f.record, 0);
  const run = { caseId: 'MM-001', runId: 'candidate', turns: [{ turnId: 't1', state: { messages: [] } }] };
  const artifacts = path.join(f.root, 'artifacts.json');
  for (const binding of [undefined, { ...input.inputBinding, publicInputSha256: '0'.repeat(64) }]) {
    run.inputBinding = binding;
    save(artifacts, { schemaVersion: 1, corpus: 'research-300', runs: [run] });
    const report = await runResearch300(['--root', f.root, '--scenario', 'MM-001', '--execution', 'evaluate-artifacts', '--artifacts', artifacts], {
      stdout: () => {}, evaluateCase: () => { assert.fail('A stale input must not reach the evaluator'); },
    });
    assert.equal(report.status, 'artifact_error');
    assert.match(report.cases[0].error.code, /^artifact_input_binding_/);
  }
  run.inputBinding = input.inputBinding;
  save(artifacts, { schemaVersion: 1, corpus: 'research-300', runs: [run] });
  const report = await runResearch300(['--root', f.root, '--scenario', 'MM-001', '--execution', 'evaluate-artifacts', '--artifacts', artifacts], {
    stdout: () => {}, evaluateCase: () => ({ status: 'unknown', allPassed: false }),
  });
  assert.equal(report.status, 'unknown');
  assert.deepEqual(report.cases[0].inputBinding, input.inputBinding);
  delete run.inputBinding;
  await assert.rejects(() => evaluateCandidateCase({ caseRecord: f.record, run, artifactRoot: f.root }), { code: 'artifact_input_binding_missing' });
});

test('runner rejects visual candidates with stale checker dependency or renderer audit binding', async t => {
  const f = visualFixture(t), input = provider.getPublicTurnInput(f.record, 0);
  const artifacts = path.join(f.root, 'artifacts.json');
  for (const field of ['validatorSources', 'authorAuditSha256']) {
    const inputBinding = structuredClone(input.inputBinding);
    if (field === 'validatorSources') inputBinding.validatorSources[1].sha256 = '0'.repeat(64);
    else inputBinding.authorAuditSha256 = '0'.repeat(64);
    save(artifacts, { schemaVersion: 1, corpus: 'research-300', runs: [{ caseId: 'MM-001', runId: 'candidate', inputBinding, turns: [{ turnId: 't1', state: { messages: [] } }, { turnId: 't2', state: { messages: [] } }] }] });
    const report = await runResearch300(['--root', f.root, '--scenario', 'MM-001', '--execution', 'evaluate-artifacts', '--artifacts', artifacts], {
      stdout: () => {}, evaluateCase: () => assert.fail('Stale visual inputs must not reach evaluation'),
    });
    assert.equal(report.status, 'artifact_error');
    assert.equal(report.cases[0].error.code, 'artifact_input_binding_stale');
  }
});

test('revised independent assessments bind the input edition as well as response and frozen source', async t => {
  const f = revised(t, { clarify: true }), input = provider.getPublicTurnInput(f.record, 0);
  const messages = [{ role: 'assistant', content: 'Which support should I use?' }];
  const run = { caseId: 'MM-001', runId: 'candidate', inputBinding: input.inputBinding, turns: [{ turnId: 't1', state: { messages } }] };
  const assessment = { caseId: 'MM-001', turnId: 't1', outputId: 'clarification', state: null,
    sourceHash: buildSourceBinding(f.record).sourceHash, currentResponseSha256: currentResponseSha256(messages, 0),
    activitySha256: currentActivitySha256(messages, 0), pass: true, reason: 'Asked the missing input.' };
  const args = { caseRecord: f.record, run, artifactRoot: f.root, assessments: [assessment] };
  await assert.rejects(() => evaluateCandidateCase(args), { code: 'reference_assessment_input_binding' });
  assessment.inputBinding = input.inputBinding;
  const result = await evaluateCandidateCase(args, { evaluateTurn: ({ evidence }) => {
    assert.deepEqual(evidence.inputBinding, input.inputBinding);
    assert.deepEqual(evidence.interactionEvidence[0].inputBinding, input.inputBinding);
    return { status: 'unknown', allPassed: false };
  } });
  assert.deepEqual(result.inputBinding, input.inputBinding);
});

test('async providers enforce both candidate and independent assessment edition bindings', async t => {
  const f = revised(t, { clarify: true }), input = provider.getPublicTurnInput(f.record, 0);
  const messages = [{ role: 'assistant', content: 'Which support should I use?' }];
  const run = { caseId: 'MM-001', runId: 'candidate', turns: [{ turnId: 't1', state: { messages } }] };
  const assessment = { caseId: 'MM-001', turnId: 't1', outputId: 'clarification', state: null,
    sourceHash: buildSourceBinding(f.record).sourceHash, currentResponseSha256: currentResponseSha256(messages, 0),
    activitySha256: currentActivitySha256(messages, 0),
    pass: true, reason: 'Asked the missing input.' };
  const args = { caseRecord: f.record, run, artifactRoot: f.root, assessments: [assessment] };
  const dependencies = {
    provider: { ...provider, getPublicTurnInput: async (...args) => provider.getPublicTurnInput(...args) },
    evaluateTurn: () => assert.fail('Unbound async-provider input must not reach evaluation'),
  };
  await assert.rejects(() => evaluateCandidateCase(args, dependencies), { code: 'artifact_input_binding_missing' });
  run.inputBinding = { ...input.inputBinding, publicInputSha256: '0'.repeat(64) };
  await assert.rejects(() => evaluateCandidateCase(args, dependencies), { code: 'artifact_input_binding_stale' });
  run.inputBinding = input.inputBinding;
  await assert.rejects(() => evaluateCandidateCase(args, dependencies), { code: 'reference_assessment_input_binding' });
  assessment.inputBinding = input.inputBinding;
  const result = await evaluateCandidateCase(args, { ...dependencies, evaluateTurn: ({ evidence }) => {
    assert.deepEqual(evidence.inputBinding, input.inputBinding);
    assert.deepEqual(evidence.interactionEvidence[0].inputBinding, input.inputBinding);
    return { status: 'unknown', allPassed: false };
  } });
  assert.deepEqual(result.inputBinding, input.inputBinding);
});
