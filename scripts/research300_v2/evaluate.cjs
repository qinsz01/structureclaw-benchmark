'use strict';
// New edition policy wraps the frozen, numerically qualified pilot evaluator.
const fs = require('node:fs');
const path = require('node:path');
const pilot = require('../pilot30/evaluate.cjs');
const {readQuantity, UNITS} = require('../../lib/requested-quantities.cjs');
const {selectAnalysisResult, selectionKey} = require('../../lib/result-selection.cjs');
const {readNativeStation, axes, samePosition} = require('../../lib/commercial-stations.cjs');
const {axesFor} = require('../../lib/physical-model-fidelity.cjs');
const pointer = value => typeof value === 'string' && value.startsWith('/')
  && value.length > 1 && !/~(?![01])/u.test(value) && !/[\r\n\0]/u.test(value);
const prose = value => typeof value === 'string' && /[\p{L}\p{N}]/u.test(value);
const clone = value => structuredClone(value);

function readMappedStaticQuantity(job, q, mapping) {
  if (q.location.kind !== 'member' || !['N', 'V2', 'V3', 'T', 'M2', 'M3'].includes(q.component))
    return readQuantity(job.state.analysisResult, q, mapping);
  const selections = q.selection.kind === 'case' ? mapping.caseMapping : mapping.combinationMapping;
  const selected = mapping.selectionMapping?.[selectionKey(q.selection)]
    || {...q.selection, id: selections?.[q.selection.id] || q.selection.id};
  const {data, record} = selectAnalysisResult(job.state.analysisResult, selected);
  if (data.memberStations) return readQuantity(job.state.analysisResult, q, mapping);
  let id = mapping.elementMapping?.[q.location.id] || q.location.id;
  const segments = mapping.elementSegments?.[q.location.id];
  if (segments?.length) {
    const x = q.location.positionM;
    const matching = segments.filter(segment => (x >= segment.start || samePosition(x, segment.start))
      && (x <= segment.end || samePosition(x, segment.end)));
    const segment = q.location.side === 'left' ? matching[0] : matching.at(-1);
    if (!segment) throw Error('Station is outside the mapped physical member');
    id = segment.id;
  }
  const row = data.memberResponses?.find(row => row.id === id);
  if (row?.state !== 'recovered') return readQuantity(job.state.analysisResult, q, mapping);
  const element = job.state.model.elements.find(element => element.id === id);
  if (!element) throw Error('Recovered cut has no executed physical member');
  const actualAxes = axes(row.axes), modelAxes = axesFor(job.state.model, element);
  if (actualAxes.some((axis, i) => axis.some((value, j) => Math.abs(value - modelAxes[i][j]) > 1e-9)))
    throw Error('Recovered cut axes differ from the executed member convention');
  const samples = row.samples.filter(sample => ['left', 'right', 'continuous'].includes(sample.side)).map(sample => ({
    positionM: sample.x, side: sample.side, referenceFrame: 'element-local', localAxes: actualAxes,
    components: {N: sample.N, Vy: sample.V2, Vz: sample.V3, T: sample.T, My: sample.M2, Mz: sample.M3}}));
  // Reuse the audited vector/cut-face transform. It checks exact station and
  // side, handles reversed endpoints, and never interpolates plotted samples.
  const cut = readNativeStation({memberStations: {[id]: samples}, memberLengths: {[id]: row.length}},
    q.location.id, q.location.positionM, q.location.side, mapping);
  const value = cut[{N: 'N', V2: 'Vy', V3: 'Vz', T: 'T', M2: 'My', M3: 'Mz'}[q.component]];
  const publicData = {units: data.units || data.meta?.units || record.meta?.units,
    memberResponses: [{id: q.location.id, state: 'recovered',
      samples: [{x: q.location.positionM, side: q.location.side, [q.component]: value}]}]};
  return readQuantity({results: {[selectionKey(q.selection)]: {selection: q.selection, data: publicData}}}, q);
}

