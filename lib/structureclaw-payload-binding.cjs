'use strict';
const { createHash } = require('node:crypto');
const { isDeepStrictEqual } = require('node:util');
const { modelFingerprint } = require('./analysis-evidence.cjs');
const record = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const finite = value => typeof value === 'number' && Number.isFinite(value);
const near = (a, b) => finite(a) && finite(b) && Math.abs(a - b) <= 1e-9 + 1e-9 * Math.max(Math.abs(a), Math.abs(b));
const dot = (a, b) => a.reduce((sum, value, i) => sum + value * b[i], 0);
const vector = value => Array.isArray(value) && value.length === 3 && value.every(finite);
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const ACTIONS = ['N', 'V2', 'V3', 'T', 'M2', 'M3'];

// Only documented input normalization aliases are ignored. No stiffness, load,
// restraint or geometric property is inferred from the candidate's answer.
function normalizedPhysics(model) {
  const value = structuredClone(model);
  for (const material of value.materials ?? []) {
    if (['steel', 'concrete', 'rebar', 'other'].includes(material.type)) {
      if (material.category != null && material.category !== material.type) throw Error('material category/type conflict');
      material.category = material.type; delete material.type;
    }
  }
  for (const collection of ['materials', 'sections']) for (const item of value[collection] ?? []) {
    if (record(item.extra) && !Object.keys(item.extra).length) delete item.extra;
  }
  if (record(value.metadata)) for (const field of ['coordinateContractVersion', 'coordinateSemantics', 'frameDimension']) delete value.metadata[field];
  return modelFingerprint(value);
}

function components(load, position, length) {
  const keys = ['wx', 'wy', 'wz'];
  if ((load.distribution ?? 'uniform') === 'piecewise_linear') {
    const points = load.points;
    if (!Array.isArray(points) || points.length < 2) throw Error('piecewise load points unavailable');
    const pair = points.slice(0, -1).map((p, i) => [p, points[i + 1]])
      .find(([p, q]) => position >= p.position * length - 1e-10 && position <= q.position * length + 1e-10);
    if (!pair || !(pair[1].position > pair[0].position)) throw Error('piecewise load interval unavailable');
    const t = (position / length - pair[0].position) / (pair[1].position - pair[0].position);
    return keys.map(key => (1 - t) * (pair[0][key] ?? 0) + t * (pair[1][key] ?? 0));
  }
  if ((load.distribution ?? 'uniform') !== 'uniform') throw Error('distributed load profile unsupported');
  return keys.map(key => (load[key] ?? 0) + (load.gradient?.[key] ?? 0) * (position - (load.start ?? 0)));
}

// Three-point Gauss integration is exact for a linear distributed load times
// every kernel used here (degree at most four). Point loads split solver members
// and are already represented by each segment's own native end actions.
function integral(loads, member, segment, length, axes, x, power) {
  const total = [0, 0, 0];
  const points = [-Math.sqrt(3 / 5), 0, Math.sqrt(3 / 5)], weights = [5 / 9, 8 / 9, 5 / 9];
  for (const load of loads) {
    if (load.element !== member.id || load.type !== 'distributed') continue;
    const lo = Math.max(segment.start, load.start ?? 0), hi = Math.min(segment.start + x, load.end ?? length);
    if (!(hi > lo)) continue;
    const cuts = [lo, ...(load.points ?? []).map(p => p.position * length).filter(p => p > lo && p < hi), hi].sort((a, b) => a - b);
    for (let j = 0; j < cuts.length - 1; j++) {
      const a = cuts[j], b = cuts[j + 1];
      for (let i = 0; i < 3; i++) {
        const t = (a + b) / 2 + points[i] * (b - a) / 2;
        const q = components(load, t, length);
        if (!vector(q)) throw Error('nonfinite distributed load');
        const local = (load.reference_frame ?? 'global') === 'global' ? axes.map(axis => dot(axis, q))
          : load.reference_frame === 'element-local' ? q : undefined;
        if (!local) throw Error('distributed load reference frame unsupported');
        const weight = weights[i] * (b - a) / 2 * (x - (t - segment.start)) ** power;
        for (let k = 0; k < 3; k++) total[k] += weight * local[k];
      }
    }
  }
  return total;
}

