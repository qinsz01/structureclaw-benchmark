'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs'), path = require('node:path');
const {evaluate, oracleAnswer, loadJobs, validateReference} = require('./evaluate.cjs');
const {counterexamples, renamedNodeJob} = require('./qualify.cjs');
const ROOT = path.resolve(__dirname, '../..');
const WORK = process.env.SCLAW_V2_ORACLE_FIXTURE || path.join(ROOT, '.bench-work/pilot30-oracle-r3-20261028');
const EDITION = process.env.SCLAW_V2_PILOT_EDITION || path.join(ROOT, 'corpora/research300-v2-pilot30-v1');
const read = file => JSON.parse(fs.readFileSync(file, 'utf8'));
const nativeAvailable = fs.existsSync(path.join(WORK, 'runs/P30-STD-001/t1/capture.json'));
const V2_WORK = process.env.SCLAW_V2_TORSION_WORK || path.join(ROOT, '.bench-work/research300-v2-oracle-local-r1-20261028');
const V2_EDITION = process.env.SCLAW_V2_TORSION_EDITION || path.join(ROOT, '.bench-work/research300-v2-authoring-r5-20261028');
const torsionAvailable = fs.existsSync(path.join(V2_WORK, 'runs/V2-INT-045/t1/capture.json'))
  && fs.existsSync(path.join(V2_EDITION, 'cases/V2-INT-045/private/t1.json'));
const nativeSkip = nativeAvailable ? false : 'Protected pilot jobs unavailable; set SCLAW_V2_ORACLE_FIXTURE (and SCLAW_V2_PILOT_EDITION for extracted archives).';
const torsionSkip = torsionAvailable ? false : 'Protected 3D fixture unavailable; set SCLAW_V2_TORSION_WORK and SCLAW_V2_TORSION_EDITION to extracted full-edition archive paths.';
function nativeFixture(caseId = 'P30-STD-001', turnId = 't1') {
  const ref = read(path.join(EDITION, 'cases', caseId, 'private', turnId + '.json'));
  const capture = read(path.join(WORK, 'runs', caseId, turnId, 'capture.json'));
  const jobs = loadJobs(WORK, caseId, capture.jobIds);
  return {ref, capture, jobs};
}

// Algebraic identity control over retained native results; no new native run
// is claimed. Rename submitted entity IDs and corresponding output keys alike.
function renamedNodes(job, prefix) {
  return renamedNodeJob(job, prefix);
}

function reversedZeroRollJob(job) {
  const result = structuredClone(job), model = result.state.model;
  const nodes = new Map(model.nodes.map(node => [node.id, node]));
  const length = id => {
    const ends = model.elements.find(element => element.id === id).nodes.map(id => nodes.get(id));
    return Math.hypot(...['x', 'y', 'z'].map(axis => ends[1][axis] - ends[0][axis]));
  };
  for (const element of model.elements) {
    assert.equal(element.rotation_angle || 0, 0, 'This independent sign fixture assumes zero roll');
    element.nodes.reverse();
  }
  for (const loadCase of model.load_cases) for (const load of loadCase.loads) {
    if (!load.element) continue;
    assert.equal(load.reference_frame || 'global', 'global');
    const size = length(load.element);
    if (load.type === 'point') load.position = size - load.position;
    if (load.start !== undefined || load.end !== undefined) {
      const start = load.start || 0, end = load.end ?? size;
      load.start = size - end; load.end = size - start;
    }
  }
  const planar = model.coordinate_system.dimension === '2d';
  for (const record of Object.values(result.state.analysisResult.results))
    for (const member of record.data.memberResponses || []) {
      if (member.state !== 'recovered') continue;
      // Independent zero-roll cut balance: reversing the face and local x
      // leaves N/T unchanged. In XZ, local y stays fixed so V2/M2 negate;
      // spatial Z-reference axes instead keep local z, so V3/M3 negate.
      member.axes = member.axes.map((axis, i) => axis.map(value => value * (i === 0 || i === (planar ? 2 : 1) ? -1 : 1)));
      member.samples = member.samples.map(sample => ({...sample, x: member.length - sample.x,
        ...(sample.side ? {side: sample.side === 'left' ? 'right' : 'left'} : {}),
        ...(planar ? {V2: -sample.V2, M2: -sample.M2} : {V3: -sample.V3, M3: -sample.M3})})).reverse();
    }
  return result;
}

