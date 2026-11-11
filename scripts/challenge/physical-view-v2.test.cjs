'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {comparePhysicalModels} = require('./physical-view-v2.cjs');
const {evaluateTurn, oracleAnswer} = require('./evaluate-v2.cjs');
const root = path.resolve(__dirname, '../..');
const read = p => JSON.parse(fs.readFileSync(p));
const reference = read(path.join(root, 'corpora/challenge-6-v1/cases/CH-001/private/t1.json'));
const opts = {coordinate: 1e-8, property: 1e-6, load: 1e-6, explicitElasticProperties: true, staticTheory: 'Euler-Bernoulli'};

test('SDK-equivalent omitted plane, known zero factors and inactive case labels compare equally', () => {
  const model = structuredClone(reference.model);
  delete model.coordinate_system.plane;
  for (const c of model.load_cases) c.type = {D: 'dead', L: 'live', WX: 'wind'}[c.id];
  model.load_combinations[0].factors.WX = 0;
  const before = structuredClone(model);
  assert.equal(comparePhysicalModels(model, reference.model, opts).pass, true);
  assert.deepEqual(model, before);
});

test('positive tiny factors, unknown zero cases and conflicting 3-D plane remain errors', () => {
  for (const change of [m => m.load_combinations[0].factors.UNKNOWN = 0,
    m => m.load_combinations[0].factors.WX = 1e-12,
    m => m.coordinate_system.plane = 'xz']) {
    const model = structuredClone(reference.model); change(model);
    assert.equal(comparePhysicalModels(model, reference.model, opts).pass, false);
  }
});

test('case classifications are not erased when automatic gravity or another control is enabled', () => {
  const expected = structuredClone(reference.model), model = structuredClone(reference.model);
  expected.analysis_control.self_weight = true; model.analysis_control.self_weight = true;
  model.load_cases[0].type = 'dead'; expected.load_cases[0].type = 'live';
  assert.equal(comparePhysicalModels(model, expected, opts).pass, false);
});

test('actual section, local axes, boundary, load and element-type errors still fail', () => {
  for (const change of [m => m.sections[0].properties.Iy *= 1.1,
    m => m.elements[0].rotation_angle = 90,
    m => m.nodes[0].restraints[0] = false,
    m => m.load_cases[0].loads[0].wz *= -1,
    m => m.elements.at(-1).type = 'beam']) {
    const model = structuredClone(reference.model); change(model);
    assert.equal(comparePhysicalModels(model, reference.model, opts).pass, false);
  }
});

// Exercise the v2 evaluator on the original retained backend oracle outputs.
// This uses private maintainer controls, not a candidate answer or score.
test('all 18 original oracle turns and adversarial evidence controls survive SDK normalization', t => {
  const work = process.env.CHALLENGE_ORACLE_WORK || path.join(root, '.bench-work/challenge-6-v1-oracle-r2-20261028');
  if (!fs.existsSync(path.join(work, 'summary.json'))) {
    t.skip('Integration check requires the retained maintainer oracle; run verify.py or set CHALLENGE_ORACLE_WORK');
    return;
  }
  const manifest = read(path.join(root, 'corpora/challenge-6-v1/manifest.json'));
  let turns = 0, negatives = 0;
  for (const item of manifest.cases) for (const turn of item.turns) {
    const ref = read(path.join(root, 'corpora/challenge-6-v1', turn.private));
    const folder = path.join(work, item.id, turn.id);
    const state = fs.existsSync(path.join(folder, 'state.json')) ? read(path.join(folder, 'state.json')) : null;
    const trustedStates = state ? read(path.join(folder, 'trusted.json')) : [];
    const answer = state ? oracleAnswer(ref, state) : read(path.join(folder, 'answer.json'));
    const input = {reference: ref, state, trustedStates, answer,
      currentRunIds: trustedStates.map(s => s.analysisResult.runId), requestsCreated: []};
    assert.equal(evaluateTurn(input).passed, true, item.id + '/' + turn.id); turns++;
    if (state) {
      assert.equal(evaluateTurn({...input, trustedStates: []}).passed, false); negatives++;
      const corrupted = structuredClone(state);
      const data = Object.values(corrupted.analysisResult.results)[0].data;
      data.displacements[Object.keys(data.displacements)[0]].ux += 1;
      assert.equal(evaluateTurn({...input, state: corrupted}).passed, false); negatives++;
      const wrongModel = structuredClone(state); wrongModel.model.sections[0].properties.Iz *= 2;
      assert.equal(evaluateTurn({...input, state: wrongModel}).passed, false); negatives++;
      const wrongReport = structuredClone(answer); wrongReport.quantities[0].value += 1;
      assert.equal(evaluateTurn({...input, answer: wrongReport}).passed, false); negatives++;
    } else {
      assert.equal(evaluateTurn({...input, requestsCreated: ['unauthorized-before-clarification']}).passed, false); negatives++;
    }
  }
  assert.equal(turns, 18);
  assert.equal(negatives, 66);
});
