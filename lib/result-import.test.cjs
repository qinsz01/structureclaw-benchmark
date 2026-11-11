'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { fixture, publishInputs } = require('./research300-test-fixtures.cjs');
const { importResult, prepareEvaluation, caseContext, detectFormat } = require('./result-import.cjs');
const { modelFingerprint } = require('./analysis-evidence.cjs');
const { runResearch300 } = require('../scripts/run-research300.cjs');
const { createHash } = require('node:crypto');
const { spawnSync } = require('node:child_process');
const { verifyAssessmentLocation, parse } = require('../scripts/evaluate-results.cjs');

function setup(t) {
  const f = fixture(t); publishInputs(f);
  f.input = path.join(f.root, 'answer.json'); f.outputRoot = path.join(f.root, 'imported');
  f.options = { root: f.root, caseId: 'STD-001', input: f.input, outputRoot: f.outputRoot };
  return f;
}
function save(file, value) { fs.writeFileSync(file, typeof value === 'string' ? value : JSON.stringify(value)); }
function state(f) {
  return { model: f.model, messages: [{ role: 'assistant', content: 'Actual delivered answer' }], analysisResult: {
    runId: 'run-one', modelSnapshot: f.model, selectedResultKey: 'case:D', results: { 'case:D': {
      selection: { kind: 'case', id: 'D' }, meta: { runId: 'run-one', modelHash: modelFingerprint(f.model), engineId: 'OpenSees' },
      data: { status: 'success', execution: { executed: true, solver: 'OpenSees', solverVersion: 'fixture', analysisReturnCode: 0 } },
    } },
  } };
}
test('auto detects capture, native snapshots, SSE and Codex streams without filename assumptions', () => {
  assert.equal(detectFormat('{"corpus":"research-300","runs":[]}'), 'capture');
  assert.equal(detectFormat('{"snapshots":{}}'), 'structureclaw');
  assert.equal(detectFormat('data: {"type":"done"}\n\n'), 'structureclaw');
  assert.equal(detectFormat('{"type":"thread.started"}\n{"type":"turn.completed"}'), 'codex');
  assert.equal(detectFormat('[{"type":"artifact_payload_sync","artifact":"model"}]'), 'structureclaw');
  assert.equal(detectFormat('{"type":"summary_replace","summaryText":"Answer"}\n{"type":"done"}'), 'structureclaw');
});
test('prepare exports only public inputs and saves binding separately', t => {
  const f = setup(t), output = path.join(f.root, 'prepared');
  const result = prepareEvaluation({ root: f.root, caseId: 'STD-001', output });
  const task = JSON.parse(fs.readFileSync(path.join(result.agentInput, 'cases/STD-001/task.json')));
  assert.equal(task.caseId, 'STD-001');
  assert.doesNotMatch(JSON.stringify(task), /sourceHash|inputBinding|reference|tolerance/);
  assert.deepEqual(JSON.parse(fs.readFileSync(result.context)), caseContext('STD-001', f.root).context);
  assert.equal(result.currentTurn, 't1');
  assert.deepEqual(result.releasedTurns, ['t1']);
  assert.throws(() => prepareEvaluation({ root: f.root, caseId: 'STD-001', output }), /already exists/);
});

