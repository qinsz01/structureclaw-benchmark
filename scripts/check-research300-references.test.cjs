'use strict';

// These hand-authored synthetic payloads test an audit boundary. They are NOT
// solver runs, accepted benchmark cases, reference truth, or solver provenance.
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { test } = require('node:test');
const { auditReferences, main, parseStrictJson } = require('./check-research300-references.cjs');

const ID = 'INT-001';
const TOLERANCE = { absolute: 1e-8, relative: 1e-6 };
const ARTIFACTS = ['native-input-receipt.json', 'native-solver-receipt.json', 'native-raw-responses.json', 'native-checks.json'];
const D = { kind: 'case', id: 'D' };
const L = { kind: 'case', id: 'L' };
const COMBO = { kind: 'combination', id: 'D' };
const copy = value => structuredClone(value);
const hash = value => crypto.createHash('sha256').update(value).digest('hex');
const save = (file, value) => fs.writeFileSync(file, JSON.stringify(value, null, 2) + '\n');
const read = file => JSON.parse(fs.readFileSync(file, 'utf8'));

function fixture(t, engine = 'OpenSees') {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'research300-crosscheck-TEST-ONLY-'));
  t.after(() => fs.rmSync(temp, { recursive: true, force: true }));
  const root = path.join(temp, 'authored');
  const caseDir = path.join(root, 'corpora', 'research-300', 'cases', ID);
  const independentRoot = path.join(temp, 'independent');
  const nativeRoot = path.join(temp, 'native');
  const independentDir = path.join(independentRoot, ID);
  const nativeDir = path.join(nativeRoot, ID);
  for (const dir of [caseDir, independentDir, nativeDir]) fs.mkdirSync(dir, { recursive: true });
  const contract = {
    schemaVersion: 1, id: ID, modelId: 'TEST-ONLY-NOT-TRUTH', family: 'INT', language: '英文', locale: 'en',
    evaluationProfile: 'engineering-v2.3', plannedEngine: engine, modelStates: ['model-state-1.json'],
    attachments: ['附件.txt', '\u{10000}.txt', '\ue000.txt'], status: 'authored-candidate',
    sameEngineTruthStatus: 'pending', inputBlindReview: 'pending', llmEndToEnd: 'not-run',
    turns: [{ id: 't1', state: 1, expectation: 'analyze', instruction: 'TEST ONLY: report the requested values.', attachments: [], unresolvedFields: [], expectedQuestions: [] }],
    requiredOutputs: [], requirementCoverage: [], sourcePlan: { testOnly: 'Synthetic audit test; not benchmark truth.' },
  };
  const model = {
    schema_version: '2.2.0', unit_system: 'SI',
    coordinate_system: { dimension: '2d', plane: 'xz', semantics: 'global-z-up', dof_order: ['ux', 'uy', 'uz', 'rx', 'ry', 'rz'] },
    nodes: [
      { id: 'a', x: 0, y: 0, z: 0, restraints: [true, true, true, true, true, true] },
      { id: 'b', x: 4, y: 0, z: 0, restraints: [false, true, false, true, false, true] },
    ],
    elements: [{ id: 'beam', type: 'beam', nodes: ['a', 'b'], material: 'mat', section: 'sec' }],
    materials: [{ id: 'mat', type: 'elastic', E: 200000, G: 80000, rho: 7850 }],
    sections: [{ id: 'sec', properties: { A: .1, Iy: .001, Iz: .002, J: .001 } }],
    load_cases: [
      { id: 'D', loads: [{ id: 'load-D', type: 'nodal', node: 'b', reference_frame: 'global', fz: -75 }] },
      { id: 'L', loads: [{ id: 'load-L', type: 'nodal', node: 'b', reference_frame: 'global', fz: 56.25 }] },
    ],
    load_combinations: [{ id: 'D', factors: { D: 1, L: 1 } }],
    analysis_control: { self_weight: false, rigid_floor: false, p_delta: false, rigid_offsets: false, construction_stage: false },
    metadata: { testOnly: 'Hand-authored synthetic unit-test inputs; not solver evidence.' },
  };
  function q(id, selection, component = 'uz', unit = 'mm', node = 'b') {
    return { id, selection: copy(selection), location: { kind: 'node', id: node }, component, unit, tolerance: copy(TOLERANCE) };
  }
  const quantities = [q('D-tip', D), q('L-tip', L), q('combination-tip', COMBO), q('D-reaction', D, 'Fz', 'kN', 'a'), q('L-reaction', L, 'Fz', 'kN', 'a')];
  const derived = [
    { id: 'total-reaction', operation: 'sum', operands: ['D-reaction', 'L-reaction'], unit: 'N', description: 'TEST ONLY signed reaction total.' },
    { id: 'delta', operation: 'difference', operands: ['D-tip', 'L-tip'], unit: 'mm', description: 'TEST ONLY signed difference.' },
    { id: 'envelope', operation: 'max_abs', operands: ['D-tip', 'L-tip'], unit: 'mm', description: 'TEST ONLY signed envelope.' },
    { id: 'cascade', operation: 'max_abs', operands: ['delta', 'combination-tip'], unit: 'mm', description: 'TEST ONLY mixed selection cascade.' },
  ];
  const requests = { schemaVersion: 1, states: [{ state: 1, model: 'model-state-1.json', quantities, derived }] };
  save(path.join(caseDir, 'contract.json'), contract);
  save(path.join(caseDir, 'reference-requests.json'), requests);
  save(path.join(caseDir, 'model-state-1.json'), model);
  fs.writeFileSync(path.join(caseDir, 'prompt.txt'), 'TEST ONLY. Synthetic unit-test case; not benchmark truth.\n');
  for (const file of contract.attachments) fs.writeFileSync(path.join(caseDir, file), 'TEST ONLY public source bytes.\n');
  const inputHashes = Object.fromEntries(['contract.json', 'reference-requests.json', ...contract.modelStates].map(file => [file, hash(fs.readFileSync(path.join(caseDir, file)))]));
  const files = [...new Set(['contract.json', 'prompt.txt', 'reference-requests.json', ...contract.modelStates, ...contract.attachments])]
    .sort((a, b) => Buffer.compare(Buffer.from(a), Buffer.from(b)))
    .map(file => ({ path: file, sha256: hash(fs.readFileSync(path.join(caseDir, file))) }));
  const sourceManifest = { schemaVersion: 1, files };
  const sourceHash = hash(Buffer.from(JSON.stringify(sourceManifest), 'utf8'));
  const binding = { inputHashes, sourceHash, sourceManifest };
  // E=200000 MPa, Iy=.001 m4, L=4 m; P L^3/(3 E Iy) gives -8,+6,-2 mm.
  const valued = quantities.map((item, index) => ({ ...copy(item), value: [-8, 6, -2, 75, -56.25][index] }));
  // Deliberately literal expectations: do not import the CLI derivation logic.
  const derivedValues = [
    { ...copy(derived[0]), tolerance: copy(TOLERANCE), value: 18750, operandSelections: [D, L] },
    { ...copy(derived[1]), tolerance: copy(TOLERANCE), value: -14, operandSelections: [D, L] },
    { ...copy(derived[2]), tolerance: copy(TOLERANCE), value: -8, governingOperand: 'D-tip', governingLeafOperands: ['D-tip'], governingSelection: D, governingSelections: [D] },
    { ...copy(derived[3]), tolerance: copy(TOLERANCE), value: -14, governingOperand: 'delta', governingLeafOperands: ['D-tip', 'L-tip'], governingSelection: null, governingSelections: [D, L] },
  ];
  const independent = {
    schemaVersion: 1, id: ID, evaluationProfile: 'engineering-v2.3', referenceKind: 'independent-elastic-matrix',
    notCommercialScoringTruth: true, sameEngineTruthStatus: 'pending', toleranceFrozenBeforeCandidate: true,
    ...copy(binding), states: [{ state: 1, quantities: copy(valued), derived: copy(derivedValues) }],
    checks: [D, L, COMBO].map(selection => ({ state: 1, selection: copy(selection), method: 'independent-direct-stiffness', freeResidual: 0, forceMomentBalance: [0, 0, 0, 0, 0, 0], addedMass: 0 })),
    warnings: ['TEST ONLY: hand-authored synthetic payload, not solver/reference truth.'],
  };
  const solver = {
    module: 'openseespy.opensees', version: '3.7.1', python: 'TEST-ONLY synthetic runtime metadata',
    runnerSha256: hash('TEST ONLY source code'), referenceIoSha256: hash('TEST ONLY IO source code'),
    nativeModuleSha256: hash('TEST ONLY wrapper bytes'), nativeBinaryModule: 'openseespylinux.opensees', nativeBinarySha256: hash('TEST ONLY native binary bytes'),
  };
  const checks = { method: 'native-openseespy', forceMomentBalance: [0, 0, 0, 0, 0, 0], balanceTolerance: [1e-6, 1e-6, 1e-5, 1e-6, 4e-5, 1e-6], freeResidual: 0, equilibriumPassed: true, nativeNodes: 2, nativeElements: 1, addedMass: 0 };
  function rawRun(selection, factors, force, displacement) {
    const nodes = Object.fromEntries(model.nodes.map((node, index) => [node.id, { tag: index + 1, xyz: [node.x, node.y, node.z], fixed: copy(node.restraints), authoredFixed: copy(node.restraints), authored: true }]));
    return {
      state: 1, selection: copy(selection), factors: copy(factors),
      responses: {
        runtime: { module: solver.module, version: solver.version }, analysisReturnCode: 0,
        nodes: {
          a: { tag: 1, displacement: [0, 0, 0, 0, 0, 0], reaction: [0, 0, -force, 0, 4 * force, 0] },
          b: { tag: 2, displacement: [0, 0, displacement, 0, -force * 16 / 400000, 0], reaction: [0, 0, 0, 0, 0, 0] },
        },
        elements: { '1': { localForce: [0, 0, -force, 0, 4 * force, 0, 0, 0, force, 0, 0, 0], globalForce: [0, 0, -force, 0, 4 * force, 0, 0, 0, force, 0, 0, 0] } },
        nativeInput: {
          nodes, members: { beam: { element: copy(model.elements[0]), length: 4, axes: [[1, 0, 0], [0, 1, 0], [0, 0, 1]], properties: { E: 200000000, G: 80000000, A: .1, Iy: .001, Iz: .002, J: .001 }, stationNodes: [[0, 'a'], [4, 'b']], cuts: [0, 4] } },
          segments: [{ tag: 1, member: 'beam', start: 0, end: 4, nodes: ['a', 'b'] }],
          pointLoads: [], nodalLoads: [{ node: 'b', values: [0, 0, force, 0, 0, 0] }], dimension: '2d', nativeNdm: 3, nativeNdf: 6, addedMass: 0,
        },
      },
    };
  }
  const runs = [rawRun(D, { D: 1 }, -75, -.008), rawRun(L, { L: 1 }, 56.25, .006), rawRun(COMBO, { D: 1, L: 1 }, -18.75, -.002)];
  const checkRuns = [D, L, COMBO].map(selection => ({ state: 1, selection: copy(selection), checks: copy(checks) }));
  const native = {
    schemaVersion: 1, id: ID, modelId: contract.modelId, referenceKind: 'native-opensees', method: 'native-openseespy', solver: copy(solver), ...copy(binding),
    sameEngineTruthStatus: 'pending', nativeIndependentReview: 'pending', llmEndToEnd: 'not-run', nativeRole: engine === 'OpenSees' ? 'same-engine-candidate' : 'cross-engine-diagnostic',
    states: [{ state: 1, model: 'model-state-1.json', quantities: copy(valued), derived: copy(derivedValues), checks: checkRuns.map(run => ({ ...copy(run.checks), selection: copy(run.selection) })) }],
    checks: checkRuns.map(run => ({ ...copy(run.checks), state: run.state, selection: copy(run.selection) })),
    warnings: ['TEST ONLY: synthetic raw evidence, not an actual runtime execution.'],
  };
  save(path.join(independentDir, 'independent-reference.json'), independent);
  save(path.join(nativeDir, ARTIFACTS[0]), { schemaVersion: 1, id: ID, ...copy(binding), states: [{ state: 1, model: copy(model), modelPath: 'model-state-1.json' }] });
  save(path.join(nativeDir, ARTIFACTS[1]), { schemaVersion: 1, id: ID, solver: copy(solver), analysis: 'Linear elastic static', units: { length: 'm', force: 'kN', modulusInput: 'MPa', rotation: 'rad' } });
  save(path.join(nativeDir, ARTIFACTS[2]), { schemaVersion: 1, id: ID, runs });
  save(path.join(nativeDir, ARTIFACTS[3]), { schemaVersion: 1, id: ID, runs: checkRuns });
  native.artifacts = ARTIFACTS.map(file => ({ path: file, sha256: hash(fs.readFileSync(path.join(nativeDir, file))) }));
  save(path.join(nativeDir, 'native-opensees-reference.json'), native);
  return { temp, root, caseDir, independentRoot, independentDir, nativeRoot, nativeDir, sourceHash, sourceManifest, options: { root, independentRoot, nativeRoot, caseIds: [ID] } };
}

