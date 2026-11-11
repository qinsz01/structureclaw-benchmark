'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const {POLICY, engineeringComparison} = require('./cross-engine-engineering-policy.cjs');
const {applyPolicy} = require('../scripts/check-research300-engineering.cjs');

function moment(overrides = {}) {
  return {value: 0., component: 'M3', unit: 'kN.m',
    location: {kind: 'member', id: 'beam', positionM: 0, side: 'right'},
    tolerance: {absolute: 1e-8, relative: 1e-6}, ...overrides};
}

test('policy changes the cross-engine budget without claiming a vendor bound or changing grading', () => {
  assert.equal(POLICY.absoluteFloor, 1e-7);
  assert.equal(POLICY.nativeArithmeticBound, false);
  assert.equal(POLICY.candidateGradingChanged, false);
  assert.equal(POLICY.acceptanceRegionChanges, true);
  const result = engineeringComparison(moment(), 9e-8);
  assert.equal(result.strictPass, false);
  assert.equal(result.engineeringPass, true);
  assert.equal(engineeringComparison(moment(), 1.1e-7).engineeringPass, false);
});

test('unit conversions preserve one physical moment budget', () => {
  for (const [unit, multiplier] of [['kN.m', 1], ['N.m', 1000], ['kN.mm', 1000], ['N.mm', 1e6]]) {
    const q = moment({unit, tolerance: {absolute: 1e-8 * multiplier, relative: 1e-6}});
    assert.equal(engineeringComparison(q, 9e-8 * multiplier).engineeringPass, true, unit);
    assert.equal(engineeringComparison(q, 1.1e-7 * multiplier).engineeringPass, false, unit);
  }
});

test('torque and support reaction moments use the same physical budget', () => {
  for (const component of ['T', 'M2', 'M3']) {
    assert.equal(engineeringComparison(moment({component}), 5e-8).engineeringPass, true);
  }
  for (const component of ['Mx', 'My', 'Mz']) {
    assert.equal(engineeringComparison(moment({component, location: {kind: 'node', id: 'support'}}), 5e-8).engineeringPass, true);
  }
});

test('force, displacement, rotation and derived tolerances are unchanged', () => {
  for (const [component, unit] of [['N', 'kN'], ['V2', 'kN'], ['ux', 'm'], ['rx', 'rad']]) {
    const result = engineeringComparison(moment({component, unit}), 2e-8);
    assert.equal(result.eligible, false);
    assert.equal(result.strictLimit, result.engineeringLimit);
    assert.equal(result.engineeringPass, false);
  }
  const derived = engineeringComparison(moment(), 2e-8, {family: 'derived'});
  assert.equal(derived.eligible, false);
  assert.equal(derived.engineeringPass, false);
});

test('wrong moment dimension is rejected instead of receiving a unitless allowance', () => {
  assert.throws(() => engineeringComparison(moment({unit: 'm'}), 0), /moment unit/);
});

test('relative tolerance remains frozen and stricter floor cannot narrow existing acceptance', () => {
  const large = engineeringComparison(moment({value: 1000}), 1000.002);
  assert.equal(large.engineeringTolerance.relative, 1e-6);
  assert.equal(large.engineeringPass, false);
  const existing = engineeringComparison(moment({tolerance: {absolute: 1e-5, relative: 1e-6}}), 5e-6);
  assert.equal(existing.strictPass, true);
  assert.equal(existing.engineeringLimit, existing.strictLimit);
});

test('observed small discrepancy passes but zeroing, sign, scale and axis mistakes still fail', () => {
  const q = moment({value: -0.0037927627563476562});
  assert.equal(engineeringComparison(q, -0.0037927300670383968).engineeringPass, true);
  for (const wrong of [0, -q.value, q.value * 1.001, q.value * 1000, 12.180032730102539]) {
    assert.equal(engineeringComparison(q, wrong).engineeringPass, false, String(wrong));
  }
});

test('nonfinite values, invalid tolerances and overflowing arithmetic are rejected', () => {
  for (const value of [NaN, Infinity, -Infinity, '0']) {
    assert.throws(() => engineeringComparison(moment(), value));
    assert.throws(() => engineeringComparison(moment({value}), 0));
  }
  assert.throws(() => engineeringComparison(moment({tolerance: {absolute: -1, relative: 0}}), 0));
  assert.throws(() => engineeringComparison(moment({value: Number.MAX_VALUE}), -Number.MAX_VALUE));
});

test('comparison leaves original input and strict failures unchanged', () => {
  const q = moment(), original = structuredClone(q);
  const comparison = engineeringComparison(q, 5e-8);
  comparison.frozenTolerance.absolute = 99;
  assert.deepEqual(q, original);
  const strict = {comparisons: 2, strict: {passed: 1, failed: 1, failures: [{
    state: 1, id: 'q', family: 'quantities', native: 0, diagnostic: 5e-8,
    component: q.component, unit: q.unit, location: q.location,
    frozenTolerance: q.tolerance, delta: 5e-8, frozenLimit: 1e-8}]}};
  const before = structuredClone(strict), engineering = applyPolicy(strict);
  assert.deepEqual(strict, before);
  assert.equal(engineering.strict.failed, 1);
  assert.equal(engineering.engineering.failed, 0);
  assert.equal(engineering.newlyAccepted.length, 1);
});

test('large numerical failures remain visible; inconsistent strict input is rejected', () => {
  const q = moment(), strict = {comparisons: 1, strict: {passed: 0, failed: 1, failures: [{
    state: 1, id: 'bad', family: 'quantities', native: 0, diagnostic: .1,
    component: q.component, unit: q.unit, location: q.location,
    frozenTolerance: q.tolerance, delta: .1, frozenLimit: 1e-8}]}};
  const engineering = applyPolicy(strict);
  assert.equal(engineering.engineering.failed, 1);
  assert.equal(engineering.newlyAccepted.length, 0);
  const stale = structuredClone(strict); stale.strict.failures[0].delta = 1e-8;
  assert.throws(() => applyPolicy(stale), /does not reproduce/);
  assert.throws(() => applyPolicy({...strict, comparisons: 2}), /Incomplete/);
});
