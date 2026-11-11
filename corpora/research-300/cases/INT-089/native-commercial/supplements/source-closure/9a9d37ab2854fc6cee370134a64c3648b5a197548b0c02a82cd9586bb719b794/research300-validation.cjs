'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { isDeepStrictEqual: equal } = require('node:util');
const { resolveCaseFile, validatePublicAttachments, getResponseContract, listFiles, sha256, CASE_ID } = require('./corpus-provider.cjs');
const {referenceAllowance,validatePrecisionScope}=require('./reference-precision.cjs');
const ROOT = path.resolve(__dirname, '..');
const PLAN_PATH = 'planning/capability-coverage-300.json';
const PLAN_SHA256 = '1f82aed740ae8c3ae032aa85fdb1280dd91530cb655281e043fd91098591a888';
const FAMILY = { STD: 'standard_workflow', INT: 'interactive_robustness', MM: 'multimodal_reverse_engineering' };
const STAGES = ['authored', 'reference-ready', 'accepted'];
const schemas = Object.fromEntries(['contract', 'reference-requests', 'manifest'].map(name => [name, JSON.parse(fs.readFileSync(path.join(ROOT, 'schemas', `research300-${name}.schema.json`), 'utf8'))]));
const readJson = file => JSON.parse(fs.readFileSync(file, 'utf8'));
const nonempty = value => typeof value === 'string' && !!value.trim();
const number = Number.isFinite;
const array = value => Array.isArray(value) ? value : [];

// A deliberately small validator for the JSON Schema keywords used by our three
// checked-in schemas. Unknown keywords fail closed, avoiding a silent partial
// implementation if a future schema introduces a new validation feature.
function validateSchema(value, schema, label = '$', errors = []) {
  const allowed = new Set(['$schema', '$id', 'title', 'description', 'type', 'const', 'enum', 'anyOf', 'oneOf', 'properties', 'required', 'additionalProperties', 'minProperties', 'items', 'minItems', 'uniqueItems', 'minimum', 'minLength', 'pattern']);
  for (const key of Object.keys(schema)) if (!allowed.has(key)) throw new Error(`Unsupported schema keyword: ${key}`);
  const fail = message => errors.push(`${label}: ${message}`);
  if (schema.anyOf || schema.oneOf) {
    const matches = (schema.anyOf || schema.oneOf).filter(s => validateSchema(value, s, label, []).length === 0).length;
    if (schema.oneOf ? matches !== 1 : matches === 0) fail('does not match schema alternatives');
  }
  if ('const' in schema && !equal(value, schema.const)) fail(`must equal ${JSON.stringify(schema.const)}`);
  if (schema.enum && !schema.enum.some(x => equal(x, value))) fail(`must be one of ${schema.enum.join(', ')}`);
  const type = value === null ? 'null' : Array.isArray(value) ? 'array' : typeof value;
  if (schema.type && !(schema.type === 'integer' ? Number.isInteger(value) : schema.type === type)) { fail(`must be ${schema.type}`); return errors; }
  if (type === 'number') {
    if (!number(value)) fail('must be finite');
    if ('minimum' in schema && value < schema.minimum) fail(`must be >= ${schema.minimum}`);
  }
  if (type === 'string') {
    if ('minLength' in schema && value.trim().length < schema.minLength) fail('must be nonempty');
    if (schema.pattern && !new RegExp(schema.pattern).test(value)) fail('invalid format');
  }
  if (type === 'array') {
    if (schema.minItems && value.length < schema.minItems) fail(`requires at least ${schema.minItems} items`);
    if (schema.uniqueItems && new Set(value.map(v => JSON.stringify(v))).size !== value.length) fail('duplicate items');
    if (schema.items) value.forEach((v, i) => validateSchema(v, schema.items, `${label}[${i}]`, errors));
  }
  if (type === 'object') {
    if (schema.minProperties && Object.keys(value).length < schema.minProperties) fail('requires properties');
    for (const key of schema.required || []) if (!Object.hasOwn(value, key)) fail(`missing ${key}`);
    for (const [key, item] of Object.entries(value)) {
      if (Object.hasOwn(schema.properties || {}, key)) validateSchema(item, schema.properties[key], `${label}.${key}`, errors);
      else if (schema.additionalProperties === false) fail(`unexpected property ${key}`);
      else if (schema.additionalProperties && typeof schema.additionalProperties === 'object') validateSchema(item, schema.additionalProperties, `${label}.${key}`, errors);
    }
  }
  return errors;
}

function validateSourcePlan(plan) {
  const errors = [], cases = array(plan?.cases), ids = cases.map(c => c.id);
  const expected = Object.keys(FAMILY).flatMap(p => Array.from({ length: 100 }, (_, i) => `${p}-${String(i + 1).padStart(3, '0')}`));
  if (!equal([...ids].sort(), expected.sort())) errors.push('Source plan must contain exactly all300 unique STD/INT/MM-001..100 IDs');
  const engines = {}, languages = {}, families = {}; let requirements = 0;
  if (plan?.modelProtocol !== '2.2.0') errors.push('Source modelProtocol must be 2.2.0');
  for (const c of cases) {
    if (c.family !== FAMILY[c.id?.split('-')[0]] || c.modelId !== `M-${c.id}`) errors.push(`${c.id}: source family/modelId mismatch`);
    engines[c.plannedEngine] = (engines[c.plannedEngine] || 0) + 1;
    families[c.family] = (families[c.family] || 0) + 1;
    const lang = `${c.family}:${c.language}`; languages[lang] = (languages[lang] || 0) + 1;
    const seen = new Set(), fields = new Set();
    for (const r of array(c.requirements)) {
      requirements++;
      if (!Number.isInteger(r.id) || r.id < 1 || seen.has(r.id)) errors.push(`${c.id}: duplicate/invalid requirement ID`);
      seen.add(r.id); fields.add(r.sourceField);
      const text = c.sourceRequirements?.[r.sourceField], range = r.sourceRange;
      if (!nonempty(text) || !Array.isArray(range) || range.length !== 2 || !range.every(Number.isInteger) || range[0] < 0 || range[1] <= range[0] || range[1] > text.length) errors.push(`${c.id}: invalid source requirement range ${r.id}`);
    }
    for (const field of Object.keys(c.sourceRequirements || {})) if (!fields.has(field)) errors.push(`${c.id}: source field has no requirement IDs: ${field}`);
  }
  if (!equal(engines, { OpenSees: 267, PKPM: 16, YJK: 17 })) errors.push('Source engine allocation must be OpenSees267/PKPM16/YJK17');
  for (const family of Object.values(FAMILY)) for (const language of ['中文', '英文']) if (languages[`${family}:${language}`] !== 50) errors.push(`Source allocation must contain 50 ${language} ${family}`);
  if (plan?.summary?.cases !== cases.length || !equal(plan?.summary?.byEngine, engines) || !equal(plan?.summary?.byFamily, families) || plan?.summary?.requirementClauses !== requirements) errors.push('Source summary differs from source rows');
  return { valid: errors.length === 0, errors };
}