function mutate(file, callback) { const value = read(file); callback(value); save(file, value); }
function changeReference(f, which, callback) {
  mutate(path.join(which === 'independent' ? f.independentDir : f.nativeDir, which === 'independent' ? 'independent-reference.json' : 'native-opensees-reference.json'), callback);
}
function bindArtifacts(f) {
  changeReference(f, 'native', value => { value.artifacts = ARTIFACTS.map(file => ({ path: file, sha256: hash(fs.readFileSync(path.join(f.nativeDir, file))) })); });
}

test('commercial scoring truth keeps its separate matrix diagnostic in a cross-check', t => {
  const f = fixture(t, 'YJK');
  const primary = path.join(f.independentDir, 'independent-reference.json');
  const diagnostic = path.join(f.independentDir, 'independent-reference-matrix-diagnostic.json');
  fs.copyFileSync(primary, diagnostic);
  save(primary, { id: ID, referenceKind: 'native-yjk', sourceHash: f.sourceHash,
    notCommercialScoringTruth: false, sameEngineTruthStatus: 'verified',
    matrixDiagnostic: { path: path.basename(diagnostic), sha256: hash(fs.readFileSync(diagnostic)) } });
  const report = auditReferences(f.options);
  assert.equal(report.valid, true, JSON.stringify(report.cases[0].errors));
  assert.equal(report.cases[0].artifacts.find(x => x.role === 'independent').path,
    ID + '/independent-reference-matrix-diagnostic.json');
  assert.ok(report.cases[0].artifacts.some(x => x.role === 'active-scoring-reference'));
});

test('a stale commercial matrix diagnostic cannot hide behind qualified scoring truth', t => {
  const f = fixture(t, 'PKPM');
  const primary = path.join(f.independentDir, 'independent-reference.json');
  const diagnostic = path.join(f.independentDir, 'independent-reference-matrix-diagnostic.json');
  fs.copyFileSync(primary, diagnostic);
  save(primary, { id: ID, referenceKind: 'native-pkpm', sourceHash: f.sourceHash,
    notCommercialScoringTruth: false, sameEngineTruthStatus: 'verified',
    matrixDiagnostic: { path: path.basename(diagnostic), sha256: '0'.repeat(64) } });
  expectInvalid(f, /matrix diagnostic.*hash/i);
});

