const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const { spawnSync } = require('node:child_process');
const { createHash } = require('node:crypto');
const runner = require('../runner.cjs');
const research = require('./run-research300.cjs');

const benchRoot = path.resolve(__dirname, '..');
const providerPath = process.env.RESEARCH300_PROVIDER_TEST_MODULE || path.join(benchRoot, 'lib', 'corpus-provider.cjs');
const evaluatorPath = process.env.RESEARCH300_EVALUATOR_TEST_MODULE || path.join(benchRoot, 'lib', 'research300-evaluation.cjs');

test('unqualified public runner selects the single research corpus without starting a SUT', () => {
  assert.equal(typeof runner.parseBenchmarkOptions, 'function');
  const options = runner.parseBenchmarkOptions([]);
  assert.equal(options.corpus, 'research-300');
  assert.equal(options.execution, 'inspect');
  assert.equal(typeof runner.loadScenarios, 'function', 'External OpenClaw still imports the scenario helper');
  assert.throws(() => runner.parseBenchmarkOptions(['--corpus', 'legacy-150']), /Unsupported corpus: legacy-150/);
  assert.throws(() => runner.parseBenchmarkOptions(['--corpus=legacy-150']), /Unsupported corpus: legacy-150/);
});

test('invalid corpus fails before trying to resolve or initialize the SUT', () => {
  const result = spawnSync(process.execPath, [path.join(benchRoot, 'runner.cjs'), '--corpus', 'typo'], {
    encoding: 'utf8', env: { ...process.env, SCLAW_ROOT: '/missing/no-sut' },
  });
  assert.equal(result.status, 2);
  assert.equal(JSON.parse(result.stdout).status, 'usage_error');
  assert.match(result.stdout, /Unsupported corpus: typo/);
  assert.doesNotMatch(result.stdout + result.stderr, /does not look like a structureclaw checkout/);
});

test('public help defaults to research-300 and explicit historical selection fails before SUT setup', () => {
  const execute = args => spawnSync(process.execPath, [path.join(benchRoot, 'runner.cjs'), ...args], {
    encoding: 'utf8', env: { ...process.env, SCLAW_ROOT: '/missing/no-sut' },
  });
  const help = execute(['--help']);
  assert.equal(help.status, 0);
  assert.match(help.stdout, /research-300/);
  assert.doesNotMatch(help.stdout, /Use legacy-150|legacy-150 or/);
  const rejected = execute(['--corpus', 'legacy-150']);
  assert.equal(rejected.status, 2);
  assert.equal(JSON.parse(rejected.stdout).status, 'usage_error');
  assert.doesNotMatch(rejected.stdout + rejected.stderr, /does not look like a structureclaw checkout/);
});

test('research selection defaults to offline inspection before legacy execution validation', () => {
  assert.equal(typeof runner.parseBenchmarkOptions, 'function');
  const options = runner.parseBenchmarkOptions(['--corpus', 'research-300']);
  assert.equal(options.corpus, 'research-300');
  assert.equal(options.execution, 'inspect');
  assert.throws(() => runner.parseBenchmarkOptions(['--corpus']), /requires a value/);
  assert.throws(() => runner.parseBenchmarkOptions(['--corpus', 'research-300', '--execution', 'full']), /offline/);
  assert.throws(() => runner.parseBenchmarkOptions(['--execution', 'validate', '--cases', 'STD-001,STD-002']), /validate accepts/);
});

test('equals-style corpus selection cannot change the single public corpus', () => {
  assert.equal(runner.parseBenchmarkOptions(['--corpus=research-300']).execution, 'inspect');
  assert.throws(() => runner.parseBenchmarkOptions(['--corpus=typo']), /Unsupported corpus: typo/);
  assert.throws(() => runner.parseBenchmarkOptions(['--corpus=']), /requires a value/);
});

test('explicit case lists deduplicate valid IDs and reject ambiguous selectors', () => {
  assert.deepEqual(research.parseResearchOptions(['--cases', 'STD-001, INT-001,STD-001']).caseIds, ['STD-001', 'INT-001']);
  for (const args of [['--cases', 'STD-000'], ['--cases', 'STD-101'], ['--cases', 'STD-001,'],
    ['--cases', 'STD-001', '--case', 'STD-001'], ['--cases', 'STD-001', '--turn', '1']]) {
    assert.throws(() => research.parseResearchOptions(args), { code: 'usage_error' });
  }
});

test('explicit captured case selection evaluates exactly that subset while default evaluation retains corpus coverage', async (t) => {
  const f = fixture(t), ids = ['INT-001', 'STD-001', 'MM-001'];
  f.provider.loadCorpus = () => ({ id: 'research-300', root: f.root, cases: ids.map(id => ({ id })) });
  f.provider.loadCase = (_corpus, id) => ({ ...f.record, id, contract: { ...f.record.contract, id } });
  f.dependencies.evaluateCase = () => ({ status: 'passed', allPassed: true, turns: [] });
  const file = artifacts(f, ids.slice(0, 2).map(caseId => ({ caseId, runId: caseId + '-run', turns: [] })));
  const args = ['--root', f.root, '--execution', 'evaluate-artifacts', '--artifacts', file];
  const subset = await research.runResearch300([...args, '--cases', 'STD-001,INT-001'], f.dependencies);
  assert.equal(subset.status, 'passed');
  assert.deepEqual(subset.cases.map(row => row.caseId), ['STD-001', 'INT-001']);
  const all = await research.runResearch300(args, f.dependencies);
  assert.equal(all.status, 'unknown');
  assert.deepEqual(all.cases.map(row => row.caseId), ids);
});

test('research CLI errors remain typed and never initialize a shared SUT', (t) => {
  const f = fixture(t);
  const sut = path.join(f.root, 'sut');
  fs.mkdirSync(path.join(sut, 'backend'), { recursive: true });
  fs.writeFileSync(path.join(sut, 'backend', 'package.json'), '{}');
  fs.mkdirSync(path.join(sut, 'tests', 'regression'), { recursive: true });
  fs.writeFileSync(path.join(sut, 'tests', 'regression', 'shared.js'), 'throw new Error("UNSAFE_SHARED_SUT_SETUP");');
  const before = fs.readdirSync(sut, { recursive: true });
  const result = spawnSync(process.execPath, [path.join(benchRoot, 'runner.cjs'), '--corpus', 'research-300', '--execution', 'full'], {
    encoding: 'utf8', env: { ...process.env, SCLAW_ROOT: sut },
  });
  assert.equal(result.status, 2);
  assert.equal(JSON.parse(result.stdout).status, 'usage_error');
  assert.doesNotMatch(result.stderr + result.stdout, /UNSAFE_SHARED_SUT_SETUP/);
  assert.deepEqual(fs.readdirSync(sut, { recursive: true }), before);
});

// Fixture providers let runner boundary tests run independently of corpus authoring.
// The full provider integration suite below uses the production provider when merged.
function fixture(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'research-runner-'));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const caseDir = path.join(root, 'corpora', 'research-300', 'cases', 'INT-001');
  fs.mkdirSync(caseDir, { recursive: true });
  fs.writeFileSync(path.join(caseDir, 'private.json'), 'hidden-answer-7841');
  const contract = {
    id: 'INT-001', family: 'INT', locale: 'en', language: '英文', plannedEngine: 'OpenSees',
    evaluationProfile: 'engineering-v2.3', modelStates: ['private.json'], requiredOutputs: [],
    turns: [
      { id: 't1', instruction: 'What information is missing?', expectation: 'clarify', state: null, attachments: [] },
      { id: 't2', instruction: 'Use the supplied drawing.', expectation: 'analyze', state: 1, attachments: ['drawing.png'] },
    ],
  };
  const record = { id: 'INT-001', contract, caseDir, hiddenReference: 'hidden-answer-7841' };
  const provider = {
    loadCorpus: ({ corpus }) => {
      assert.equal(corpus, 'research-300');
      return { id: corpus, root, cases: [{ id: 'INT-001' }] };
    },
    loadCase: (_corpus, id) => {
      if (id !== 'INT-001') throw Object.assign(new Error('Unknown case'), { code: 'case_not_found' });
      return record;
    },
    getPublicTurnInput: (_record, index) => {
      if (!contract.turns[index]) throw Object.assign(new Error('Unknown turn'), { code: 'invalid_turn' });
      return { id: 'INT-001', turnId: contract.turns[index].id,
        instruction: contract.turns[index].instruction, attachments: [...contract.turns[index].attachments] };
    },
  };
  const emitted = [];
  return { root, caseDir, record, provider, emitted, dependencies: { provider, stdout: (data) => emitted.push(data) } };
}

test('inspection writes no files without --output and exposes only the selected public turn', async (t) => {
  const f = fixture(t);
  assert.equal(typeof research.runResearch300, 'function');
  const before = fs.readdirSync(f.root, { recursive: true });
  const report = await research.runResearch300(['--root', f.root, '--scenario', 'INT-001', '--turn', '1'], f.dependencies);
  assert.equal(report.execution, 'inspect');
  assert.equal(report.agentExecution, 'not-run');
  assert.deepEqual(report.cases[0].turns.map((turn) => turn.input.turnId), ['t1']);
  assert.deepEqual(report.cases[0].turns[0].input.attachments, []);
  assert.doesNotMatch(JSON.stringify(report), /hidden-answer|private.json|drawing.png/);
  assert.deepEqual(fs.readdirSync(f.root, { recursive: true }), before);
  assert.deepEqual(JSON.parse(f.emitted.join('')), report);
});