function validateModel(model, state, errors) {
  const fail = msg => errors.push(`state ${state}: ${msg}`);
  if (model?.schema_version !== '2.2.0' || model?.unit_system !== 'SI' || model?.coordinate_system?.semantics !== 'global-z-up') fail('model must use protocol2.2.0, SI and global-z-up');
  for (const key of ['nodes', 'elements', 'materials', 'sections', 'load_cases', 'load_combinations']) {
    if (!Array.isArray(model?.[key]) || (key !== 'load_combinations' && !model[key].length)) fail(`explicit ${key} array required`);
    const seen = new Set();
    for (const item of array(model?.[key])) {
      if (!nonempty(item?.id) || seen.has(item.id)) fail(`duplicate/invalid ${key} id`);
      seen.add(item?.id);
    }
  }
  for (const setting of ['self_weight', 'rigid_floor', 'p_delta', 'rigid_offsets', 'construction_stage']) if (typeof model?.analysis_control?.[setting] !== 'boolean') fail(`explicit analysis_control.${setting} required`);
  const nodes = new Map(array(model?.nodes).map(n => [n.id, n]));
  for (const n of nodes.values()) if (!['x', 'y', 'z'].every(k => number(n[k])) || !Array.isArray(n.restraints) || n.restraints.length !== 6 || !n.restraints.every(v => typeof v === 'boolean')) fail(`node ${n.id} requires finite XYZ and six boolean restraints`);
  const materials = new Set(array(model?.materials).map(m => m.id)), sections = new Set(array(model?.sections).map(s => s.id));
  for (const e of array(model?.elements)) {
    if (!Array.isArray(e.nodes) || e.nodes.length !== 2 || e.nodes[0] === e.nodes[1] || e.nodes.some(n => !nodes.has(n))) fail(`element ${e.id} requires two distinct existing nodes`);
    if (!materials.has(e.material) || !sections.has(e.section)) fail(`element ${e.id} has missing material/section`);
  }
  for (const material of array(model?.materials)) if (!number(material.E) || material.E <= 0 || !number(material.G) || material.G <= 0 || !number(material.nu)) fail(`material ${material.id} requires explicit E/G/nu`);
  for (const section of array(model?.sections)) for (const p of ['A', 'Iy', 'Iz', 'J']) if (!number(section.properties?.[p]) || section.properties[p] <= 0) fail(`section ${section.id} requires positive ${p}`);
}

const quantityKey = q => `${q.selection?.kind}:${q.selection?.id}:${q.id}`;
const UNIT = { m: ['length', 1], mm: ['length', 0.001], rad: ['rotation', 1], kN: ['force', 1], N: ['force', 0.001], 'kN.m': ['moment', 1], 'kN*m': ['moment', 1], 'kN·m': ['moment', 1], 'N.m': ['moment', 0.001], 'N*m': ['moment', 0.001] };
const DEFAULT_TOLERANCE = Object.freeze({ absolute: 1e-8, relative: 1e-6 });
const isExtremum = operation => ['max', 'min', 'max_abs'].includes(operation);
function compensatedSum(values) {
  let sum = 0, correction = 0;
  for (const value of values) {
    const next = sum + value;
    correction += Math.abs(sum) >= Math.abs(value) ? (sum - next) + value : (value - next) + sum;
    sum = next;
  }
  return sum + correction;
}
function validateRequests(requests, contract, models, errors) {
  const shapeErrors = validateSchema(requests, schemas['reference-requests'], 'reference-requests');
  errors.push(...shapeErrors);
  if (shapeErrors.length) return new Map();
  const states = array(requests?.states), seenStates = new Set(), maps = new Map();
  for (const s of states) {
    const label = `reference state ${s.state}`, fail = msg => errors.push(`${label}: ${msg}`), model = models[s.state - 1];
    const validateTolerance = (record, kind) => {
      const tolerance = record.tolerance;
      if (tolerance && (tolerance.absolute !== DEFAULT_TOLERANCE.absolute || tolerance.relative !== DEFAULT_TOLERANCE.relative) && !nonempty(record.toleranceJustification) && !(nonempty(contract.tolerancePolicy?.justification) && contract.tolerancePolicy.frozenBeforeCandidate === true)) fail(`${kind} ${record.id} nondefault tolerance needs frozen justification`);
      if (tolerance?.absolute === 0 && tolerance?.relative === 0) fail(`${kind} ${record.id} tolerance cannot be identically zero`);
    };
    if (seenStates.has(s.state)) fail('duplicate state'); seenStates.add(s.state);
    if (!model || s.model !== contract.modelStates?.[s.state - 1]) { fail('model/state does not match contract'); continue; }
    const nodes = new Map(array(model.nodes).map(n => [n.id, n])), members = new Map(array(model.elements).map(e => [e.id, e]));
    const unique = new Set(), byId = new Map();
    for (const q of array(s.quantities)) {
      const key = quantityKey(q);
      if (unique.has(key)) fail(`duplicate quantity ${key}`); unique.add(key);
      byId.set(q.id, [...(byId.get(q.id) || []), q]);
      const collection = q.selection?.kind === 'case' ? model.load_cases : model.load_combinations;
      if (!array(collection).some(c => c.id === q.selection?.id)) fail(`quantity ${q.id} selection does not exist`);
      const c = q.component;
      const units = /^(u[xyz])$/.test(c) ? ['m', 'mm'] : /^r[xyz]$/.test(c) ? ['rad'] : /^(F[xyz]|N|V[23])$/.test(c) ? ['kN', 'N'] : ['kN.m', 'N.m', 'kN*m', 'N*m', 'kN·m'];
      if (!units.includes(q.unit)) fail(`quantity ${q.id} component/unit mismatch`);
      if (q.location?.kind === 'node') {
        const n = nodes.get(q.location.id);
        if (!n) fail(`quantity ${q.id} node does not exist`);
        if (!/^(u[xyz]|r[xyz]|F[xyz]|M[xyz])$/.test(c)) fail(`quantity ${q.id} invalid node component`);
        // Requested reactions at released DOFs are legitimate exact-zero checks.
        // Do not invent a restraint or drop a source-requested support moment.
        if (n && /^u/.test(c) && !array(model.elements).some(e => e.nodes?.includes(n.id))) fail(`quantity ${q.id} displacement observation node is unconnected`);
      } else if (q.location?.kind === 'member') {
        const e = members.get(q.location.id);
        if (!e) fail(`quantity ${q.id} member does not exist`);
        if (!/^(N|V2|V3|T|M2|M3|u[xyz]|r[xyz])$/.test(c)) fail(`quantity ${q.id} invalid member component`);
        if (e && e.nodes?.every(n => nodes.has(n))) {
          const [a, b] = e.nodes.map(n => nodes.get(n));
          const length = Math.hypot(a.x - b.x, a.y - b.y, a.z - b.z);
          if (!(length > 0) || q.location.positionM > length + 1e-10) fail(`quantity ${q.id} station outside member`);
        }
      }
      validateTolerance(q, 'quantity');
    }
    const derived = new Map(), derivedOrder = new Map();
    for (const d of array(s.derived)) {
      if (byId.has(d.id) || derived.has(d.id)) fail(`duplicate derived quantity ${d.id}`);
      derivedOrder.set(d.id, derived.size);
      derived.set(d.id, d);
      validateTolerance(d, 'derived');
      if (Object.hasOwn(d, 'tiePolicy') && !isExtremum(d.operation)) fail(`derived ${d.id} tiePolicy is only valid for extrema`);
    }
    const visiting = new Set(), done = new Set();
    function visit(d) {
      if (visiting.has(d.id)) { fail(`derived cycle at ${d.id}`); return; }
      if (done.has(d.id)) return;
      visiting.add(d.id);
      if (d.operation === 'difference' && d.operands?.length !== 2) fail(`difference ${d.id} requires two operands`);
      for (const id of array(d.operands)) {
        const qs = byId.get(id), child = derived.get(id), operand = qs?.[0] || child;
        if (!operand || qs?.length > 1) fail(`derived ${d.id} operand ${id} missing or ambiguous across selections`);
        if (operand && (!UNIT[d.unit] || UNIT[operand.unit]?.[0] !== UNIT[d.unit][0])) fail(`derived ${d.id} operand unit mismatch`);
        if (child && derivedOrder.get(child.id) >= derivedOrder.get(d.id)) fail(`derived ${d.id} forward operand ${id} must reference an earlier derived record`);
        if (child) visit(child);
      }
      visiting.delete(d.id); done.add(d.id);
    }
    for (const d of derived.values()) visit(d);
    maps.set(s.state, { byId, derived });
  }
  for (let i = 1; i <= contract.modelStates?.length; i++) if (!seenStates.has(i)) errors.push(`Missing reference request state ${i}`);
  return maps;
}