test('commercial diagnostic lookup rejects an engine mismatch or an unreviewed reference', t => {
  const f = fixture(t, 'YJK');
  const primary = path.join(f.independentDir, 'independent-reference.json');
  save(primary, { id: ID, referenceKind: 'native-pkpm', sourceHash: f.sourceHash,
    notCommercialScoringTruth: false, sameEngineTruthStatus: 'verified' });
  expectInvalid(f, /commercial scoring reference/i);
  save(primary, { id: ID, referenceKind: 'native-yjk', sourceHash: f.sourceHash,
    notCommercialScoringTruth: true, sameEngineTruthStatus: 'pending' });
  expectInvalid(f, /commercial scoring reference/i);
});
function expectInvalid(f, pattern) {
  const report = auditReferences(f.options);
  assert.equal(report.valid, false, 'adversarial evidence must not validate');
  assert.equal(report.cases.length, 1);
  assert.ok(report.cases[0].errors.length, 'failure must give a precise per-case error');
  if (pattern) assert.match(report.cases[0].errors.join('\n'), pattern);
  return report.cases[0];
}
function cli(f, extra = []) {
  // The managed test sandbox drops nested child-process stdout. Exercise the
  // exported executable entry point directly instead of treating lost output
  // or a child-process EPERM as a successful CLI run.
  let stdout = '', stderr = '';
  const out = process.stdout.write, err = process.stderr.write;
  process.stdout.write = chunk => { stdout += chunk; return true; };
  process.stderr.write = chunk => { stderr += chunk; return true; };
  try {
    return { status: main(['--root', f.root, '--independent-root', f.independentRoot, '--native-root', f.nativeRoot, '--case', ID, ...extra]), get stdout() { return stdout; }, get stderr() { return stderr; } };
  } finally { process.stdout.write = out; process.stderr.write = err; }
}

test('valid synthetic fixtures bind canonical Unicode source bytes and retain pending acceptance', t => {
  const f = fixture(t);
  const report = auditReferences(f.options);
  assert.equal(report.valid, true, JSON.stringify(report, null, 2));
  const item = report.cases[0];
  assert.equal(item.id, ID);
  assert.equal(item.referenceValidated, true);
  assert.equal(item.nativeAgreement, true);
  assert.equal(item.plannedEngine, 'OpenSees');
  assert.equal(item.sourceHash, f.sourceHash);
  assert.equal(item.comparisonCounts.primitive, 5);
  assert.equal(item.comparisonCounts.derived, 4);
  assert.equal(item.comparisonCounts.passed, 9);
  assert.equal(item.comparisonCounts.failed, 0);
  const serialized = JSON.stringify(item);
  for (const file of ARTIFACTS) assert.ok(serialized.includes(hash(fs.readFileSync(path.join(f.nativeDir, file)))), `audit retains ${file} digest`);
  for (const dirFile of [[f.independentDir, 'independent-reference.json'], [f.nativeDir, 'native-opensees-reference.json']]) assert.ok(serialized.includes(hash(fs.readFileSync(path.join(...dirFile)))), 'audit retains reference digest');
  const solver = read(path.join(f.nativeDir, 'native-opensees-reference.json')).solver;
  for (const value of [solver.version, solver.runnerSha256, solver.referenceIoSha256, solver.nativeBinarySha256]) assert.ok(serialized.includes(value), 'audit retains solver version/source/binary binding');
  assert.doesNotMatch(JSON.stringify(report), /"(?:accepted|nativeVerified)":true/);
  for (const name of ['acceptance.json', 'reference-provenance.json', 'independent-reference.json']) assert.equal(fs.existsSync(path.join(f.caseDir, name)), false);
});

test('commercial planned engine is a cross-engine diagnostic and never native acceptance', t => {
  const f = fixture(t, 'YJK');
  const report = auditReferences(f.options);
  assert.equal(report.valid, true, JSON.stringify(report));
  assert.equal(report.cases[0].plannedEngine, 'YJK');
  assert.equal(report.cases[0].nativeAgreement, true);
  assert.match(JSON.stringify(report), /cross-engine|CROSS-ENGINE/);
  assert.doesNotMatch(JSON.stringify(report), /"(?:accepted|nativeVerified|sameEngine)":true/);
});

for (const filename of ['contract.json', 'prompt.txt', 'model-state-1.json', 'reference-requests.json', '附件.txt']) {
  test(`changed authored bytes invalidate stale source binding: ${filename}`, t => {
    const f = fixture(t);
    fs.appendFileSync(path.join(f.caseDir, filename), '\n');
    expectInvalid(f, /sourceHash|inputHashes|source.*(?:stale|mismatch)/i);
  });
}

for (const which of ['independent', 'native']) {
  test(`${which} cannot relabel the bound authored analysis convention`, t => {
    const f = fixture(t, 'YJK');
    changeReference(f, which, value => { value.analysisConvention = { id: 'commercial-linear-static-v2', bendingTheory: 'Timoshenko' }; });
    expectInvalid(f, /analysisConvention/);
  });
  test(`${which} requires exact current inputHashes and sourceHash`, t => {
    const f = fixture(t);
    changeReference(f, which, value => { value.inputHashes['model-state-1.json'] = '0'.repeat(64); delete value.sourceHash; });
    expectInvalid(f, /inputHashes|sourceHash/);
  });
  test(`${which} rejects stale source manifest even when sourceHash string remains current`, t => {
    const f = fixture(t);
    changeReference(f, which, value => { value.sourceManifest.files[0].sha256 = '0'.repeat(64); });
    expectInvalid(f, /sourceManifest|manifest/i);
  });
  test(`${which} rejects wrong case ID, duplicate states and extra quantities`, t => {
    const f = fixture(t);
    changeReference(f, which, value => { value.id = 'INT-002'; value.states.push(copy(value.states[0])); value.states[0].quantities.push({ ...copy(value.states[0].quantities[0]), id: 'extra' }); });
    expectInvalid(f, /case|\bid\b|duplicate|extra/i);
  });
  test(`${which} rejects omitted requested quantities`, t => {
    const f = fixture(t);
    changeReference(f, which, value => { value.states[0].quantities.splice(0, 1); });
    expectInvalid(f, /D-tip|missing|omitted/i);
  });
  test(`${which} rejects duplicated quantity records`, t => {
    const f = fixture(t);
    changeReference(f, which, value => { value.states[0].quantities.push(copy(value.states[0].quantities[0])); });
    expectInvalid(f, /duplicate/i);
  });
  for (const [field, replacement] of [['selection', L], ['location', { kind: 'node', id: 'a' }], ['component', 'ux'], ['unit', 'm'], ['tolerance', { absolute: 1, relative: .1 }]]) {
    test(`${which} rejects incompatible quantity ${field}`, t => {
      const f = fixture(t);
      changeReference(f, which, value => { value.states[0].quantities[0][field] = copy(replacement); });
      expectInvalid(f, new RegExp(`${field}|D-tip|identity|missing`, 'i'));
    });
  }
}

test('signed primitive disagreement cannot pass magnitude comparison', t => {
  const f = fixture(t);
  changeReference(f, 'native', value => { value.states[0].quantities[0].value = 8; });
  const item = expectInvalid(f, /D-tip|value|agreement/i);
  assert.equal(item.nativeAgreement, false);
});

test('all-close-to-zero comparisons keep frozen absolute and relative tolerance', t => {
  const f = fixture(t);
  for (const which of ['independent', 'native']) changeReference(f, which, value => {
    const state = value.states[0];
    // Keep reaction-derived arithmetic exact while adding a zero displacement.
    state.quantities[2].value = which === 'independent' ? 0 : 2e-8;
  });
  const item = expectInvalid(f, /combination-tip|tolerance|agreement/i);
  assert.equal(item.nativeAgreement, false);
});

