'use strict';

// Versioned comparison budget, not an estimate of vendor arithmetic error.
// This module is deliberately separate from candidate grading/reference truth.
const POLICY = Object.freeze({
  id: 'cross-engine-moment-resolution-v1',
  scope: 'Cross-engine primary member moments/torques and nodal reaction moments',
  canonicalUnit: 'kN.m',
  absoluteFloor: 1e-7,
  relative: 'preserve frozen relative tolerance',
  otherQuantities: 'preserve frozen absolute and relative tolerances',
  derived: 'preserve frozen tolerances; no automatic error propagation',
  acceptanceRegionChanges: true,
  candidateGradingChanged: false,
  nativeArithmeticBound: false,
  calibration: 'Engineering resolution choice after reviewing observed discrepancies; not an independent holdout validation',
});
const MOMENT_FACTORS = Object.freeze({'kN.m': 1, 'N.m': 1e-3, 'kN.mm': 1e-3, 'N.mm': 1e-6});
const finite = value => typeof value === 'number' && Number.isFinite(value);

function engineeringComparison(reference, diagnostic, {family = 'quantities'} = {}) {
  const tolerance = reference.tolerance;
  if (!['quantities', 'derived'].includes(family) || !finite(reference.value) || !finite(diagnostic)
      || !tolerance || !finite(tolerance.absolute) || !finite(tolerance.relative)
      || tolerance.absolute < 0 || tolerance.relative < 0) {
    throw new Error('Invalid cross-engine comparison values or frozen tolerance');
  }
  const memberMoment = reference.location?.kind === 'member' && ['T', 'M2', 'M3'].includes(reference.component);
  const reactionMoment = reference.location?.kind === 'node' && ['Mx', 'My', 'Mz'].includes(reference.component);
  const eligible = family === 'quantities' && (memberMoment || reactionMoment);
  if (eligible && !Object.hasOwn(MOMENT_FACTORS, reference.unit)) {
    throw new Error('Moment comparison requires a supported moment unit');
  }
  const absolute = eligible ? Math.max(tolerance.absolute, POLICY.absoluteFloor / MOMENT_FACTORS[reference.unit]) : tolerance.absolute;
  const strictLimit = tolerance.absolute + tolerance.relative * Math.abs(reference.value);
  const engineeringLimit = absolute + tolerance.relative * Math.abs(reference.value);
  const delta = Math.abs(reference.value - diagnostic);
  if (![strictLimit, engineeringLimit, delta].every(finite)) throw new Error('Nonfinite comparison arithmetic');
  return {policy: POLICY.id, eligible, delta, strictLimit, engineeringLimit,
    strictPass: delta <= strictLimit, engineeringPass: delta <= engineeringLimit,
    frozenTolerance: {...tolerance}, engineeringTolerance: {absolute, relative: tolerance.relative}};
}

module.exports = {POLICY, engineeringComparison};
