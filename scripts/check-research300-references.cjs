#!/usr/bin/env node
'use strict';

// Benchmark-only, read-only cross-check. No provider, evaluator, solver, network,
// reference installation, or acceptance/provenance writer is used here.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { isDeepStrictEqual: equal } = require('node:util');
const { TextDecoder } = require('node:util');

const DEFAULT_TOLERANCE = Object.freeze({ absolute: 1e-8, relative: 1e-6 });
const RAW_FILES = ['native-input-receipt.json', 'native-solver-receipt.json',
  'native-raw-responses.json', 'native-checks.json'];
const GENERATED = new Set([...RAW_FILES, 'independent-reference.json',
  'independent-reference-matrix-diagnostic.json',
  'native-opensees-reference.json', 'reference-provenance.json', 'acceptance.json']);
const CASE_ID = /^(STD|INT|MM)-(00[1-9]|0[1-9][0-9]|100)$/;
const HASH = /^[a-f0-9]{64}$/;
const UNITS = {
  m: ['length', 1], mm: ['length', .001], cm: ['length', .01],
  rad: ['rotation', 1], mrad: ['rotation', .001], deg: ['rotation', Math.PI / 180],
  kN: ['force', 1], N: ['force', .001], MN: ['force', 1000],
  'kN.m': ['moment', 1], 'N.m': ['moment', .001], 'kN.mm': ['moment', .001],
  'N.mm': ['moment', 1e-6], 'MN.m': ['moment', 1000],
};
const DOFS = ['ux', 'uy', 'uz', 'rx', 'ry', 'rz'];
const FORCES = ['fx', 'fy', 'fz', 'mx', 'my', 'mz'];
const ACTIONS = ['N', 'V2', 'V3', 'T', 'M2', 'M3'];
const sha256 = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const assert = (condition, message) => { if (!condition) throw new Error(message); };
const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const finite = value => typeof value === 'number' && Number.isFinite(value);
const nonempty = value => typeof value === 'string' && value.trim().length > 0;
const list = (value, label) => { assert(Array.isArray(value), `${label} must be an array`); return value; };

// JSON.parse alone silently accepts duplicate object keys and overflows 1e999.
// Parse the grammar before constructing objects, including escaped duplicate keys.
function parseStrictJson(bytes) {
  const text = typeof bytes === 'string' ? bytes : new TextDecoder('utf-8', { fatal: true }).decode(bytes);
  let at = 0;
  const whitespace = () => { while (/[\t\n\r ]/.test(text[at] || '!')) at++; };
  function string() {
    const start = at++;
    while (at < text.length) {
      if (text[at] === '\\') { at += 2; continue; }
      if (text[at++] === '"') return JSON.parse(text.slice(start, at));
    }
    throw new Error('Unterminated JSON string');
  }
  function value(depth) {
    assert(depth <= 200, 'JSON nesting exceeds 200');
    whitespace();
    const first = text[at];
    if (first === '"') return string();
    if (first === '{' || first === '[') {
      const isObject = first === '{', result = isObject ? {} : [], keys = new Set();
      const end = isObject ? '}' : ']';
      at++; whitespace();
      if (text[at] === end) { at++; return result; }
      while (true) {
        whitespace();
        if (isObject) {
          assert(text[at] === '"', 'Expected JSON object key');
          const key = string();
          assert(!keys.has(key), `Duplicate JSON key: ${key}`); keys.add(key);
          whitespace(); assert(text[at++] === ':', 'Expected JSON colon');
          Object.defineProperty(result, key, { value: value(depth + 1), enumerable: true, writable: true, configurable: true });
        } else result.push(value(depth + 1));
        whitespace();
        if (text[at] === end) { at++; return result; }
        assert(text[at++] === ',', 'Expected JSON comma');
      }
    }
    for (const [token, result] of [['true', true], ['false', false], ['null', null]]) {
      if (text.startsWith(token, at)) { at += token.length; return result; }
    }
    const match = /^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?/.exec(text.slice(at));
    assert(match, `Invalid JSON value at byte/character ${at}`);
    at += match[0].length;
    const result = Number(match[0]);
    assert(finite(result), 'Non-finite JSON number'); return result;
  }
  const result = value(0); whitespace();
  assert(at === text.length, 'Unexpected trailing JSON content');
  assert(object(result), 'JSON document must be an object');
  return result;
}

function relativeParts(name) {
  assert(nonempty(name) && !name.includes('\\') && !name.includes(':') && !name.includes('\0'), `Unsafe relative path: ${name}`);
  const parts = name.split('/');
  assert(parts.every(part => part && part !== '.' && part !== '..'), `Unsafe relative path: ${name}`);
  return parts;
}

// Linux directory handles prevent symlink replacement of intermediate parents.
// Deliberately fail closed on hosts without these primitives; no realpath fallback.
function openDirectory(directory) {
  assert(process.platform === 'linux' && fs.constants.O_NOFOLLOW, 'Safe file loader requires Linux O_NOFOLLOW and /proc/self/fd');
  assert(nonempty(directory) && !directory.split('/').includes('..') && !directory.includes('\0'), 'Unsafe directory path');
  const absolute = path.resolve(directory);
  let fd = fs.openSync('/', fs.constants.O_RDONLY | fs.constants.O_DIRECTORY | fs.constants.O_NOFOLLOW);
  try {
    for (const component of absolute.split('/').filter(Boolean)) {
      const next = fs.openSync(`/proc/self/fd/${fd}/${component}`, fs.constants.O_RDONLY | fs.constants.O_DIRECTORY | fs.constants.O_NOFOLLOW);
      fs.closeSync(fd); fd = next;
    }
    return fd;
  } catch (error) { fs.closeSync(fd); throw new Error(`Unsafe or inaccessible directory ${absolute} (symlinks forbidden): ${error.message}`); }
}