function staticViews(ref, jobs) {
  if (!jobs.length) throw Error('Actual jobs missing');
  // First validate every original executed model. The following disposable
  // view only relabels observed values into the public request convention;
  // no reference value is used, and broker states are never modified.
  const maps = jobs.map(job => {
    if (!job.verified || job.engine !== ref.engine || !job.state?.analysisResult)
      throw Error('Actual private static broker job required');
    if (job.state.analysisResult.meta?.engineId !== 'builtin-' + ref.engine.toLowerCase())
      throw Error('Wrong static solver');
    const result = pilot.physical(job.state.model, ref.model);
    if (!result.pass) throw Error('Physical model differs: ' + result.failures.join('; '));
    return {...result.diagnostics, model: job.state.model};
  });
  const views = jobs.map(job => ({...job, state: {...job.state, model: ref.model,
    analysisResult: {...job.state.analysisResult, results: {}}}}));
  const selections = new Map();
  for (const q of ref.requests) {
    const key = q.selection.kind + ':' + q.selection.id;
    if (!selections.has(key)) selections.set(key, []);
    selections.get(key).push(q);
  }
  for (const [key, requests] of selections) {
    let provider = -1, values, lastError;
    for (let i = 0; i < jobs.length; i++) {
      try {
        const observed = requests.map(q => readMappedStaticQuantity(jobs[i],
          {...q, unit: UNITS[q.component]}, maps[i]));
        provider = i; values = observed;
      } catch (error) { lastError = error; }
    }
    if (provider < 0) throw Error('No actual job supplies ' + key + ': ' + lastError?.message);
    const data = {units: {displacement: 'm', rotation: 'rad', force: 'kN', moment: 'kN.m'},
      displacements: {}, reactions: {}, memberResponses: []};
    for (let i = 0; i < requests.length; i++) {
      const q = requests[i], location = q.location;
      if (location.kind === 'node') {
        const rows = /^[ur]/.test(q.component) ? data.displacements : data.reactions;
        (rows[location.id] ||= {})[q.component.toLowerCase()] = values[i];
      } else {
        let member = data.memberResponses.find(row => row.id === location.id);
        if (!member) data.memberResponses.push(member = {id: location.id, state: 'recovered', samples: []});
        let sample = member.samples.find(row => row.x === location.positionM && row.side === location.side);
        if (!sample) member.samples.push(sample = {x: location.positionM, side: location.side});
        sample[q.component] = values[i];
      }
    }
    views[provider].state.analysisResult.results[key] = {selection: requests[0].selection, data};
  }
  return views;
}

function evaluationViews(ref, jobs, schemeRows = []) {
  if (['static', 'query'].includes(ref.kind)) return staticViews(ref, jobs);
  if (ref.kind !== 'scheme') return jobs;
  const normalized = new Map();
  for (const truth of ref.schemeTruth) {
    const row = schemeRows.find(row => row.id === truth.id);
    if (!Array.isArray(row?.jobIds) || !row.jobIds.length) throw Error('Scheme execution missing');
    const group = row.jobIds.map(id => jobs.find(job => job.jobId === id));
    if (group.some(job => !job)) throw Error('Untrusted scheme job');
    const requests = ref.schemeSelections.flatMap(id => ref.constraint.nodes.map(node => ({
      selection: {kind: 'combination', id}, location: {kind: 'node', id: node},
      component: ref.constraint.component, unit: 'm'})));
    const views = staticViews({...ref, model: truth.model, requests}, group);
    for (const view of views) {
      if (normalized.has(view.jobId)) throw Error('One execution cannot stand for multiple distinct schemes');
      normalized.set(view.jobId, view);
    }
  }
  return jobs.map(job => normalized.get(job.jobId) || job);
}

function validateReference(ref) {
  if (!ref || !['static', 'query', 'clarify', 'modal', 'transient', 'scheme'].includes(ref.kind))
    throw Error('Invalid reference analysis kind');
  if (ref.expectedIssuePaths !== undefined && (!Array.isArray(ref.expectedIssuePaths)
      || !ref.expectedIssuePaths.every(pointer)
      || new Set(ref.expectedIssuePaths).size !== ref.expectedIssuePaths.length))
    throw Error('Reference issue identities must be unique JSON pointer strings');
  if (ref.requireShapes && (ref.kind !== 'modal' || ref.parameters?.direction !== 'x'))
    throw Error('This edition qualifies distinct X-direction modes only');
  if (ref.kind === 'query' && ref.requireFreshExecution)
    throw Error('Query-only reference cannot also require a fresh analysis');
  return true;
}