test('relative tolerance is based on independent value without magnitude inflation', t => {
  const f = fixture(t);
  changeReference(f, 'native', value => { value.states[0].quantities[2].value = -2.00000202; });
  expectInvalid(f, /combination-tip|tolerance|agreement/i);
});

function addZeroQuantity(f, tolerance) {
  const quantity = { id: 'exact-zero', selection: copy(D), location: { kind: 'node', id: 'a' }, component: 'uz', unit: 'mm', tolerance: copy(tolerance) };
  mutate(path.join(f.caseDir, 'reference-requests.json'), value => { value.states[0].quantities.push(copy(quantity)); });
  for (const which of ['independent', 'native']) changeReference(f, which, value => { value.states[0].quantities.push({ ...copy(quantity), value: 0 }); });
  rebindAuthored(f);
}

test('zero absolute and relative tolerances require exact equality', t => {
  const f = fixture(t);
  addZeroQuantity(f, { absolute: 0, relative: 0 });
  assert.equal(auditReferences(f.options).valid, true);
  changeReference(f, 'native', value => { value.states[0].quantities.at(-1).value = 1e-30; });
  const result = expectInvalid(f, /exact-zero|value|tolerance/i);
  assert.equal(result.comparisons.find(q => q.id === 'exact-zero').limit, 0);
});

test('zero-reference absolute tolerance accepts the exact boundary and rejects the next larger value', t => {
  const f = fixture(t);
  addZeroQuantity(f, { absolute: 1e-8, relative: 0 });
  changeReference(f, 'native', value => { value.states[0].quantities.at(-1).value = 1e-8; });
  const accepted = auditReferences(f.options);
  assert.equal(accepted.valid, true, JSON.stringify(accepted));
  changeReference(f, 'native', value => { value.states[0].quantities.at(-1).value = 1.0000000000000002e-8; });
  expectInvalid(f, /exact-zero|value|tolerance/i);
});

function memberFixture(t) {
  const f = fixture(t);
  mutate(path.join(f.caseDir, 'model-state-1.json'), model => {
    model.load_cases[0].loads.push({ id: 'midpoint-load', type: 'point', element: 'beam', reference_frame: 'global', position: 2, fz: -25 });
  });
  const quantities = [
    { id: 'jump-left', selection: copy(D), location: { kind: 'member', id: 'beam', positionM: 2, side: 'left' }, component: 'V3', unit: 'kN', tolerance: copy(TOLERANCE) },
    { id: 'jump-right', selection: copy(D), location: { kind: 'member', id: 'beam', positionM: 2, side: 'right' }, component: 'V3', unit: 'kN', tolerance: copy(TOLERANCE) },
    { id: 'moment-left', selection: copy(D), location: { kind: 'member', id: 'beam', positionM: 2, side: 'left' }, component: 'M2', unit: 'kN.m', tolerance: copy(TOLERANCE) },
  ];
  mutate(path.join(f.caseDir, 'reference-requests.json'), value => { value.states[0].quantities = copy(quantities); value.states[0].derived = []; });
  mutate(path.join(f.nativeDir, ARTIFACTS[0]), value => { value.states[0].model = read(path.join(f.caseDir, 'model-state-1.json')); });
  for (const which of ['independent', 'native']) changeReference(f, which, value => {
    value.states[0].quantities = quantities.map((q, i) => ({ ...copy(q), value: [100, 75, 150][i] }));
    value.states[0].derived = [];
    value.checks = [value.checks[0]];
    if (which === 'native') {
      value.checks[0].nativeNodes = 3; value.checks[0].nativeElements = 2;
      value.states[0].checks = [value.states[0].checks[0]];
      value.states[0].checks[0].nativeNodes = 3; value.states[0].checks[0].nativeElements = 2;
    }
  });
  mutate(path.join(f.nativeDir, ARTIFACTS[3]), value => { value.runs = [value.runs[0]]; value.runs[0].checks.nativeNodes = 3; value.runs[0].checks.nativeElements = 2; });
  mutate(path.join(f.nativeDir, ARTIFACTS[2]), value => {
    value.runs = [value.runs[0]];
    const raw = value.runs[0].responses;
    const mid = '__native_station_3';
    raw.nodes.a.reaction = [0, 0, 100, 0, -350, 0];
    raw.nodes.b.displacement = [0, 0, -.008833333333333333, 0, .00325, 0];
    raw.nodes[mid] = { tag: 3, displacement: [0, 0, -.0028333333333333335, 0, .0025, 0], reaction: [0, 0, 0, 0, 0, 0] };
    const left = [0, 0, 100, 0, -350, 0, 0, 0, -100, 0, 150, 0];
    const right = [0, 0, 75, 0, -150, 0, 0, 0, -75, 0, 0, 0];
    raw.elements = { '1': { localForce: left, globalForce: copy(left) }, '2': { localForce: right, globalForce: copy(right) } };
    const plan = raw.nativeInput;
    plan.nodes[mid] = { tag: 3, xyz: [2, 0, 0], authored: false, fixed: [false, true, false, true, false, true] };
    plan.members.beam.stationNodes = [[0, 'a'], [2, mid], [4, 'b']];
    plan.members.beam.cuts = [0, 2, 4];
    plan.segments = [{ tag: 1, member: 'beam', start: 0, end: 2, nodes: ['a', mid] }, { tag: 2, member: 'beam', start: 2, end: 4, nodes: [mid, 'b'] }];
    plan.nodalLoads.push({ node: mid, values: [0, 0, -25, 0, 0, 0] });
  });
  rebindAuthored(f);
  return f;
}

test('member station left/right load jump and signed local actions match saved raw vectors', t => {
  const f = memberFixture(t);
  const report = auditReferences(f.options);
  assert.equal(report.valid, true, JSON.stringify(report));
  assert.equal(report.cases[0].comparisonCounts.primitive, 3);
});

for (const [name, modify] of [
  ['selected left/right value swap', quantities => { quantities[0].value = 75; quantities[1].value = 100; }],
  ['signed local moment inversion', quantities => { quantities[2].value = -150; }],
  ['request side relabel', quantities => { quantities[0].location.side = 'right'; }],
]) {
  test(`member raw check rejects ${name} even when both summaries agree`, t => {
    const f = memberFixture(t);
    for (const which of ['independent', 'native']) changeReference(f, which, value => modify(value.states[0].quantities));
    expectInvalid(f, /jump-left|jump-right|moment-left|location|raw|value/i);
  });
}

test('both references cannot collude on an arithmetically incorrect signed sum', t => {
  const f = fixture(t);
  for (const which of ['independent', 'native']) changeReference(f, which, value => { value.states[0].derived[0].value = 131250; });
  expectInvalid(f, /total-reaction|sum|arithmetic/i);
});

for (const [name, modify] of [
  ['derived omission', state => { state.derived.pop(); }],
  ['derived duplicate', state => { state.derived.push(copy(state.derived[0])); }],
  ['wrong derived operation', state => { state.derived[0].operation = 'max'; }],
  ['reversed signed difference operands', state => { state.derived[1].operands.reverse(); }],
  ['cascade fabricated single governing selection', state => { state.derived[3].governingSelection = copy(D); }],
  ['cascade missing governing leaf', state => { state.derived[3].governingLeafOperands.pop(); }],
  ['cascade incorrect governing selections', state => { state.derived[3].governingSelections.reverse(); }],
  ['sum incorrect operand selections', state => { state.derived[0].operandSelections.reverse(); }],
  ['envelope discarded negative sign', state => { state.derived[2].value = 8; }],
]) {
  test(`derived validation rejects ${name}`, t => {
    const f = fixture(t);
    for (const which of ['independent', 'native']) changeReference(f, which, value => modify(value.states[0]));
    expectInvalid(f, /derived|total-reaction|delta|cascade|envelope|governing|operand/i);
  });
}