function withParent(root, relative, callback) {
  const parts = relativeParts(relative);
  let fd = openDirectory(root);
  try {
    for (const component of parts.slice(0, -1)) {
      const next = fs.openSync(`/proc/self/fd/${fd}/${component}`, fs.constants.O_RDONLY | fs.constants.O_DIRECTORY | fs.constants.O_NOFOLLOW);
      fs.closeSync(fd); fd = next;
    }
    return callback(`/proc/self/fd/${fd}/${parts.at(-1)}`);
  } finally { fs.closeSync(fd); }
}

function readFile(root, relative) {
  return withParent(root, relative, file => {
    const fd = fs.openSync(file, fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW | fs.constants.O_NONBLOCK);
    try {
      assert(fs.fstatSync(fd).isFile(), `Not a regular file: ${relative}`);
      assert(fs.fstatSync(fd).size <= 128 * 1024 * 1024, `File exceeds 128 MiB: ${relative}`);
      const bytes = fs.readFileSync(fd);
      assert(bytes.length > 0, `Empty file: ${relative}`);
      return bytes;
    } finally { fs.closeSync(fd); }
  });
}

function index(records, key, label) {
  const result = new Map();
  for (const record of list(records, label)) {
    assert(object(record), `${label} record must be an object`);
    const id = key(record);
    assert(id !== undefined && id !== null && id !== '', `${label} missing identity`);
    assert(!result.has(id), `Duplicate ${label}: ${id}`); result.set(id, record);
  }
  return result;
}
function exactKeys(actual, expected, label) {
  for (const key of expected.keys()) assert(actual.has(key), `${label} missing ${key}`);
  for (const key of actual.keys()) assert(expected.has(key), `${label} extra ${key}`);
}
function selectionKey(selection) {
  assert(object(selection) && ['case', 'combination'].includes(selection.kind) && nonempty(selection.id), 'Invalid selection');
  assert(equal(Object.keys(selection).sort(), ['id', 'kind']), 'Selection must contain exactly kind and id');
  return JSON.stringify([selection.kind, selection.id]);
}
const quantityKey = record => JSON.stringify([record.id, selectionKey(record.selection)]);
const runKey = record => JSON.stringify([record.state, selectionKey(record.selection)]);

function tolerance(record) {
  const result = record.tolerance === undefined ? DEFAULT_TOLERANCE : record.tolerance;
  assert(object(result) && finite(result.absolute) && result.absolute >= 0 && finite(result.relative) && result.relative >= 0,
    `Invalid frozen tolerance for ${record.id}`);
  return result;
}
function close(actual, expected, tol) {
  const limit = tol.absolute + tol.relative * Math.abs(expected);
  const delta = Math.abs(actual - expected);
  assert(finite(limit) && finite(delta), 'Non-finite comparison arithmetic');
  return { passed: delta <= limit, delta, limit };
}
function unitInfo(unit) {
  assert(nonempty(unit), 'Missing unit');
  const canonical = unit.replace(/[·*]/g, '.');
  const info = Object.hasOwn(UNITS, canonical) ? UNITS[canonical] : undefined;
  assert(info, `Unsupported unit: ${unit}`); return info;
}
function convert(value, from, to) {
  const a = unitInfo(from), b = unitInfo(to);
  assert(a[0] === b[0], `Incompatible units: ${from} and ${to}`);
  const result = value * a[1] / b[1]; assert(finite(result), 'Non-finite converted value'); return result;
}
function componentUnit(component) {
  if (DOFS.slice(0, 3).includes(component)) return 'm';
  if (DOFS.slice(3).includes(component)) return 'rad';
  if (['Fx', 'Fy', 'Fz', 'fx', 'fy', 'fz', 'N', 'V2', 'V3'].includes(component)) return 'kN';
  if (['Mx', 'My', 'Mz', 'mx', 'my', 'mz', 'T', 'M2', 'M3'].includes(component)) return 'kN.m';
  throw new Error(`Unsupported component: ${component}`);
}

// Expansion summation preserves small signed terms through severe cancellation.
function preciseSum(values) {
  const partials = [];
  for (let x of values) {
    let count = 0;
    for (let y of partials) {
      if (Math.abs(x) < Math.abs(y)) [x, y] = [y, x];
      const high = x + y, low = y - (high - x);
      assert(finite(high) && finite(low), 'Non-finite derived sum');
      if (low) partials[count++] = low;
      x = high;
    }
    partials.length = count; partials.push(x);
  }
  let remaining = partials.length, result = remaining ? partials[--remaining] : 0, low = 0;
  while (remaining) {
    const x = result, y = partials[--remaining];
    result = x + y; low = y - (result - x);
    if (low) break;
  }
  // Resolve half-even rounding using the sign of the unconsumed expansion.
  if (remaining && ((low < 0 && partials[remaining - 1] < 0) || (low > 0 && partials[remaining - 1] > 0))) {
    const twice = 2 * low, rounded = result + twice;
    if (rounded - result === twice) result = rounded;
  }
  assert(finite(result), 'Non-finite derived sum'); return result;
}

function selectionFactors(model, selection) {
  selectionKey(selection);
  const cases = index(model.load_cases, record => record.id, 'model load case');
  const combinations = index(model.load_combinations || [], record => record.id, 'model combination');
  if (selection.kind === 'case') {
    assert(cases.has(selection.id), `Unknown case selection ${selection.id}`);
    return { [selection.id]: 1 };
  }
  const factors = combinations.get(selection.id)?.factors;
  assert(object(factors) && Object.keys(factors).length, `Unknown/empty combination ${selection.id}`);
  for (const [id, value] of Object.entries(factors)) assert(cases.has(id) && finite(value), `Invalid factor ${id}`);
  return factors;
}

