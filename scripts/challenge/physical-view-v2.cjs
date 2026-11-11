'use strict';
// Compare legal static SDK representations without rewriting the actual model,
// native result, model fingerprint, public inputs or frozen v1 evaluator.
const physical = require('../../lib/physical-model-fidelity.cjs');
const CONTROLS = ['self_weight', 'rigid_floor', 'p_delta', 'rigid_offsets', 'construction_stage'];
const STATIC_LABELS = new Set(['dead', 'live', 'wind', 'other']);

function comparisonView(model, ignoreStaticCaseLabels) {
  const result = structuredClone(model);
  if (result.coordinate_system?.dimension === '3d' && result.coordinate_system.plane === undefined) {
    result.coordinate_system.plane = null;
  }
  const cases = new Set(result.load_cases?.map(c => c.id));
  for (const combination of result.load_combinations || []) {
    combination.factors = Object.fromEntries(Object.entries(combination.factors || {})
      .filter(([id, value]) => !(value === 0 && cases.has(id))));
  }
  if (ignoreStaticCaseLabels) {
    for (const loadCase of result.load_cases || []) {
      if (loadCase.type === undefined || STATIC_LABELS.has(loadCase.type)) delete loadCase.type;
    }
  }
  return result;
}

function comparePhysicalModels(actual, expected, options) {
  // This wrapper belongs only to this static OpenSees pilot. Classification can
  // affect automatic gravity/dynamic/design logic elsewhere; never erase it
  // when either model enables any such control.
  const labelsInactive = [actual, expected].every(model => CONTROLS.every(k => model?.analysis_control?.[k] === false));
  return physical.comparePhysicalModels(comparisonView(actual, labelsInactive), comparisonView(expected, labelsInactive), options);
}

module.exports = {comparisonView, comparePhysicalModels};
