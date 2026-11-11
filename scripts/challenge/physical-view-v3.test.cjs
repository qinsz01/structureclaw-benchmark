'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {comparePhysicalModels, liftPlanar} = require('./physical-view-v3.cjs');
const {evaluateTurn} = require('./evaluate-v3.cjs');
const read = p => JSON.parse(fs.readFileSync(p));
const original = read(path.resolve(__dirname, '../../corpora/challenge-6-v1/cases/CH-002/private/t1.json')).model;
const opts = {coordinate: 1e-8, property: 1e-6, load: 1e-6, explicitElasticProperties: true, staticTheory: 'Euler-Bernoulli'};

test('fully restrained planar embedding preserves physical model identity and original evidence', () => {
  const spatial = liftPlanar(original), before = structuredClone(spatial);
  // Reversing both transverse axes by 180 degrees preserves the stiffness
  // tensor. Global loads and global node responses keep their meaning.
  for (const e of spatial.elements) if (e.type === 'column') spatial.metadata.elementReferenceVectors[e.id] = [1, 0, 0];
  const input = structuredClone(spatial);
  assert.equal(comparePhysicalModels(spatial, original, opts).pass, true);
  assert.deepEqual(spatial, input);
  assert.equal(before.coordinate_system.dimension, '3d');
  assert.equal(original.coordinate_system.dimension, '2d');
});

test('new transverse freedom, out-of-plane geometry or loading cannot pass as planar equivalence', () => {
  for (const mutate of [m => m.nodes.at(-1).restraints[1] = false,
    m => m.nodes.at(-1).restraints[3] = false,
    m => m.nodes.at(-1).y = .01,
    m => m.load_cases[2].loads[0].fy = 1,
    m => m.load_cases[0].loads[0].wy = 1]) {
    const candidate = liftPlanar(original); mutate(candidate);
    assert.equal(comparePhysicalModels(candidate, original, opts).pass, false);
  }
});

test('different section axes, material, support and member physics still fail', () => {
  for (const mutate of [m => m.elements[0].rotation_angle = 90,
    m => m.materials[0].E *= 1.1,
    m => m.nodes[0].restraints[0] = false,
    m => m.elements.at(-1).type = 'beam']) {
    const candidate = liftPlanar(original); mutate(candidate);
    assert.equal(comparePhysicalModels(candidate, original, opts).pass, false);
  }
});

test('a contradictory planar coordinate declaration is not erased by lifting', () => {
  const candidate = structuredClone(original); candidate.coordinate_system.plane = 'xy';
  assert.equal(comparePhysicalModels(candidate, liftPlanar(original), opts).pass, false);
});

test('a precise short Chinese clarification is accepted; empty/punctuation-only questions fail', () => {
  const reference = {kind: 'clarify', clarificationFields: ['node:N4-0-0:ux']};
  const input = {reference, answer: {clarifications: [{field: 'node:N4-0-0:ux', question: '固定吗？'}]}};
  assert.equal(evaluateTurn(input).passed, true);
  for (const question of ['', '   ', '？']) {
    assert.equal(evaluateTurn({...input, answer: {clarifications: [{field: 'node:N4-0-0:ux', question}]}}).passed, false);
  }
});