function releaseFixture(t) {
  const f = fixture(t, 'INT-001');
  const ids = f.contract.requiredOutputs.map(output => output.id);
  f.contract.turns[0].requiredOutputIds = ids;
  for (const [number, word] of [[2, 'TWO'], [3, 'THREE']]) {
    const attachment = `release-${number}.txt`;
    f.contract.attachments.push(attachment);
    f.write(attachment, `Observation note: ROUND_${word}_ATTACHMENT.\n`);
    f.contract.turns.push({ id: `t${number}`, state: 1, expectation: 'query',
      instruction: `Report the same response using ${attachment}. ROUND_${word}_INSTRUCTION.`,
      attachments: [attachment], requiredOutputIds: ids, unresolvedFields: [], expectedQuestions: [], preservedFields: ['/'] });
  }
  f.save(); publishInputs(f);
  return f;
}
function releasedPacket(result, caseId = 'INT-001') {
  const files = require('./corpus-provider.cjs').listFiles(result.agentInput).sort();
  return { files,
    text: files.map(file => fs.readFileSync(path.join(result.agentInput, file), 'utf8')).join('\n'),
    task: JSON.parse(fs.readFileSync(path.join(result.agentInput, 'cases', caseId, 'task.json'))),
    index: JSON.parse(fs.readFileSync(path.join(result.agentInput, 'index.json'))),
    context: JSON.parse(fs.readFileSync(result.context)),
  };
}
test('prepare releases only current and past public instructions and files while retaining complete private capture context', t => {
  const f = releaseFixture(t);
  const first = prepareEvaluation({ root: f.root, caseId: 'INT-001', output: path.join(f.root, 'packet-one') });
  const one = releasedPacket(first);
  assert.deepEqual(one.task.turns.map(turn => turn.id), ['t1']);
  assert.equal(one.index.cases[0].turns, 1);
  assert.doesNotMatch(one.text, /ROUND_TWO|ROUND_THREE|input-t2|input-t3|release-2|release-3|inputBinding|sourceHash/);
  assert.deepEqual(one.files, ['README.md', 'cases/INT-001/input.md', 'cases/INT-001/task.json', 'index.json']);
  const second = prepareEvaluation({ root: f.root, caseId: 'INT-001', turn: 't2', output: path.join(f.root, 'packet-two') });
  const two = releasedPacket(second);
  assert.equal(second.currentTurn, 't2');
  assert.deepEqual(second.releasedTurns, ['t1', 't2']);
  assert.deepEqual(two.task.turns, [...one.task.turns, two.task.turns[1]]);
  assert.deepEqual(two.task.turns.map(turn => turn.id), ['t1', 't2']);
  assert.equal(two.index.cases[0].turns, 2);
  assert.match(two.text, /ROUND_TWO_INSTRUCTION/);
  assert.match(two.text, /ROUND_TWO_ATTACHMENT/);
  assert.doesNotMatch(two.text, /ROUND_THREE|input-t3|release-3|inputBinding|sourceHash/);
  assert.deepEqual(two.files, ['README.md', 'cases/INT-001/input-t2.md', 'cases/INT-001/input.md', 'cases/INT-001/task.json', 'index.json']);
  assert.deepEqual(one.context, two.context);
  assert.deepEqual(one.context.turns.map(turn => turn.turnId), ['t1', 't2', 't3']);
  assert.deepEqual(one.context.inputBinding, caseContext('INT-001', f.root).context.inputBinding);
  assert.throws(() => prepareEvaluation({ root: f.root, caseId: 'INT-001', turn: 't2', output: first.output }), /already exists/);
  assert.deepEqual(releasedPacket(first).task, one.task);
  const input = path.join(f.root, 'complete-capture.json');
  const turnIds = ['t1', 't2', 't3'];
  const messages = turnIds.map(turnId => ({ role: 'assistant', content: `Recorded answer for ${turnId}` }));
  save(input, { turns: turnIds.map((turnId, index) => ({ turnId,
    state: { messages: messages.slice(0, index + 1) } })) });
  const imported = importResult({ root: f.root, caseId: 'INT-001', input, context: first.context,
    format: 'structureclaw', outputRoot: path.join(f.root, 'complete-import') });
  assert.equal(imported.provenance.binding, 'prepared-context');
  assert.deepEqual(JSON.parse(fs.readFileSync(imported.artifactsPath)).runs[0].turns.map(turn => turn.turnId), ['t1', 't2', 't3']);
});
test('prepare rejects unknown turn IDs without publishing a directory', t => {
  const f = releaseFixture(t);
  for (const [index, turn] of ['t0', 't4', '2', '', null, 2].entries()) {
    const output = path.join(f.root, `invalid-turn-${index}`);
    assert.throws(() => prepareEvaluation({ root: f.root, caseId: 'INT-001', turn, output }), /exact public turn ID/);
    assert.equal(fs.existsSync(output), false);
  }
});
test('failed context publication removes only the newly owned preparation directory', t => {
  const f = setup(t), output = path.join(f.root, 'failed-packet');
  const originalWrite = fs.writeFileSync;
  t.mock.method(fs, 'writeFileSync', (file, ...args) => {
    if (file === path.join(output, 'capture-context.json')) throw new Error('Synthetic context write failure');
    return originalWrite(file, ...args);
  });
  assert.throws(() => prepareEvaluation({ root: f.root, caseId: 'STD-001', output }), /Synthetic context write failure/);
  assert.equal(fs.existsSync(output), false);
  assert.ok(fs.existsSync(path.join(f.caseDir, 'contract.json')));
});
test('actual prepare CLI accepts an exact released turn and evaluation rejects the prepare-only option', t => {
  const f = releaseFixture(t), output = path.join(f.root, 'cli-packet');
  const cli = spawnSync(process.execPath, [path.resolve(__dirname, '../scripts/evaluate-results.cjs'), '--prepare',
    '--root', f.root, '--case', 'INT-001', '--turn', 't2', '--output', output], { encoding: 'utf8', timeout: 60000 });
  assert.equal(cli.status, 0, cli.stderr + cli.stdout);
  const result = JSON.parse(cli.stdout), packet = releasedPacket(result);
  assert.equal(result.currentTurn, 't2');
  assert.deepEqual(result.releasedTurns, ['t1', 't2']);
  assert.doesNotMatch(packet.text, /ROUND_THREE|input-t3|release-3/);
  assert.throws(() => parse(['--input', 'answer.json', '--output', 'report.json', '--turn', 't2']), /only supported with --prepare/);
});
test('raw text records declared inputs and preserves missing numerical evidence', t => {
  const f = setup(t); save(f.input, 'The actual answer has no solver data.');
  const result = importResult(f.options), run = JSON.parse(fs.readFileSync(result.artifactsPath)).runs[0];
  assert.equal(result.provenance.binding, 'operator-declared-current-input');
  assert.equal(run.turns[0].turnId, 't1');
  assert.equal(run.turns[0].state.model, undefined);
  assert.match(run.turns[0].state.messages.at(-1).content, /actual answer/);
  assert.ok(result.provenance.warnings.length);
});
test('prepared context rejects stale digest before creating output', t => {
  const f = setup(t); save(f.input, 'Answer');
  const contextFile = path.join(f.root, 'context.json'), context = caseContext('STD-001', f.root).context;
  save(contextFile, context);
  assert.equal(importResult({ ...f.options, context: contextFile }).provenance.binding, 'prepared-context');
  context.sourceHash = '0'.repeat(64); save(contextFile, context);
  const outputRoot = path.join(f.root, 'bad-import');
  assert.throws(() => importResult({ ...f.options, outputRoot, context: contextFile }), /stale/);
  assert.equal(fs.existsSync(outputRoot), false);
});
test('native import adds benchmark context only, preserving actual model, values and execution', t => {
  const f = setup(t), original = state(f); save(f.input, original);
  const result = importResult({ ...f.options, format: 'structureclaw' });
  const turn = JSON.parse(fs.readFileSync(result.artifactsPath)).runs[0].turns[0];
  assert.deepEqual(turn.state.model, original.model);
  assert.deepEqual(turn.state.analysisResult.results['case:D'].data, original.analysisResult.results['case:D'].data);
  assert.equal(turn.state.analysisResult.results['case:D'].meta.state, 1);
  assert.equal(turn.state.analysisResult.results['case:D'].meta.sourceHash, caseContext('STD-001', f.root).context.sourceHash);
  assert.deepEqual(turn.artifacts['run-one'].selections, { 'case:D': {} });
  assert.match(result.provenance.warnings.join('\n'), /receipt/);
});
test('conflicting candidate engine/model/source/state declarations are never repaired by importer', t => {
  const f = setup(t), original = state(f);
  Object.assign(original.analysisResult.results['case:D'].meta, { state: 9, sourceHash: 'bad', engineId: 'YJK', modelHash: 'bad' });
  save(f.input, original);
  const result = importResult({ ...f.options, format: 'structureclaw' });
  const actual = JSON.parse(fs.readFileSync(result.artifactsPath)).runs[0].turns[0].state;
  assert.deepEqual(actual.analysisResult.results['case:D'].meta, original.analysisResult.results['case:D'].meta);
});
test('existing capture artifacts are copied exactly and path escapes are rejected', t => {
  const f = setup(t);
  fs.mkdirSync(path.join(f.root, 'evidence')); save(path.join(f.root, 'evidence/native.json'), 'native bytes\n');
  const envelope = { schemaVersion: 1, corpus: 'research-300', runs: [{ caseId: 'STD-001', runId: 'r',
    inputBinding: caseContext('STD-001', f.root).context.inputBinding,
    turns: [{ turnId: 't1', state: {}, artifacts: { r: { normalizedInput: 'evidence/native.json', solverResponse: 'evidence/native.json' } } }] }] };
  save(f.input, envelope);
  const result = importResult(f.options), saved = JSON.parse(fs.readFileSync(result.artifactsPath));
  const relative = saved.runs[0].turns[0].artifacts.r.normalizedInput;
  assert.equal(fs.readFileSync(path.join(result.artifactRoot, relative), 'utf8'), 'native bytes\n');
  envelope.runs[0].turns[0].artifacts.r.normalizedInput = '../outside'; save(f.input, envelope);
  assert.throws(() => importResult({ ...f.options, outputRoot: path.join(f.root, 'escape') }), /Unsafe evidence path/);
});
test('output and artifact symlinks cannot cross evidence or source boundaries', t => {
  const f = setup(t); save(f.input, 'Answer');
  const link = path.join(f.root, 'link'); fs.symlinkSync(path.join(f.root, 'corpora'), link);
  assert.throws(() => importResult({ ...f.options, outputRoot: path.join(link, 'new') }), /Symlink/);
  assert.throws(() => importResult({ ...f.options, outputRoot: path.join(f.root, 'corpora/new') }), /source directories/);
});
test('actual text-only CLI import reaches evaluator without pretending to have a model', async t => {
  const f = setup(t); save(f.input, 'No analysis was performed.');
  const imported = importResult(f.options);
  const report = await runResearch300(['--root', f.root, '--case', 'STD-001', '--execution', 'evaluate-artifacts',
    '--artifacts', imported.artifactsPath, '--artifact-root', imported.artifactRoot], { stdout() {} });
  // This intentionally unqualified fixture has no native reference; it remains pending.
  assert.notEqual(report.status, 'passed');
  assert.equal(report.cases[0].runId.startsWith('import-'), true);
});