test('public response format and per-turn output units remain visible in the runner input envelope', async (t) => {
  const f = fixture(t);
  const publicInput = f.provider.getPublicTurnInput;
  f.provider.getPublicTurnInput = (record, index) => ({ ...publicInput(record, index), responseContract: {
    format: 'markdown-table', requiredOutputIds: ['deflection'],
    quantities: [{ id: 'deflection-L', selection: { kind: 'case', id: 'L' }, location: { kind: 'node', id: 'N2' }, component: 'uz', unit: 'mm' }],
    outputUnits: { deflection: 'mm' },
  } });
  const report = await research.runResearch300(['--root', f.root, '--scenario', 'INT-001', '--turn', '2'], f.dependencies);
  assert.equal(report.cases[0].turns[0].input.responseContract.quantities[0].unit, 'mm');
  assert.equal(report.cases[0].turns[0].input.responseContract.quantities[0].id, 'deflection-L');
  assert.deepEqual(report.cases[0].turns[0].input.responseContract.requiredOutputIds, ['deflection']);
});

test('each offline report records the active response/evaluator versions and actual source fingerprints', {
  skip: !fs.existsSync(evaluatorPath) && 'Engineering evaluator is supplied by the evaluator branch',
}, async (t) => {
  const f = fixture(t);
  writeSourceFixture(f);
  const evaluator = require(evaluatorPath);
  f.provider.RESPONSE_CONTRACT_VERSION = 'fixture-response-v1';
  const dependencies = { ...f.dependencies, evaluateTurn: evaluator.evaluateResearchTurn,
    validateCorpus: () => ({ valid: true }) };
  const file = artifacts(f, [{ caseId: 'INT-001', runId: 'actual-conversation', turns: [{ turnId: 't1',
    state: { messages: [{ role: 'assistant', content: 'What span should I use?' }] } }] }]);
  for (const execution of ['inspect', 'validate', 'evaluate-artifacts']) {
    const args = ['--root', f.root, '--execution', execution, '--scenario', 'INT-001', '--turn', '1'];
    if (execution === 'evaluate-artifacts') args.push('--artifacts', file);
    const report = await research.runResearch300(args, dependencies);
    assert.equal(report.runtime.providerVersion, 'fixture-response-v1');
    assert.equal(report.runtime.responseContractVersion, 'fixture-response-v1');
    assert.equal(report.runtime.evaluatorVersion, evaluator.EVALUATOR_VERSION);
    assert.equal(report.runtime.evaluatorResponseContractVersion, evaluator.RESPONSE_CONTRACT_VERSION);
    assert.equal(report.runtime.nodeVersion, process.versions.node);
    const entry = report.runtime.sources.find((source) => source.role === 'evaluator' && source.path === 'lib/research300-evaluation.cjs');
    assert.equal(entry.sha256, sha256ForTest(fs.readFileSync(evaluatorPath)));
    const dependency = report.runtime.sources.find((source) => source.role === 'evaluator' && source.path === 'lib/requested-quantities.cjs');
    assert.equal(dependency.sha256, sha256ForTest(fs.readFileSync(path.join(path.dirname(evaluatorPath), 'requested-quantities.cjs'))));
    const runnerSource = report.runtime.sources.find((source) => source.role === 'runner' && source.path === 'scripts/run-research300.cjs');
    assert.equal(runnerSource.sha256, sha256ForTest(fs.readFileSync(path.join(benchRoot, 'scripts/run-research300.cjs'))));
  }
  const injected = await research.runResearch300(['--root', f.root, '--execution', 'evaluate-artifacts', '--artifacts', file], {
    ...dependencies, evaluateCase: () => ({ status: 'unknown' }),
  });
  assert.equal(injected.runtime.evaluatorVersion, null, 'An injected case evaluator must not be labeled with the installed evaluator version');
});

test('unknown case is a corpus error rather than an empty success or agent failure', async (t) => {
  const f = fixture(t);
  assert.equal(typeof research.runResearch300, 'function');
  const result = await research.runResearch300(['--root', f.root, '--scenario', 'INT-999'], f.dependencies);
  assert.equal(result.status, 'corpus_error');
  assert.equal(result.error.code, 'case_not_found');
  assert.equal(research.researchExitCode(result), 2);
});

test('validation calls the corpus validator and never labels authored cases native accepted', async (t) => {
  const f = fixture(t);
  assert.equal(typeof research.runResearch300, 'function');
  f.dependencies.validateCorpus = (options) => {
    assert.equal(options.root, f.root);
    assert.equal(options.stage, 'authored');
    return { valid: false, errors: [{ code: 'missing_public_input', message: 'Missing public input' }] };
  };
  const result = await research.runResearch300(['--root', f.root, '--execution', 'validate'], f.dependencies);
  assert.equal(result.status, 'corpus_error');
  assert.equal(result.validation.errors[0].code, 'missing_public_input');
  assert.equal(result.agentExecution, 'not-run');
});

function artifacts(f, runs) {
  const file = path.join(f.root, 'runs.json');
  fs.writeFileSync(file, JSON.stringify({ schemaVersion: 1, corpus: 'research-300', runs }));
  return file;
}

function writeSourceFixture(f) {
  f.record.contract.attachments = ['drawing.png'];
  f.record.contract.modelStates = ['model-state-1.json'];
  f.record.models = [{ schema_version: '2.2.0', nodes: [], elements: [] }];
  f.record.root = f.root;
  fs.writeFileSync(path.join(f.caseDir, 'contract.json'), JSON.stringify(f.record.contract));
  fs.writeFileSync(path.join(f.caseDir, 'prompt.txt'), 'Public prompt');
  fs.writeFileSync(path.join(f.caseDir, 'reference-requests.json'), '{"schemaVersion":1,"states":[]}');
  fs.writeFileSync(path.join(f.caseDir, 'model-state-1.json'), JSON.stringify(f.record.models[0]));
  fs.writeFileSync(path.join(f.caseDir, 'drawing.png'), 'drawing bytes');
}

function savedResponse(f, data = { displacements: {} }) {
  const { modelFingerprint } = require('../lib/analysis-evidence.cjs');
  return { results: { 'case:D': { selection: { kind: 'case', id: 'D' },
    meta: { runId: 'analysis-1', engineId: 'OpenSees', state: 1, sourceHash: research.buildSourceBinding(f.record).sourceHash, modelHash: modelFingerprint(f.record.models[0]) },
    data: { ...data, execution: { executed: true, solver: 'OpenSees', solverVersion: 'test-1', analysisReturnCode: 0 } },
  } } };
}

test('source binding changes when an attachment or hidden model changes under the same filename', (t) => {
  const f = fixture(t);
  writeSourceFixture(f);
  assert.equal(typeof research.buildSourceBinding, 'function');
  const original = research.buildSourceBinding(f.record);
  assert.equal(original.manifest.schemaVersion, 1);
  assert.deepEqual(original.manifest.files.map((entry) => entry.path), ['contract.json', 'drawing.png', 'model-state-1.json', 'prompt.txt', 'reference-requests.json']);
  fs.writeFileSync(path.join(f.caseDir, 'drawing.png'), 'different drawing');
  const attachmentChanged = research.buildSourceBinding(f.record).sourceHash;
  assert.notEqual(attachmentChanged, original.sourceHash);
  fs.writeFileSync(path.join(f.caseDir, 'model-state-1.json'), '{"nodes":[{"id":"new"}]}');
  assert.notEqual(research.buildSourceBinding(f.record).sourceHash, attachmentChanged);
});

test('real turn adapter computes source and byte evidence and scopes a later clarification to its own messages', async (t) => {
  const f = fixture(t);
  writeSourceFixture(f);
  assert.equal(typeof research.evaluateCandidateCase, 'function');
  f.record.contract.turns[1].expectation = 'clarify';
  f.record.contract.turns[1].state = null;
  const actualModel = f.record.models[0];
  const state = { model: actualModel, messages: [{ content: 'Earlier analysis' }, { content: 'Which support?' }],
    analysisResult: { results: { 'case:D': { selection: { kind: 'case', id: 'D' }, meta: { runId: 'analysis-1', modelHash: 'candidate-lie' } } } } };
  const run = { caseId: 'INT-001', runId: 'conversation-1', turns: [
    { turnId: 't1', state: { ...state, messages: state.messages.slice(0, 1) } },
    { turnId: 't2', state, evidence: { sourceHash: 'candidate-lie', referenceEvidence: { status: 'native-verified' } } },
  ] };
  const result = await research.evaluateCandidateCase({ caseRecord: f.record, run, artifactRoot: f.root, turnIndex: 1 }, {
    evaluateTurn: ({ turnIndex, evidence }) => {
      assert.equal(turnIndex, 1);
      assert.match(evidence.sourceHash, /^[0-9a-f]{64}$/);
      assert.equal(evidence.turnEvidence.messageStartIndex, 1);
      assert.deepEqual(evidence.turnEvidence.analysisRunIds, []);
      assert.equal(evidence.referenceEvidence, undefined);
      return { status: 'pass', allPassed: true, metrics: [] };
    },
  });
  assert.equal(result.status, 'passed');
  assert.equal(result.turns.length, 1);
});