function validateOutputsAndCoverage(contract, planCase, maps, errors) {
  const outputs = new Map(), turns = new Set(array(contract.turns).map(t => t.id));
  for (const o of array(contract.requiredOutputs)) {
    if (outputs.has(o.id)) errors.push(`Duplicate requiredOutput ${o.id}`); outputs.set(o.id, o);
    if (o.state !== null && !maps.has(o.state)) errors.push(`Output ${o.id} references unknown state`);
    for (const id of array(o.turnIds)) if (!array(contract.turns).some(t => t.id === id && t.state === o.state)) errors.push(`Output ${o.id} turnIds must resolve to turns using the output state`);
    if (['numerical', 'derived'].includes(o.kind) && (!array(o.quantityIds).length || o.state === null)) errors.push(`Output ${o.id} requires state and quantityIds`);
    if (o.kind === 'interaction' && array(o.quantityIds).length) errors.push(`Interaction output ${o.id} cannot stand in for quantities`);
    for (const id of array(o.quantityIds)) {
      const m = maps.get(o.state), q = m?.byId.get(id), d = m?.derived.get(id);
      if (!q && !d) errors.push(`Output ${o.id} requests nonexistent quantity ${id}`);
      if (q?.length > 1) errors.push(`Output ${o.id} quantity ${id} ambiguous across selections`);
      if (o.kind === 'derived' && !d) errors.push(`Derived output ${o.id} must reference derived quantity ${id}`);
    }
  }
  const source = new Map(array(planCase?.requirements).map(r => [r.id, r])), covered = new Set(), outputTargets = new Set(), quantityTargets = new Set();
  const gates = new Set(array(contract.acceptanceGates).map(g => g.id));
  for (const row of array(contract.requirementCoverage)) {
    for (const id of array(row.requirementIds)) {
      const r = source.get(id);
      if (!r || r.sourceField !== row.sourceField) errors.push(`Coverage requirement ${id} does not match original sourceField ${row.sourceField}`);
      covered.add(id);
    }
    for (const target of array(row.targets)) {
      const parts = typeof target === 'string' ? target.match(/^([^:]+):(.+)$/) : null;
      let kind = parts?.[1] || target?.kind, id = parts?.[2] || target?.id;
      kind = ({ turns: 'turn', attachments: 'attachment', quantities: 'quantity', requiredOutputs: 'output', gates: 'gate' })[kind] || kind;
      if (typeof target === 'string' && array(contract.attachments).includes(target)) { kind = 'attachment'; id = target; }
      if (typeof target === 'string' && turns.has(target)) { kind = 'turn'; id = target; }
      let valid = false;
      if (kind === 'turn') valid = turns.has(id);
      if (kind === 'attachment') valid = array(contract.attachments).includes(id);
      if (kind === 'output') { valid = outputs.has(id); if (valid) outputTargets.add(id); }
      if (kind === 'quantity') { valid = [...maps.entries()].some(([state, m]) => (!target.state || state === target.state) && (m.byId.has(id) || m.derived.has(id))); if (valid) quantityTargets.add(id); }
      if (target === 'requiredOutputs') { valid = outputs.size > 0; for (const id of outputs.keys()) outputTargets.add(id); }
      if (target === 'reference-requests.json') { valid = maps.size > 0; for (const m of maps.values()) for (const id of [...m.byId.keys(), ...m.derived.keys()]) quantityTargets.add(id); }
      if (['gate', 'acceptance-gate'].includes(kind)) valid = nonempty(id) && (gates.size ? gates.has(id) : /review|reference|native|execution|evidence|truth|accept|policy|pending|fidelity|coverage|output|modality|analysis|unit|sign|engine|state|report|interaction/.test(id));
      if (!valid) errors.push(`Unresolved coverage target ${JSON.stringify(target)}`);
    }
  }
  for (const r of source.values()) if (!covered.has(r.id)) errors.push(`Missing coverage for original requirement ${r.id} (${r.sourceField})`);
  // Every output must be reachable from the retained source requirements. Text
  // mapping is evidence of authoring only; it never sets any acceptance status.
  for (const o of outputs.values()) if (!outputTargets.has(o.id) && !(array(o.quantityIds).length && o.quantityIds.every(id => quantityTargets.has(id)))) errors.push(`Required output ${o.id} is not linked from requirementCoverage`);
  const expected = planCase?.sourceRequirements?.['task.expectedOutput'] || '';
  if (/图|diagram|plot|figure/i.test(expected) && ![...outputs.values()].some(o => o.kind === 'figure')) errors.push('Source figure output cannot be fulfilled by numeric-only outputs');
}