test('explicit null solver context is preserved instead of being replaced by current source/state', t => {
  const f = setup(t), original = state(f);
  original.analysisResult.results['case:D'].meta.state = null;
  original.analysisResult.results['case:D'].meta.sourceHash = null;
  save(f.input, original);
  const imported = importResult({ ...f.options, format: 'structureclaw' });
  const meta = JSON.parse(fs.readFileSync(imported.artifactsPath)).runs[0].turns[0].state.analysisResult.results['case:D'].meta;
  assert.equal(meta.state, null); assert.equal(meta.sourceHash, null);
});

test('explicit raw and sidecar identity declarations cannot be relabeled as current inputs', t => {
  const f = setup(t), context = caseContext('STD-001', f.root).context;
  for (const [index, declaration] of [{ caseId: 'STD-002' }, { inputBinding: null }, { sourceHash: '0'.repeat(64) },
    { state: { sourceHash: null } }, { turns: [{ state: { inputBinding: { ...context.inputBinding, publicInputSha256: '0'.repeat(64) } } }] }].entries()) {
    save(f.input, declaration);
    const outputRoot = path.join(f.root, `invalid-identity-${index}`);
    assert.throws(() => importResult({ ...f.options, outputRoot }), /explicitly declares a different/);
    assert.equal(fs.existsSync(outputRoot), false);
  }
  const sidecarFile = path.join(f.root, 'sidecar.json');
  save(f.input, 'Actual answer'); save(sidecarFile, { ...state(f), caseId: 'STD-002' });
  assert.throws(() => importResult({ ...f.options, state: sidecarFile }), /explicitly declares a different caseId/);
  for (const [index, answer] of ['```json\n{"caseId":"STD-002","state":{}}\n```',
    [{ type: 'turn.started' }, { type: 'item.completed', item: { id: 'answer', type: 'agent_message', text: '{"caseId":"STD-002","state":{}}' } }, { type: 'turn.completed' }].map(event => JSON.stringify(event)).join('\n')].entries()) {
    save(f.input, answer);
    assert.throws(() => importResult({ ...f.options, outputRoot: path.join(f.root, `structured-identity-${index}`) }), /explicitly declares a different caseId/);
  }
});