test('extrema ties preserve first operand and its signed value', t => {
  const f = fixture(t);
  // D-tip and D-tip-copy are distinct authored quantities with equal magnitude.
  const requestsFile = path.join(f.caseDir, 'reference-requests.json');
  mutate(requestsFile, value => {
    value.states[0].quantities.push({ ...copy(value.states[0].quantities[0]), id: 'D-tip-copy' });
    value.states[0].derived.push({ id: 'tie', operation: 'max_abs', operands: ['D-tip', 'D-tip-copy'], unit: 'mm' });
  });
  rebindAuthored(f);
  for (const which of ['independent', 'native']) changeReference(f, which, value => {
    value.states[0].quantities.push({ ...copy(value.states[0].quantities[0]), id: 'D-tip-copy' });
    value.states[0].derived.push({ id: 'tie', operation: 'max_abs', operands: ['D-tip', 'D-tip-copy'], unit: 'mm', tolerance: copy(TOLERANCE), value: -8, governingOperand: 'D-tip', governingLeafOperands: ['D-tip'], governingSelection: copy(D), governingSelections: [copy(D)] });
  });
  assert.equal(auditReferences(f.options).valid, true);
  for (const which of ['independent', 'native']) changeReference(f, which, value => {
    const tie = value.states[0].derived.at(-1);
    tie.governingOperand = 'D-tip-copy'; tie.governingLeafOperands = ['D-tip-copy'];
  });
  expectInvalid(f, /tie|governing/i);
});

// Synthetic signed reactions with independently specified expected governors.
// Values are in kN before encoding each primitive's requested unit; no solver or
// production derivation helper is used to construct the expected co-set.
function extremaFixture(t, options = {}) {
  const f = fixture(t);
  const {
    operation = 'max_abs', values = [-19.2, 19.20000000000002, 1], nativeValues = values,
    units = ['kN', 'kN', 'kN'], frozen = TOLERANCE, explicitTolerance = false,
    chosen = 0, coSet = ['first', 'second'], tiePolicy,
  } = options;
  const ids = ['first', 'second', 'third'], selections = [D, L, COMBO];
  const scale = { kN: 1, N: 1000, MN: .001 };
  const quantities = ids.map((id, i) => ({ id, selection: copy(selections[i]),
    location: { kind: 'node', id: 'a' }, component: 'Fx', unit: units[i], tolerance: copy(TOLERANCE) }));
  const definition = { id: 'tie', operation, operands: ids, unit: 'kN' };
  if (explicitTolerance) definition.tolerance = copy(frozen);
  if (tiePolicy !== undefined) definition.tiePolicy = tiePolicy;
  mutate(path.join(f.caseDir, 'reference-requests.json'), doc => {
    Object.assign(doc.states[0], { quantities: copy(quantities), derived: [copy(definition)] });
  });
  for (const which of ['independent', 'native']) changeReference(f, which, doc => {
    const numbers = which === 'native' ? nativeValues : values;
    doc.states[0].quantities = quantities.map((q, i) => ({ ...copy(q), value: numbers[i] * scale[units[i]] }));
    doc.states[0].derived = [{ ...copy(definition), tolerance: copy(frozen), value: numbers[chosen],
      governingOperand: ids[chosen], governingLeafOperands: [ids[chosen]],
      governingSelection: copy(selections[chosen]), governingSelections: [copy(selections[chosen])],
      coGoverningOperands: copy(coSet) }];
  });
  mutate(path.join(f.nativeDir, ARTIFACTS[2]), doc => {
    doc.runs.forEach((run, i) => { run.responses.nodes.a.reaction[0] = nativeValues[i]; });
  });
  rebindAuthored(f);
  return f;
}

for (const tiePolicy of [undefined, 'first', 'any']) {
  test(`roundoff opposite-sign co-governors keep canonical signed first (${tiePolicy ?? 'default'})`, t => {
    const f = extremaFixture(t, { tiePolicy, nativeValues: [-19.2, 19.2, 1] });
    const report = auditReferences(f.options);
    assert.equal(report.valid, true, JSON.stringify(report.cases[0].errors));
    const comparison = report.cases[0].comparisons.find(q => q.id === 'tie');
    assert.equal(comparison.independent, -19.2);
    assert.equal(comparison.native, -19.2);
    assert.equal(comparison.passed, true);
    assert.equal(report.acceptance, 'pending');
    // Metadata is optional for older references, but arithmetic still uses the
    // same tolerance-aware canonical choice when the co-set is absent.
    for (const which of ['independent', 'native']) changeReference(f, which, doc => { delete doc.states[0].derived[0].coGoverningOperands; });
    assert.equal(auditReferences(f.options).valid, true);
  });
}

for (const operation of ['max', 'min', 'max_abs']) {
  test(`${operation} co-set uses converted units and inclusive frozen absolute plus relative bound`, t => {
    const values = operation === 'min' ? [-9.625, -10, -9.5] : operation === 'max_abs' ? [-9.625, 10, -9.5] : [9.625, 10, 9.5];
    const f = extremaFixture(t, { operation, values, units: ['N', 'MN', 'kN'],
      explicitTolerance: true, frozen: { absolute: .125, relative: .025 } });
    const report = auditReferences(f.options);
    assert.equal(report.valid, true, JSON.stringify(report.cases[0].errors));
    // Third lies outside the .375 kN bound, even though it is a near-extremum.
    for (const which of ['independent', 'native']) changeReference(f, which, doc => { doc.states[0].derived[0].coGoverningOperands.push('third'); });
    expectInvalid(f, /coGoverningOperands/);
  });

  test(`${operation} co-set is measured from true best, never chained through earlier ties`, t => {
    const values = operation === 'min' ? [-9.5, -9.75, -10] : operation === 'max_abs' ? [-9.5, -9.75, 10] : [9.5, 9.75, 10];
    const f = extremaFixture(t, { operation, values, chosen: 1, coSet: ['second', 'third'],
      explicitTolerance: true, frozen: { absolute: .3, relative: 0 } });
    const report = auditReferences(f.options);
    assert.equal(report.valid, true, JSON.stringify(report.cases[0].errors));
  });
}

test('zero frozen tolerance does not turn a strict roundoff extremum into a tie', t => {
  const f = extremaFixture(t, { explicitTolerance: true, frozen: { absolute: 0, relative: 0 }, chosen: 1, coSet: ['second'] });
  const report = auditReferences(f.options);
  assert.equal(report.valid, true, JSON.stringify(report.cases[0].errors));
  for (const which of ['independent', 'native']) changeReference(f, which, doc => { doc.states[0].derived[0].coGoverningOperands.unshift('first'); });
  expectInvalid(f, /coGoverningOperands/);
});

for (const [operation, values, chosen, coSet] of [
  ['max', [-20, 10, -5], 1, ['second']],
  ['min', [-10, 20, 5], 0, ['first']],
]) {
  test(`${operation} scores signed mixed-sign operands without taking magnitudes`, t => {
    const f = extremaFixture(t, { operation, values, chosen, coSet });
    const report = auditReferences(f.options);
    assert.equal(report.valid, true, JSON.stringify(report.cases[0].errors));
  });
}

test('near-zero extrema use frozen absolute tolerance without a unit-sized floor', t => {
  const f = extremaFixture(t, { values: [-(2 ** -30), 2 ** -29, 0], chosen: 1, coSet: ['second'],
    explicitTolerance: true, frozen: { absolute: 2 ** -31, relative: 0 } });
  const report = auditReferences(f.options);
  assert.equal(report.valid, true, JSON.stringify(report.cases[0].errors));
  for (const which of ['independent', 'native']) changeReference(f, which, doc => { doc.states[0].derived[0].coGoverningOperands.unshift('first'); });
  expectInvalid(f, /coGoverningOperands/);
});