function atPointer(object, pointer) {
  if (!pointer.startsWith('/')) return undefined;
  return pointer.slice(1).split('/').map(s => s.replace(/~1/g, '/').replace(/~0/g, '~')).reduce((v, k) => {
    if (v == null) return undefined;
    if (Array.isArray(v) && !/^\d+$/.test(k)) return v.find(item => item?.id === k);
    return Object.hasOwn(v, k) ? v[k] : undefined;
  }, object);
}

function validateTurns(contract, planCase, models, errors, caseDir) {
  const turns = array(contract.turns), analyzed = new Set();
  const visible = new Set();
  let currentState = null;
  const count = planCase?.sourceRequirements?.['task.inputForm']?.match(/(?:文本)(单|[0-9]+)轮/);
  if (count && turns.length !== (count[1] === '单' ? 1 : Number(count[1]))) errors.push('Turn count differs from original source inputForm');
  for (const [index, t] of turns.entries()) {
    const fail = msg => errors.push(`turn ${index + 1}: ${msg}`);
    for (const name of array(t.attachments)) visible.add(name);
    if (t.id !== `t${index + 1}`) fail('id must preserve sequential t1..tN order');
    if (contract.locale === 'en' && /[\u3400-\u9fff]/.test(t.instruction || '')) fail('English instruction contains Chinese text');
    if (t.state !== null && !models[t.state - 1]) fail('state does not exist');
    const nonblocking = t.clarificationBlocksAnalysis === false;
    if (nonblocking && (t.expectation !== 'analyze' || t.state === null || !models[t.state - 1] || !array(t.unresolvedFields).length || !array(t.expectedQuestions).length || !array(t.unresolvedFields).every(field => typeof field === 'string' && /^\/requestedOutputs\/(?:[^~/]|~[01])+(?:\/(?:[^~/]|~[01])+)*$/.test(field)))) {
      fail('clarificationBlocksAnalysis:false requires analyze, a known state, expectedQuestions, and exclusively /requestedOutputs/<...> ambiguity; physical omissions remain blocking');
    }
    if (t.expectation === 'clarify') {
      if (!array(t.unresolvedFields).length || !array(t.expectedQuestions).length) fail('clarify requires unresolvedFields and expectedQuestions');
      if (t.state !== null) fail('clarify with essential missing input requires null state');
      // A JSON pointer is a machine-checkable unresolved field. Natural-language
      // omissions and drawings still require the independent input blind review.
      for (const field of array(t.unresolvedFields).filter(f => f.startsWith('/'))) {
        for (const name of visible) {
          if (!name.endsWith('.json')) continue;
          try {
            const publicValue = atPointer(readJson(resolveCaseFile(caseDir, name)), field);
            if (publicValue !== undefined && publicValue !== null && publicValue !== '') fail(`attachment ${name} exposes unresolved field ${field}`);
          } catch (e) { fail(`Cannot inspect unresolved field in ${name}: ${e.message}`); }
        }
      }
    } else {
      if (t.state === null || (!nonblocking && (array(t.unresolvedFields).length || array(t.expectedQuestions).length))) fail('analyze/query requires resolved state and no pending questions');
    }
    if (t.expectation === 'query' && !analyzed.has(t.state)) fail('query requires an earlier analyzed state');
    if (t.expectation === 'query' && currentState !== t.state) fail('query must use the current analyzed state');
    if (array(t.changedFields).length && t.expectation !== 'analyze') fail('actual edit requires current analysis');
    if (currentState !== null && t.state !== null) {
      const previous = models[currentState - 1], current = models[t.state - 1];
      const value = (model, pointer) => pointer === '/' ? model : atPointer(model, pointer);
      for (const pointer of array(t.changedFields)) if (equal(value(previous, pointer), value(current, pointer))) fail(`changedFields pointer ${pointer} did not change`);
      for (const pointer of array(t.preservedFields)) if (value(previous, pointer) === undefined || !equal(value(previous, pointer), value(current, pointer))) fail(`preservedFields pointer ${pointer} is missing or changed`);
    }
    if (t.expectation === 'analyze') { analyzed.add(t.state); currentState = t.state; }
    if (array(t.changedFields).some(p => array(t.preservedFields).includes(p))) fail('changedFields overlaps preservedFields');
  }
  for (let state = 1; state <= models.length; state++) if (!analyzed.has(state)) errors.push(`Model state ${state} has no analysis turn`);
}

