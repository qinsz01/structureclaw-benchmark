'use strict';
// All positives use genuine protected broker outputs. Controls do not run solvers.
const fs = require('node:fs'), path = require('node:path'), crypto = require('node:crypto');
const {evaluate, oracleAnswer, loadJobs, physical, validateReference} = require('./evaluate.cjs');
const {closedPlanarDomain, liftPlanar} = require('../challenge/physical-view-v3.cjs');
const {resolveBatches} = require('./execution_batches.cjs');
const clone = value => structuredClone(value), read = file => JSON.parse(fs.readFileSync(file, 'utf8'));
const sha = file => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');

function renamedNodeJob(job, prefix) {
  const result = clone(job), model = result.state.model;
  const names = Object.fromEntries(model.nodes.map(node => [node.id, prefix + node.id]));
  for (const node of model.nodes) node.id = names[node.id];
  for (const element of model.elements) element.nodes = element.nodes.map(id => names[id]);
  for (const loadCase of model.load_cases) for (const load of loadCase.loads)
    if (load.node !== undefined) load.node = names[load.node] || load.node;
  function responseKeys(value) {
    if (Array.isArray(value)) { value.forEach(responseKeys); return; }
    if (!value || typeof value !== 'object') return;
    for (const [key, child] of Object.entries(value)) {
      if (['displacements', 'reactions', 'modeShape', 'nodes'].includes(key)
          && child && typeof child === 'object' && !Array.isArray(child))
        value[key] = Object.fromEntries(Object.entries(child).map(([id, row]) => [names[id] || id, row]));
      else responseKeys(child);
    }
  }
  responseKeys(result.state.analysisResult);
  responseKeys(result.state.dynamicResult);
  return result;
}

function verifyManifest(edition) {
  const manifest = read(path.join(edition, 'manifest.json'));
  for (const row of manifest.files) {
    const file = path.resolve(edition, row.path);
    if (!file.startsWith(edition + path.sep) || sha(file) !== row.sha256)
      throw Error('Edition file binding differs: ' + row.path);
  }
  return manifest;
}