for (const which of ['independent', 'native']) {
  for (const coSet of [[], ['first'], ['second', 'first'], ['first', 'second', 'second'], ['first', 'second', 'third'], ['first', 'missing'], null, 'first']) {
    test(`${which} rejects incorrect ordered co-set ${JSON.stringify(coSet)}`, t => {
      const f = extremaFixture(t, { values: [-19.2, 19.2, 1] });
      changeReference(f, which, doc => { doc.states[0].derived[0].coGoverningOperands = coSet; });
      expectInvalid(f, /coGoverningOperands/);
    });
  }
  test(`${which} canonical sign cannot be replaced with the opposite co-governor sign`, t => {
    const f = extremaFixture(t, { values: [-19.2, 19.2, 1], tiePolicy: 'any' });
    changeReference(f, which, doc => { doc.states[0].derived[0].value = 19.2; });
    const item = expectInvalid(f, /arithmetic\/signed value mismatch/);
    assert.equal(item.comparisons.find(q => q.id === 'tie').passed, false, 'final comparison remains signed');
  });
  test(`${which} any reporting policy still rejects a noncanonical reference governor`, t => {
    const f = extremaFixture(t, { values: [-19.2, 19.2, 1], tiePolicy: 'any' });
    changeReference(f, which, doc => Object.assign(doc.states[0].derived[0], {
      value: 19.2, governingOperand: 'second', governingLeafOperands: ['second'], governingSelection: copy(L), governingSelections: [copy(L)],
    }));
    expectInvalid(f, /governingOperand mismatch/);
  });
  test(`${which} recorded tiePolicy cannot override the authored policy`, t => {
    const f = extremaFixture(t, { values: [-19.2, 19.2, 1] });
    changeReference(f, which, doc => { doc.states[0].derived[0].tiePolicy = 'any'; });
    expectInvalid(f, /tiePolicy/);
  });
}

test('both references cannot silently absolute-value a negative canonical co-governor', t => {
  const f = extremaFixture(t, { values: [-19.2, 19.2, 1], tiePolicy: 'any' });
  for (const which of ['independent', 'native']) changeReference(f, which, doc => { doc.states[0].derived[0].value = 19.2; });
  const item = expectInvalid(f, /arithmetic\/signed value mismatch/);
  assert.equal(item.comparisons.find(q => q.id === 'tie').passed, true, 'matching summaries cannot bypass recomputation');
});

test('tied cascade preserves the first direct operand and its multiple leaf selections', t => {
  const f = extremaFixture(t, { values: [-10, 20.00000000000002, 10] });
  const sum = { id: 'delta', operation: 'difference', operands: ['first', 'third'], unit: 'kN' };
  const tie = { id: 'tie', operation: 'max_abs', operands: ['delta', 'second'], unit: 'kN', tiePolicy: 'any' };
  mutate(path.join(f.caseDir, 'reference-requests.json'), doc => { doc.states[0].derived = [copy(sum), copy(tie)]; });
  for (const which of ['independent', 'native']) changeReference(f, which, doc => {
    doc.states[0].derived = [
      { ...copy(sum), tolerance: copy(TOLERANCE), value: -20, operandSelections: [copy(D), copy(COMBO)] },
      { ...copy(tie), tolerance: copy(TOLERANCE), value: -20, governingOperand: 'delta', governingLeafOperands: ['first', 'third'],
        governingSelection: null, governingSelections: [copy(D), copy(COMBO)], coGoverningOperands: ['delta', 'second'] },
    ];
  });
  rebindAuthored(f);
  const report = auditReferences(f.options);
  assert.equal(report.valid, true, JSON.stringify(report.cases[0].errors));
  for (const which of ['independent', 'native']) changeReference(f, which, doc => { doc.states[0].derived[1].governingLeafOperands = ['second']; });
  expectInvalid(f, /governingLeafOperands/);
});

for (const policy of ['last', null, false]) {
  test(`invalid authored tiePolicy ${JSON.stringify(policy)} fails before comparison`, t => {
    const f = extremaFixture(t, { tiePolicy: policy, values: [-19.2, 19.2, 1] });
    expectInvalid(f, /authored input:.*tiePolicy/);
  });
}

test('changing only authored tiePolicy invalidates the old source hash despite matching numbers', t => {
  const f = extremaFixture(t, { values: [-19.2, 19.2, 1] });
  assert.equal(auditReferences(f.options).valid, true);
  mutate(path.join(f.caseDir, 'reference-requests.json'), doc => { doc.states[0].derived[0].tiePolicy = 'any'; });
  const item = expectInvalid(f, /sourceHash missing or stale/);
  assert.equal(item.comparisonCounts.failed, 0);
  assert.equal(item.referenceValidated, false);
  assert.equal(item.nativeAgreement, false);
});

for (const [name, change, pattern] of [
  ['missing operand', state => { state.derived[0].operands[0] = 'missing'; }, /Unknown, ambiguous or forward\/cyclic/],
  ['duplicate operand', state => { state.derived[0].operands[1] = 'first'; }, /Duplicate operand/],
  ['self cycle', state => { state.derived[0].operands[0] = 'tie'; }, /forward\/cyclic/],
  ['forward cycle', state => { state.derived[0].operands[0] = 'later'; state.derived.push({ id: 'later', operation: 'sum', operands: ['tie'], unit: 'kN' }); }, /forward\/cyclic/],
  ['incompatible units', state => { state.derived[0].unit = 'mm'; }, /Incompatible units/],
  ['invalid tolerance', state => { state.derived[0].tolerance = { absolute: -1, relative: 0 }; }, /Invalid frozen tolerance/],
]) {
  test(`tie handling still rejects authored ${name}`, t => {
    const f = extremaFixture(t, { values: [-19.2, 19.2, 1], tiePolicy: 'any' });
    mutate(path.join(f.caseDir, 'reference-requests.json'), doc => change(doc.states[0]));
    rebindAuthored(f);
    const item = expectInvalid(f, pattern);
    assert.equal(item.comparisonCounts.primitive, 0, 'invalid derived requests fail before comparing references');
  });
}

test('same-selection sum and cascaded extrema retain all contributing primitive leaves', t => {
  const f = fixture(t);
  mutate(path.join(f.caseDir, 'reference-requests.json'), value => {
    const state = value.states[0];
    state.quantities.push({ ...copy(state.quantities[0]), id: 'D-tip-copy' });
    state.derived.push({ id: 'same-sum', operation: 'sum', operands: ['D-tip', 'D-tip-copy'], unit: 'mm' });
    state.derived.push({ id: 'same-envelope', operation: 'max_abs', operands: ['same-sum', 'L-tip'], unit: 'mm' });
  });
  rebindAuthored(f);
  for (const which of ['independent', 'native']) changeReference(f, which, value => {
    const state = value.states[0];
    state.quantities.push({ ...copy(state.quantities[0]), id: 'D-tip-copy' });
    state.derived.push({ id: 'same-sum', operation: 'sum', operands: ['D-tip', 'D-tip-copy'], unit: 'mm', tolerance: copy(TOLERANCE), value: -16, selection: copy(D), operandSelections: [copy(D), copy(D)] });
    state.derived.push({ id: 'same-envelope', operation: 'max_abs', operands: ['same-sum', 'L-tip'], unit: 'mm', tolerance: copy(TOLERANCE), value: -16, governingOperand: 'same-sum', governingLeafOperands: ['D-tip', 'D-tip-copy'], governingSelection: copy(D), governingSelections: [copy(D)] });
  });
  const report = auditReferences(f.options);
  assert.equal(report.valid, true, JSON.stringify(report));
  for (const which of ['independent', 'native']) changeReference(f, which, value => { value.states[0].derived.at(-1).governingSelection = copy(L); });
  expectInvalid(f, /same-envelope|governing/i);
});