function validateReference(reference, requests, errors, caseDir, contract) {
  if (!reference || !Array.isArray(reference.states)) { errors.push('independent-reference.json with states is required'); return; }
  if (reference.toleranceFrozenBeforeCandidate !== true) errors.push('Independent reference must declare toleranceFrozenBeforeCandidate');
  if (!equal(reference.analysisConvention, contract?.analysisConvention)) errors.push('Reference analysisConvention differs from the authored contract');
  if (contract?.analysisConvention && reference.referenceKind === 'independent-elastic-matrix') {
    const checks = array(reference.checks);
    const selections = array(requests?.states).flatMap(state => [...new Map(array(state.quantities).map(q => [JSON.stringify(q.selection), q.selection])).values()].map(selection => ({ state: state.state, selection })));
    if (checks.length !== selections.length || selections.some(expected => {
      const matches = checks.filter(check => check.state === expected.state && equal(check.selection, expected.selection));
      return matches.length !== 1 || matches[0].theory !== 'Timoshenko';
    })) errors.push('Revised matrix reference requires a Timoshenko check for every typed state/selection');
  }
  if (caseDir) {
    const expectedHashes = Object.fromEntries(['contract.json', 'reference-requests.json', ...array(contract.modelStates)].map(name => [name, sha256(fs.readFileSync(resolveCaseFile(caseDir, name)))]));
    if (!equal(reference.inputHashes, expectedHashes)) errors.push('Independent reference inputHashes are missing or stale');
    if (reference.sourceHash !== sourceHash(caseDir, contract)) errors.push('Independent reference sourceHash is missing or stale');
  }
  const actual = new Map();
  for (const state of reference.states) {
    if (actual.has(state.state)) errors.push('Duplicate independent reference state');
    actual.set(state.state, state);
  }
  for (const wanted of array(requests?.states)) {
    const state = actual.get(wanted.state);
    if (!state) { errors.push(`Missing independent reference state ${wanted.state}`); continue; }
    const values = new Map();
    for (const q of array(state.quantities)) {
      if (values.has(quantityKey(q))) errors.push(`Duplicate independent quantity ${quantityKey(q)}`);
      values.set(quantityKey(q), q);
    }
    for (const q of array(wanted.quantities)) {
      const result = values.get(quantityKey(q));
      if (!result || !number(result.value)) { errors.push(`Missing finite reference value ${wanted.state}:${quantityKey(q)}`); continue; }
      for (const field of ['selection', 'location', 'component', 'unit', 'tolerance']) if (!equal(q[field], result[field])) errors.push(`Reference quantity ${q.id} ${field} differs from frozen request`);
      if (result.engineeringPrecision !== undefined) {
        try {
          if (contract?.plannedEngine !== 'PKPM' || array(wanted.derived).length)
            throw new Error('Certified recovery precision only covers PKPM raw member-end requests without derived propagation');
          referenceAllowance(result);
          validatePrecisionScope(result,readJson(resolveCaseFile(caseDir,wanted.model)));
        } catch(error) {errors.push(`Reference quantity ${q.id}: ${error.message}`);}
      }
    }
    for (const d of array(wanted.derived)) {
      const value = array(state.derived).find(x => x.id === d.id);
      if (!value || !number(value.value) || value.unit !== d.unit) errors.push(`Missing finite derived reference ${d.id}`);
      if (isExtremum(d.operation) && (!array(d.operands).includes(value?.governingOperand) || !(value?.governingSelection || value?.selection || array(value?.governingSelections).length))) errors.push(`${d.operation} reference ${d.id} must retain governing operand/selection and signed value`);
    }
    const computed = new Map(), visiting = new Set();
    function compute(record) {
      if (computed.has(record.id)) return computed.get(record.id);
      if (visiting.has(record.id)) throw new Error(`Derived reference cycle ${record.id}`);
      visiting.add(record.id);
      const sources = record.operands.map(id => {
        const raw = array(state.quantities).filter(q => q.id === id);
        if (raw.length === 1) return { ...raw[0], leaves: [{ id: raw[0].id, selection: raw[0].selection }] };
        const derived = array(wanted.derived).find(d => d.id === id);
        if (!derived || raw.length) throw new Error(`Missing/ambiguous derived reference operand ${id}`);
        return compute(derived);
      });
      const numbers = sources.map(s => {
        if (!number(s.value) || !UNIT[record.unit] || UNIT[s.unit]?.[0] !== UNIT[record.unit][0]) throw new Error(`Invalid derived reference unit/value ${record.id}`);
        const converted = s.value * UNIT[s.unit][1] / UNIT[record.unit][1];
        if (!number(converted)) throw new Error(`Invalid derived reference converted value ${record.id}`);
        return converted;
      });
      const tolerance = record.tolerance ?? DEFAULT_TOLERANCE;
      if (!number(tolerance.absolute) || !number(tolerance.relative) || tolerance.absolute < 0 || tolerance.relative < 0 || (tolerance.absolute === 0 && tolerance.relative === 0)) throw new Error(`Invalid derived reference tolerance ${record.id}`);
      let value, governing, coGoverningOperands;
      if (record.operation === 'difference') value = numbers[0] - numbers[1];
      else if (record.operation === 'sum') value = compensatedSum(numbers);
      else {
        const scores = record.operation === 'max_abs' ? numbers.map(Math.abs) : numbers;
        const best = scores.reduce((a, b) => record.operation === 'min' ? Math.min(a, b) : Math.max(a, b));
        const limit = tolerance.absolute + tolerance.relative * Math.abs(best);
        if (!number(limit)) throw new Error(`Invalid derived reference tolerance bound ${record.id}`);
        const coGovernors = scores.map((score, i) => Math.abs(score - best) <= limit ? i : -1).filter(i => i >= 0);
        // Reference truth is canonical even when the public answer may choose
        // any co-governor. Compare signed values against this first operand.
        governing = coGovernors[0];
        coGoverningOperands = coGovernors.map(i => record.operands[i]);
        value = numbers[governing];
      }
      if (!number(value)) throw new Error(`Invalid derived reference arithmetic value ${record.id}`);
      const leaves = governing === undefined ? sources.flatMap(source => source.leaves) : sources[governing].leaves;
      const selections = [];
      for (const leaf of leaves) if (!selections.some(selection => equal(selection, leaf.selection))) selections.push(leaf.selection);
      const selection = selections.length === 1 ? selections[0] : undefined;
      const result = { id: record.id, unit: record.unit, value, selection, leaves };
      const actual = array(state.derived).find(d => d.id === record.id);
      if (!actual || !number(actual.value) || Math.abs(actual.value - value) > tolerance.absolute + tolerance.relative * Math.abs(value)) errors.push(`Derived reference ${record.id} arithmetic/signed value differs from operands`);
      if (actual && (!equal(actual.operands, record.operands) || actual.operation !== record.operation)) errors.push(`Derived reference ${record.id} differs from requested operation/operands`);
      if (governing !== undefined && actual && (actual.governingOperand !== record.operands[governing] || !equal(actual.governingSelection || actual.selection, selection))) errors.push(`Derived reference ${record.id} governing operand/selection mismatch`);
      if (actual && (record.tolerance || Object.hasOwn(actual, 'tolerance')) && !equal(actual.tolerance, tolerance)) errors.push(`Derived reference ${record.id} tolerance differs from frozen request`);
      if (actual && Object.hasOwn(actual, 'tiePolicy') && actual.tiePolicy !== (record.tiePolicy ?? 'first')) errors.push(`Derived reference ${record.id} tiePolicy differs from frozen request`);
      if (actual && Object.hasOwn(actual, 'coGoverningOperands') && !equal(actual.coGoverningOperands, coGoverningOperands)) errors.push(`Derived reference ${record.id} coGoverningOperands differs from ordered tolerance co-set`);
      if (governing !== undefined && actual && Object.hasOwn(actual, 'governingLeafOperands') && !equal(actual.governingLeafOperands, leaves.map(leaf => leaf.id))) errors.push(`Derived reference ${record.id} governingLeafOperands mismatch`);
      if (governing !== undefined && actual && Object.hasOwn(actual, 'governingSelections') && !equal(actual.governingSelections, selections)) errors.push(`Derived reference ${record.id} governingSelections mismatch`);
      computed.set(record.id, result); visiting.delete(record.id); return result;
    }
    for (const d of array(wanted.derived)) compute(d);
  }
  if (actual.size !== array(requests?.states).length) errors.push('Independent reference has extra states');
}

