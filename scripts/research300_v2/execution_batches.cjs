'use strict';
// Select whole completed cases. Never combine turns from different attempts.
const fs = require('node:fs'), path = require('node:path'), crypto = require('node:crypto');
const read = file => JSON.parse(fs.readFileSync(file, 'utf8'));
const sha = file => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
const fail = message => { throw Error(message); };

function executionRecord(work, manifestHash) {
  const completion = path.join(work, 'execution-summary.json');
  if (fs.existsSync(completion)) {
    const summary = read(completion);
    if (summary.manifestSha256 !== manifestHash || summary.allSucceeded === false)
      fail('Invalid completed execution summary: ' + work);
    return {summary, file: 'execution-summary.json', sha256: sha(completion)};
  }
  const folder = path.join(work, 'execution-attempts');
  const candidates = fs.existsSync(folder) ? fs.readdirSync(folder).filter(name => name.endsWith('.json')).map(name => {
    const file = path.join(folder, name), summary = read(file);
    if (summary.manifestSha256 !== manifestHash || typeof summary.finishedAt !== 'string' || !Number.isFinite(Date.parse(summary.finishedAt)))
      fail('Attempt manifest/time binding differs: ' + file);
    return {summary, file: 'execution-attempts/' + name, sha256: sha(file)};
  }) : [];
  candidates.sort((a, b) => a.summary.finishedAt.localeCompare(b.summary.finishedAt) || a.file.localeCompare(b.file));
  if (!candidates.length) fail('No closed execution attempt is available: ' + work);
  if (candidates.length > 1 && candidates.at(-1).summary.finishedAt === candidates.at(-2).summary.finishedAt)
    fail('Latest closed execution attempt is ambiguous: ' + work);
  const plans = candidates.map(row => JSON.stringify([...(row.summary.caseIds
    || new Set(row.summary.turns.map(turn => turn.caseId)))].sort()));
  if (new Set(plans).size !== 1) fail('Closed attempts have different execution plans: ' + work);
  return candidates.at(-1);
}

function resolveBatches(edition, manifest, works, selectedIds = manifest.cases.map(c => c.id)) {
  const hash = sha(path.join(edition, 'manifest.json'));
  const known = new Map(manifest.cases.map(item => [item.id, item]));
  if (new Set(works).size !== works.length) fail('Repeated work directory');
  const batches = [], providers = new Map(), attempts = new Map();
  for (let index = 0; index < works.length; index++) {
    const work = works[index], record = executionRecord(work, hash), summary = record.summary;
    if (summary.candidateCalls !== 0 || !Array.isArray(summary.turns)) fail('Invalid maintainer execution summary: ' + work);
    const ids = summary.caseIds || [...new Set(summary.turns.map(row => row.caseId))];
    if (!Array.isArray(ids) || new Set(ids).size !== ids.length || ids.some(id => !known.has(id)))
      fail('Unknown/duplicate case in execution batch: ' + work);
    const runtimeFile = path.join(work, 'runtime-binding.json');
    if (fs.existsSync(runtimeFile)) {
      const runtime = read(runtimeFile);
      if (runtime.manifestSha256 !== hash || runtime.sutCommit !== manifest.sutCommit
          || runtime.plan.length !== ids.length || new Set(runtime.plan.map(row => row.caseId)).size !== ids.length
          || runtime.plan.some(row => !ids.includes(row.caseId)
            || known.get(row.caseId)?.engine !== row.engine)) fail('Runtime edition/plan binding differs: ' + work);
    }
    const rows = new Map();
    for (const row of summary.turns) {
      const key = row.caseId + '/' + row.turnId;
      if (!ids.includes(row.caseId) || !known.get(row.caseId).turns.some(turn => turn.id === row.turnId) || rows.has(key))
        fail('Unknown/duplicate turn in execution summary: ' + work);
      if (typeof row.executionPrepared !== 'boolean') fail('Execution summary has a nonterminal turn: ' + work);
      rows.set(key, row);
    }
    const batch = {batch: index + 1, summaryFile: record.file, summarySha256: record.sha256,
      allSucceeded: summary.allSucceeded !== false, caseIds: ids, completeCaseIds: [], incompleteCases: [],
      recordedNativeJobs: summary.nativeJobs};
    for (const cid of ids) {
      const completeTurns = [], incompleteTurns = [];
      for (const turn of known.get(cid).turns) {
        const row = rows.get(cid + '/' + turn.id), file = path.join(work, 'runs', cid, turn.id, 'capture.json');
        if (!row) fail('Closed execution summary omits a planned turn: ' + work);
        let capture;
        if (fs.existsSync(file)) {
          capture = read(file);
          if (capture.caseId !== cid || capture.turnId !== turn.id || capture.manifestSha256 !== hash
              || capture.maintainerOracle !== true || capture.candidateCall !== false
              || !Array.isArray(capture.jobIds) || !Array.isArray(capture.currentJobIds))
            fail('Capture identity/role binding differs: ' + file);
        }
        const closed = row.executionPrepared === true;
        (closed && capture ? completeTurns : incompleteTurns).push(turn.id);
      }
      if (!attempts.has(cid)) attempts.set(cid, []);
      attempts.get(cid).push(index + 1);
      if (!incompleteTurns.length) {
        if (providers.has(cid)) fail('Case has duplicate complete execution batches: ' + cid);
        providers.set(cid, index + 1);
        batch.completeCaseIds.push(cid);
      } else batch.incompleteCases.push({caseId: cid, completedTurns: completeTurns, incompleteTurns});
    }
    if (batch.allSucceeded && batch.incompleteCases.length)
      fail('A completed execution marker has incomplete case evidence: ' + work);
    batches.push(batch);
  }
  const selected = manifest.cases.filter(item => selectedIds.includes(item.id));
  if (selected.length !== new Set(selectedIds).size) fail('Unknown selected case');
  for (const item of selected) if (!providers.has(item.id)) fail('No complete execution batch recovered case: ' + item.id);
  const caseBatches = Object.fromEntries(selected.map(item => [item.id, providers.get(item.id)]));
  const recoveredCases = selected.filter(item => attempts.get(item.id).length > 1).map(item => ({
    caseId: item.id, completedBatch: providers.get(item.id),
    incompleteBatches: attempts.get(item.id).filter(index => index !== providers.get(item.id))}));
  const unfinishedAttempts = batches.filter(batch => batch.incompleteCases.length).map(batch => ({
    batch: batch.batch, summaryFile: batch.summaryFile, summarySha256: batch.summarySha256,
    incompleteCases: batch.incompleteCases}));
  return {manifestSha256: hash, caseBatches, executionBatches: batches, recoveredCases, unfinishedAttempts};
}

if (require.main === module) {
  const args = {};
  for (let i = 2; i < process.argv.length; i += 2) args[process.argv[i].replace(/^--/, '')] = process.argv[i + 1];
  const edition = path.resolve(args.edition), manifest = read(path.join(edition, 'manifest.json'));
  console.log(JSON.stringify(resolveBatches(edition, manifest, args.work.split(',').map(value => path.resolve(value)))));
}
module.exports = {executionRecord, resolveBatches};