function derive(quantities, definitions) {
  const values = new Map(), leaves = new Map();
  for (const quantity of quantities) {
    if (!values.has(quantity.id)) values.set(quantity.id, []);
    values.get(quantity.id).push(quantity);
  }
  const defined = new Set(values.keys());
  for (const record of list(definitions, 'derived requests')) {
    assert(nonempty(record.id) && !defined.has(record.id), `Duplicate derived/quantity ID: ${record.id}`);
    defined.add(record.id);
  }
  const results = [];
  for (const request of definitions) {
    const { id, operation, operands } = request;
    assert(!Object.hasOwn(request, 'value'), `Derived request ${id} contains value`);
    assert(['sum', 'difference', 'max', 'min', 'max_abs'].includes(operation), `Unknown derived operation ${operation}`);
    assert(request.tiePolicy === undefined || ['first', 'any'].includes(request.tiePolicy), `Invalid tiePolicy for ${id}`);
    assert(Array.isArray(operands) && operands.length && (operation !== 'difference' || operands.length === 2), `Invalid operands for ${id}`);
    assert(new Set(operands).size === operands.length, `Duplicate operand for ${id}`);
    const sources = operands.map(operand => {
      const matches = values.get(operand);
      assert(matches?.length === 1, `Unknown, ambiguous or forward/cyclic operand ${operand} for ${id}`);
      return matches[0];
    });
    const numbers = sources.map(source => convert(source.value, source.unit, request.unit));
    const sourceLeaves = sources.map(source => leaves.get(source.id) || [source]);
    let selected, value, metadata;
    if (operation === 'sum' || operation === 'difference') {
      value = operation === 'sum' ? preciseSum(numbers) : numbers[0] - numbers[1];
      selected = sourceLeaves.flat();
      metadata = { operandSelections: selected.map(leaf => leaf.selection) };
    } else {
      const scores = numbers.map(number => operation === 'max_abs' ? Math.abs(number) : number);
      const best = scores.reduce((a, b) => operation === 'min' ? Math.min(a, b) : Math.max(a, b));
      const tol = tolerance(request);
      // Measure every score from the true best after unit conversion. Comparing
      // successive operands instead would let a chain of near-ties drift.
      const coGovernors = scores.map((score, i) => close(score, best, tol).passed ? i : -1).filter(i => i >= 0);
      // 'any' permits alternative public reports, never alternative canonical
      // references. Preserve this first operand's signed value and exact leaves.
      const chosen = coGovernors[0];
      value = numbers[chosen]; selected = sourceLeaves[chosen];
      metadata = { governingOperand: operands[chosen], governingLeafOperands: selected.map(leaf => leaf.id),
        coGoverningOperands: coGovernors.map(i => operands[i]) };
    }
    assert(finite(value), `Non-finite derived value ${id}`);
    const selections = [...new Map(selected.map(leaf => [selectionKey(leaf.selection), leaf.selection])).values()];
    if (operation === 'sum' || operation === 'difference') {
      if (selections.length === 1) metadata.selection = selections[0];
    } else {
      metadata.governingSelection = selections.length === 1 ? selections[0] : null;
      metadata.governingSelections = selections;
    }
    const result = { id, operation, operands, unit: request.unit, tolerance: tolerance(request), value, ...metadata };
    values.set(id, [result]); leaves.set(id, selected); results.push(result);
  }
  return results;
}