function authoredFiles(caseDir, contract) {
  return [...new Set(['contract.json', 'prompt.txt', 'reference-requests.json', ...array(contract.attachments), ...array(contract.modelStates)])].sort((a, b) => Buffer.compare(Buffer.from(a), Buffer.from(b))).map(file => ({ path: file, sha256: sha256(fs.readFileSync(resolveCaseFile(caseDir, file))) }));
}

// Shared root provenance decision: compact UTF-8 JSON, keys in this order,
// paths sorted by UTF-8 bytes, with reference/native outputs excluded.
function sourceHash(caseDir, contract) {
  return sha256(Buffer.from(JSON.stringify({ schemaVersion: 1, files: authoredFiles(caseDir, contract) }), 'utf8'));
}

// Acceptance is an explicit independent review artifact, not a mutable contract
// label or a solver success flag. File digests bind the review to these inputs.
function validateAcceptance(caseDir, contract, requests, reference, errors) {
  const bindingErrors = [], reviewErrors = [], nativeErrors = [];
  const attempt = (fn, target) => { try { return fn(); } catch (e) { target.push(e.message); } };
  const acceptance = attempt(() => readJson(resolveCaseFile(caseDir, 'acceptance.json')), bindingErrors);
  if (!acceptance) { errors.push(...bindingErrors); return { inputReviewed: false, nativeVerified: false }; }
  if (acceptance.schemaVersion !== 1) bindingErrors.push('Acceptance schemaVersion must be 1');
  const digest = attempt(() => sourceHash(caseDir, contract), bindingErrors);
  if (acceptance.sourceHash !== digest) bindingErrors.push('Acceptance authored file hashes/sourceHash are stale');
  const refHash = attempt(() => sha256(fs.readFileSync(resolveCaseFile(caseDir, 'independent-reference.json'))), nativeErrors);
  if (acceptance.independentReferenceSha256 !== refHash) nativeErrors.push('Acceptance independent reference hash is stale');
  const review = acceptance.inputBlindReview, truth = acceptance.sameEngineTruth;
  if (review?.status !== 'passed' || !nonempty(review.reviewer)) reviewErrors.push('Independent input blind review is pending');
  if (truth?.status !== 'verified' || truth.engine !== contract.plannedEngine || truth.independentlyReviewed !== true || !nonempty(truth.reviewer)) nativeErrors.push('Same-engine independently reviewed native truth is pending');
  if (reference?.notCommercialScoringTruth === true && contract.plannedEngine !== 'OpenSees') nativeErrors.push('Commercial diagnostic reference is not same-engine scoring truth');
  const verifyFile = descriptor => {
    if (!descriptor || !/^[a-f0-9]{64}$/.test(descriptor.sha256)) throw new Error('Evidence requires path and SHA-256');
    const file = resolveCaseFile(caseDir, descriptor.path);
    if (sha256(fs.readFileSync(file)) !== descriptor.sha256) throw new Error(`Evidence hash mismatch: ${descriptor.path}`);
    return file;
  };
  if (['PKPM', 'YJK'].includes(contract.plannedEngine)) attempt(() => {
    if (reference?.referenceKind !== `native-${contract.plannedEngine.toLowerCase()}` ||
        reference.notCommercialScoringTruth !== false || reference.sameEngineTruthStatus !== 'verified')
      throw new Error('Commercial scoring reference requires qualified same-engine native values');
    if (!equal(reference.independentReview, truth?.evidence)) throw new Error('Commercial native review descriptor mismatch');
    const nativeReview = readJson(verifyFile(truth?.evidence));
    const candidate = readJson(verifyFile(reference.candidateArtifact));
    const scoring = document => array(document.states).map(state => ({state:state.state,model:state.model,
      quantities:array(state.quantities).map(quantity => { const {nativeStatus, ...scored} = quantity; return scored; }),
      derived:array(state.derived)}));
    if (candidate.id !== contract.id || candidate.sourceHash !== digest ||
        candidate.referenceKind !== `native-${contract.plannedEngine.toLowerCase()}-candidate` ||
        !equal(candidate.analysisConvention, reference.analysisConvention) || !equal(scoring(candidate), scoring(reference)))
      throw new Error('Commercial scoring values differ from the independently reviewed candidate');
    const installedArtifacts = [];
    const mapArtifacts = value => {
      if (Array.isArray(value)) return value.map(mapArtifacts);
      if (!value || typeof value !== 'object') throw new Error('Invalid native artifact container');
      if (Object.hasOwn(value, 'path')) {
        const artifact = {...value,path:`native-commercial/evidence/${value.path}`};
        installedArtifacts.push(artifact); return artifact;
      }
      return Object.fromEntries(Object.entries(value).map(([id,child]) => [id,mapArtifacts(child)]));
    };
    const expectedArtifacts = mapArtifacts(candidate.nativeArtifacts || {});
    const expectedStateArtifacts = array(candidate.states).map(state => mapArtifacts(state.evidenceArtifacts || []));
    if (!installedArtifacts.length || !equal(reference.nativeArtifacts || {}, expectedArtifacts) ||
        !equal(array(reference.states).map(state => state.evidenceArtifacts || []), expectedStateArtifacts))
      throw new Error('Commercial native artifacts differ from the reviewed candidate bindings');
    for (const artifact of installedArtifacts) verifyFile(artifact);
    const certificates=new Map();
    for(const state of array(reference.states))for(const quantity of array(state.quantities)){
      if(quantity.engineeringPrecision===undefined)continue;
      if(contract.plannedEngine!=='PKPM'||array(state.derived).length)
        throw new Error('Certified recovery precision requires PKPM without derived propagation');
      referenceAllowance(quantity);
      const modelFile=resolveCaseFile(caseDir,contract.modelStates[state.state-1]);
      validatePrecisionScope(quantity,readJson(modelFile));
      if(quantity.rawTrace.nativeRun!==state.nativeRun||quantity.rawTrace.sourceModelSha256!==sha256(fs.readFileSync(modelFile)))
        throw new Error('Certified recovery precision native trace differs from its state or model');
      const {certificateSha256,...precision}=quantity.engineeringPrecision;
      const descriptor=installedArtifacts.find(artifact=>artifact.sha256===certificateSha256);
      if(!descriptor)throw new Error('Certified precision evidence is not retained in native artifacts');
      if(!certificates.has(certificateSha256))certificates.set(certificateSha256,readJson(verifyFile(descriptor)));
      const certificate=certificates.get(certificateSha256);
      const records=array(certificate.quantities).filter(row=>row.state===state.state&&row.id===quantity.id&&equal(row.selection,quantity.selection));
      if(certificate.schemaVersion!==1||certificate.engine!=='PKPM'||certificate.caseId!==contract.id||
        certificate.sourceHash!==digest||records.length!==1||!equal(records[0].precision,precision)||
        records[0].recovery?.nativeRun!==state.nativeRun||
        !['selection','location','component','unit'].every(key=>equal(records[0][key],quantity[key])))
        throw new Error('Certified precision differs from its source, selector or canonical recovery proof');
    }
    const rows = array(nativeReview.cases).filter(row => row.id === contract.id);
    if (nativeReview.schemaVersion !== 1 || nativeReview.reviewer !== truth.reviewer || rows.length !== 1 ||
        rows[0].status !== 'qualified' || rows[0].sourceHash !== digest ||
        rows[0].candidateSha256 !== reference.candidateArtifact.sha256)
      throw new Error('Commercial native qualification does not bind this source and candidate');
  }, nativeErrors);
  attempt(() => verifyFile(review?.evidence), reviewErrors);
  for (const state of array(requests?.states)) {
    const selections = new Map(array(state.quantities).map(q => [JSON.stringify(q.selection), q.selection]));
    if (!selections.size) nativeErrors.push(`Native evidence has no requested selections for state ${state.state}`);
    for (const selection of selections.values()) {
      const receipt = array(truth?.receipts).find(r => r.state === state.state && equal(r.selection, selection));
      if (!receipt) { nativeErrors.push(`Missing native receipt state${state.state}:${selection.kind}:${selection.id}`); continue; }
      attempt(() => {
        const body = readJson(verifyFile(receipt));
        const modelSha256 = sha256(fs.readFileSync(resolveCaseFile(caseDir, state.model)));
        if (body.engine !== contract.plannedEngine || body.modelSha256 !== modelSha256 || !equal(body.selection, selection) || body.state !== state.state || body.status !== 'succeeded' || !nonempty(body.runId) || !nonempty(body.engineVersion)) throw new Error('Native receipt does not bind successful engine/model/state/selection/version/run');
        if (!array(body.artifacts).length) throw new Error('Native receipt requires raw artifact hashes');
        for (const artifact of body.artifacts) verifyFile(artifact);
      }, nativeErrors);
    }
  }
  errors.push(...bindingErrors, ...reviewErrors, ...nativeErrors);
  return { inputReviewed: !bindingErrors.length && !reviewErrors.length, nativeVerified: !bindingErrors.length && !nativeErrors.length };
}