function counterexamples(ref, answer, jobs, currentJobIds, schemeJobs = {}) {
  const controls = [];
  const test = (name, r, a, j, current, expected) => {
    const observed = evaluate(r, a, j, current);
    controls.push({name, scope: 'full-evaluator', expected, actual: observed.passed,
      passed: observed.passed === expected, metrics: observed.metrics});
  };
  const compare = (name, actual, expected, pass) => {
    const observed = physical(actual, expected);
    controls.push({name, scope: 'physical-comparator-only', expected: pass,
      actual: observed.pass, passed: observed.pass === pass, failures: observed.failures});
  };
  if (ref.expectedIssuePaths?.length) {
    const missing = clone(answer); missing.issues.pop();
    test('missing-model-issue', ref, missing, jobs, currentJobIds, false);
    const wrong = clone(answer); wrong.issues[0].path = '/not-an-issued-field';
    test('wrong-model-issue-path', ref, wrong, jobs, currentJobIds, false);
    const blank = clone(answer); blank.issues[0].reason = '???';
    test('empty-model-issue-explanation', ref, blank, jobs, currentJobIds, false);
    const equivalent = clone(answer); equivalent.issues[0].reason = '修正。';
    test('concise-Chinese-model-issue', ref, equivalent, jobs, currentJobIds, true);
  }
  if (ref.kind === 'clarify') {
    if (answer.clarifications.length) {
      const bad = clone(answer); bad.clarifications[0].field = 'wrong';
      test('wrong-clarification', ref, bad, jobs, [], false);
    }
    test('premature-execution', ref, answer, [{jobId: 'fake'}], ['fake'], false);
    const claim = clone(answer); claim.jobIds = ['invented-completed-job'];
    test('invented-job-on-clarification', ref, claim, jobs, [], false);
    return controls;
  }
  test('missing-execution', ref, answer, [], [], false);
  const noIds = clone(answer); delete noIds.jobIds;
  test('missing-reported-job-ids', ref, noIds, jobs, currentJobIds, false);
  if (answer.quantities?.length) {
    const noQuantities = clone(answer); delete noQuantities.quantities;
    test('missing-reported-quantities', ref, noQuantities, jobs, currentJobIds, false);
  }
  if (jobs.length > 1) {
    const renamed = jobs.map((job, index) => renamedNodeJob(job, 'JOB' + index + '__'));
    test('equivalent-per-job-node-identities', ref, answer, renamed, currentJobIds, true);
  }
  const altered = clone(jobs);
  const usedMaterial = altered[0].state.model.elements[0].material;
  altered[0].state.model.materials.find(material => material.id === usedMaterial).E *= 1.2;
  test('wrong-active-stiffness', ref, answer, altered, currentJobIds, false);
  const bad = clone(answer);
  if (bad.quantities.length) bad.quantities[0].value += Math.max(1, Math.abs(bad.quantities[0].value));
  else if (bad.schemes?.length) bad.schemes[0].maximum += Math.max(1, Math.abs(bad.schemes[0].maximum));
  test('wrong-reported-number', ref, bad, jobs, currentJobIds, false);
  const withJ = ref.model.sections.some(section => Number.isFinite(section.properties.J) && section.properties.J !== 0);
  if (ref.model.coordinate_system.dimension === '2d') {
    if (withJ) {
      const alternative = clone(ref.model);
      for (const section of alternative.sections) if (section.properties.J) section.properties.J *= 1.05;
      compare('inactive-2d-J', alternative, ref.model, true);
    }
    if (closedPlanarDomain(ref.model) && ref.model.elements.every(e => !e.releases && !e.offsets)) {
      const spatial = liftPlanar(ref.model);
      compare('canonical-restrained-spatial-embedding', spatial, ref.model, true);
      const freed = clone(spatial); freed.nodes[0].restraints[1] = false;
      compare('spatial-embedding-free-transverse-dof', freed, ref.model, false);
    }
  } else if (ref.model.elements.every(e => ['truss', 'brace'].includes(e.type))) {
    if (withJ) {
      const alternative = clone(ref.model);
      for (const section of alternative.sections) if (section.properties.J) section.properties.J *= 1.05;
      compare('inactive-truss-J', alternative, ref.model, true);
    }
    const beams = clone(ref.model); for (const element of beams.elements) element.type = 'beam';
    compare('truss-as-beams-rejected', beams, ref.model, false);
  }
  const length = answer.quantities.find(q => q.unit === 'm');
  if (length) {
    const alternative = clone(answer), q = alternative.quantities.find(q => q.id === length.id);
    q.value *= 1000; q.unit = 'mm';
    test('equivalent-mm', ref, alternative, jobs, currentJobIds, true);
  }
  if (ref.kind === 'query') test('query-new-execution', ref, answer, jobs, answer.jobIds, false);
  if (ref.requireFreshExecution) test('missing-required-fresh-execution', ref, answer, jobs, [], false);
  if (ref.model.analysis_control.self_weight && [undefined, null, '-z'].includes(ref.model.analysis_control.gravity_direction)) {
    const explicit = clone(ref.model); explicit.analysis_control.gravity_direction = '-z';
    compare('explicit-default-gravity-direction', explicit, ref.model, true);
    const wrong = clone(ref.model); wrong.analysis_control.gravity_direction = 'x';
    compare('wrong-gravity-direction', wrong, ref.model, false);
  }
  if (ref.derived?.length) {
    const omitted = clone(answer); delete omitted.derived;
    test('missing-derived-field', ref, omitted, jobs, currentJobIds, false);
    const empty = clone(answer); empty.derived = [];
    test('empty-derived-report', ref, empty, jobs, currentJobIds, false);
    const governor = clone(answer); governor.derived[0].governingOperand = 'not-an-issued-operand';
    test('wrong-derived-governor', ref, governor, jobs, currentJobIds, false);
    const wrong = clone(answer);
    wrong.derived[0].value = Math.abs(wrong.derived[0].value) > 1e-6 ? -wrong.derived[0].value : 1;
    test('wrong-derived-value-or-sign', ref, wrong, jobs, currentJobIds, false);
  }
  if (ref.requireShapes) {
    const missing = clone(answer); delete missing.modeShapes;
    test('missing-modal-shapes', ref, missing, jobs, currentJobIds, false);
    const equivalent = clone(answer);
    for (const mode of equivalent.modeShapes) for (const node in mode.values) mode.values[node] *= -3;
    test('shape-sign-and-scale', ref, equivalent, jobs, currentJobIds, true);
    const zero = clone(answer);
    for (const mode of zero.modeShapes) for (const node in mode.values) mode.values[node] = 0;
    test('zero-modal-shape', ref, zero, jobs, currentJobIds, false);
    const broken = clone(jobs);
    for (const mode of broken[0].state.dynamicResult.data.modes)
      for (const value of Object.values(mode.modeShape)) value[0] = 0;
    test('broken-native-modal-shape', ref, answer, broken, currentJobIds, false);
  }
  if (ref.requests.some(q => q.time !== undefined)) {
    const missing = clone(answer); delete missing.quantities.find(q => q.time !== undefined).time;
    test('missing-reported-peak-time', ref, missing, jobs, currentJobIds, false);
    const wrong = clone(answer); wrong.quantities.find(q => q.time !== undefined).time += .02;
    test('wrong-reported-peak-time', ref, wrong, jobs, currentJobIds, false);
    const broken = clone(jobs);
    for (const row of broken[0].state.dynamicResult.data.timeHistory) row.time += .02;
    test('wrong-native-peak-time', ref, answer, broken, currentJobIds, false);
  }
  if (ref.kind === 'scheme') {
    for (const field of ['selectedScheme', 'maximum', 'volume', 'feasible']) {
      const missing = clone(answer);
      if (field === 'selectedScheme') delete missing[field];
      else delete missing.schemes[0][field];
      test('missing-scheme-' + field, ref, missing, jobs, currentJobIds, false);
    }
    const wrong = clone(answer); wrong.selectedScheme = 'nonexistent';
    test('invalid-scheme-choice', ref, wrong, jobs, currentJobIds, false);
    if (answer.schemes.every(scheme => scheme.maximum > 0)) {
      const impossible = clone(ref); impossible.constraint.absoluteLimit = 0;
      test('explicit-no-feasible-scheme', impossible, oracleAnswer(impossible, jobs, schemeJobs), jobs, currentJobIds, true);
    }
    const omitted = clone(answer); omitted.schemes.pop();
    test('omitted-scheme', ref, omitted, jobs, currentJobIds, false);
  }
  return controls;
}