function loadAuthored(root, id, evidence) {
  const caseDir = path.join(root, 'corpora/research-300/cases', id);
  const cached = new Map();
  const read = name => {
    if (!cached.has(name)) cached.set(name, readFile(caseDir, name));
    return cached.get(name);
  };
  const contract = parseStrictJson(read('contract.json'));
  assert(contract.id === id && contract.schemaVersion === 1 && contract.evaluationProfile === 'engineering-v2.3', 'Authored contract identity/schema/profile mismatch');
  assert(nonempty(contract.modelId), 'Authored contract modelId missing');
  assert(['OpenSees', 'YJK', 'PKPM'].includes(contract.plannedEngine), `Unsupported plannedEngine: ${contract.plannedEngine}`);
  evidence.plannedEngine = contract.plannedEngine;
  evidence.nativeRole = contract.plannedEngine === 'OpenSees' ? 'same-engine-candidate' : 'cross-engine-diagnostic';
  evidence.comparisonRole = contract.plannedEngine === 'OpenSees' ? 'OpenSees independent numerical cross-check' : 'CROSS-ENGINE DIAGNOSTIC';
  const models = list(contract.modelStates, 'modelStates');
  assert(models.length && new Set(models).size === models.length, 'Missing/duplicate modelStates');
  const attachments = list(contract.attachments, 'attachments');
  assert(new Set(attachments).size === attachments.length, 'Duplicate public attachment path');
  const paths = [...new Set(['contract.json', 'prompt.txt', 'reference-requests.json', ...models, ...attachments])];
  for (const name of paths) {
    relativeParts(name); assert(!GENERATED.has(name.split('/').at(-1)), `Generated evidence cannot be authored input: ${name}`);
  }
  assert(attachments.every(name => !['contract.json', 'reference-requests.json', ...models].includes(name)), 'Public attachment aliases private input');
  const sourceManifest = { schemaVersion: 1, files: paths.sort((a, b) => Buffer.compare(Buffer.from(a), Buffer.from(b)))
    .map(name => ({ path: name, sha256: sha256(read(name)) })) };
  const sourceHash = sha256(Buffer.from(JSON.stringify(sourceManifest)));
  const inputHashes = Object.fromEntries(['contract.json', 'reference-requests.json', ...models].map(name => [name, sha256(read(name))]));
  Object.assign(evidence, { sourceHash, sourceManifest, inputHashes });
  const requests = parseStrictJson(read('reference-requests.json'));
  assert(requests.schemaVersion === 1, 'Reference requests schemaVersion must be 1');
  const states = index(requests.states, state => state.state, 'authored state');
  assert(states.size === models.length, 'Requests must cover every model state');
  const runs = new Map();
  for (const [number, state] of states) {
    assert(Number.isInteger(number) && number >= 1 && number <= models.length && state.model === models[number - 1], `Invalid authored state/model ${number}`);
    state.authoredModel = parseStrictJson(read(state.model));
    assert(state.authoredModel.schema_version === '2.2.0', `State ${number} model protocol must be 2.2.0`);
    const nodes = index(state.authoredModel.nodes, n => n.id, 'model node');
    const members = index(state.authoredModel.elements, e => e.id, 'model element');
    const quantities = index(state.quantities, quantityKey, `state ${number} requested quantity`);
    assert(quantities.size > 0, `State ${number} has no requested quantities/native evidence`);
    for (const quantity of quantities.values()) {
      assert(nonempty(quantity.id) && !Object.hasOwn(quantity, 'value'), 'Invalid quantity ID or authored answer value');
      tolerance(quantity); convert(0, componentUnit(quantity.component), quantity.unit);
      const location = quantity.location;
      assert(object(location) && ['node', 'member'].includes(location.kind), `Invalid location for ${quantity.id}`);
      assert((location.kind === 'node' ? nodes : members).has(location.id), `Unknown location for ${quantity.id}`);
      if (location.kind === 'node') assert(!ACTIONS.includes(quantity.component), `Member component at node for ${quantity.id}`);
      else assert(!FORCES.includes(quantity.component.toLowerCase()), `Support component at member for ${quantity.id}`);
      if (location.kind === 'member') assert(finite(location.positionM) && location.positionM >= 0 && ['left', 'right'].includes(location.side), `Invalid member position/side for ${quantity.id}`);
      const selection = quantity.selection;
      const factors = selectionFactors(state.authoredModel, selection);
      runs.set(runKey({ state: number, selection }), { state: number, selection, factors });
    }
    state.derived = state.derived === undefined ? [] : state.derived;
    derive(state.quantities.map(q => ({ ...q, value: 0 })), state.derived);
  }
  return { id, caseDir, contract, states, runs, sourceHash, sourceManifest, inputHashes,
    unchanged() { for (const [name, bytes] of cached) assert(sha256(readFile(caseDir, name)) === sha256(bytes), `Authored file changed during audit: ${name}`); } };
}

function bindInput(document, authored, label) {
  assert(document.id === authored.id && document.schemaVersion === 1, `${label} case/schema mismatch`);
  assert(equal(document.analysisConvention, authored.contract.analysisConvention), `${label} analysisConvention differs from authored input`);
  assert(document.sourceHash === authored.sourceHash, `${label} sourceHash missing or stale`);
  assert(equal(document.inputHashes, authored.inputHashes), `${label} inputHashes missing or stale`);
  if (document.sourceManifest !== undefined) assert(equal(document.sourceManifest, authored.sourceManifest), `${label} sourceManifest mismatch`);
}

function checkEquilibrium(check, native) {
  assert(check.method === (native ? 'native-openseespy' : 'independent-direct-stiffness'), 'Equilibrium check method mismatch');
  assert(finite(check.freeResidual) && check.freeResidual >= 0, 'Equilibrium freeResidual missing/non-finite/negative');
  assert(Array.isArray(check.forceMomentBalance) && check.forceMomentBalance.length === 6 && check.forceMomentBalance.every(finite), 'Equilibrium forceMomentBalance must contain six finite balances');
  if (native) {
    assert(check.equilibriumPassed === true, 'Native equilibriumPassed must be true');
    assert(Array.isArray(check.balanceTolerance) && check.balanceTolerance.length === 6 && check.balanceTolerance.every(v => finite(v) && v >= 0), 'Native balanceTolerance must contain six finite nonnegative bounds');
    assert(check.forceMomentBalance.every((v, i) => Math.abs(v) <= check.balanceTolerance[i]), 'Native equilibrium balance exceeds declared balanceTolerance');
    assert(check.freeResidual <= Math.max(...check.balanceTolerance), 'Native freeResidual exceeds declared balanceTolerance');
  }
}