function multiTurnSetup(t) {
  const f = fixture(t, 'INT-001');
  const ids = f.contract.requiredOutputs.map(output => output.id);
  f.contract.turns[0].requiredOutputIds = ids;
  f.contract.turns.push({ id: 't2', state: 1, expectation: 'query', instruction: 'Report the same result again.',
    attachments: [], requiredOutputIds: ids, unresolvedFields: [], expectedQuestions: [] });
  f.save(); publishInputs(f);
  f.input = path.join(f.root, 'answer.json'); f.outputRoot = path.join(f.root, 'imported');
  f.options = { root: f.root, caseId: 'INT-001', input: f.input, outputRoot: f.outputRoot, format: 'structureclaw' };
  return f;
}

test('query reuse retains the first run context and rejects changed bytes, selections, model or metadata', t => {
  const f = multiTurnSetup(t), first = state(f), second = structuredClone(first);
  second.messages.push({ role: 'assistant', content: 'Current query answer' });
  const source = { turns: [{ turnId: 't1', state: first }, { turnId: 't2', state: second }] };
  save(f.input, source);
  const imported = importResult(f.options), turns = JSON.parse(fs.readFileSync(imported.artifactsPath)).runs[0].turns;
  assert.deepEqual(turns[0].artifacts, turns[1].artifacts);
  assert.deepEqual(turns[0].state.analysisResult.results['case:D'], turns[1].state.analysisResult.results['case:D']);
  for (const [index, change] of [
    value => { value.analysisResult.results['case:D'].data.extraNumber = 99; },
    value => { value.model.nodes[0].x += 1; },
    value => { value.analysisResult.results['case:D'].meta.sourceHash = null; },
    value => { value.analysisResult.results['case:L'] = { ...structuredClone(value.analysisResult.results['case:D']), selection: { kind: 'case', id: 'L' } }; },
  ].entries()) {
    const changed = structuredClone(source); change(changed.turns[1].state); save(f.input, changed);
    const outputRoot = path.join(f.root, `changed-run-${index}`);
    assert.throws(() => importResult({ ...f.options, outputRoot }), /Immutable run ID/);
    assert.equal(fs.existsSync(outputRoot), false, 'Rejected imports clean their own partial output');
  }
});