test('candidate artifact hashes are recomputed and traversal or symlink evidence paths are rejected', async (t) => {
  const f = fixture(t);
  writeSourceFixture(f);
  assert.equal(typeof research.evaluateCandidateCase, 'function');
  f.record.contract.turns[0].expectation = 'analyze';
  f.record.contract.turns[0].state = 1;
  const normalized = JSON.stringify({ model: f.record.models[0], selection: { kind: 'case', id: 'D' } });
  fs.writeFileSync(path.join(f.root, 'normalized.json'), normalized);
  const response = savedResponse(f, { displacements: { N1: { uz: 0.25 } } });
  fs.writeFileSync(path.join(f.root, 'response.json'), JSON.stringify(response));
  const run = { caseId: 'INT-001', runId: 'conversation-1', turns: [{ turnId: 't1', state: {
    model: f.record.models[0], messages: [], analysisResult: response },
    artifacts: { 'analysis-1': { normalizedInput: 'normalized.json', solverResponse: 'response.json' } },
    evidence: { trustedArtifactHashes: { normalizedInput: 'candidate-lie' } },
  }] };
  const dependencies = { evaluateTurn: ({ evidence }) => {
    const entry = evidence.artifactEvidence['analysis-1'];
    assert.equal(entry.artifactBytes.normalizedInput.toString(), normalized);
    assert.equal(entry.trustedArtifactHashes.normalizedInput, createHash('sha256').update(normalized).digest('hex'));
    assert.notEqual(entry.modelHash, 'candidate-lie');
    assert.match(entry.resultHashes['case:D'], /^[a-f0-9]{64}$/);
    assert.deepEqual(evidence.turnEvidence.analysisRunIds, ['analysis-1']);
    return { status: 'pass', allPassed: true, metrics: [] };
  } };
  assert.equal((await research.evaluateCandidateCase({ caseRecord: f.record, run, artifactRoot: f.root, turnIndex: 0 }, dependencies)).status, 'passed');
  run.turns[0].artifacts['analysis-1'].normalizedInput = '../outside.json';
  await assert.rejects(() => research.evaluateCandidateCase({ caseRecord: f.record, run, artifactRoot: f.root, turnIndex: 0 }, dependencies), /relative|escape|Unsafe/);
  fs.symlinkSync(path.join(f.root, 'normalized.json'), path.join(f.root, 'alias.json'));
  run.turns[0].artifacts['analysis-1'].normalizedInput = 'alias.json';
  await assert.rejects(() => research.evaluateCandidateCase({ caseRecord: f.record, run, artifactRoot: f.root, turnIndex: 0 }, dependencies), /Symlink/);
});

test('selection-specific native receipts retain distinct canonical bytes and immutable capture context', async (t) => {
  const f = fixture(t); writeSourceFixture(f);
  Object.assign(f.record.contract.turns[0], { expectation: 'analyze', state: 1 });
  const capture = { normalizedInput: 'capture-input.json', solverResponse: 'capture-response.json' };
  fs.writeFileSync(path.join(f.root, capture.normalizedInput), JSON.stringify({ model: f.record.models[0], selection: { kind: 'case', id: 'D' } }));
  const nativeData = { displacements: {}, reactions: {}, forces: {}, solverMesh: { nodes: [], elements: [] }, effectiveLoads: [],
    segmentResults: { displacements: {}, forces: {} } };
  const response = savedResponse(f, nativeData);
  const native = { normalizedInput: 'native-input.json', settings: 'settings.json', solverResponse: 'native-response.json' };
  const payloads = { normalizedInput: f.record.models[0], settings: { parameters: { loadCaseIds: ['D'] } }, solverResponse: nativeData };
  const receipt = { hashFormat: 'sha256:python-json-sort-keys-utf8-compact-v1', solverResponseKeys: Object.keys(nativeData) };
  for (const [key, name] of Object.entries(native)) {
    const bytes = JSON.stringify(payloads[key]);
    fs.writeFileSync(path.join(f.root, name), bytes);
    receipt[key + 'Sha256'] = sha256ForTest(bytes);
  }
  response.results['case:D'].data.execution.artifacts = receipt;
  fs.writeFileSync(path.join(f.root, capture.solverResponse), JSON.stringify(response));
  const paths = { capture, selections: { 'case:D': native } };
  const state = { model: f.record.models[0], messages: [], analysisResult: response };
  const run = { caseId: 'INT-001', runId: 'conversation', turns: [{ turnId: 't1', state, artifacts: { 'analysis-1': paths } }] };
  const input = { caseRecord: f.record, run, artifactRoot: f.root, turnIndex: 0 };
  const dependencies = { evaluateTurn: ({ evidence }) => {
    const captured = evidence.artifactEvidence['analysis-1'];
    assert.equal(JSON.parse(captured.artifactBytes.normalizedInput).model.schema_version, '2.2.0');
    assert.equal(JSON.parse(captured.selectionArtifacts['case:D'].artifactBytes.normalizedInput).schema_version, '2.2.0');
    assert.equal(captured.contexts['case:D'].payloadBinding.pass, true);
    assert.equal(captured.selectionArtifacts['case:D'].trustedArtifactHashes.settings, sha256ForTest(fs.readFileSync(path.join(f.root, native.settings))));
    return { status: 'pass', allPassed: true, metrics: [] };
  } };
  assert.equal((await research.evaluateCandidateCase(input, dependencies)).status, 'passed');
  paths.selections['case:unknown'] = native;
  await assert.rejects(() => research.evaluateCandidateCase(input, dependencies), /exactly the captured selections/);
  delete paths.selections['case:unknown'];
  native.settings = '../outside.json';
  await assert.rejects(() => research.evaluateCandidateCase(input, dependencies), /Unsafe/);
  native.settings = 'settings.json';
  fs.writeFileSync(path.join(f.root, 'changed-settings.json'), '{"changed":true}');
  const laterPaths = structuredClone(paths); laterPaths.selections['case:D'].settings = 'changed-settings.json';
  run.turns.push({ turnId: 't2', state, artifacts: { 'analysis-1': laterPaths } });
  await assert.rejects(() => research.evaluateCandidateCase(input, dependencies), { code: 'artifact_run_rebound' });
});

test('newly supplied execution evidence belongs to its current turn even if state previously claimed the run or now omits it', async (t) => {
  const f = fixture(t);
  writeSourceFixture(f);
  f.record.contract.turns[1].expectation = 'clarify';
  fs.writeFileSync(path.join(f.root, 'input.json'), JSON.stringify({ model: f.record.models[0], selection: { kind: 'case', id: 'D' } }));
  const response = savedResponse(f);
  fs.writeFileSync(path.join(f.root, 'response.json'), JSON.stringify(response));
  const state = { messages: [], analysisResult: response };
  const run = { caseId: 'INT-001', runId: 'conversation-1', turns: [
    { turnId: 't1', state },
    { turnId: 't2', state, artifacts: { 'analysis-1': { normalizedInput: 'input.json', solverResponse: 'response.json' } } },
  ] };
  const dependencies = { evaluateTurn: ({ evidence }) => {
    assert.deepEqual(evidence.turnEvidence.analysisRunIds, ['analysis-1']);
    return { status: 'agent_failure', allPassed: false, metrics: [] };
  } };
  const input = { caseRecord: f.record, run, artifactRoot: f.root, turnIndex: 1 };
  assert.equal((await research.evaluateCandidateCase(input, dependencies)).status, 'agent_failure');
  run.turns[1].state = { messages: [] };
  assert.equal((await research.evaluateCandidateCase(input, dependencies)).status, 'agent_failure');
});

test('historical result contexts retain their original state while the evaluator selects the current requested state', async (t) => {
  const f = fixture(t);
  writeSourceFixture(f);
  f.record.contract.turns[1].state = 2;
  fs.writeFileSync(path.join(f.root, 'input.json'), JSON.stringify({ model: f.record.models[0], selection: { kind: 'case', id: 'D' } }));
  const response = savedResponse(f);
  fs.writeFileSync(path.join(f.root, 'response.json'), JSON.stringify(response));
  const state = { messages: [], analysisResult: response };
  const run = { caseId: 'INT-001', runId: 'conversation-1', turns: [
    { turnId: 't1', state, artifacts: { 'analysis-1': { normalizedInput: 'input.json', solverResponse: 'response.json' } } },
    { turnId: 't2', state },
  ] };
  let evaluated = false;
  await research.evaluateCandidateCase({ caseRecord: f.record, run, artifactRoot: f.root, turnIndex: 1 }, {
    evaluateTurn: ({ evidence }) => {
      evaluated = true;
      assert.equal(evidence.artifactEvidence['analysis-1'].contexts['case:D'].meta.state, 1);
      assert.equal(evidence.turnEvidence.state, 2);
      return { status: 'agent_failure', allPassed: false, metrics: [] };
    },
  });
  assert.equal(evaluated, true);
});

test('reference provenance must bind the exact source, reference file and expected model before becoming trusted', async (t) => {
  const f = fixture(t);
  writeSourceFixture(f);
  const { modelFingerprint } = require('../lib/analysis-evidence.cjs');
  const referenceBytes = Buffer.from('{"states":[]}');
  fs.writeFileSync(path.join(f.caseDir, 'independent-reference.json'), referenceBytes);
  const provenance = { schemaVersion: 1, caseId: 'INT-001', sourceHash: research.buildSourceBinding(f.record).sourceHash,
    referenceSha256: sha256ForTest(referenceBytes), states: [{ state: 1, modelHash: modelFingerprint(f.record.models[0]), engineId: 'OpenSees', status: 'validated' }] };
  fs.writeFileSync(path.join(f.caseDir, 'reference-provenance.json'), JSON.stringify(provenance));
  const run = { caseId: 'INT-001', runId: 'r1', turns: [
    { turnId: 't1', state: { messages: [] } }, { turnId: 't2', state: { messages: [] } },
  ] };
  const input = { caseRecord: f.record, run, artifactRoot: f.root, turnIndex: 1 };
  const dependencies = { validateCase: () => ({ referenceReady: true, accepted: false }), evaluateTurn: ({ evidence }) => {
    assert.equal(evidence.referenceEvidence.status, 'validated');
    assert.equal(evidence.referenceEvidence.modelHash, modelFingerprint(f.record.models[0]));
    return { status: 'pass', allPassed: true, metrics: [] };
  } };
  assert.equal((await research.evaluateCandidateCase(input, dependencies)).status, 'passed');
  fs.writeFileSync(path.join(f.caseDir, 'independent-reference.json'), '{"states":[1]}');
  await assert.rejects(() => research.evaluateCandidateCase(input, dependencies), /provenance is stale/);
  fs.writeFileSync(path.join(f.caseDir, 'independent-reference.json'), referenceBytes);
  provenance.states[0].status = 'native-verified';
  fs.writeFileSync(path.join(f.caseDir, 'reference-provenance.json'), JSON.stringify(provenance));
  await assert.rejects(() => research.evaluateCandidateCase(input, dependencies), /independently reviewed/);
  const native = research.loadReference(f.record, provenance.sourceHash, {
    validateCase: () => ({ referenceReady: true, nativeVerified: true, inputReviewed: false, accepted: false }),
  });
  assert.equal(native.evidenceByState.get(1).status, 'native-verified');
});