function validateReference(document, authored, native, recordError) {
  const label = native ? 'native' : 'independent';
  recordError(`${label} provenance`, () => {
    bindInput(document, authored, label);
    assert(document.referenceKind === (native ? 'native-opensees' : 'independent-elastic-matrix'), `${label} referenceKind mismatch/relabel`);
    assert(document.sameEngineTruthStatus === 'pending', `${label} may not claim same-engine truth`);
    if (native) {
      assert(document.method === 'native-openseespy', 'Native method mismatch');
      assert(document.modelId === authored.contract.modelId, 'Native modelId mismatch');
      assert(document.nativeRole === (authored.contract.plannedEngine === 'OpenSees' ? 'same-engine-candidate' : 'cross-engine-diagnostic'), 'Native role/engine relabel mismatch');
      assert(document.nativeIndependentReview === 'pending' && document.llmEndToEnd === 'not-run', 'Native review/LLM stages must remain pending/not-run');
    } else {
      assert(document.evaluationProfile === 'engineering-v2.3', 'Independent evaluationProfile mismatch');
      assert(document.toleranceFrozenBeforeCandidate === true && document.notCommercialScoringTruth === true, 'Independent frozen tolerance/diagnostic declarations missing');
    }
    for (const key of ['engine', 'engineId', 'solverEngine']) if (document[key] !== undefined) assert(native && document[key] === 'OpenSees', `${label} incompatible engine claim ${key}`);
    if (document.plannedEngine !== undefined) assert(document.plannedEngine === authored.contract.plannedEngine, `${label} plannedEngine mismatch`);
    assert(document.accepted !== true && document.nativeVerified !== true, `${label} unsupported acceptance claim`);
  });
  let states = new Map(), checks = new Map();
  recordError(`${label} states`, () => {
    states = index(document.states, s => s.state, `${label} state`); exactKeys(states, authored.states, `${label} states`);
  });
  recordError(`${label} equilibrium`, () => {
    checks = index(document.checks, runKey, `${label} check`); exactKeys(checks, authored.runs, `${label} checks`);
  });
  for (const [key] of authored.runs) recordError(`${label} equilibrium ${key}`, () => checkEquilibrium(checks.get(key) || {}, native));
  for (const [number, request] of authored.states) {
    recordError(`${label} state ${number} quantities`, () => {
      const state = states.get(number); assert(state, 'Missing state');
      if (native || state.model !== undefined) assert(state.model === request.model, 'State model path mismatch');
      const expected = index(request.quantities, quantityKey, 'requested quantity');
      const actual = index(state.quantities, quantityKey, 'reference quantity'); exactKeys(actual, expected, 'quantities');
      for (const [key, quantity] of expected) {
        const value = actual.get(key);
        for (const field of ['id', 'selection', 'location', 'component', 'unit']) assert(equal(value[field], quantity[field]), `Quantity ${quantity.id} ${field} mismatch`);
        assert(equal(value.tolerance, tolerance(quantity)), `Quantity ${quantity.id} frozen tolerance changed`);
        assert(finite(value.value), `Quantity ${quantity.id} value must be finite`);
      }
      const computed = index(derive(state.quantities, request.derived), d => d.id, 'computed derived');
      const derived = index(state.derived, d => d.id, 'reference derived'); exactKeys(derived, computed, 'derived');
      const fields = ['id', 'operation', 'operands', 'unit', 'tolerance', 'selection', 'operandSelections',
        'governingOperand', 'governingSelection', 'governingSelections', 'governingLeafOperands'];
      for (const [id, expectedValue] of computed) {
        const actualValue = derived.get(id);
        for (const field of fields) assert(equal(actualValue[field], expectedValue[field]), `Derived ${id} ${field} mismatch`);
        const definition = request.derived.find(d => d.id === id);
        if (Object.hasOwn(actualValue, 'coGoverningOperands')) assert(equal(actualValue.coGoverningOperands, expectedValue.coGoverningOperands), `Derived ${id} coGoverningOperands mismatch`);
        if (Object.hasOwn(actualValue, 'tiePolicy')) assert(actualValue.tiePolicy === (definition.tiePolicy ?? 'first'), `Derived ${id} tiePolicy mismatch`);
        for (const field of ['location', 'component']) assert(equal(actualValue[field], definition[field]), `Derived ${id} ${field} mismatch`);
        assert(finite(actualValue.value) && close(actualValue.value, expectedValue.value, expectedValue.tolerance).passed, `Derived ${id} arithmetic/signed value mismatch`);
      }
      if (native) {
        const local = index(state.checks, c => runKey({ ...c, state: number }), 'native state check');
        const expectedChecks = new Map([...checks].filter(([, c]) => c.state === number));
        exactKeys(local, expectedChecks, 'native state checks');
        for (const [key, check] of local) assert(equal({ ...check, state: number }, expectedChecks.get(key)), 'Native state/top-level checks disagree');
      }
    });
  }
  return { states, checks };
}

function validateSolver(solver) {
  assert(object(solver) && ['openseespy.opensees', 'openseespylinux.opensees', 'openseespywin.opensees', 'openseespymac.opensees'].includes(solver.module), 'Native solver module is not actual OpenSees runtime');
  assert(nonempty(solver.version) && /^\d+\.\d+(?:\.\d+)*(?:[-+].*)?$/.test(solver.version), 'Native solver runtime version missing/invalid (package version is insufficient)');
  for (const field of ['runnerSha256', 'referenceIoSha256', 'nativeBinarySha256']) assert(HASH.test(solver[field]), `Native solver ${field} missing/invalid`);
  if (solver.nativeModuleSha256 !== undefined) assert(HASH.test(solver.nativeModuleSha256), 'Invalid nativeModuleSha256');
  if (solver.nativeBinaryModule !== undefined) assert(/^opensees(?:py|pylinux|pywin|pymac)\.opensees$/.test(solver.nativeBinaryModule), 'Wrong native binary module');
}