test('an unresolved physical input cannot claim invented jobs or scheme results', () => {
  const ref = {kind: 'clarify', engine: 'OpenSees', clarificationFields: ['parameters:groundMotionUnit']};
  const good = {clarifications: [{field: 'parameters:groundMotionUnit', question: '请确认加速度单位。'}],
    jobIds: [], quantities: []};
  assert.equal(evaluate(ref, good, [], []).passed, true);
  assert.equal(evaluate(ref, {...good, jobIds: ['invented']}, [], []).passed, false);
  assert.equal(evaluate(ref, {...good, selectedScheme: 'A'}, [], []).passed, false);
  assert.equal(evaluate(ref, {...good, derived: [{id: 'fiction', value: 1}]}, [], []).passed, false);
});

test('malformed issue identities and unsupported modal scope fail as reference errors', () => {
  assert.throws(() => validateReference({kind: 'static', expectedIssuePaths: ['/a', '/a']}), /unique/);
  assert.throws(() => validateReference({kind: 'static', expectedIssuePaths: ['a']}), /pointer/);
  assert.throws(() => validateReference({kind: 'static', expectedIssuePaths: ['/bad~escape']}), /pointer/);
  assert.throws(() => validateReference({kind: 'query', requireFreshExecution: true}), /fresh/);
  assert.throws(() => validateReference({kind: 'modal', requireShapes: true, parameters: {direction: 'y'}}), /X-direction/);
});

test('actual protected native evidence still passes the unchanged numerical checks', {skip: nativeSkip}, () => {
  const {ref, capture, jobs} = nativeFixture();
  const answer = oracleAnswer(ref, jobs);
  assert.equal(evaluate(ref, answer, jobs, capture.currentJobIds).passed, true);
});

test('audit paths are exact while concise Chinese and English explanations are equivalent', {skip: nativeSkip}, () => {
  const {ref, capture, jobs} = nativeFixture();
  ref.expectedIssuePaths = ['/materials/M1/E', '/elements/E01/type'];
  const answer = oracleAnswer(ref, jobs);
  assert.equal(evaluate(ref, answer, jobs, capture.currentJobIds).passed, true);
  answer.issues[0].reason = '改正。';
  answer.issues[1].reason = 'Restore the issued beam type.';
  assert.equal(evaluate(ref, answer, jobs, capture.currentJobIds).passed, true);
  const wrong = structuredClone(answer); wrong.issues[0].path = '/materials/OTHER/E';
  assert.equal(evaluate(ref, wrong, jobs, capture.currentJobIds).passed, false);
  const missing = structuredClone(answer); missing.issues.pop();
  assert.equal(evaluate(ref, missing, jobs, capture.currentJobIds).passed, false);
  const duplicate = structuredClone(answer); duplicate.issues[1].path = duplicate.issues[0].path;
  assert.equal(evaluate(ref, duplicate, jobs, capture.currentJobIds).passed, false);
  const blank = structuredClone(answer); blank.issues[0].reason = '???';
  assert.equal(evaluate(ref, blank, jobs, capture.currentJobIds).passed, false);
});

test('correct issue words cannot hide an incorrect executed model', {skip: nativeSkip}, () => {
  const {ref, capture, jobs} = nativeFixture();
  ref.expectedIssuePaths = ['/materials/M1/E'];
  const answer = oracleAnswer(ref, jobs);
  const incorrect = structuredClone(jobs);
  incorrect[0].state.model.materials[0].E *= .5;
  assert.equal(evaluate(ref, answer, incorrect, capture.currentJobIds).passed, false);
  assert.equal(evaluate(ref, answer, [], []).passed, false);
});

test('an explicit freshness requirement is bound to protected current-turn jobs', {skip: nativeSkip}, () => {
  const {ref, capture, jobs} = nativeFixture();
  ref.requireFreshExecution = true;
  const answer = oracleAnswer(ref, jobs);
  assert.equal(evaluate(ref, answer, jobs, capture.currentJobIds).passed, true);
  assert.equal(evaluate(ref, answer, jobs, []).passed, false);
});

test('generic audit counterexamples reject wrong fields, values and active stiffness', {skip: nativeSkip}, () => {
  const {ref, capture, jobs} = nativeFixture();
  ref.expectedIssuePaths = ['/materials/M1/E'];
  const answer = oracleAnswer(ref, jobs);
  const controls = counterexamples(ref, answer, jobs, capture.currentJobIds);
  assert(controls.some(row => row.name === 'wrong-model-issue-path'));
  assert(controls.some(row => row.name === 'wrong-active-stiffness'));
  assert(controls.some(row => row.name === 'concise-Chinese-model-issue'));
  assert(controls.every(row => row.passed), JSON.stringify(controls.filter(row => !row.passed)));
});