test('explicit immutable capture files are reused by a later query instead of reconstructing new artifacts', t => {
  const f = multiTurnSetup(t), first = state(f), later = structuredClone(first);
  save(path.join(f.root, 'native-input.json'), { model: f.model, selection: { kind: 'case', id: 'D' } });
  save(path.join(f.root, 'native-result.json'), first.analysisResult);
  const artifacts = { 'run-one': { normalizedInput: 'native-input.json', solverResponse: 'native-result.json' } };
  save(f.input, { turns: [{ turnId: 't1', state: first, artifacts }, { turnId: 't2', state: later }] });
  const imported = importResult(f.options), turns = JSON.parse(fs.readFileSync(imported.artifactsPath)).runs[0].turns;
  assert.deepEqual(turns[0].artifacts, turns[1].artifacts);
  assert.equal(imported.provenance.sources.filter(source => source.role === 'artifact').length, 2);
  assert.equal(imported.provenance.evidence.length, 2);
});

test('input, context and physical sidecar identities retain exact supplied byte digests', t => {
  const f = setup(t), contextFile = path.join(f.root, 'context.json'), stateFile = path.join(f.root, 'state.json');
  save(f.input, 'Actual answer\n'); save(contextFile, caseContext('STD-001', f.root).context); save(stateFile, state(f));
  const imported = importResult({ ...f.options, context: contextFile, state: stateFile });
  for (const [role, file] of [['input', f.input], ['context', contextFile], ['state', stateFile]]) {
    const source = imported.provenance.sources.find(item => item.role === role);
    assert.equal(source.path, file);
    assert.equal(source.sha256, createHash('sha256').update(fs.readFileSync(file)).digest('hex'));
    assert.equal(source.bytes, fs.statSync(file).size);
  }
  assert.deepEqual(JSON.parse(fs.readFileSync(path.join(imported.artifactRoot, 'import.json'))), imported.provenance);
});