function validateRaw(raw, solver, model) {
  assert(object(raw) && raw.analysisReturnCode === 0, 'Native raw analysisReturnCode must be zero');
  assert(raw.runtime?.module === solver.module && raw.runtime?.version === solver.version, 'Native raw runtime/solver mismatch');
  for (const field of ['nodes', 'elements', 'nativeInput']) assert(object(raw[field]) && Object.keys(raw[field]).length, `Native raw ${field} missing/empty`);
  const vector = (value, size, label) => assert(Array.isArray(value) && value.length === size && value.every(finite), `Native raw ${label} must have ${size} finite values`);
  for (const [id, node] of Object.entries(raw.nodes)) {
    vector(node.displacement, 6, `${id} displacement`); vector(node.reaction, 6, `${id} reaction`);
  }
  for (const [id, element] of Object.entries(raw.elements)) {
    vector(element.globalForce, 12, `${id} globalForce`);
    if (element.localForce !== undefined) vector(element.localForce, 12, `${id} localForce`);
    else assert(finite(element.axialForce), `Native raw ${id} axialForce missing/non-finite`);
  }
  const plan = raw.nativeInput;
  assert(object(plan.nodes) && Object.keys(plan.nodes).length && object(plan.members) && Object.keys(plan.members).length && Array.isArray(plan.segments) && plan.segments.length, 'Native raw nativeInput lacks nodes/members/segments');
  assert(equal(Object.keys(plan.nodes).sort(), Object.keys(raw.nodes).sort()), 'Native raw input/response node mapping mismatch');
  const segments = index(plan.segments, segment => String(segment.tag), 'native segment');
  assert(equal([...segments.keys()].sort(), Object.keys(raw.elements).sort()), 'Native raw input/response element mapping mismatch');
  for (const [id, node] of Object.entries(plan.nodes)) assert(raw.nodes[id].tag === node.tag, `Native raw node tag mismatch ${id}`);
  for (const node of model.nodes) {
    const source = plan.nodes[node.id];
    assert(source?.authored === true && equal(source.xyz, [node.x, node.y, node.z]) && equal(source.authoredFixed, node.restraints), `Native raw authored node geometry/restraints mismatch ${node.id}`);
  }
  assert(equal(Object.keys(plan.members).sort(), model.elements.map(e => e.id).sort()), 'Native raw authored member mapping mismatch');
  for (const element of model.elements) assert(equal(plan.members[element.id]?.element, element), `Native raw authored member definition mismatch ${element.id}`);
}

// Read saved native response vectors only. This independently checks the result
// association and sign convention, without a stiffness solver or SUT imports.
function rawQuantity(raw, quantity) {
  const { location, component } = quantity, plan = raw.nativeInput;
  const index = DOFS.indexOf(component);
  let value;
  if (location.kind === 'node') {
    const node = raw.nodes[location.id]; assert(node, `Missing raw node ${location.id}`);
    assert(!(index >= 3 && plan.nodes[location.id].inactiveRotations && !plan.nodes[location.id].authoredFixed?.[index]), 'Inactive truss rotation is not a physical raw response quantity');
    value = index >= 0 ? node.displacement[index] : node.reaction[FORCES.indexOf(component.toLowerCase())];
  } else {
    const member = plan.members[location.id]; assert(member, `Missing raw member ${location.id}`);
    assert(finite(member.length) && member.length > 0, `Invalid raw member length ${location.id}`);
    const stationTolerance = 32 * Number.EPSILON * Math.max(1, member.length);
    assert(location.positionM >= 0 && location.positionM <= member.length + stationTolerance, `Raw member station outside ${location.id}`);
    const x = Math.min(location.positionM, member.length);
    const truss = ['truss', 'brace'].includes(member.element?.type);
    if (index >= 0) {
      if (truss) {
        assert(index < 3, 'Truss rotations are not physical raw response quantities');
        const [start, end] = member.element.nodes, t = x / member.length;
        value = (1 - t) * raw.nodes[start].displacement[index] + t * raw.nodes[end].displacement[index];
      } else {
        const stations = list(member.stationNodes, 'raw stationNodes').filter(item => Array.isArray(item) && finite(item[0]));
        assert(stations.length, 'Missing raw observation stations');
        const closest = stations.reduce((a, b) => Math.abs(b[0] - x) < Math.abs(a[0] - x) ? b : a);
        assert(Math.abs(closest[0] - x) <= stationTolerance, 'Raw beam observation node not connected at requested station');
        value = raw.nodes[closest[1]]?.displacement[index];
      }
    } else {
      const action = ACTIONS.indexOf(component); assert(action >= 0, `Unsupported raw member component ${component}`);
      const segments = plan.segments.filter(segment => segment.member === location.id && segment.start - stationTolerance <= x && x <= segment.end + stationTolerance)
        .sort((a, b) => a.start - b.start);
      assert(segments.length, `Missing raw member segment ${location.id}`);
      const segment = location.side === 'left' ? segments[0] : segments.at(-1);
      const response = raw.elements[String(segment.tag)];
      if (truss) value = component === 'N' ? response.axialForce : 0;
      else {
        const atStart = Math.abs(x - segment.start) <= stationTolerance;
        assert(atStart || Math.abs(x - segment.end) <= stationTolerance, 'Raw beam action requires a connected observation node');
        const signs = atStart ? [-1, 1, 1, -1, -1, -1] : [1, -1, -1, 1, 1, 1];
        value = response.localForce?.[action + (atStart ? 0 : 6)] * signs[action];
      }
    }
  }
  assert(finite(value), `Raw requested response missing/non-finite: ${quantity.id}`);
  return convert(value, componentUnit(component), quantity.unit);
}