test('reviewed commercial acceptance supplies native truth without requiring input blind review or a redundant provenance file', (t) => {
  const f = fixture(t);
  f.record.contract.plannedEngine = 'PKPM';
  writeSourceFixture(f);
  fs.writeFileSync(path.join(f.caseDir, 'independent-reference.json'), JSON.stringify({ states: [{ state: 1 }] }));
  const sourceHash = research.buildSourceBinding(f.record).sourceHash;
  const validateCase = options => {
    assert.equal(options.stage, 'reference-ready');
    return { referenceReady: true, nativeVerified: true, inputReviewed: false, accepted: false };
  };
  const loaded = research.loadReference(f.record, sourceHash, { validateCase });
  assert.deepEqual(loaded.evidenceByState.get(1), { state: 1, engineId: 'PKPM',
    modelHash: require('../lib/analysis-evidence.cjs').modelFingerprint(f.record.models[0]), sourceHash, status: 'native-verified' });
  const pending = research.loadReference(f.record, sourceHash, { validateCase: () => ({ referenceReady: true, nativeVerified: false }) });
  assert.equal(pending.evidenceByState, undefined);
  assert.throws(() => research.loadReference(f.record, sourceHash, { validateCase: () => ({ referenceReady: false, nativeVerified: false }) }),
    { code: 'reference_invalid' });
  fs.writeFileSync(path.join(f.caseDir, 'independent-reference.json'), JSON.stringify({ nativeVerified: true, states: [{ state: 1 }] }));
  assert.throws(() => research.loadReference(f.record, sourceHash, { validateCase: () => ({ referenceReady: true, nativeVerified: false }) }),
    { code: 'reference_native_unreviewed' });
});

test('missing or malformed replay files remain artifact errors while missing authored files remain corpus errors', async (t) => {
  const f = fixture(t);
  writeSourceFixture(f);
  const run = { caseId: 'INT-001', runId: 'conversation-1', turns: [{ turnId: 't1', state: { messages: [] },
    artifacts: { 'analysis-1': { normalizedInput: 'missing.json', solverResponse: 'missing.json' } } }] };
  const input = { caseRecord: f.record, run, artifactRoot: f.root, turnIndex: 0 };
  const dependencies = { evaluateTurn: () => { throw new Error('Malformed files must not reach evaluation'); } };
  await assert.rejects(() => research.evaluateCandidateCase(input, dependencies), { code: 'artifact_unreadable' });
  run.turns[0].artifacts['analysis-1'] = null;
  await assert.rejects(() => research.evaluateCandidateCase(input, dependencies), { code: 'artifact_schema_invalid' });
  fs.unlinkSync(path.join(f.caseDir, 'prompt.txt'));
  await assert.rejects(() => research.evaluateCandidateCase(input, dependencies), { code: 'reference_unreadable' });
});

test('query turns can reuse prior run artifacts and numeric files cannot satisfy requested figures', async (t) => {
  const f = fixture(t);
  writeSourceFixture(f);
  f.record.contract.turns[1].expectation = 'query';
  fs.writeFileSync(path.join(f.root, 'input.json'), JSON.stringify({ model: f.record.models[0], selection: { kind: 'case', id: 'D' } }));
  const response = savedResponse(f);
  fs.writeFileSync(path.join(f.root, 'response.json'), JSON.stringify(response));
  fs.writeFileSync(path.join(f.root, 'chart.png'), '{"displacement":1}');
  const state = { model: f.record.models[0], messages: [], analysisResult: response };
  const run = { caseId: 'INT-001', runId: 'r1', turns: [
    { turnId: 't1', state, artifacts: { 'analysis-1': { normalizedInput: 'input.json', solverResponse: 'response.json' } } },
    { turnId: 't2', state, figures: [{ outputId: 'deflection-plot', state: 1, runId: 'analysis-1', path: 'chart.png' }] },
  ] };
  const numeric = await research.evaluateCandidateCase({ caseRecord: f.record, run, artifactRoot: f.root, turnIndex: 1 }, {
    evaluateTurn: ({ evidence }) => {
      assert.equal(JSON.parse(evidence.artifactEvidence['analysis-1'].artifactBytes.normalizedInput).model.schema_version, '2.2.0');
      assert.deepEqual(evidence.turnEvidence.analysisRunIds, []);
      assert.equal(evidence.figureEvidence[0].decoded, false);
      return { status: 'pass', allPassed: true, metrics: [] };
    },
  });
  assert.equal(numeric.status, 'passed');
  fs.writeFileSync(path.join(f.root, 'chart.svg'), '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20"><path d="M0 0L10 10"/></svg>');
  run.turns[1].figures[0].path = 'chart.svg';
  const svg = await research.evaluateCandidateCase({ caseRecord: f.record, run, artifactRoot: f.root, turnIndex: 1 }, {
    evaluateTurn: ({ evidence }) => {
      assert.equal(evidence.figureEvidence[0].decoded, true);
      assert.equal(evidence.figureEvidence[0].verified, undefined, 'Decoding does not certify image semantics');
      assert.match(evidence.figureEvidence[0].sha256, /^[a-f0-9]{64}$/);
      return { status: 'pass', allPassed: true, metrics: [] };
    },
  });
  assert.equal(svg.status, 'passed');
  const invalidPng = Buffer.alloc(25);
  Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]).copy(invalidPng);
  invalidPng.write('IHDR', 12, 'ascii');
  fs.writeFileSync(path.join(f.root, 'chart.png'), invalidPng);
  run.turns[1].figures[0].path = 'chart.png';
  const png = await research.evaluateCandidateCase({ caseRecord: f.record, run, artifactRoot: f.root, turnIndex: 1 }, {
    evaluateTurn: ({ evidence }) => {
      assert.equal(evidence.figureEvidence[0].decoded, false, 'A PNG prefix without a decodable image is not a figure');
      return { status: 'pass', allPassed: true, metrics: [] };
    },
  });
  assert.equal(png.status, 'passed');
});

function sha256ForTest(bytes) { return createHash('sha256').update(bytes).digest('hex'); }
test('multiple actual files for one figure output form a sealed set without merging or inventing images',async t=>{
  const f=fixture(t);writeSourceFixture(f);f.record.contract.turns[1].expectation='query';
  const state={messages:[]},svg='<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20"><path d="M0 0L10 10"/></svg>';
  fs.writeFileSync(path.join(f.root,'first.svg'),svg);fs.writeFileSync(path.join(f.root,'second.svg'),svg.replace('10 10','15 15'));
  const figures=['first.svg','second.svg'].map((p,i)=>({outputId:'diagram',state:1,runId:'run-'+i,path:p}));
  const run={caseId:f.record.id,runId:'conversation',turns:[{turnId:'t1',state},{turnId:'t2',state,figures}]};
  const evaluate=()=>research.evaluateCandidateCase({caseRecord:f.record,run,artifactRoot:f.root,turnIndex:1},{evaluateTurn:({evidence})=>{
    const set=evidence.figureEvidence[0];assert.equal(evidence.figureEvidence.length,1);assert.equal(set.decoded,true);
    assert.equal(set.figures.length,2);assert.equal(set.runId,undefined,'no shared execution is invented');
    assert.equal(set.sha256,require('../lib/research300-evaluation.cjs').figureSetFingerprint(set.figures));
    assert.equal(set.figures[0].sha256,sha256ForTest(fs.readFileSync(path.join(f.root,'first.svg'))));
    return{status:'pass',allPassed:true,metrics:[]};
  }});
  await evaluate();figures.push({...figures[0]});
  await assert.rejects(evaluate,{code:'artifact_figure_invalid'});
});

test('production evaluator scores actual clarification snapshots and keeps missing commercial truth pending', {
  skip: !fs.existsSync(evaluatorPath) && 'Engineering evaluator is supplied by the evaluator branch',
}, async (t) => {
  const f = fixture(t);
  writeSourceFixture(f);
  const evaluateTurn = require(evaluatorPath).evaluateResearchTurn;
  const state = { messages: [{ tool_calls: [{ name: 'ask_user_clarification', args: { question: 'What is the span?' } }] }] };
  const run = { caseId: 'INT-001', runId: 'actual-conversation', turns: [{ turnId: 't1', state }] };
  const input = { caseRecord: f.record, run, artifactRoot: f.root, turnIndex: 0 };
  const clarification = await research.evaluateCandidateCase(input, { evaluateTurn });
  assert.equal(clarification.status, 'review_pending');
  f.record.contract.turns[0].expectation = 'analyze';
  f.record.contract.turns[0].state = 1;
  f.record.contract.plannedEngine = 'PKPM';
  f.record.referenceRequests = { states: [{ state: 1, quantities: [] }] };
  const pending = await research.evaluateCandidateCase(input, { evaluateTurn });
  assert.equal(pending.status, 'native_truth_pending');
  f.record.contract.plannedEngine = 'OpenSees';
  assert.equal((await research.evaluateCandidateCase(input, { evaluateTurn })).status, 'corpus_error');
});

