'use strict';
// Challenge-pilot grading. Reuses frozen physical/quantity gates and adds trusted
// broker-output binding. No candidate has access to references or trustedStates.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const {comparePhysicalModels} = require('./physical-view-v3.cjs');
const {readQuantity, compareRequestedQuantities, compareReportQuantities} = require('../../lib/requested-quantities.cjs');
const {verifyExecutionEvidence, modelFingerprint, resultFingerprint} = require('../../lib/analysis-evidence.cjs');
const {selectAnalysisResult} = require('../../lib/result-selection.cjs');
const hash = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const read = file => JSON.parse(fs.readFileSync(file, 'utf8'));
const check = (ok, message) => {if (!ok) throw new Error(message);};

function markdown(rows) {
  return rows.map(row => {
    const s = row.selection, l = row.location;
    const selection = `${s?.kind}:${s?.id}`;
    const location = l?.kind === 'node' ? l.id : `${l?.id}@${l?.positionM}:${l?.side}`;
    check(typeof row.value === 'number' && Number.isFinite(row.value), 'Finite reported values required');
    return `| ${row.id} | ${selection} | ${location} | ${row.component} | ${row.value} | ${row.unit} |`;
  }).join('\n');
}

function evaluateTurn({reference, state, answer, trustedStates = [], currentRunIds = [], requestsCreated = []}) {
  const metrics = [];
  const add = (metric, pass, detail) => metrics.push({metric, pass: !!pass, detail});
  try {
    check(answer && typeof answer === 'object', 'Current answer.json is missing');
    if (reference.kind === 'clarify') {
      add('no_execution', requestsCreated.length === 0 && !state?.analysisResult, 'Clarification must precede any solver request');
      const rows = answer.clarifications;
      const fields = Array.isArray(rows) ? rows.map(q => q.field) : [];
      add('targeted_clarification', Array.isArray(rows) && rows.length === reference.clarificationFields.length
        && new Set(fields).size === fields.length
        && reference.clarificationFields.every(f => fields.includes(f))
        && rows.every(q => typeof q.question === 'string' && /[\p{L}\p{N}]/u.test(q.question)), fields);
      add('no_invented_result', !answer.quantities || answer.quantities.length === 0, 'No numerical result before necessary information is confirmed');
      return {passed: metrics.every(m => m.pass), metrics};
    }
    check(state?.model && state.analysisResult, 'Current model/actual result state is missing');
    check(reference.requests.every(q => q.location.kind === 'node'), 'This pilot equivalence profile supports global node requests only');
    const physical = comparePhysicalModels(state.model, reference.model, {coordinate: 1e-8, property: 1e-6, load: 1e-6,
      explicitElasticProperties: true, staticTheory: 'Euler-Bernoulli'});
    add('model_matches', physical.pass, physical.failures);
    if (!physical.pass) return {passed: false, metrics};
    const mappings = {...physical.diagnostics, model: state.model};
    for (const q of reference.requests) {
      const map = q.selection.kind === 'case' ? mappings.caseMapping : mappings.combinationMapping;
      const selection = {...q.selection, id: map[q.selection.id]};
      const selected = selectAnalysisResult(state.analysisResult, selection);
      const meta = selected.record.meta || {};
      const identity = `${selection.kind}:${selection.id}`;
      if (metrics.some(m => m.metric === 'execution:' + identity)) continue;
      let bound = false;
      for (const actual of trustedStates) {
        try {
          const trusted = selectAnalysisResult(actual.analysisResult, selection);
          if (trusted.record.meta?.runId === meta.runId
              && modelFingerprint(actual.model) === modelFingerprint(state.model)
              && resultFingerprint(trusted.data) === resultFingerprint(selected.data)
              && resultFingerprint(trusted.record.meta) === resultFingerprint(meta)) bound = true;
        } catch { /* Another legitimate selection/run. */ }
      }
      const execution = verifyExecutionEvidence(state, selection);
      const fresh = reference.kind === 'query' || currentRunIds.includes(meta.runId);
      add('execution:' + identity, bound && execution.pass && fresh
        && meta.engineId === 'builtin-opensees', {bound, fresh, failures: execution.failures});
    }
    if (reference.kind === 'query') add('query_reuses_execution', requestsCreated.length === 0, 'An unchanged query must not launch a new solve');
    const quantities = compareRequestedQuantities(state.analysisResult, reference.requests, mappings);
    add('requested_quantities', quantities.pass, quantities.failures);
    check(Array.isArray(answer.quantities), 'Current answer quantities are missing');
    const ids = answer.quantities.map(q => q.id);
    check(ids.length === reference.requests.length && new Set(ids).size === ids.length
      && reference.requests.every(q => ids.includes(q.id)), 'Reported request coverage differs');
    const reported = compareReportQuantities({markdown: markdown(answer.quantities)}, reference.requests,
      {equivalentUnitIds: reference.requests.map(q => q.id)});
    add('reported_quantities', reported.pass, reported.failures);
    add('no_unrequested_clarification', !answer.clarifications?.length, 'Fully determined tasks should proceed');
  } catch (error) {
    add('complete_evidence', false, error.message);
  }
  return {passed: metrics.every(m => m.pass), metrics};
}

