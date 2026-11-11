'use strict';
// This pilot requests global node responses only. A six-DOF spatial model of
// the same XZ structure, with every inactive DOF restrained, is an equivalent
// representation. Lift the authored planar model for comparison; never project
// away a candidate DOF, load, section axis, constraint or native result.
const sdk = require('./physical-view-v2.cjs');

function closedPlanarDomain(model) {
  if (!['2d', '3d'].includes(model?.coordinate_system?.dimension)) return false;
  if (model.coordinate_system.dimension === '2d' && model.coordinate_system.plane !== 'xz') return false;
  if (model.coordinate_system.dimension === '3d' && model.coordinate_system.plane != null) return false;
  if (!['self_weight', 'rigid_floor', 'p_delta', 'rigid_offsets', 'construction_stage']
    .every(k => model.analysis_control?.[k] === false)) return false;
  if (!model.nodes?.length || !model.nodes.every(n => n.y === 0 && [1, 3, 5].every(i => n.restraints?.[i] === true))) return false;
  return model.load_cases?.every(c => c.loads?.every(load =>
    ['nodal', 'point', 'distributed'].includes(load.type)
    && [undefined, 'global'].includes(load.reference_frame)
    && ['fy', 'mx', 'mz', 'wy', 'wy_start', 'wy_end'].every(k => load[k] === undefined || load[k] === 0)
    && !['direction', 'axis', 'points', 'segments', 'forces'].some(k => load[k] !== undefined)));
}

function liftPlanar(model) {
  if (model.coordinate_system.dimension !== '2d') return model;
  const result = structuredClone(model);
  result.coordinate_system = {...result.coordinate_system, dimension: '3d', plane: null};
  result.metadata = {...result.metadata, elementReferenceVectors: {}};
  for (const element of result.elements) {
    const [a, b] = element.nodes.map(id => result.nodes.find(n => n.id === id));
    if (!a || !b) return model;
    const length = Math.hypot(b.x - a.x, b.z - a.z);
    if (!(length > 0)) return model;
    // ref = cross(localX, globalY): cross(ref, localX) = globalY.
    result.metadata.elementReferenceVectors[element.id] = [-(b.z-a.z)/length, 0, (b.x-a.x)/length];
  }
  return result;
}

function comparePhysicalModels(actual, expected, options) {
  if (actual.coordinate_system?.dimension !== expected.coordinate_system?.dimension
      && closedPlanarDomain(actual) && closedPlanarDomain(expected)) {
    return sdk.comparePhysicalModels(liftPlanar(actual), liftPlanar(expected), options);
  }
  return sdk.comparePhysicalModels(actual, expected, options);
}

module.exports = {closedPlanarDomain, liftPlanar, comparePhysicalModels};
