import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import ts from 'typescript';

const source = fs.readFileSync(new URL('../src/reference-math.ts', import.meta.url), 'utf8');
const js = ts.transpileModule(source, {
  compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ES2022 },
}).outputText;
const { beamCheck, referenceResult, memberMoment } = await import(
  `data:text/javascript;base64,${Buffer.from(js).toString('base64')}`
);
const reference = (id) =>
  JSON.parse(fs.readFileSync(new URL(`../public/data/models/${id}.json`, import.meta.url)));

test('simple beam reproduces signed deflection, reactions and equilibrium without changing input', () => {
  const r = reference('beam-simple-6m'),
    before = JSON.stringify(r),
    c = beamCheck(r);
  assert.equal(c.family, 'uniform');
  assert.equal(c.E, 205000000);
  assert.ok(Math.abs(c.checks[0].expected - -0.016463414634146342) < 1e-15);
  for (const check of c.checks) assert.ok(Math.abs(check.expected - check.actual) < 1e-10);
  assert.ok(Math.abs(c.forceResidual) < 1e-10);
  assert.ok(Math.abs(c.momentResidual) < 1e-10);
  assert.equal(c.samples[40].moment, 90);
  assert.equal(c.samples[0].shear, 60);
  assert.equal(c.samples[80].shear, -60);
  assert.equal(JSON.stringify(r), before);
});
test('cantilever endpoints, sign convention and load scaling are independent of frozen values', () => {
  const r = reference('beam-cantilever-3m-point10'),
    c = beamCheck(r);
  assert.equal(c.family, 'cantilever');
  assert.equal(c.samples[0].moment, -30);
  assert.ok(Math.abs(c.momentResidual) < 1e-10);
  assert.equal(Math.abs(c.samples[80].moment), 0);
  assert.ok(Math.abs(c.checks[0].expected - (-10 * 27) / (3 * 205000000 * 0.0001)) < 1e-15);
  assert.ok(Math.abs(c.checks[0].expected - c.checks[0].actual) < 1e-10);
  r.numerical.analysisSelection.factors.LC1 = 2;
  assert.equal(beamCheck(r).checks[0].expected, 2 * c.checks[0].expected);
});
test('ineligible geometry, loads, units and restraints do not get a beam solution', () => {
  const changes = [
    (r) => (r.model.nodes[1].z = 1),
    (r) => (r.model.nodes[1].restraints = [false, false, true, false, false, false]),
    (r) => (r.model.load_cases[0].loads[0].wz = -25),
    (r) => (r.model.load_cases[0].loads[0].reference_frame = 'local'),
    (r) =>
      r.model.load_cases[0].loads.push({
        type: 'nodal',
        node: '2',
        fz: -1,
        reference_frame: 'global',
      }),
    (r) => (r.model.unit_system = 'US'),
    (r) => (r.numerical.analysisSelection.factors = { missing: 1 }),
    (r) => (r.model.elements[1].nodes = ['1', '2']),
  ];
  for (const mutate of changes) {
    const r = reference('beam-simple-6m');
    mutate(r);
    assert.equal(beamCheck(r), null);
  }
});
test('engine gating never borrows numerical results and incomplete moments stay unavailable', () => {
  const r = reference('beam-simple-6m');
  assert.equal(referenceResult(r, []).result, undefined);
  assert.equal(
    referenceResult(r, [
      { type: 'numerical_matches', groundTruthId: r.id, engineId: 'builtin-pkpm' },
    ]).result,
    undefined,
  );
  assert.equal(memberMoment({ n1: { M: 12 } }), undefined);
  assert.equal(memberMoment({ n1: { M: -12 }, n2: { M: 9 } }), 12);
});
test('all eligible frozen models agree at comparable analytical control locations', () => {
  let count = 0;
  for (const file of fs.readdirSync(new URL('../public/data/models/', import.meta.url))) {
    const r = reference(file.replace('.json', '')),
      c = beamCheck(r);
    if (!c) continue;
    count++;
    for (const v of c.checks)
      if (v.actual !== undefined)
        assert.ok(
          Math.abs(v.actual - v.expected) < 1e-7 + 1e-6 * Math.abs(v.expected),
          `${r.id}/${v.label}: ${v.actual} != ${v.expected}`,
        );
  }
  assert.ok(count >= 2);
});