function main(argv = process.argv.slice(2)) {
  const args = {};
  for (let i = 0; i < argv.length; i += 2) {
    if (!argv[i].startsWith('--') || argv[i + 1] === undefined) throw Error('Arguments require --name value pairs');
    args[argv[i].slice(2)] = argv[i + 1];
  }
  for (const field of ['edition', 'work', 'output']) if (!args[field]) throw Error('Missing --' + field);
  const edition = path.resolve(args.edition), output = path.resolve(args.output);
  const workRoots = args.work.split(',').map(value => path.resolve(value));
  const manifest = verifyManifest(edition), hash = sha(path.join(edition, 'manifest.json'));
  const requested = args.cases ? new Set(args.cases.split(',')) : new Set(manifest.cases.map(c => c.id));
  for (const id of requested) if (!manifest.cases.some(c => c.id === id)) throw Error('Unknown case: ' + id);
  const selected = manifest.cases.filter(c => requested.has(c.id));
  const resolution = resolveBatches(edition, manifest, workRoots, [...requested]);
  const caseWork = new Map(Object.entries(resolution.caseBatches).map(([cid, index]) => [cid, workRoots[index - 1]]));
  if (fs.existsSync(output)) throw Error('New qualification output directory required');
  fs.mkdirSync(output, {recursive: true});
  const rows = [];
  for (const item of selected) for (const turn of item.turns) {
    const work = caseWork.get(item.id), folder = path.join(work, 'runs', item.id, turn.id);
    const ref = read(path.join(edition, turn.private));
    const record = {caseId: item.id, turnId: turn.id, kind: ref.kind, controls: []};
    try {
      validateReference(ref);
      const capture = read(path.join(folder, 'capture.json'));
      if (capture.manifestSha256 !== hash || capture.caseId !== item.id || capture.turnId !== turn.id
          || !capture.maintainerOracle || capture.candidateCall !== false)
        throw Error('Capture identity or role differs');
      const jobs = loadJobs(work, item.id, capture.jobIds), schemeFile = path.join(folder, 'scheme-jobs.json');
      const schemeJobs = fs.existsSync(schemeFile) ? read(schemeFile) : {};
      const answer = oracleAnswer(ref, jobs, schemeJobs);
      record.positive = evaluate(ref, answer, jobs, capture.currentJobIds);
      if (record.positive.passed)
        record.controls = counterexamples(ref, answer, jobs, capture.currentJobIds, schemeJobs);
      fs.writeFileSync(path.join(output, item.id + '-' + turn.id + '-answer.json'), JSON.stringify(answer, null, 2) + '\n');
    } catch (error) { record.error = error.stack; }
    record.passed = !!record.positive?.passed && record.controls.every(control => control.passed);
    fs.writeFileSync(path.join(output, item.id + '-' + turn.id + '.json'), JSON.stringify(record, null, 2) + '\n');
    rows.push(record);
    console.log(JSON.stringify({caseId: item.id, turnId: turn.id, passed: record.passed,
      error: record.error || record.positive?.metrics.filter(metric => !metric.pass)}));
  }
  const summary = {edition: manifest.edition, manifestSha256: hash, role: 'maintainer-oracle-and-counterexamples',
    candidateCalls: 0, fullEditionCoverage: selected.length === manifest.cases.length,
    cases: selected.length, editionCases: manifest.cases.length, turns: rows.length,
    passedTurns: rows.filter(row => row.passed).length,
    controls: rows.reduce((count, row) => count + row.controls.length, 0),
    failedControls: rows.flatMap(row => row.controls).filter(control => !control.passed).length,
    allPassed: rows.every(row => row.passed),
    executionBatches: resolution.executionBatches,
    recoveredCases: resolution.recoveredCases,
    unfinishedAttempts: resolution.unfinishedAttempts,
    rows: rows.map(({positive, controls, error, ...row}) => ({...row, error: error?.split('\n')[0]}))};
  fs.writeFileSync(path.join(output, 'summary.json'), JSON.stringify(summary, null, 2) + '\n');
  console.log(JSON.stringify({summary: {...summary, rows: undefined}}));
  return summary;
}

if (require.main === module) process.exitCode = main().allPassed ? 0 : 1;
module.exports = {verifyManifest, counterexamples, main, renamedNodeJob};