test('different legal node IDs in each selection retain their own response mapping', {skip: nativeSkip}, () => {
  const {ref, capture, jobs} = nativeFixture('P30-STD-006');
  const original = JSON.stringify(jobs), answer = oracleAnswer(ref, jobs);
  const renamed = jobs.map((job, i) => renamedNodes(job, 'JOB' + i + '_'));
  const result = evaluate(ref, answer, renamed, capture.currentJobIds);
  assert.equal(result.passed, true, JSON.stringify(result.metrics.filter(row => !row.pass)));
  assert.deepEqual(oracleAnswer(ref, renamed), answer);
  const incorrect = structuredClone(renamed);
  incorrect[0].state.model.materials[0].E *= .8;
  assert.equal(evaluate(ref, answer, incorrect, capture.currentJobIds).passed, false);
  assert.equal(JSON.stringify(jobs), original, 'Protected native evidence is immutable');
});

test('every declared derived output and its correct governor must be reported', {skip: nativeSkip}, () => {
  const {ref, capture, jobs} = nativeFixture('P30-INT-003', 't2');
  const answer = oracleAnswer(ref, jobs);
  assert.equal(evaluate(ref, answer, jobs, capture.currentJobIds).passed, true);
  for (const kind of ['missing', 'empty', 'governor']) {
    const altered = structuredClone(answer);
    if (kind === 'missing') delete altered.derived;
    if (kind === 'empty') altered.derived = [];
    if (kind === 'governor') altered.derived[0].governingOperand = 'not-an-issued-operand';
    assert.equal(evaluate(ref, altered, jobs, capture.currentJobIds).passed, false, kind);
  }
  const controls = counterexamples(ref, answer, jobs, capture.currentJobIds);
  for (const name of ['missing-derived-field', 'empty-derived-report', 'wrong-derived-governor'])
    assert(controls.some(row => row.name === name && row.passed), name);
});

test('required modal, transient and scheme fields cannot disappear as optional reports', {skip: nativeSkip}, () => {
  const manifest = read(path.join(EDITION, 'manifest.json'));
  for (const kind of ['modal', 'transient', 'scheme']) {
    let fixture, folder;
    for (const item of manifest.cases) {
      const turn = item.turns.find(turn => {
        const ref = read(path.join(EDITION, turn.private));
        return ref.kind === kind && (kind !== 'modal' || ref.requireShapes);
      });
      if (turn) { fixture = nativeFixture(item.id, turn.id); folder = path.join(WORK, 'runs', item.id, turn.id); break; }
    }
    const {ref, capture, jobs} = fixture;
    const schemeJobs = kind === 'scheme' ? read(path.join(folder, 'scheme-jobs.json')) : {};
    const answer = oracleAnswer(ref, jobs, schemeJobs);
    assert.equal(evaluate(ref, answer, jobs, capture.currentJobIds).passed, true, kind);
    for (const field of ['quantities', 'jobIds']) {
      if (field === 'quantities' && kind === 'scheme') continue;
      const omitted = structuredClone(answer); delete omitted[field];
      assert.equal(evaluate(ref, omitted, jobs, capture.currentJobIds).passed, false, kind + ':' + field);
    }
    const fields = kind === 'modal' ? ['modeShapes'] : kind === 'transient' ? ['time']
      : ['selectedScheme', 'maximum', 'volume', 'feasible'];
    for (const field of fields) {
      const altered = structuredClone(answer);
      if (field === 'time') delete altered.quantities.find(row => row.time !== undefined).time;
      else if (['maximum', 'volume', 'feasible'].includes(field)) delete altered.schemes[0][field];
      else delete altered[field];
      assert.equal(evaluate(ref, altered, jobs, capture.currentJobIds).passed, false, kind + ':' + field);
    }
  }
});