test('signed sum preserves a small term through severe cancellation', t => {
  const f = fixture(t);
  const modelFile = path.join(f.caseDir, 'model-state-1.json');
  mutate(modelFile, value => {
    value.load_cases[0].loads[0].fz = -1e16;
    value.load_cases[1].loads[0].fz = -1;
    value.load_combinations[0].factors = { D: -1 };
  });
  mutate(path.join(f.nativeDir, ARTIFACTS[0]), value => { value.states[0].model = read(modelFile); });
  const quantities = [D, L, COMBO].map((selection, i) => ({ id: `cancellation-${i}`, selection: copy(selection), location: { kind: 'node', id: 'a' }, component: 'Fz', unit: 'kN', tolerance: copy(TOLERANCE) }));
  const derived = { id: 'cancellation-sum', operation: 'sum', operands: quantities.map(q => q.id), unit: 'kN' };
  mutate(path.join(f.caseDir, 'reference-requests.json'), value => { value.states[0].quantities = copy(quantities); value.states[0].derived = [copy(derived)]; });
  for (const which of ['independent', 'native']) changeReference(f, which, value => {
    value.states[0].quantities = quantities.map((q, i) => ({ ...copy(q), value: [1e16, 1, -1e16][i] }));
    value.states[0].derived = [{ ...copy(derived), tolerance: copy(TOLERANCE), value: 1, operandSelections: [copy(D), copy(L), copy(COMBO)] }];
  });
  mutate(path.join(f.nativeDir, ARTIFACTS[2]), value => value.runs.forEach((run, i) => {
    const force = [-1e16, -1, 1e16][i];
    run.factors = i === 2 ? { D: -1 } : i === 0 ? { D: 1 } : { L: 1 };
    const raw = run.responses;
    raw.nodes.a.reaction = [0, 0, -force, 0, 4 * force, 0];
    raw.nodes.b.displacement = [0, 0, force * 64 / 600000, 0, -force * 16 / 400000, 0];
    raw.elements['1'].localForce = [0, 0, -force, 0, 4 * force, 0, 0, 0, force, 0, 0, 0];
    raw.elements['1'].globalForce = copy(raw.elements['1'].localForce);
    raw.nativeInput.nodalLoads[0].values = [0, 0, force, 0, 0, 0];
  }));
  rebindAuthored(f);
  const report = auditReferences(f.options);
  assert.equal(report.valid, true, JSON.stringify(report));
  for (const which of ['independent', 'native']) changeReference(f, which, value => { value.states[0].derived[0].value = 0; });
  expectInvalid(f, /cancellation-sum|arithmetic|value/i);
});

function rebindAuthored(f) {
  const contract = read(path.join(f.caseDir, 'contract.json'));
  const inputHashes = Object.fromEntries(['contract.json', 'reference-requests.json', ...contract.modelStates].map(file => [file, hash(fs.readFileSync(path.join(f.caseDir, file)))]));
  const sourceManifest = { schemaVersion: 1, files: [...new Set(['contract.json', 'prompt.txt', 'reference-requests.json', ...contract.modelStates, ...contract.attachments])].sort((a, b) => Buffer.compare(Buffer.from(a), Buffer.from(b))).map(file => ({ path: file, sha256: hash(fs.readFileSync(path.join(f.caseDir, file))) })) };
  const binding = { inputHashes, sourceManifest, sourceHash: hash(Buffer.from(JSON.stringify(sourceManifest))) };
  for (const which of ['independent', 'native']) changeReference(f, which, value => Object.assign(value, copy(binding)));
  mutate(path.join(f.nativeDir, ARTIFACTS[0]), value => Object.assign(value, copy(binding)));
  bindArtifacts(f);
}

for (const [which, modify] of [
  ['independent', value => { value.referenceKind = 'native-opensees'; }],
  ['native', value => { value.referenceKind = 'independent-elastic-matrix'; }],
  ['native', value => { value.method = 'SAP2000'; }],
  ['native', value => { value.solver.module = 'sap2000'; }],
  ['native', value => { delete value.solver.version; }],
  ['native', value => { delete value.solver.nativeBinarySha256; }],
  ['native', value => { value.nativeRole = 'cross-engine-diagnostic'; }],
]) {
  test(`${which} rejects wrong engine/kind/runtime provenance: ${modify.toString()}`, t => {
    const f = fixture(t);
    changeReference(f, which, modify);
    expectInvalid(f, /kind|method|solver|module|version|binary|nativeRole|role/i);
  });
}

test('commercial payload relabeled same-engine-candidate is rejected', t => {
  const f = fixture(t, 'PKPM');
  changeReference(f, 'native', value => { value.nativeRole = 'same-engine-candidate'; });
  expectInvalid(f, /role|engine/i);
});

for (const file of ARTIFACTS) {
  test(`missing native artifact fails: ${file}`, t => {
    const f = fixture(t);
    fs.unlinkSync(path.join(f.nativeDir, file));
    expectInvalid(f, /artifact|receipt|ENOENT|missing/i);
  });
  test(`changed native artifact bytes fail frozen digest: ${file}`, t => {
    const f = fixture(t);
    fs.appendFileSync(path.join(f.nativeDir, file), '\n');
    expectInvalid(f, /sha256|hash|digest|artifact/i);
  });
}

for (const [name, modify] of [
  ['missing artifacts', value => { delete value.artifacts; }],
  ['duplicate artifact', value => { value.artifacts.push(copy(value.artifacts[0])); }],
  ['traversal artifact', value => { value.artifacts[0].path = '../native-input-receipt.json'; }],
  ['extra artifact', value => { value.artifacts.push({ path: 'extra.json', sha256: '0'.repeat(64) }); }],
]) {
  test(name, t => {
    const f = fixture(t);
    changeReference(f, 'native', modify);
    expectInvalid(f, /artifact|path|duplicate|extra/i);
  });
}

for (const [name, filename, modify] of [
  ['empty raw evidence', ARTIFACTS[2], value => { value.runs = []; }],
  ['empty raw nodes', ARTIFACTS[2], value => { value.runs[0].responses.nodes = {}; }],
  ['empty raw elements', ARTIFACTS[2], value => { value.runs[0].responses.elements = {}; }],
  ['empty native input', ARTIFACTS[2], value => { value.runs[0].responses.nativeInput = {}; }],
  ['raw authored node geometry mismatch', ARTIFACTS[2], value => { value.runs[0].responses.nativeInput.nodes.b.xyz[0] = 5; }],
  ['raw authored member definition mismatch', ARTIFACTS[2], value => { value.runs[0].responses.nativeInput.members.beam.element.section = 'wrong-section'; }],
  ['raw authored restraint mismatch', ARTIFACTS[2], value => { value.runs[0].responses.nativeInput.nodes.a.authoredFixed[0] = false; }],
  ['raw unsuccessful solve', ARTIFACTS[2], value => { value.runs[0].responses.analysisReturnCode = -1; }],
  ['raw wrong runtime version', ARTIFACTS[2], value => { value.runs[0].responses.runtime.version = 'FAKE-VERSION'; }],
  ['raw D/L factors swapped', ARTIFACTS[2], value => { value.runs[0].factors = { L: 1 }; }],
  ['raw D/L responses swapped behind unchanged selected summaries', ARTIFACTS[2], value => { const a = value.runs[0].responses; value.runs[0].responses = value.runs[1].responses; value.runs[1].responses = a; }],
  ['raw selected D/L swapped', ARTIFACTS[2], value => { const a = value.runs[0].selection; value.runs[0].selection = value.runs[1].selection; value.runs[1].selection = a; }],
  ['raw same-named case/combination swapped', ARTIFACTS[2], value => { value.runs[0].selection = copy(COMBO); }],
  ['raw missing DOF', ARTIFACTS[2], value => { value.runs[0].responses.nodes.a.reaction.pop(); }],
  ['raw duplicate selection', ARTIFACTS[2], value => { value.runs.push(copy(value.runs[0])); }],
  ['input receipt wrong model', ARTIFACTS[0], value => { value.states[0].model.nodes[1].x = 5; }],
  ['input receipt wrong state', ARTIFACTS[0], value => { value.states[0].state = 2; }],
  ['input receipt stale sourceHash', ARTIFACTS[0], value => { value.sourceHash = '0'.repeat(64); }],
  ['solver receipt wrong binary', ARTIFACTS[1], value => { value.solver.nativeBinarySha256 = '0'.repeat(64); }],
  ['raw checks missing selection', ARTIFACTS[3], value => { value.runs.pop(); }],
  ['raw checks changed balance', ARTIFACTS[3], value => { value.runs[0].checks.forceMomentBalance[0] = 1; }],
]) {
  test(`semantic evidence fails even after digest rebinding: ${name}`, t => {
    const f = fixture(t);
    mutate(path.join(f.nativeDir, filename), modify);
    bindArtifacts(f);
    expectInvalid(f, /raw|receipt|native|runtime|balance|model|state|selection|factor|sourceHash|solver|check/i);
  });
}