function validateResearchCase({ root = ROOT, caseDir, planCase, stage = 'authored' } = {}) {
  if (!STAGES.includes(stage)) throw new Error(`Unknown validation stage: ${stage}`);
  const errors = [], warnings = [], referenceErrors = [], acceptanceErrors = [];
  const attempt = (fn, target = errors) => { try { return fn(); } catch (e) { target.push(e.message); } };
  caseDir = path.resolve(caseDir);
  const contract = attempt(() => readJson(resolveCaseFile(caseDir, 'contract.json')));
  if (!planCase) planCase = attempt(() => readJson(resolveCaseFile(root, PLAN_PATH)).cases.find(c => c.id === path.basename(caseDir)));
  if (!contract) return { id: path.basename(caseDir), valid: false, authored: false, referenceReady: false, accepted: false, errors, warnings, referenceErrors, acceptanceErrors };
  validateSchema(contract, schemas.contract, 'contract', errors);
  if (contract.id !== path.basename(caseDir)) errors.push('Case directory does not match contract.id');
  if (!planCase) errors.push('Case ID absent from source plan');
  for (const field of ['id', 'modelId', 'family', 'language', 'plannedEngine']) if (contract[field] !== planCase?.[field]) errors.push(`${field} differs from exact source plan`);
  if (!equal(contract.sourcePlan?.sourceRequirements || contract.sourcePlan, planCase?.sourceRequirements)) errors.push('sourcePlan must preserve all exact original sourceRequirements');
  if (contract.sourcePlan?.requirements && !equal(contract.sourcePlan.requirements, planCase?.requirements)) errors.push('sourcePlan requirements must preserve original IDs, ranges and semantics exactly');
  if (contract.locale !== (contract.language === '英文' ? 'en' : 'zh')) errors.push('locale must match source language');
  const prompt = attempt(() => fs.readFileSync(resolveCaseFile(caseDir, 'prompt.txt'), 'utf8'));
  if (!nonempty(prompt) || /model-state-\d+\.json|independent-reference\.json|reference-requests\.json/.test(prompt)) errors.push('Prompt is missing or leaks hidden filenames');
  if (contract.locale === 'en' && /[\u3400-\u9fff]/.test(prompt || '')) errors.push('English prompt contains Chinese text');
  const publicErrors = attempt(() => validatePublicAttachments(caseDir, contract));
  if (publicErrors) errors.push(...publicErrors);
  if (Object.hasOwn(contract, 'analysisConvention')) {
    if (!['PKPM', 'YJK'].includes(contract.plannedEngine)) errors.push('analysisConvention is restricted to commercial engines');
    const appendix = contract.analysisConvention?.publicAttachment;
    if (!nonempty(appendix) || !array(contract.attachments).includes(appendix) || !array(contract.turns?.[0]?.attachments).includes(appendix)) errors.push('analysisConvention requires its bound public first-turn appendix');
  }
  if (contract.family === 'multimodal_reverse_engineering') {
    const attachments = array(contract.attachments);
    for (const name of attachments) {
      if (name.endsWith('.svg') && !attachments.includes(name.slice(0, -4) + '.png')) errors.push(`MM image ${name} requires corresponding actual PNG`);
      if (name.endsWith('.png') && !attachments.includes(name.slice(0, -4) + '.svg')) errors.push(`MM image ${name} requires corresponding SVG`);
      if (name.endsWith('.json')) attempt(() => {
        const document = readJson(resolveCaseFile(caseDir, name));
        function geometryLeak(value) {
          if (!value || typeof value !== 'object') return false;
          if (Array.isArray(value)) return value.some(geometryLeak);
          if (Object.keys(value).some(k => /^(nodes|elements|nodeTable|memberTable|coordinates|geometry|supports|restraints)$/i.test(k))) return true;
          return Object.values(value).some(geometryLeak);
        }
        if (geometryLeak(document)) errors.push(`MM attachment ${name} provides a coordinate/connection JSON bypass`);
      });
    }
  }
  const models = array(contract.modelStates).map((name, i) => {
    if (name !== `model-state-${i + 1}.json`) errors.push('Hidden models must use sequential model-state-N.json filenames');
    const model = attempt(() => readJson(resolveCaseFile(caseDir, name)));
    attempt(() => validateModel(model, i + 1, errors)); return model;
  });
  const requests = attempt(() => readJson(resolveCaseFile(caseDir, 'reference-requests.json')));
  const maps = attempt(() => validateRequests(requests, contract, models, errors)) || new Map();
  attempt(() => validateTurns(contract, planCase, models, errors, caseDir));
  attempt(() => validateOutputsAndCoverage(contract, planCase, maps, errors));
  for (const [index] of array(contract.turns).entries()) {
    try { getResponseContract({ id: contract.id, corpus: 'research-300', caseDir, contract, referenceRequests: requests, models }, index); }
    catch (error) { errors.push(`turn ${index + 1}: ${error.message}`); }
  }
  const reference = attempt(() => readJson(resolveCaseFile(caseDir, 'independent-reference.json')), referenceErrors);
  if (reference) attempt(() => validateReference(reference, requests, referenceErrors, caseDir, contract), referenceErrors);
  const acceptanceStatus = attempt(() => validateAcceptance(caseDir, contract, requests, reference, acceptanceErrors), acceptanceErrors) || { inputReviewed: false, nativeVerified: false };
  const authored = errors.length === 0, referenceReady = authored && referenceErrors.length === 0, accepted = referenceReady && acceptanceErrors.length === 0;
  if (referenceErrors.length) warnings.push('Independent reference pending or invalid');
  if (acceptanceErrors.length) warnings.push('Input review / native acceptance pending or invalid');
  for (const messages of [errors, warnings, referenceErrors, acceptanceErrors]) for (let i = 0; i < messages.length; i++) messages[i] = messages[i].split(caseDir + path.sep).join('').split(path.resolve(root) + path.sep).join('');
  const selectedErrors = [...errors, ...(stage !== 'authored' ? referenceErrors : []), ...(stage === 'accepted' ? acceptanceErrors : [])];
  return { id: contract.id, valid: selectedErrors.length === 0, authored, referenceReady, accepted, ...acceptanceStatus, agentStatus: contract.llmEndToEnd, errors: selectedErrors, authoredErrors: errors, warnings, referenceErrors, acceptanceErrors };
}