test('capture imports infer one selected case and retain all explicitly captured case IDs', t => {
  const f = setup(t);
  const envelope = { schemaVersion: 1, corpus: 'research-300', runs: [{ caseId: 'STD-001', runId: 'one', turns: [] }] };
  save(f.input, envelope);
  const options = { ...f.options }; delete options.caseId;
  const one = importResult(options);
  assert.equal(one.caseId, 'STD-001'); assert.deepEqual(one.caseIds, ['STD-001']);
  envelope.runs.push({ caseId: 'INT-001', runId: 'two', turns: [] }); save(f.input, envelope);
  const multiple = importResult({ ...options, outputRoot: path.join(f.root, 'multiple') });
  assert.equal(multiple.caseId, undefined); assert.deepEqual(multiple.caseIds, ['STD-001', 'INT-001']);
});

test('semantic review remains independent of original evidence and capture sources after copying', t => {
  const f = setup(t), candidate = path.join(f.root, 'candidate'), reviews = path.join(f.root, 'reviews');
  fs.mkdirSync(candidate); fs.mkdirSync(reviews);
  const input = path.join(candidate, 'answer.json'), stateFile = path.join(reviews, 'state.json');
  save(input, '{}'); save(stateFile, '{}');
  const internal = path.join(candidate, 'assessment.json'); save(internal, '{}');
  assert.throws(() => verifyAssessmentLocation({ input, assessments: internal }), /outside original candidate evidence/);
  assert.throws(() => verifyAssessmentLocation({ input, assessments: stateFile, state: stateFile }), /candidate or capture context source/);
  const alias = path.join(reviews, 'hardlink.json'); fs.linkSync(stateFile, alias);
  assert.throws(() => verifyAssessmentLocation({ input, assessments: alias, state: stateFile }), /candidate or capture context source/);
  const independent = path.join(reviews, 'assessment.json'); save(independent, '{}');
  assert.doesNotThrow(() => verifyAssessmentLocation({ input, assessments: independent }));
});