test('numerical replay with the production evaluator binds raw engine, execution, results and turn availability', {
  skip: !fs.existsSync(evaluatorPath) && 'Engineering evaluator is supplied by the evaluator branch',
}, async (t) => {
  const f = fixture(t);
  writeSourceFixture(f);
  const { modelFingerprint } = require('../lib/analysis-evidence.cjs');
  const model = structuredClone(require('../fixtures/ground-truth-models.json').find((row) => row.id === 'beam-simple-6m').model);
  const quantity = { id: 'support-ux', selection: { kind: 'case', id: 'LC1' }, location: { kind: 'node', id: '1' }, component: 'ux', unit: 'm', tolerance: { absolute: 1e-8, relative: 1e-6 } };
  f.record.models = [model];
  f.record.referenceRequests = { schemaVersion: 1, states: [{ state: 1, model: 'model-state-1.json', quantities: [quantity], derived: [] }] };
  f.record.contract.turns = [{ id: 't1', instruction: 'Analyze', expectation: 'analyze', state: 1, attachments: [], requiredOutputIds: ['displacement'] },
    { id: 't2', instruction: 'Query', expectation: 'query', state: 1, attachments: [], requiredOutputIds: ['displacement'] }];
  f.record.contract.requiredOutputs = [{ id: 'displacement', kind: 'numerical', state: 1, quantityIds: ['support-ux'] }];
  fs.writeFileSync(path.join(f.caseDir, 'contract.json'), JSON.stringify(f.record.contract));
  fs.writeFileSync(path.join(f.caseDir, 'model-state-1.json'), JSON.stringify(model));
  fs.writeFileSync(path.join(f.caseDir, 'reference-requests.json'), JSON.stringify(f.record.referenceRequests));
  let sourceHash = research.buildSourceBinding(f.record).sourceHash;
  const reference = Buffer.from(JSON.stringify({ toleranceFrozenBeforeCandidate: true, states: [{ state: 1, quantities: [{ ...quantity, value: 0 }] }] }));
  fs.writeFileSync(path.join(f.caseDir, 'independent-reference.json'), reference);
  fs.writeFileSync(path.join(f.caseDir, 'reference-provenance.json'), JSON.stringify({ schemaVersion: 1, caseId: 'INT-001', sourceHash,
    referenceSha256: sha256ForTest(reference), states: [{ state: 1, modelHash: modelFingerprint(model), engineId: 'OpenSees', status: 'validated' }] }));
  let normalized = Buffer.from(JSON.stringify({ model, selection: quantity.selection }));
  fs.writeFileSync(path.join(f.root, 'input.json'), normalized);
  const raw = { results: { 'case:LC1': { selection: quantity.selection, meta: { engineId: 'OpenSees', runId: 'solver-1', modelHash: modelFingerprint(model), state: 1, sourceHash },
    execution: { executed: true, solver: 'OpenSees', solverVersion: 'test-1', analysisReturnCode: 0 }, data: { displacements: { '1': { ux: 0 } } } } } };
  const dependencies = { evaluateTurn: require(evaluatorPath).evaluateResearchTurn, validateCase: () => ({ referenceReady: true, accepted: false }) };
  function capture(rawResponse, candidateResponse = raw) {
    const responseBytes = Buffer.from(JSON.stringify(rawResponse));
    fs.writeFileSync(path.join(f.root, 'response.json'), responseBytes);
    const candidate = structuredClone(candidateResponse);
    for (const result of Object.values(candidate.results)) (result.data.execution || result.execution).artifacts = { normalizedInputSha256: sha256ForTest(normalized), solverResponseSha256: sha256ForTest(responseBytes) };
    const markdown = f.record.referenceRequests.states[0].quantities.map((q) => `| ${q.id} | ${q.selection.kind}:${q.selection.id} | 1 | ux | 0 | m |`).join('\n');
    const state = { model, messages: [{ role: 'assistant', content: markdown }], analysisResult: candidate, report: { markdown } };
    return { caseId: 'INT-001', runId: 'conversation-1', turns: [{ turnId: 't1', state, artifacts: { 'solver-1': { normalizedInput: 'input.json', solverResponse: 'response.json' } } }] };
  }
  async function evaluate(run, turnIndex = 0, assessments = []) {
    return research.evaluateCandidateCase({ caseRecord: f.record, run, artifactRoot: f.root, turnIndex, assessments }, dependencies);
  }
  const good = await evaluate(capture(raw));
  assert.equal(good.status, 'passed', JSON.stringify(good));
  for (const layer of ['record', 'data', 'execution']) {
    for (const status of ['cancelled', 'canceled', 'preliminary', 'failed', null]) {
      const rejected = structuredClone(raw);
      const record = rejected.results['case:LC1'];
      (layer === 'record' ? record : record[layer]).status = status;
      assert.equal((await evaluate(capture(rejected, raw))).status, 'agent_failure', `Raw ${layer} status ${status} must reject`);
      assert.equal((await evaluate(capture(raw, rejected))).status, 'agent_failure', `Candidate ${layer} status ${status} must reject`);
    }
  }
  const wrongEngine = structuredClone(raw);
  wrongEngine.results['case:LC1'].meta.engineId = 'PKPM';
  wrongEngine.results['case:LC1'].meta.runId = 'other-run';
  assert.equal((await evaluate(capture(wrongEngine))).status, 'agent_failure');
  const unexecuted = structuredClone(raw);
  unexecuted.results['case:LC1'].execution.executed = false;
  unexecuted.results['case:LC1'].execution.analysisReturnCode = -9;
  assert.equal((await evaluate(capture(unexecuted))).status, 'agent_failure');
  const alteredNumerical = structuredClone(raw);
  alteredNumerical.results['case:LC1'].data.displacements['1'].ux = 9;
  assert.equal((await evaluate(capture(alteredNumerical))).status, 'agent_failure');
  const future = capture(raw);
  future.turns.push({ turnId: 't2', state: future.turns[0].state, artifacts: future.turns[0].artifacts });
  delete future.turns[0].artifacts;
  assert.equal((await evaluate(future)).status, 'agent_failure');
  const rebound = capture(raw);
  fs.writeFileSync(path.join(f.root, 'other-response.json'), JSON.stringify(alteredNumerical));
  rebound.turns.push({ turnId: 't2', state: rebound.turns[0].state, artifacts: { 'solver-1': { normalizedInput: 'input.json', solverResponse: 'other-response.json' } } });
  await assert.rejects(() => evaluate(rebound, 1), /immutable analysis run ID/);

  const combinationQuantity = { ...quantity, id: 'support-ux-combination', selection: { kind: 'combination', id: 'ULS' } };
  f.record.referenceRequests.states[0].quantities.push(combinationQuantity);
  f.record.contract.requiredOutputs[0].quantityIds.push(combinationQuantity.id);
  fs.writeFileSync(path.join(f.caseDir, 'contract.json'), JSON.stringify(f.record.contract));
  fs.writeFileSync(path.join(f.caseDir, 'reference-requests.json'), JSON.stringify(f.record.referenceRequests));
  sourceHash = research.buildSourceBinding(f.record).sourceHash;
  const batchReference = Buffer.from(JSON.stringify({ toleranceFrozenBeforeCandidate: true,
    states: [{ state: 1, quantities: [quantity, combinationQuantity].map((q) => ({ ...q, value: 0 })) }] }));
  fs.writeFileSync(path.join(f.caseDir, 'independent-reference.json'), batchReference);
  fs.writeFileSync(path.join(f.caseDir, 'reference-provenance.json'), JSON.stringify({ schemaVersion: 1, caseId: 'INT-001', sourceHash,
    referenceSha256: sha256ForTest(batchReference), states: [{ state: 1, modelHash: modelFingerprint(model), engineId: 'OpenSees', status: 'validated' }] }));
  normalized = Buffer.from(JSON.stringify({ model, selections: [quantity.selection, combinationQuantity.selection] }));
  fs.writeFileSync(path.join(f.root, 'input.json'), normalized);
  raw.results['case:LC1'].meta.sourceHash = sourceHash;
  raw.results['combination:ULS'] = structuredClone(raw.results['case:LC1']);
  raw.results['combination:ULS'].selection = combinationQuantity.selection;
  const batch = await evaluate(capture(raw));
  assert.equal(batch.status, 'passed', `One actual run may cover distinct case and combination selections: ${JSON.stringify(batch)}`);
  const embeddedExecution = structuredClone(raw);
  for (const result of Object.values(embeddedExecution.results)) {
    result.data.execution = result.execution;
    delete result.execution;
  }
  assert.equal((await evaluate(capture(embeddedExecution, embeddedExecution))).status, 'passed', 'Execution receipts inside data must not create a circular solver response hash');

  f.record.referenceRequests.states[0].derived = [{ id: 'support-sum', operation: 'sum', operands: ['support-ux', 'support-ux-combination'], unit: 'm' }];
  f.record.contract.requiredOutputs.push({ id: 'derived-total', kind: 'derived', state: 1, quantityIds: ['support-sum'] },
    { id: 'explanation', kind: 'interaction', state: 1 });
  for (const turn of f.record.contract.turns) turn.requiredOutputIds = f.record.contract.requiredOutputs.map((output) => output.id);
  fs.writeFileSync(path.join(f.caseDir, 'contract.json'), JSON.stringify(f.record.contract));
  fs.writeFileSync(path.join(f.caseDir, 'reference-requests.json'), JSON.stringify(f.record.referenceRequests));
  sourceHash = research.buildSourceBinding(f.record).sourceHash;
  fs.writeFileSync(path.join(f.caseDir, 'reference-provenance.json'), JSON.stringify({ schemaVersion: 1, caseId: 'INT-001', sourceHash,
    referenceSha256: sha256ForTest(batchReference), states: [{ state: 1, modelHash: modelFingerprint(model), engineId: 'OpenSees', status: 'validated' }] }));
  for (const result of Object.values(raw.results)) result.meta.sourceHash = sourceHash;
  const withDerived = capture(raw);
  withDerived.turns[0].state.messages[0].content += '\n| derived | support-sum | 0 | m | - | - |\nThe support displacement sum is zero.';
  const receipt = { caseId: 'INT-001', turnId: 't1', outputId: 'explanation', state: 1, sourceHash,
    currentResponseSha256: research.currentResponseSha256(withDerived.turns[0].state.messages, 0),
    activitySha256: research.currentActivitySha256(withDerived.turns[0].state.messages, 0),
    pass: true, reason: 'Explains the reported support sum.', reviewerId: 'independent-reviewer', reviewedAt: '2026-10-15T00:00:00Z' };
  assert.equal((await evaluate(withDerived)).status, 'review_pending', 'Missing independent semantic assessment must remain unavailable');
  assert.equal((await evaluate(withDerived, 0, [receipt])).status, 'passed', 'Actual current derived row and bound independent semantic assessment must pass');
  assert.equal((await evaluate(withDerived, 0, [{ ...receipt, pass: false }])).status, 'agent_failure');
  const wrongDerived = structuredClone(withDerived);
  wrongDerived.turns[0].state.messages[0].content = wrongDerived.turns[0].state.messages[0].content.replace('support-sum | 0', 'support-sum | 9');
  await assert.rejects(() => evaluate(wrongDerived, 0, [receipt]), { code: 'reference_assessment_binding' });
  assert.equal((await evaluate(wrongDerived, 0, [{ ...receipt, currentResponseSha256: research.currentResponseSha256(wrongDerived.turns[0].state.messages, 0),
    activitySha256: research.currentActivitySha256(wrongDerived.turns[0].state.messages, 0) }])).status, 'agent_failure');
});