function evaluate(ref, answer, jobs, currentJobIds = []) {
  validateReference(ref);
  let result;
  try {
    result = pilot.evaluate(ref, answer, evaluationViews(ref, jobs, answer?.schemes), currentJobIds);
    if (['static', 'query', 'scheme'].includes(ref.kind)) {
      result.diagnostics ||= {};
      delete result.diagnostics.fullInputReconstruction;
      result.diagnostics.responseIdentityPolicy = 'Each original job is physically checked and read with its own mapping before public-ID comparison.';
    }
  } catch (error) {
    result = {passed: false, metrics: [{name: 'complete_valid_evidence', pass: false, detail: error.message}]};
  }
  const add = (name, pass, detail) => result.metrics.push({name, pass: !!pass, detail});
  if (ref.derived?.length) {
    const rows = answer?.derived;
    add('required_derived_report', Array.isArray(rows) && rows.length === ref.derived.length
      && new Set(rows.map(row => row?.id)).size === rows.length
      && ref.derived.every(definition => rows.some(row => row?.id === definition.id)),
      'Every public derived definition must be explicitly reported; omission is not an optional field.');
  }
  if (ref.expectedIssuePaths !== undefined) {
    const rows = answer?.issues;
    add('identified_model_issues', Array.isArray(rows)
      && rows.length === ref.expectedIssuePaths.length
      && new Set(rows.map(row => row?.path)).size === rows.length
      && rows.every(row => pointer(row?.path) && prose(row?.reason))
      && ref.expectedIssuePaths.every(expected => rows.some(row => row?.path === expected)),
      {expectedPaths: ref.expectedIssuePaths,
       explanationPolicy: 'A nonempty multilingual explanation is required; corrected physics and actual results are checked independently.'});
  }
  if (ref.kind === 'clarify') {
    add('clarification_has_no_result_claims',
      ['jobIds', 'quantities', 'derived', 'modeShapes', 'schemes'].every(key =>
        answer?.[key] === undefined || Array.isArray(answer[key]) && answer[key].length === 0)
        && (answer?.selectedScheme === undefined || answer.selectedScheme === null),
      'An unresolved physical task must not report a completed analysis or invented results');
  } else if (ref.requireFreshExecution) {
    const current = new Set(currentJobIds);
    add('required_fresh_execution', jobs.length > 0 && jobs.every(job => current.has(job.jobId)),
        'Every reported job must have been executed on this turn when explicitly required');
  }
  result.passed = result.metrics.every(metric => metric.pass);
  return result;
}

function oracleAnswer(ref, jobs, schemeJobs = {}) {
  validateReference(ref);
  const schemeRows = Object.entries(schemeJobs).map(([id, jobIds]) => ({id, jobIds}));
  const answer = pilot.oracleAnswer(ref, evaluationViews(ref, jobs, schemeRows), schemeJobs);
  if (ref.expectedIssuePaths !== undefined)
    answer.issues = ref.expectedIssuePaths.map(field => ({path: field,
      reason: ref.issueReasons?.[field] || '修正该字段，使实际模型符合本题签发的物理资料。'}));
  return answer;
}

function loadJobs(work, caseId, ids) {
  const jobs = pilot.loadJobs(work, caseId, ids);
  for (const id of ids) {
    const receipt = JSON.parse(fs.readFileSync(path.join(work, 'solver-jobs', caseId, id, 'broker-receipt.json')));
    if (!receipt.stateSha256 || !['oracle', 'candidate'].includes(receipt.role))
      throw Error('Every v2 job requires a sealed private broker receipt');
  }
  return jobs;
}

module.exports = {...pilot, evaluate, oracleAnswer, loadJobs, validateReference};