// Synthetic native receipts exercise byte/context binding; they make no claim
// to represent a real engineering reference or a successful numerical score.
function nativeCapture(f) {
  const captured = state(f), captureRoot = path.join(f.root, 'native-capture');
  fs.mkdirSync(captureRoot);
  const payload = { displacements: { m: { uz: -0.001 } }, reactions: {}, forces: {},
    solverMesh: { nodes: [], elements: [] }, effectiveLoads: [], segmentResults: { forces: {}, displacements: {} } };
  const receipt = { hashFormat: 'sha256:python-json-sort-keys-utf8-compact-v1', solverResponseKeys: Object.keys(payload) };
  const artifacts = {};
  for (const [name, value] of Object.entries({ normalizedInput: f.model, settings: { parameters: { loadCaseIds: ['D'] } }, solverResponse: payload })) {
    artifacts[name] = `${name}.json`; save(path.join(captureRoot, artifacts[name]), value);
    receipt[name + 'Sha256'] = createHash('sha256').update(fs.readFileSync(path.join(captureRoot, artifacts[name]))).digest('hex');
  }
  const data = captured.analysisResult.results['case:D'].data;
  Object.assign(data, payload); data.execution.artifacts = receipt;
  save(path.join(captureRoot, 'request.json'), { input: { model: f.model } });
  save(path.join(captureRoot, 'capture.json'), { kind: 'structureclaw-python-worker-capture', exitCode: 0,
    requestSha256: createHash('sha256').update(fs.readFileSync(path.join(captureRoot, 'request.json'))).digest('hex'),
    receipts: [{ artifacts, receipt }] });
  return { captured, captureRoot };
}

test('completed native recovery removes only its per-turn Codex missing-files warning and records original sources', t => {
  const f = setup(t), { captured, captureRoot } = nativeCapture(f), stateFile = path.join(f.root, 'sidecar.json');
  save(stateFile, captured); save(f.input, '{"type":"turn.started"}\n{"type":"turn.completed"}\n');
  const imported = importResult({ ...f.options, state: stateFile, captureRoot });
  assert.doesNotMatch(imported.provenance.warnings.join('\n'), /raw execution artifacts are missing/);
  assert.match(imported.provenance.warnings.join('\n'), /no completed current assistant answer/);
  assert.equal(imported.provenance.sources.filter(source => source.role.startsWith('structureclaw-native-')).length, 3);
  assert.ok(imported.provenance.implementation.some(item => item.path === 'lib/result-import.cjs' && /^[a-f0-9]{64}$/.test(item.sha256)));
  const manifestFile = path.join(captureRoot, 'capture.json'), manifest = JSON.parse(fs.readFileSync(manifestFile));
  delete manifest.receipts[0].artifacts.settings; save(manifestFile, manifest);
  const partial = importResult({ ...f.options, outputRoot: path.join(f.root, 'partial'), state: stateFile, captureRoot });
  assert.match(partial.provenance.warnings.join('\n'), /raw execution artifacts are missing/);
  assert.match(partial.provenance.warnings.join('\n'), /settings canonical bytes could not be reproduced/);
});

test('actual CLI rejects host numerical tampering while original native receipts and bytes remain unchanged', t => {
  const f = setup(t), { captured, captureRoot } = nativeCapture(f);
  const originalReceipt = structuredClone(captured.analysisResult.results['case:D'].data.execution.artifacts);
  captured.analysisResult.results['case:D'].data.displacements.m.uz = -99;
  save(f.input, captured);
  const output = path.join(f.root, 'report.json');
  const cli = spawnSync(process.execPath, [path.resolve(__dirname, '../scripts/evaluate-results.cjs'), '--root', f.root,
    '--case', 'STD-001', '--format', 'structureclaw', '--input', f.input, '--capture-root', captureRoot, '--output', output],
    { encoding: 'utf8', timeout: 60000 });
  assert.equal(cli.status, 1, cli.stderr + cli.stdout);
  const report = JSON.parse(fs.readFileSync(output));
  assert.equal(report.status, 'agent_failure');
  const metrics = report.cases[0].evaluation.turns[0].evaluation.metrics;
  assert.ok(metrics.some(item => item.metric === 'captured_execution_context' && /displacements: candidate differs from native solver payload/.test(item.actual)));
  const envelope = JSON.parse(fs.readFileSync(report.import.capture));
  assert.deepEqual(envelope.runs[0].turns[0].state.analysisResult.results['case:D'].data.execution.artifacts, originalReceipt);
  assert.equal(JSON.parse(fs.readFileSync(path.join(captureRoot, 'solverResponse.json'))).displacements.m.uz, -0.001);
});