test('offline replay passes supplied candidate runs separately from hidden evaluator records', async (t) => {
  const f = fixture(t);
  assert.equal(typeof research.runResearch300, 'function');
  const file = artifacts(f, [{ caseId: 'INT-001', runId: 'actual-run-1', turns: [{ turnId: 't1', response: 'Need dimensions.' }] }]);
  f.dependencies.evaluateCase = ({ caseRecord, run, artifactRoot }) => {
    assert.equal(caseRecord.hiddenReference, 'hidden-answer-7841');
    assert.deepEqual(run, { caseId: 'INT-001', runId: 'actual-run-1', turns: [{ turnId: 't1', response: 'Need dimensions.' }] });
    assert.equal(artifactRoot, f.root);
    return { status: 'native_truth_pending', allPassed: false, metrics: [] };
  };
  const report = await research.runResearch300(['--root', f.root, '--execution', 'evaluate-artifacts', '--artifacts', file, '--artifact-root', f.root], f.dependencies);
  assert.equal(report.status, 'native_truth_pending');
  assert.equal(report.cases[0].evaluation.status, 'native_truth_pending');
  assert.equal(research.researchExitCode(report), 3);
  assert.doesNotMatch(JSON.stringify(report), /hidden-answer/);
});

test('offline semantic assessments require an explicit file outside candidate evidence and exact response/source/turn/output bindings', async (t) => {
  const f = fixture(t);
  writeSourceFixture(f);
  f.record.contract.turns[0].state = 1;
  f.record.contract.turns[0].expectation = 'query';
  f.record.contract.requiredOutputs = [{ id: 'explanation', kind: 'interaction', state: 1 }];
  const state = { messages: [{ role: 'assistant', content: 'The span is missing.' }] };
  const run = { caseId: 'INT-001', runId: 'actual-conversation', turns: [{ turnId: 't1', state }] };
  const candidateFile = artifacts(f, [run]);
  const reviewDirectory = fs.mkdtempSync(path.join(os.tmpdir(), 'research-runner-review-'));
  t.after(() => fs.rmSync(reviewDirectory, { recursive: true, force: true }));
  const reviewFile = path.join(reviewDirectory, 'assessments.json');
  assert.equal(typeof research.currentResponseSha256, 'function');
  const responseHash = research.currentResponseSha256(state.messages, 0);
  assert.equal(responseHash, research.currentResponseSha256([{ content: 'The span is missing.', role: 'assistant' }], 0), 'Object insertion order must not alter the response binding');
  assert.equal(responseHash, research.currentResponseSha256([{ role: 'tool', content: 'private tool response' }, ...state.messages], 0), 'Only current assistant messages are assessed');
  const receipt = { caseId: 'INT-001', turnId: 't1', outputId: 'explanation', state: 1,
    sourceHash: research.buildSourceBinding(f.record).sourceHash, currentResponseSha256: responseHash,
    activitySha256: research.currentActivitySha256(state.messages, 0),
    pass: true, reason: 'Identifies the required missing span.', reviewerId: 'independent-reviewer', reviewedAt: '2026-10-15T00:00:00Z' };
  const writeReview = (item = receipt, file = reviewFile) => fs.writeFileSync(file, JSON.stringify({ schemaVersion: 1, corpus: 'research-300', assessments: [item] }));
  writeReview();
  const args = ['--root', f.root, '--execution', 'evaluate-artifacts', '--scenario', 'INT-001', '--turn', '1', '--artifacts', candidateFile, '--assessments', reviewFile];
  const dependencies = { ...f.dependencies, evaluateTurn: ({ evidence }) => {
    assert.equal(evidence.interactionEvidence[0].pass, true);
    assert.equal(evidence.interactionEvidence[0].sourceHash, receipt.sourceHash);
    assert.equal(evidence.turnEvidence.currentResponseSha256, responseHash);
    return { status: 'pass', allPassed: true, metrics: [] };
  } };
  assert.equal((await research.runResearch300(args, dependencies)).status, 'passed');
  writeReview({ ...receipt, currentResponseSha256: '0'.repeat(64) });
  assert.equal((await research.runResearch300(args, dependencies)).status, 'corpus_error');
  writeReview({ ...receipt, sourceHash: '0'.repeat(64) });
  assert.equal((await research.runResearch300(args, dependencies)).status, 'corpus_error');
  writeReview({ ...receipt, outputId: 'not-required' });
  assert.equal((await research.runResearch300(args, dependencies)).status, 'corpus_error');
  writeReview({ ...receipt, reviewerId: '' });
  assert.equal((await research.runResearch300(args, dependencies)).status, 'corpus_error');
  const candidateReview = path.join(f.root, 'candidate-assessment.json');
  writeReview(receipt, candidateReview);
  assert.equal((await research.runResearch300([...args.slice(0, -1), candidateReview], dependencies)).status, 'corpus_error');
  assert.throws(() => research.parseResearchOptions(['--assessments', reviewFile]), /require evaluate-artifacts/);
});

test('null-state clarification produces bound review requests and accepts independent positive or negative reviews', async (t) => {
  const f = fixture(t);
  Object.assign(f.record.contract.turns[0], { state: null, expectation: 'clarify',
    expectedQuestions: ['What is the force unit?'], unresolvedFields: ['/loads/forceUnit'] });
  f.record.contract.requiredOutputs = [{ id: 'clarification', kind: 'interaction', state: null, turnIds: ['t1'] }];
  writeSourceFixture(f);
  const state = { messages: [{ role: 'assistant', content: 'Are these loads measured in newtons or kilonewtons?' }] };
  const candidateFile = artifacts(f, [{ caseId: 'INT-001', runId: 'clarify-conversation', turns: [{ turnId: 't1', state }] }]);
  const args = ['--root', f.root, '--execution', 'evaluate-artifacts', '--scenario', 'INT-001', '--turn', '1', '--artifacts', candidateFile];
  const dependencies = { ...f.dependencies, evaluateTurn: require(evaluatorPath).evaluateResearchTurn };
  const pending = await research.runResearch300(args, dependencies);
  assert.equal(pending.status, 'review_pending');
  assert.equal(research.researchExitCode(pending), 3);
  assert.equal(pending.cases[0].evaluation.turns[0].evaluation.score, null);
  assert.equal(pending.reviewRequests.length, 1);
  const request = pending.reviewRequests[0];
  assert.equal(request.state, null);
  assert.equal(request.outputId, 'clarification');
  assert.equal(request.currentResponseSha256, research.currentResponseSha256(state.messages, 0));
  assert.deepEqual(request.messages, state.messages);
  const reviewDirectory = fs.mkdtempSync(path.join(os.tmpdir(), 'research-null-review-'));
  t.after(() => fs.rmSync(reviewDirectory, { recursive: true, force: true }));
  const reviewFile = path.join(reviewDirectory, 'assessments.json');
  const receipt = { ...request, pass: true, reason: 'Asks for the omitted force unit.', reviewerId: 'independent-reviewer', reviewedAt: '2026-10-22T00:00:00Z' };
  const review = async changes => {
    fs.writeFileSync(reviewFile, JSON.stringify({ schemaVersion: 1, corpus: 'research-300', assessments: [{ ...receipt, ...changes }] }));
    return research.runResearch300([...args, '--assessments', reviewFile], dependencies);
  };
  const accepted = await review({});
  assert.equal(accepted.status, 'passed');
  assert.deepEqual(accepted.reviewRequests, []);
  const rejected = await review({ pass: false, reason: 'The question does not resolve the requested ambiguity.' });
  assert.equal(rejected.status, 'agent_failure');
  assert.equal(research.researchExitCode(rejected), 1);
  assert.notEqual(rejected.cases[0].evaluation.turns[0].evaluation.score, null);
  assert.equal((await review({ state: 1 })).status, 'corpus_error');
  assert.equal((await review({ currentResponseSha256: '0'.repeat(64) })).status, 'corpus_error');
});