function validateResearchCorpus({ root = ROOT, caseId, stage = 'authored', allowPartial = false } = {}) {
  root = path.resolve(root);
  if (!STAGES.includes(stage)) throw new Error(`Unknown validation stage: ${stage}`);
  const errors = [], warnings = [], cases = [];
  let plan, base;
  try {
    const file = resolveCaseFile(root, PLAN_PATH), bytes = fs.readFileSync(file);
    if (sha256(bytes) !== PLAN_SHA256) errors.push('Source capability plan hash differs from approved original');
    plan = JSON.parse(bytes); errors.push(...validateSourcePlan(plan).errors);
    base = resolveCaseFile(root, 'corpora/research-300/cases', { directory: true });
  } catch (e) { errors.push(e.message); }
  if (base && plan) {
    const all = fs.readdirSync(base).sort();
    if (!caseId && !allowPartial && !equal(all, plan.cases.map(c => c.id).sort())) errors.push('Corpus must contain exactly all300 planned case directories');
    if (caseId && !all.includes(caseId)) errors.push(`Missing requested case ${caseId}`);
    for (const id of caseId ? all.filter(id => id === caseId) : all) {
      try {
        if (!CASE_ID.test(id)) throw new Error(`Invalid case directory ${id}`);
        const caseDir = resolveCaseFile(base, id, { directory: true });
        const result = validateResearchCase({ root, caseDir, planCase: plan.cases.find(c => c.id === id), stage });
        cases.push(result); errors.push(...result.errors.map(e => `${id}: ${e}`));
      } catch (e) { errors.push(`${id}: ${e.message}`); }
    }
  }
  if (allowPartial || caseId) warnings.push('Partial validation does not establish all300 completeness');
  for (let i = 0; i < errors.length; i++) errors[i] = errors[i].split(root + path.sep).join('');
  const summary = { planned: 300, discovered: cases.length, authored: cases.filter(c => c.authored).length, referenceReady: cases.filter(c => c.referenceReady).length, accepted: cases.filter(c => c.accepted).length, inputReviewed: cases.filter(c => c.inputReviewed).length, nativeVerified: cases.filter(c => c.nativeVerified).length, agentNotRun: cases.filter(c => c.agentStatus === 'not-run').length };
  return { valid: errors.length === 0, stage, errors, warnings, cases, summary };
}

module.exports = { validateSchema, validateSourcePlan, validateResearchCase, validateResearchCorpus, validateRequests, validateReference, authoredFiles, sourceHash, PLAN_PATH, PLAN_SHA256, STAGES, schemas };