function expectedSample(model, native, row, sample) {
  const member = model.elements.find(item => item.id === row.id);
  if (!member || member.nodes.length !== 2 || !finite(sample.x)) throw Error('unknown physical member or position');
  const a = model.nodes.find(item => item.id === member.nodes[0]), b = model.nodes.find(item => item.id === member.nodes[1]);
  if (!a || !b) throw Error('member node unavailable');
  const length = Math.hypot(b.x - a.x, b.y - a.y, b.z - a.z);
  if (!near(row.length, length) || sample.x < -1e-10 || sample.x > length + 1e-10) throw Error('member sample length/position mismatch');
  const parts = native.solverMesh.elements.filter(item => item.physicalElementId === member.id).sort((x, y) => x.start - y.start);
  const matches = parts.filter(part => sample.x >= part.start - 1e-10 && sample.x <= part.end + 1e-10);
  const segment = sample.side === 'left' ? matches[0] : matches.at(-1);
  if (!segment || !['left', 'right', undefined].includes(sample.side)) throw Error('native solver segment/side unavailable');
  const x = Math.max(0, Math.min(segment.end - segment.start, sample.x - segment.start)), L = segment.end - segment.start;
  const force = native.segmentResults.forces[segment.id];
  const axes = ['x', 'y', 'z'].map(key => force?.localAxes?.[key] ?? segment.localAxes?.[key]);
  if (!axes.every(vector) || axes.some(axis => !near(dot(axis, axis), 1))) throw Error('native member axes unavailable');
  const u = segment.nodes.map(id => native.segmentResults.displacements[id]);
  if (u.some(value => !value || !['ux', 'uy', 'uz'].every(key => finite(value[key])))) throw Error('native segment displacements unavailable');
  const local = u.map(value => axes.map(axis => dot(axis, [value.ux, value.uy, value.uz])));
  const n1 = force.n1;
  const position = [a.x, a.y, a.z].map((value, i) => value + ([b.x, b.y, b.z][i] - value) * sample.x / length);
  if (member.type === 'truss' || member.type === 'brace') {
    const displacement = ['ux', 'uy', 'uz'].map(key => u[0][key] + (u[1][key] - u[0][key]) * x / L);
    return { N: force.axial, displacement, position };
  }
  if (!['beam', 'column'].includes(member.type) || !n1 || !ACTIONS.every(key => finite(n1[key]))) throw Error('native frame end actions unavailable');
  const loads = native.effectiveLoads;
  const q0 = integral(loads, member, segment, length, axes, x, 0), q1 = integral(loads, member, segment, length, axes, x, 1);
  const answer = { N: -n1.N - q0[0], V2: n1.V2 + q0[1], V3: n1.V3 + q0[2], T: -n1.T,
    M2: -n1.M2 - n1.V3 * x - q1[2], M3: -n1.M3 + n1.V2 * x + q1[1], position };
  if (sample.displacement !== undefined) {
    const E = model.materials.find(item => item.id === member.material)?.E * 1000;
    const p = model.sections.find(item => item.id === member.section)?.properties;
    if (!(E > 0) || !p || !(p.A > 0) || !(p.Iy > 0) || !(p.Iz > 0)) throw Error('native bound stiffness required for displacement recovery');
    const polynomial = t => {
      const first = integral(loads, member, segment, length, axes, t, 1), third = integral(loads, member, segment, length, axes, t, 3);
      return [-first[0] / (E * p.A), (-n1.M3 * t * t / 2 + n1.V2 * t ** 3 / 6 + third[1] / 6) / (E * p.Iz),
        (n1.M2 * t * t / 2 + n1.V3 * t ** 3 / 6 + third[2] / 6) / (E * p.Iy)];
    };
    const px = polynomial(x), pL = polynomial(L);
    const d = local[0].map((value, i) => value + (local[1][i] - value - pL[i]) * x / L + px[i]);
    answer.displacement = [0, 1, 2].map(i => axes.reduce((sum, axis, j) => sum + axis[i] * d[j], 0));
  }
  return answer;
}