for (const which of ['independent', 'native']) {
  test(`${which} requires each selected equilibrium check`, t => {
    const f = fixture(t);
    changeReference(f, which, value => { value.checks.splice(0, 1); });
    expectInvalid(f, /check|equilibrium|selection/i);
  });
  test(`${which} rejects duplicated equilibrium check`, t => {
    const f = fixture(t);
    changeReference(f, which, value => { value.checks.push(copy(value.checks[0])); });
    expectInvalid(f, /check|duplicate/i);
  });
  test(`${which} requires finite nonnegative residual`, t => {
    const f = fixture(t);
    changeReference(f, which, value => { value.checks[0].freeResidual = -1; });
    expectInvalid(f, /residual|check/i);
  });
}

for (const [name, modify] of [
  ['equilibriumPassed false', check => { check.equilibriumPassed = false; }],
  ['balance beyond frozen tolerance', check => { check.forceMomentBalance[0] = 1; }],
  ['missing balance tolerance', check => { delete check.balanceTolerance; }],
  ['negative balance tolerance', check => { check.balanceTolerance[0] = -1; }],
  ['free residual beyond balance bounds', check => { check.freeResidual = 1; }],
]) {
  test(`native rejects ${name} consistently in all check copies`, t => {
    const f = fixture(t);
    changeReference(f, 'native', value => { modify(value.checks[0]); modify(value.states[0].checks[0]); });
    mutate(path.join(f.nativeDir, ARTIFACTS[3]), value => modify(value.runs[0].checks));
    bindArtifacts(f);
    expectInvalid(f, /balance|residual|equilibrium|tolerance|check/i);
  });
}

test('strict JSON rejects duplicate object keys, overflowing numbers and non-JSON constants', () => {
  for (const source of ['{"a":1,"a":2}', '{"x":{"a":1,"a":2}}', '{"a":1e999}', '{"a":NaN}', '{"a":Infinity}']) {
    assert.throws(() => parseStrictJson(Buffer.from(source)), undefined, source);
  }
  assert.deepEqual(parseStrictJson(Buffer.from('{"text":"brace } comma, quote \\" Unicode 附件","x":-0.1e2}')), { text: 'brace } comma, quote " Unicode 附件', x: -10 });
});

test('duplicate JSON reference keys fail before numerical comparison', t => {
  const f = fixture(t);
  const file = path.join(f.independentDir, 'independent-reference.json');
  const raw = fs.readFileSync(file, 'utf8');
  fs.writeFileSync(file, raw.replace('"schemaVersion": 1', '"schemaVersion": 1, "schemaVersion": 1'));
  expectInvalid(f, /duplicate|JSON/i);
});

test('overflowing reference value fails strict finite parsing', t => {
  const f = fixture(t);
  const file = path.join(f.independentDir, 'independent-reference.json');
  fs.writeFileSync(file, fs.readFileSync(file, 'utf8').replace('"value": -8', '"value": 1e999'));
  expectInvalid(f, /finite|number|JSON/i);
});

for (const target of ['attachment', 'reference', 'receipt', 'case-directory']) {
  test(`symlink ${target} is rejected even when bytes match`, t => {
    const f = fixture(t);
    const link = target === 'attachment' ? path.join(f.caseDir, '附件.txt') : target === 'reference' ? path.join(f.independentDir, 'independent-reference.json') : target === 'receipt' ? path.join(f.nativeDir, ARTIFACTS[0]) : f.caseDir;
    const relocated = path.join(f.temp, `relocated-${target}`);
    fs.renameSync(link, relocated);
    fs.symlinkSync(relocated, link, target === 'case-directory' ? 'dir' : 'file');
    expectInvalid(f, /symlink|symbolic|safe|link|ENOTDIR/i);
  });
}

test('authored attachment path traversal is rejected', t => {
  const f = fixture(t);
  mutate(path.join(f.caseDir, 'contract.json'), value => { value.attachments.push('../outside.txt'); });
  fs.writeFileSync(path.join(f.caseDir, '..', 'outside.txt'), 'TEST ONLY');
  expectInvalid(f, /path|traversal|relative|unsafe/i);
});

test('CLI prints JSON by default and preserves corpus bytes', t => {
  const f = fixture(t);
  const before = new Map(fs.readdirSync(f.caseDir).map(file => [file, hash(fs.readFileSync(path.join(f.caseDir, file)))]));
  const result = cli(f);
  assert.equal(result.status, 0, result.stderr + result.stdout);
  assert.equal(JSON.parse(result.stdout).valid, true);
  const after = new Map(fs.readdirSync(f.caseDir).map(file => [file, hash(fs.readFileSync(path.join(f.caseDir, file)))]));
  assert.deepEqual(after, before);
});

test('CLI explicit report output creates only a new file and refuses existing output', t => {
  const f = fixture(t);
  const output = path.join(f.temp, 'audit-report.json');
  const first = cli(f, ['--output', output]);
  assert.equal(first.status, 0, first.stderr + first.stdout);
  assert.equal(read(output).valid, true);
  const original = fs.readFileSync(output);
  const second = cli(f, ['--output', output]);
  assert.notEqual(second.status, 0);
  assert.deepEqual(fs.readFileSync(output), original);
});

test('CLI rejects symlink output and duplicate or traversal case selections', t => {
  const f = fixture(t);
  const original = path.join(f.temp, 'existing.txt');
  fs.writeFileSync(original, 'preserve existing bytes');
  const output = path.join(f.temp, 'linked.json');
  fs.symlinkSync(original, output);
  for (const args of [['--output', output], ['--case', ID], ['--case', '../INT-001']]) assert.notEqual(cli(f, args).status, 0);
  assert.equal(fs.readFileSync(original, 'utf8'), 'preserve existing bytes');
});

test('CLI invalid case yields JSON errors and nonzero exit without writing provenance', t => {
  const f = fixture(t);
  fs.appendFileSync(path.join(f.caseDir, 'prompt.txt'), 'CHANGED');
  const result = cli(f);
  assert.notEqual(result.status, 0);
  assert.equal(JSON.parse(result.stdout).valid, false);
  assert.equal(fs.existsSync(path.join(f.caseDir, 'reference-provenance.json')), false);
  assert.equal(fs.existsSync(path.join(f.caseDir, 'acceptance.json')), false);
});