test('reversed OpenSees bending cuts preserve beam equilibrium and exact one-sided endpoints', {skip: nativeSkip}, () => {
  const {ref, capture, jobs} = nativeFixture();
  const answer = oracleAnswer(ref, jobs), reverse = jobs.map(reversedZeroRollJob);
  const cuts = answer.quantities.filter(row => row.id.includes('member:'));
  assert.equal(cuts.length, 2);
  // Independent simply supported beam: R=20*6/2=60 kN,
  // signed M2(3)=-R*3+20*3^2/2=-90 kN.m at both adjacent cuts.
  for (const row of cuts) assert(Math.abs(row.value - (-60 * 3 + 20 * 3 ** 2 / 2)) < 1e-9);
  assert.equal(evaluate(ref, answer, reverse, capture.currentJobIds).passed, true);
  assert.deepEqual(oracleAnswer(ref, reverse), answer);
  for (const corruption of ['sign', 'axis', 'missing-axis', 'side']) {
    const wrong = structuredClone(reverse);
    const row = Object.values(wrong[0].state.analysisResult.results)[0].data.memberResponses.find(row => row.id === 'E01');
    if (corruption === 'sign') for (const sample of row.samples) sample.M2 *= -1;
    if (corruption === 'axis') row.axes = [[1, 0, 0], [0, 1, 0], [0, 0, 1]];
    if (corruption === 'missing-axis') delete row.axes;
    if (corruption === 'side') row.samples.find(sample => sample.x === 0 && sample.side === 'right').side = 'left';
    assert.equal(evaluate(ref, answer, wrong, capture.currentJobIds).passed, false, corruption);
  }
});

test('reversed unloaded truss N keeps its tension sign without bending-axis requirements', {skip: nativeSkip}, () => {
  const {ref, capture, jobs} = nativeFixture('P30-MM-002');
  assert(jobs.every(job => job.state.model.elements.every(element => ['truss', 'brace'].includes(element.type))));
  const answer = oracleAnswer(ref, jobs), reverse = structuredClone(jobs);
  for (const job of reverse) {
    for (const element of job.state.model.elements) element.nodes.reverse();
    for (const result of Object.values(job.state.analysisResult.results))
      for (const member of result.data.memberResponses || []) {
        assert.equal(member.state, 'truss');
        delete member.axes;
        member.samples = member.samples.map(sample => ({...sample, x: member.length - sample.x,
          ...(sample.side ? {side: sample.side === 'left' ? 'right' : 'left'} : {})})).reverse();
      }
  }
  assert.equal(evaluate(ref, answer, reverse, capture.currentJobIds).passed, true);
  assert.deepEqual(oracleAnswer(ref, reverse), answer);
  const wrong = structuredClone(reverse);
  for (const job of wrong) for (const result of Object.values(job.state.analysisResult.results))
    for (const member of result.data.memberResponses || []) for (const sample of member.samples) sample.N *= -1;
  assert.equal(evaluate(ref, answer, wrong, capture.currentJobIds).passed, false);
});

test('retained 3D native torsion agrees with the independent reference after endpoint reversal', {skip: torsionSkip}, () => {
  const cid = 'V2-INT-045', ref = read(path.join(V2_EDITION, 'cases', cid, 'private/t1.json'));
  const capture = read(path.join(V2_WORK, 'runs', cid, 't1/capture.json'));
  const jobs = loadJobs(V2_WORK, cid, capture.jobIds), answer = oracleAnswer(ref, jobs);
  const torsion = ref.requests.find(q => q.component === 'T' && Math.abs(q.value) > .001);
  assert(torsion, 'A real nonzero independently solved torsion case is required');
  const row = answer.quantities.find(row => row.id === torsion.id);
  assert(Math.abs(row.value - torsion.value) < 1e-8, 'Native T must match the independent FE reference');
  const reverse = jobs.map(reversedZeroRollJob);
  assert.equal(evaluate(ref, answer, reverse, capture.currentJobIds).passed, true);
  const reread = oracleAnswer(ref, reverse).quantities.find(q => q.id === torsion.id);
  assert(Math.abs(reread.value - row.value) < 1e-12);
  const selected = jobs.find(job => job.state.analysisResult.results['combination:SERVICE']);
  const member = selected.state.analysisResult.results['combination:SERVICE'].data.memberResponses.find(row => row.id === torsion.location.id);
  const ends = member.samples.filter(sample => sample.side);
  assert(Math.abs(ends[0].T - ends.at(-1).T) < 1e-10, 'No distributed torsional moment: end cuts have equal signed T');
  const wrong = structuredClone(reverse);
  for (const job of wrong) for (const result of Object.values(job.state.analysisResult.results))
    for (const member of result.data.memberResponses || []) if (member.id === torsion.location.id)
      for (const sample of member.samples) sample.T *= -1;
  assert.equal(evaluate(ref, answer, wrong, capture.currentJobIds).passed, false, 'Wrong native torsion sign is rejected');
});