/** Bind graded fields to verified native bytes, including host-derived section curves. */
function verifyStructureClawPayloadBinding({ model, selection, data, meta, execution, artifactBytes }) {
  const failures = []; let verifiedMemberSamples = 0;
  try {
    if (!record(execution) || String(execution.solver).toLowerCase() !== 'opensees'
      || execution.artifacts?.hashFormat !== 'sha256:python-json-sort-keys-utf8-compact-v1') throw Error('unsupported native payload receipt');
    const parsed = {};
    for (const name of ['normalizedInput', 'settings', 'solverResponse']) {
      const bytes = artifactBytes?.[name];
      if (!(bytes instanceof Uint8Array) || sha(bytes) !== execution.artifacts[name + 'Sha256']) throw Error(`${name} native payload SHA256 mismatch`);
      parsed[name] = JSON.parse(Buffer.from(bytes).toString('utf8'));
    }
    if (normalizedPhysics(model) !== normalizedPhysics(parsed.normalizedInput)) throw Error('native normalized input differs from candidate physical model');
    const parameters = parsed.settings.parameters ?? {};
    if (selection?.kind === 'case' ? parameters.loadCaseIds?.length !== 1 || parameters.loadCaseIds[0] !== selection.id
      : selection?.kind === 'combination' ? parameters.loadCombinationId !== selection.id : true) throw Error('native settings differ from result selection');
    const native = parsed.solverResponse, keys = execution.artifacts.solverResponseKeys;
    if (!Array.isArray(keys) || !isDeepStrictEqual([...keys].sort(), Object.keys(native).sort())) throw Error('native response field manifest mismatch');
    for (const key of ['displacements', 'reactions', 'forces', 'solverMesh', 'effectiveLoads', 'segmentResults']) {
      if (!keys.includes(key)) throw Error(`native response does not bind ${key}`);
    }
    // JSON equality deliberately treats native -0.0 and JavaScript 0 as the
    // same response number; the original canonical bytes were hashed above.
    for (const key of keys) if (!isDeepStrictEqual(JSON.parse(JSON.stringify(native[key])), JSON.parse(JSON.stringify(data[key] ?? null)))) failures.push(`${key}: candidate differs from native solver payload`);
    for (const units of [data.units, data.meta?.units, meta?.units]) if (record(units)) {
      for (const [key, expected] of Object.entries({ displacement: 'm', length: 'm', position: 'm', rotation: 'rad', force: 'kN', moment: 'kN.m' }))
        if (units[key] !== undefined && units[key] !== expected) failures.push(`${key}: candidate unit differs from canonical native unit`);
    }
    if (data.memberStations != null || data.nativeContext != null) failures.push('unbound commercial station data cannot override an OpenSees payload');
    if (failures.length) return { pass: false, failures, verifiedMemberSamples };
    const rows = data.memberResponses ?? [], ids = new Set();
    if (!Array.isArray(rows)) throw Error('memberResponses must be an array');
    for (const row of rows) {
      if (!record(row) || ids.has(row.id)) throw Error('duplicate/invalid host member response');
      ids.add(row.id);
      if (!['recovered', 'truss'].includes(row.state)) continue;
      if (!Array.isArray(row.samples)) throw Error('host member samples unavailable');
      for (const sample of row.samples) {
        const expected = expectedSample(parsed.normalizedInput, native, row, sample);
        for (const component of ACTIONS) if (sample[component] !== undefined && !near(sample[component], expected[component])) throw Error(`${row.id}@${sample.x}:${component} differs from native equilibrium recovery`);
        for (const field of ['displacement', 'position']) if (sample[field] !== undefined
          && (!vector(sample[field]) || !vector(expected[field]) || sample[field].some((v, i) => !near(v, expected[field][i])))) throw Error(`${row.id}@${sample.x}:${field} differs from native recovery`);
        verifiedMemberSamples++;
      }
    }
  } catch (error) { failures.push(error.message); }
  return { pass: failures.length === 0, failures, verifiedMemberSamples };
}
module.exports = { verifyStructureClawPayloadBinding };