function validateArtifacts(document, authored, directory, evidence, readJson, recordError, referenceChecks) {
  let artifacts = new Map();
  recordError('native artifact manifest', () => {
    artifacts = index(document.artifacts, a => a.path, 'native artifact');
    exactKeys(artifacts, new Map(RAW_FILES.map(name => [name, true])), 'native artifacts');
    for (const artifact of artifacts.values()) assert(HASH.test(artifact.sha256), `Invalid artifact hash ${artifact.path}`);
  });
  const receipts = new Map();
  for (const name of RAW_FILES) recordError(`native artifact ${name}`, () => {
    const item = readJson(directory, name, 'native'); receipts.set(name, item.value);
    assert(artifacts.get(name)?.sha256 === item.sha256, `Raw artifact hash mismatch/missing: ${name}`);
    assert(item.value.schemaVersion === 1 && item.value.id === authored.id, `Raw receipt case/schema mismatch: ${name}`);
  });
  recordError('native solver', () => {
    evidence.solver = document.solver; validateSolver(document.solver);
    const receipt = receipts.get('native-solver-receipt.json');
    assert(equal(receipt?.solver, document.solver), 'Native solver receipt/runtime/source/binary hash mismatch');
    assert(receipt.analysis === 'Linear elastic static', 'Native solver analysis mismatch');
    assert(equal(receipt.units, { length: 'm', force: 'kN', modulusInput: 'MPa', rotation: 'rad' }), 'Native raw solver units mismatch');
  });
  recordError('native input receipt', () => {
    const receipt = receipts.get('native-input-receipt.json'); assert(receipt, 'Missing native input receipt');
    bindInput(receipt, authored, 'native input receipt');
    const states = index(receipt.states, s => s.state, 'native input state'); exactKeys(states, authored.states, 'native input states');
    for (const [number, request] of authored.states) assert(states.get(number).modelPath === request.model && equal(states.get(number).model, request.authoredModel), `Native input state ${number} model mismatch`);
  });
  recordError('native raw runs', () => {
    const runs = index(receipts.get('native-raw-responses.json')?.runs, runKey, 'native raw run'); exactKeys(runs, authored.runs, 'native raw runs');
    for (const [key, expected] of authored.runs) {
      const run = runs.get(key);
      assert(equal(run.factors, expected.factors), `Native raw selection factors mismatch ${key}`);
      validateRaw(run.responses, document.solver, authored.states.get(expected.state).authoredModel);
      const state = document.states.find(s => s.state === expected.state);
      const values = index(state?.quantities, quantityKey, 'native raw reported quantity');
      for (const request of authored.states.get(expected.state).quantities.filter(q => equal(q.selection, expected.selection))) {
        const nativeValue = values.get(quantityKey(request))?.value;
        const rawValue = rawQuantity(run.responses, request);
        assert(finite(nativeValue) && close(nativeValue, rawValue, tolerance(request)).passed,
          `Native raw selected value mismatch ${key} ${request.id}: raw=${rawValue}, reference=${nativeValue}`);
      }
    }
  });
  recordError('native checks receipt', () => {
    const runs = index(receipts.get('native-checks.json')?.runs, runKey, 'native checks receipt run'); exactKeys(runs, authored.runs, 'native checks receipt runs');
    for (const [key, run] of runs) {
      checkEquilibrium(run.checks, true);
      assert(equal({ ...run.checks, state: run.state, selection: run.selection }, referenceChecks.get(key)), `Native raw/reference checks disagree ${key}`);
    }
  });
}

function auditCase(options, id) {
  const result = { id, plannedEngine: null, referenceValidated: false, nativeAgreement: false,
    comparisonCounts: { primitive: 0, derived: 0, passed: 0, failed: 0 }, comparisons: [], errors: [], artifacts: [],
    nativeVerified: false, accepted: false, acceptance: 'pending', inputBlindReview: 'pending',
    sameEngineTruthStatus: 'pending', nativeIndependentReview: 'pending', llmEndToEnd: 'not-run' };
  const recordError = (label, action) => {
    try { return action(); } catch (error) { result.errors.push(`${label}: ${error.message}`); return undefined; }
  };
  const snapshot = [];
  const readJson = (root, name, role) => {
    const bytes = readFile(root, name), hash = sha256(bytes);
    result.artifacts.push({ role, path: `${id}/${name}`, sha256: hash, bytes: bytes.length });
    snapshot.push({ root, name, hash });
    return { value: parseStrictJson(bytes), sha256: hash };
  };
  const authored = recordError('authored input', () => loadAuthored(options.root, id, result));
  if (!authored) return result;
  const independentDir = path.join(options.independentRoot, id), nativeDir = path.join(options.nativeRoot, id);
  const beforeIndependent = result.errors.length;
  const independent = recordError('independent reference', () => {
    const active = readJson(independentDir, 'independent-reference.json', 'independent');
    if (!['native-pkpm', 'native-yjk'].includes(active.value.referenceKind)) return active.value;
    const expectedKind = `native-${authored.contract.plannedEngine.toLowerCase()}`;
    assert(active.value.referenceKind === expectedKind && active.value.id === id &&
      active.value.sourceHash === authored.sourceHash && active.value.notCommercialScoringTruth === false &&
      active.value.sameEngineTruthStatus === 'verified', 'Invalid commercial scoring reference binding/status/engine');
    result.artifacts.at(-1).role = 'active-scoring-reference';
    const descriptor = active.value.matrixDiagnostic;
    assert(descriptor?.path === 'independent-reference-matrix-diagnostic.json' && HASH.test(descriptor.sha256),
      'Commercial scoring reference requires its bound matrix diagnostic');
    const diagnostic = readJson(independentDir, descriptor.path, 'independent');
    assert(diagnostic.sha256 === descriptor.sha256, 'Commercial matrix diagnostic hash mismatch');
    return diagnostic.value;
  });
  const independentResult = independent && validateReference(independent, authored, false, recordError);
  result.referenceValidated = result.errors.length === beforeIndependent;
  const native = recordError('native reference', () => readJson(nativeDir, 'native-opensees-reference.json', 'native').value);
  const nativeResult = native && validateReference(native, authored, true, recordError);
  if (native) validateArtifacts(native, authored, nativeDir, result, readJson, recordError, nativeResult.checks);
  for (const [number, state] of authored.states) {
    for (const kind of ['primitive', 'derived']) {
      const definitions = kind === 'primitive' ? state.quantities : state.derived;
      for (const request of definitions) {
        result.comparisonCounts[kind]++;
        const comparison = { state: number, kind, id: request.id, unit: request.unit, tolerance: tolerance(request), passed: false };
        if (request.selection) comparison.selection = request.selection;
        recordError(`comparison state ${number} ${kind} ${request.id}`, () => {
          const field = kind === 'primitive' ? 'quantities' : 'derived';
          const matches = reference => (reference?.states.get(number)?.[field] || []).filter(q => q.id === request.id && (kind === 'derived' || equal(q.selection, request.selection)));
          const a = matches(independentResult), b = matches(nativeResult);
          assert(a.length === 1 && b.length === 1, 'Missing/duplicate independent or native quantity');
          assert(finite(a[0].value) && finite(b[0].value), 'Comparison values must be finite');
          Object.assign(comparison, { independent: a[0].value, native: b[0].value }, close(b[0].value, a[0].value, tolerance(request)));
          assert(comparison.passed, `Signed value disagreement: independent=${a[0].value}, native=${b[0].value}, delta=${comparison.delta}, frozen limit=${comparison.limit}`);
        });
        result.comparisonCounts[comparison.passed ? 'passed' : 'failed']++;
        result.comparisons.push(comparison);
      }
    }
  }
  const oldErrors = result.errors.length;
  recordError('input stability', () => {
    authored.unchanged();
    for (const item of snapshot) assert(sha256(readFile(item.root, item.name)) === item.hash, `Reference artifact changed during audit: ${item.name}`);
  });
  if (result.errors.length > oldErrors) result.referenceValidated = false;
  result.nativeAgreement = result.errors.length === 0 && result.comparisonCounts.passed > 0;
  return result;
}