test('missing candidate evidence stays unknown and never substitutes a reference run', async (t) => {
  const f = fixture(t);
  assert.equal(typeof research.runResearch300, 'function');
  const file = artifacts(f, []);
  f.dependencies.evaluateCase = () => assert.fail('No candidate run must not be evaluated as an oracle run');
  const report = await research.runResearch300(['--root', f.root, '--execution', 'evaluate-artifacts', '--artifacts', file], f.dependencies);
  assert.equal(report.status, 'unknown');
  assert.equal(report.cases[0].status, 'unknown');
  assert.equal(research.researchExitCode(report), 3);
});

test('captured Codex tool lifecycle requires independent behavior review and stale trace reviews are rejected', async (t) => {
  const f = fixture(t);
  Object.assign(f.record.contract.turns[0], { state: null, expectation: 'clarify', expectedQuestions: ['What is the span?'] });
  f.record.contract.requiredOutputs = [{ id: 'question', kind: 'interaction', state: null, turnIds: ['t1'] }];
  writeSourceFixture(f);
  const { extractCodex } = require('../lib/import-codex.cjs');
  const tool = { type: 'item.started', item: { id: 'shell', type: 'command_execution', command: 'python task.py' } };
  const commentary = { type: 'item.completed', item: { id: 'commentary', type: 'agent_message', text: 'I assumed 6 m and solved the model.' } };
  const extracted = extractCodex([{ type: 'turn.started' }, tool, commentary,
    { type: 'item.completed', item: { id: 'answer', type: 'agent_message', text: 'What is the span?' } }, { type: 'turn.completed' }], { turnIds: ['t1'] });
  const run = { caseId: 'INT-001', runId: 'conversation', turns: extracted.turns };
  const input = { caseRecord: f.record, run, artifactRoot: f.root, turnIndex: 0 };
  const pending = await research.evaluateCandidateCase(input);
  assert.equal(pending.status, 'review_pending');
  assert.equal(pending.turns[0].evaluation.score, null);
  assert.deepEqual(new Set(pending.reviewRequests.map(r => r.outputId)), new Set(['question', 'benchmark:should-not-analyze']));
  for (const request of pending.reviewRequests) {
    assert.deepEqual(request.toolEvents, [tool]);
    assert.equal(request.activitySha256, research.currentActivitySha256(run.turns[0].state.messages, 0, [tool], run.turns[0].assistantEvents));
    assert.deepEqual(request.assistantEvents[0], commentary);
  }
  const assessments = pending.reviewRequests.map(request => ({ ...request, pass: false, reason: 'Earlier current-turn commentary assumes the omitted span and claims analysis.',
    reviewerId: 'independent-reviewer', reviewedAt: '2026-10-22T00:00:00Z' }));
  assert.equal((await research.evaluateCandidateCase({ ...input, assessments })).status, 'agent_failure');
  run.turns[0].assistantEvents[0].item.text = 'I am inspecting the input.';
  await assert.rejects(() => research.evaluateCandidateCase({ ...input, assessments }), { code: 'reference_assessment_binding' });
  run.turns[0].assistantEvents[0].item.text = commentary.item.text;
  run.turns[0].toolEvents[0].item.command = 'python other.py';
  await assert.rejects(() => research.evaluateCandidateCase({ ...input, assessments }), { code: 'reference_assessment_binding' });
  const changed = await research.evaluateCandidateCase(input);
  assert.equal(changed.status, 'review_pending');
  assert.equal(changed.reviewRequests[0].currentResponseSha256, pending.reviewRequests[0].currentResponseSha256);
  assert.notEqual(changed.reviewRequests[0].activitySha256, pending.reviewRequests[0].activitySha256);
  run.turns[0].toolEvents = [{ type: 'step_upsert', step: { tool: 'run_analysis', status: 'error' } }];
  const blocked = await research.evaluateCandidateCase(input);
  assert.equal(blocked.status, 'agent_failure');
  assert.deepEqual(blocked.reviewRequests, []);
});

test('a real decodable blank image stays pending and figure reviews bind the actual image bytes', async (t) => {
  const f = fixture(t), { modelFingerprint } = require('../lib/analysis-evidence.cjs');
  const model = structuredClone(require('../fixtures/ground-truth-models.json').find(row => row.id === 'beam-simple-6m').model);
  const quantity = { id: 'support-ux', selection: { kind: 'case', id: 'LC1' }, location: { kind: 'node', id: '1' }, component: 'ux', unit: 'm', tolerance: { absolute: 1e-8, relative: 1e-6 } };
  f.record.models = [model];
  f.record.referenceRequests = { states: [{ state: 1, quantities: [quantity], derived: [] }] };
  f.record.contract.turns = [{ id: 't1', instruction: 'Analyze and show supports, loads and displacement.', expectation: 'analyze', state: 1 }];
  f.record.contract.requiredOutputs = [{ id: 'value', kind: 'numerical', state: 1, quantityIds: [quantity.id] },
    { id: 'plot', kind: 'figure', state: 1, quantityIds: [], description: 'Show the correct supports, applied loads and displacement units.' }];
  writeSourceFixture(f);
  f.record.models = [model];
  fs.writeFileSync(path.join(f.caseDir, 'model-state-1.json'), JSON.stringify(model));
  fs.writeFileSync(path.join(f.caseDir, 'reference-requests.json'), JSON.stringify(f.record.referenceRequests));
  const sourceHash = research.buildSourceBinding(f.record).sourceHash;
  const reference = Buffer.from(JSON.stringify({ toleranceFrozenBeforeCandidate: true, states: [{ state: 1, quantities: [{ ...quantity, value: 0 }] }] }));
  fs.writeFileSync(path.join(f.caseDir, 'independent-reference.json'), reference);
  fs.writeFileSync(path.join(f.caseDir, 'reference-provenance.json'), JSON.stringify({ schemaVersion: 1, caseId: 'INT-001', sourceHash,
    referenceSha256: sha256ForTest(reference), states: [{ state: 1, modelHash: modelFingerprint(model), engineId: 'OpenSees', status: 'validated' }] }));
  const normalized = Buffer.from(JSON.stringify({ model, selection: quantity.selection }));
  const raw = { results: { 'case:LC1': { selection: quantity.selection,
    meta: { engineId: 'OpenSees', runId: 'solver', modelHash: modelFingerprint(model), state: 1, sourceHash },
    execution: { executed: true, solver: 'OpenSees', solverVersion: 'test-1', analysisReturnCode: 0 }, data: { displacements: { '1': { ux: 0 } } } } } };
  const response = Buffer.from(JSON.stringify(raw));
  fs.writeFileSync(path.join(f.root, 'input.json'), normalized); fs.writeFileSync(path.join(f.root, 'response.json'), response);
  raw.results['case:LC1'].execution.artifacts = { normalizedInputSha256: sha256ForTest(normalized), solverResponseSha256: sha256ForTest(response) };
  fs.writeFileSync(path.join(f.root, 'blank.svg'), '<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"><rect width="1" height="1" fill="white"/></svg>');
  const state = { model, analysisResult: raw, messages: [{ role: 'assistant', content: '| support-ux | case:LC1 | 1 | ux | 0 | m |' }] };
  const run = { caseId: 'INT-001', runId: 'conversation', turns: [{ turnId: 't1', state,
    artifacts: { solver: { normalizedInput: 'input.json', solverResponse: 'response.json' } },
    figures: [{ outputId: 'plot', state: 1, runId: 'solver', path: 'blank.svg' }] }] };
  const input = { caseRecord: f.record, run, artifactRoot: f.root, turnIndex: 0 };
  const dependencies = { validateCase: () => ({ referenceReady: true, accepted: false }) };
  const pending = await research.evaluateCandidateCase(input, dependencies);
  assert.equal(pending.status, 'review_pending', JSON.stringify(pending));
  assert.equal(pending.turns[0].evaluation.score, null);
  const request = pending.reviewRequests[0];
  assert.equal(request.outputId, 'plot'); assert.equal(request.figure.decoded, true);
  assert.equal(request.figure.width, 1); assert.equal(request.figure.height, 1);
  assert.equal(request.figureSha256, sha256ForTest(fs.readFileSync(path.join(f.root, 'blank.svg'))));
  assert.deepEqual(request.model, model);
  const receipt = { ...request, pass: false, reason: 'Blank image has no supports, loads or result units.', reviewerId: 'independent-reviewer', reviewedAt: '2026-10-22T00:00:00Z' };
  assert.equal((await research.evaluateCandidateCase({ ...input, assessments: [receipt] }, dependencies)).status, 'agent_failure');
  fs.writeFileSync(path.join(f.root, 'blank.svg'), '<svg xmlns="http://www.w3.org/2000/svg" width="2" height="2"><path d="M0 0L2 2"/></svg>');
  await assert.rejects(() => research.evaluateCandidateCase({ ...input, assessments: [{ ...receipt, pass: true }] }, dependencies), { code: 'reference_assessment_binding' });
});