function oracleAnswer(reference, state) {
  const physical = comparePhysicalModels(state.model, reference.model, {coordinate: 1e-8, property: 1e-6, load: 1e-6,
    explicitElasticProperties: true, staticTheory: 'Euler-Bernoulli'});
  check(physical.pass, 'Oracle native model differs from the authored model: ' + physical.failures.join('; '));
  return {quantities: reference.requests.map(q => ({...q,
    value: readQuantity(state.analysisResult, q, {...physical.diagnostics, model: state.model})}))};
}

function verifyEdition(root) {
  const manifest = read(path.join(root, 'manifest.json'));
  check(manifest.edition === 'challenge-6-v1' && manifest.cases.length === 6, 'Unexpected challenge edition');
  const seen = new Set();
  for (const row of manifest.files) {
    check(!seen.has(row.path) && !path.isAbsolute(row.path) && !row.path.split('/').includes('..'), 'Unsafe/duplicate source path');
    seen.add(row.path);
    const bytes = fs.readFileSync(path.join(root, row.path));
    check(bytes.length === row.bytes && hash(bytes) === row.sha256, 'Edition input changed: ' + row.path);
  }
  return manifest;
}

function main(argv) {
  const args = {};
  for (let i = 0; i < argv.length; i += 2) {
    check(['--edition', '--run', '--case', '--turn', '--output'].includes(argv[i]) && argv[i+1], 'Invalid argument');
    args[argv[i].slice(2)] = argv[i+1];
  }
  const root = path.resolve(args.edition), run = path.resolve(args.run), manifest = verifyEdition(root);
  const item = manifest.cases.find(c => c.id === args.case), turn = item?.turns.find(t => t.id === args.turn);
  check(turn, 'Unknown challenge case/turn');
  const folder = path.join(run, 'runs', item.id, turn.id), capture = read(path.join(folder, 'capture.json'));
  check(capture.manifestSha256 === hash(fs.readFileSync(path.join(root, 'manifest.json'))), 'Capture source edition differs');
  const trustedStates = [];
  for (const id of capture.allJobIds) {
    check(/^[a-f0-9]{32}$/.test(id), 'Unsafe job identity');
    const job = path.join(run, 'solver-jobs', item.id, id);
    if (!fs.existsSync(path.join(job, 'state.json'))) continue;
    const receipt = read(path.join(job, 'broker-receipt.json'));
    check(receipt.ok && receipt.caseId === item.id && receipt.engine === 'OpenSees', 'Unsuccessful native execution');
    trustedStates.push(read(path.join(job, 'state.json')));
  }
  const state = fs.existsSync(path.join(folder, 'state.json')) ? read(path.join(folder, 'state.json')) : null;
  const answer = fs.existsSync(path.join(folder, 'answer.json')) ? read(path.join(folder, 'answer.json')) : null;
  const currentRunIds = trustedStates.map(s => s.analysisResult.runId).filter(id => capture.currentRunIds.includes(id));
  const result = {evaluatorVersion: 'challenge-v3-physical-equivalence', caseId: item.id, turnId: turn.id, manifestSha256: capture.manifestSha256,
    ...evaluateTurn({reference: read(path.join(root, turn.private)), state, answer,
      trustedStates, currentRunIds, requestsCreated: capture.requestsCreated})};
  if (args.output) fs.writeFileSync(args.output, JSON.stringify(result, null, 2) + '\n', {flag: 'wx'});
  else process.stdout.write(JSON.stringify(result, null, 2) + '\n');
  return result.passed ? 0 : 1;
}

module.exports = {evaluateTurn, oracleAnswer, verifyEdition};
if (require.main === module) {
  try {process.exitCode = main(process.argv.slice(2));}
  catch (error) {process.stderr.write(error.stack + '\n'); process.exitCode = 2;}
}