function auditReferences(options) {
  assert(object(options), 'Explicit audit options required');
  for (const name of ['root', 'independentRoot', 'nativeRoot']) { const fd = openDirectory(options[name]); fs.closeSync(fd); }
  const casesRoot = path.join(options.root, 'corpora/research-300/cases');
  let ids = options.caseIds || [];
  assert(Array.isArray(ids), 'caseIds must be an array');
  if (!ids.length) {
    const fd = openDirectory(casesRoot);
    try { ids = fs.readdirSync(`/proc/self/fd/${fd}`).sort(); } finally { fs.closeSync(fd); }
  }
  assert(ids.length > 0 && ids.every(id => typeof id === 'string' && CASE_ID.test(id)), 'No cases or invalid research-300 case ID');
  assert(new Set(ids).size === ids.length, 'Duplicate --case ID');
  const cases = ids.map(id => auditCase(options, id));
  return { schemaVersion: 1, reportKind: 'research-300-reference-cross-check',
    scope: 'benchmark-only numerical diagnostics for independent root review',
    checker: { nodeVersion: process.version, sourceSha256: sha256(fs.readFileSync(__filename)) },
    roots: { authored: path.resolve(options.root), independent: path.resolve(options.independentRoot), native: path.resolve(options.nativeRoot) },
    valid: cases.every(c => c.nativeAgreement),
    acceptance: 'pending', accepted: false, nativeVerified: false, nativeIndependentReview: 'pending',
    sameEngineTruthStatus: 'pending', llmEndToEnd: 'not-run',
    referenceValidationScope: 'Current authored binding, exact requested records, arithmetic and equilibrium evidence; independent review still required',
    cases, summary: { cases: cases.length, referenceValidated: cases.filter(c => c.referenceValidated).length,
      nativeAgreement: cases.filter(c => c.nativeAgreement).length, errors: cases.reduce((n, c) => n + c.errors.length, 0) } };
}

function main(argv = process.argv.slice(2)) {
  try {
    const options = { caseIds: [] };
    for (let i = 0; i < argv.length; i++) {
      const flag = argv[i];
      if (flag === '--help') {
        process.stdout.write('Usage: check-research300-references.cjs --root benchmarkRoot --independent-root DIR --native-root DIR [--case ID ...] [--output NEWFILE]\nJSON stdout by default; exclusive explicit output. Exit 0 agreement, 1 audit failures, 2 invocation/I/O failure. No acceptance or provenance is created. Linux + Node 22.\n');
        return 0;
      }
      const names = { '--root': 'root', '--independent-root': 'independentRoot', '--native-root': 'nativeRoot', '--output': 'output', '--case': 'caseIds' };
      const name = Object.hasOwn(names, flag) ? names[flag] : undefined;
      assert(name && nonempty(argv[i + 1]) && !argv[i + 1].startsWith('--'), `Unknown option/missing value: ${flag}`);
      if (name === 'caseIds') options.caseIds.push(argv[++i]);
      else { assert(options[name] === undefined, `Duplicate option ${flag}`); options[name] = argv[++i]; }
    }
    const report = auditReferences(options);
    const serialized = `${JSON.stringify(report, null, 2)}\n`;
    if (options.output) {
      assert(!options.output.split('/').includes('..'), 'Unsafe output path');
      const output = path.resolve(options.output), corpus = path.join(path.resolve(options.root), 'corpora/research-300');
      assert(output !== corpus && !output.startsWith(`${corpus}/`), 'Report output must be outside authored corpus');
      withParent(path.dirname(output), path.basename(output), target => {
        const fd = fs.openSync(target, fs.constants.O_WRONLY | fs.constants.O_CREAT | fs.constants.O_EXCL | fs.constants.O_NOFOLLOW, 0o644);
        try { fs.writeFileSync(fd, serialized); fs.fsyncSync(fd); } finally { fs.closeSync(fd); }
      });
    } else process.stdout.write(serialized);
    return report.valid ? 0 : 1;
  } catch (error) { process.stderr.write(`reference cross-check failed: ${error.message}\n`); return 2; }
}

module.exports = { auditReferences, main, parseStrictJson };
if (require.main === module) process.exitCode = main();