test('malformed artifacts are infrastructure errors and evaluator exceptions are evaluation errors', async (t) => {
  const f = fixture(t);
  assert.equal(typeof research.runResearch300, 'function');
  const file = path.join(f.root, 'broken.json');
  fs.writeFileSync(file, '{broken');
  const args = ['--root', f.root, '--execution', 'evaluate-artifacts', '--artifacts', file];
  const broken = await research.runResearch300(args, f.dependencies);
  assert.equal(broken.status, 'artifact_error');
  assert.equal(research.researchExitCode(broken), 2);
  const valid = artifacts(f, [{ caseId: 'INT-001', runId: 'actual-run-1', turns: [] }]);
  f.dependencies.evaluateCase = () => { throw Object.assign(new Error('Evaluator internal failure'), { code: 'evaluator_internal' }); };
  const evaluation = await research.runResearch300([...args.slice(0, -1), valid], f.dependencies);
  assert.equal(evaluation.status, 'evaluation_error');
  assert.equal(evaluation.cases[0].error.code, 'evaluator_internal');
});

test('duplicate runs and mismatched corpus artifacts are rejected before scoring', async (t) => {
  const f = fixture(t);
  assert.equal(typeof research.runResearch300, 'function');
  const file = artifacts(f, [{ caseId: 'INT-001', runId: 'r1', turns: [] }, { caseId: 'INT-001', runId: 'r2', turns: [] }]);
  const args = ['--root', f.root, '--execution', 'evaluate-artifacts', '--artifacts', file];
  const duplicate = await research.runResearch300(args, f.dependencies);
  assert.equal(duplicate.status, 'artifact_error');
  assert.equal(duplicate.error.code, 'artifact_duplicate_case');
  fs.writeFileSync(file, JSON.stringify({ schemaVersion: 1, corpus: 'legacy-150', runs: [] }));
  assert.equal((await research.runResearch300(args, f.dependencies)).status, 'artifact_error');
});

test('an output parent symlink cannot redirect the report into the corpus', async (t) => {
  const f = fixture(t);
  const alias = path.join(f.root, 'output-alias');
  fs.symlinkSync(f.caseDir, alias, 'dir');
  const result = await research.runResearch300(['--root', f.root, '--output', path.join(alias, 'report.json')], f.dependencies);
  assert.equal(result.status, 'output_error');
  assert.equal(result.error.code, 'output_path_protected');
  assert.equal(fs.existsSync(path.join(f.caseDir, 'report.json')), false);
});

test('output cannot write inside a SUT checkout even when SCLAW_ROOT is unset', async (t) => {
  const f = fixture(t);
  const sut = path.join(f.root, 'production');
  fs.mkdirSync(path.join(sut, 'backend'), { recursive: true });
  fs.writeFileSync(path.join(sut, 'backend', 'package.json'), '{}');
  const destination = path.join(sut, 'report.json');
  const result = await research.runResearch300(['--root', f.root, '--output', destination], f.dependencies);
  assert.equal(result.status, 'output_error');
  assert.equal(result.error.code, 'output_path_protected');
  assert.equal(fs.existsSync(destination), false);
});

test('the default evidence directory is protected from output writes', async (t) => {
  const f = fixture(t);
  const file = artifacts(f, []);
  const output = path.join(f.root, 'new-report.json');
  const result = await research.runResearch300(['--root', f.root, '--execution', 'evaluate-artifacts', '--artifacts', file, '--output', output], f.dependencies);
  assert.equal(result.status, 'output_error');
  assert.equal(result.error.code, 'output_path_protected');
  assert.equal(fs.existsSync(output), false);
});

test('candidate failure retains exit 1 while pending and missing evidence retain exit 3', async (t) => {
  const f = fixture(t);
  const file = artifacts(f, [{ caseId: 'INT-001', runId: 'r1', turns: [] }]);
  f.dependencies.evaluateCase = () => ({ status: 'agent_failure', allPassed: false, reason: 'Requested displacement omitted' });
  const result = await research.runResearch300(['--root', f.root, '--execution', 'evaluate-artifacts', '--artifacts', file], f.dependencies);
  assert.equal(result.status, 'agent_failure');
  assert.equal(research.researchExitCode(result), 1);
});

test('all offline modes avoid model requests, subprocesses and file writes without --output', async (t) => {
  const f = fixture(t);
  const file = artifacts(f, [{ caseId: 'INT-001', runId: 'r1', turns: [] }]);
  const childProcess = require('node:child_process');
  const forbidden = () => { throw new Error('Offline runner attempted a side effect'); };
  const originalWrite = fs.writeFileSync;
  const originalFetch = global.fetch;
  const originalSpawn = childProcess.spawn;
  const originalSpawnSync = childProcess.spawnSync;
  const originalExec = childProcess.execSync;
  f.dependencies.validateCorpus = () => ({ valid: true, errors: [] });
  f.dependencies.evaluateCase = () => ({ status: 'unknown', allPassed: false });
  try {
    fs.writeFileSync = forbidden;
    global.fetch = forbidden;
    childProcess.spawn = forbidden;
    childProcess.spawnSync = forbidden;
    childProcess.execSync = forbidden;
    const inspected = await research.runResearch300(['--root', f.root], f.dependencies);
    assert.equal(inspected.status, 'inspected');
    const validated = await research.runResearch300(['--root', f.root, '--execution', 'validate'], f.dependencies);
    assert.equal(validated.status, 'validated');
    const evaluated = await research.runResearch300(['--root', f.root, '--execution', 'evaluate-artifacts', '--artifacts', file], f.dependencies);
    assert.equal(evaluated.status, 'unknown');
    assert.equal(evaluated.error, undefined);
  } finally {
    fs.writeFileSync = originalWrite;
    global.fetch = originalFetch;
    childProcess.spawn = originalSpawn;
    childProcess.spawnSync = originalSpawnSync;
    childProcess.execSync = originalExec;
  }
});

test('explicit output is exclusive and cannot overwrite corpus inputs or shared SUT files', async (t) => {
  const f = fixture(t);
  assert.equal(typeof research.runResearch300, 'function');
  const output = path.join(f.root, 'report.json');
  const report = await research.runResearch300(['--root', f.root, '--output', output], f.dependencies);
  assert.equal(JSON.parse(fs.readFileSync(output, 'utf8')).execution, 'inspect');
  assert.equal(report.status, 'inspected');
  const again = await research.runResearch300(['--root', f.root, '--output', output], f.dependencies);
  assert.equal(again.status, 'output_error');
  const oldSutRoot = process.env.SCLAW_ROOT;
  process.env.SCLAW_ROOT = f.root;
  try {
    const blocked = await research.runResearch300(['--root', f.root, '--output', path.join(f.root, 'sut-write.json')], f.dependencies);
    assert.equal(blocked.status, 'output_error');
    assert.equal(fs.existsSync(path.join(f.root, 'sut-write.json')), false);
  } finally {
    if (oldSutRoot === undefined) delete process.env.SCLAW_ROOT;
    else process.env.SCLAW_ROOT = oldSutRoot;
  }
});

test('production corpus provider preserves delayed attachments and rejects private attachment injection', {
  skip: !fs.existsSync(providerPath) && 'Corpus provider is supplied by the contracts branch',
}, async (t) => {
  const { fixture: authoredFixture, publishInputs } = require('../lib/research300-test-fixtures.cjs');
  const f = authoredFixture(t, 'INT-001'), contract = f.contract;
  contract.turns = [
    { id: 't1', instruction: 'Please request the missing beam span before analysis.', expectation: 'clarify', state: null,
      attachments: [], unresolvedFields: ['/nodes'], expectedQuestions: ['What is the beam span?'] },
    { ...contract.turns[0], id: 't2' },
  ];
  f.save();
  f.write('prompt.txt', contract.turns[0].instruction);
  f.write('private-notes.txt', 'hidden-answer-7841');
  publishInputs(f);
  const dependencies = { provider: require(providerPath), stdout: () => {} };
  const args = ['--root', f.root, '--scenario', 'INT-001', '--turn', '1'];
  const first = await research.runResearch300(args, dependencies);
  assert.equal(first.status, 'inspected');
  assert.equal(first.runtime.providerVersion, dependencies.provider.RESPONSE_CONTRACT_VERSION);
  const providerSource = first.runtime.sources.find((source) => source.role === 'provider' && source.path === 'lib/corpus-provider.cjs');
  assert.equal(providerSource.sha256, sha256ForTest(fs.readFileSync(providerPath)));
  assert.match(first.runtime.sourceManifestSha256, /^[a-f0-9]{64}$/);
  assert.equal(first.cases[0].turns[0].input.turnId, 't1');
  assert.deepEqual(first.cases[0].turns[0].input.attachments, []);
  assert.doesNotMatch(JSON.stringify(first), /hidden-answer|model-state|properties.json|geometry.csv/);
  const second = await research.runResearch300([...args.slice(0, -1), '2'], dependencies);
  assert.equal(second.status, 'inspected');
  assert.equal(second.cases[0].turns[0].input.attachments.length, 1);
  assert.match(second.cases[0].turns[0].input.attachments[0].name, /\.md$/);
  contract.attachments.push('model-state-1.json');
  contract.turns[0].attachments.push('model-state-1.json');
  fs.writeFileSync(path.join(f.caseDir, 'contract.json'), JSON.stringify(contract));
  const injected = await research.runResearch300(args, dependencies);
  assert.equal(injected.status, 'corpus_error');
  assert.equal(injected.cases.length, 0);
});
