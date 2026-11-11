'use strict';
const fs = require('node:fs');
const path = require('node:path');
const {evaluateTurn, oracleAnswer} = require('./evaluate.cjs');
const read = p => JSON.parse(fs.readFileSync(p));
const reference = read(process.argv[2]), folder = process.argv[3];
const state = fs.existsSync(path.join(folder, 'state.json')) ? read(path.join(folder, 'state.json')) : null;
const trustedStates = state ? read(path.join(folder, 'trusted.json')) : [];
const answer = state ? oracleAnswer(reference, state) : read(path.join(folder, 'answer.json'));
const base = {reference, state, answer, trustedStates,
  currentRunIds: reference.kind === 'query' ? [] : trustedStates.map(s => s.analysisResult.runId),
  requestsCreated: reference.kind === 'analyze' ? trustedStates.map((_, i) => String(i)) : []};
const evaluated = evaluateTurn(base), controls = [];
const reject = (name, input) => controls.push({name, passed: !evaluateTurn(input).passed});
if (reference.kind === 'clarify') {
  reject('analysis-before-clarification', {...base, requestsCreated: ['request']});
  reject('untargeted-question', {...base, answer: {clarifications: [{field: 'unknown', question: 'Please clarify everything'}]}});
  reject('invented-numerical-result', {...base, answer: {...answer, quantities: [{value: 1}]}});
} else {
  const mutate = change => {const altered = structuredClone(base); change(altered); return altered;};
  reject('reference-values-without-real-execution', {...base, trustedStates: []});
  reject('wrong-section', mutate(x => x.state.model.sections[0].properties.Iy *= 1.1));
  reject('wrong-global-load', mutate(x => x.state.model.load_cases[0].loads[0].wz *= -1));
  reject('wrong-report-sign', mutate(x => {const q = x.answer.quantities.find(q => Math.abs(q.value) > 1e-4); q.value *= -1;}));
  reject('duplicate-report-row', mutate(x => x.answer.quantities.push(x.answer.quantities[0])));
  reject('tampered-solver-results', mutate(x => {
    const result = Object.values(x.state.analysisResult.results)[0];
    const node = Object.keys(result.data.displacements)[0]; result.data.displacements[node].ux += .01;
  }));
  if (reference.kind === 'analyze') reject('stale-execution', {...base, currentRunIds: []});
  if (reference.kind === 'query') reject('query-starts-new-solver', {...base, requestsCreated: ['new-request']});
}
fs.writeFileSync(path.join(folder, 'oracle-evaluation.json'), JSON.stringify({role: 'maintainer-control-not-Codex', evaluated, controls}, null, 2) + '\n', {flag: 'wx'});
process.stdout.write(JSON.stringify({passed: evaluated.passed, negativeControls: controls.length,
  negativeControlsPassed: controls.every(c => c.passed), ...(evaluated.passed ? {} : {metrics: evaluated.metrics})}) + '\n');
