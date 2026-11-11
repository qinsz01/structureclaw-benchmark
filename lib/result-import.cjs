'use strict';

const fs = require('node:fs');
const path = require('node:path');
const zlib = require('node:zlib');
const { createHash } = require('node:crypto');
const { isDeepStrictEqual } = require('node:util');
const provider = require('./corpus-provider.cjs');
const { modelFingerprint } = require('./analysis-evidence.cjs');
const { buildSourceBinding } = require('../scripts/run-research300.cjs');
const { extractCodex } = require('./import-codex.cjs');
const { extractStructureClaw, reconstructOpenSeesArtifacts } = require('./import-structureclaw.cjs');

const ROOT = path.resolve(__dirname, '..');
const digest = bytes => createHash('sha256').update(bytes).digest('hex');
const clone = value => structuredClone(value);
const own = (value, key) => value !== null && typeof value === 'object' && Object.hasOwn(value, key);
const within = (parent, file) => file === parent || file.startsWith(parent + path.sep);
const jsonBytes = value => Buffer.from(JSON.stringify(value, null, 2) + '\n');
function fail(message) { throw Object.assign(new Error(message), { code: 'import_invalid' }); }

function noSymlinks(file) {
  let current = path.parse(path.resolve(file)).root;
  for (const part of path.resolve(file).slice(current.length).split(path.sep).filter(Boolean)) {
    current = path.join(current, part);
    const stat = fs.lstatSync(current, { throwIfNoEntry: false });
    if (!stat) break;
    if (stat.isSymbolicLink()) fail('Symlink input/output paths are forbidden');
  }
}
function readFile(file) {
  noSymlinks(file);
  if (!fs.statSync(file).isFile()) fail('Expected a regular input file');
  return fs.readFileSync(file);
}
function readInput(file) {
  const bytes = readFile(file);
  return { text: (file.endsWith('.gz') ? zlib.gunzipSync(bytes) : bytes).toString('utf8'), sha256: digest(bytes), bytes: bytes.length };
}
function sourceIdentity(file, role, bytes = readFile(file)) {
  return { role, path: path.resolve(file), sha256: digest(bytes), bytes: bytes.length };
}
function protectOutput(file, root = ROOT) {
  noSymlinks(file);
  for (const base of new Set([ROOT, root])) {
    for (const name of ['corpora', 'planning', 'lib', 'scripts', 'schemas', 'docs', 'viewer', 'scenarios', 'external', '.git']) {
      if (within(path.resolve(base, name), path.resolve(file))) fail('Output must be outside benchmark source directories');
    }
  }
  for (let dir = path.dirname(path.resolve(file)); ; dir = path.dirname(dir)) {
    if (fs.existsSync(path.join(dir, 'backend', 'package.json'))) fail('Output must be outside a StructureClaw source checkout');
    if (dir === path.dirname(dir)) break;
  }
  if (fs.existsSync(file)) fail('Output already exists; choose a new destination');
}
function putBytes(root, bytes, extension = '.json') {
  const relative = `files/${digest(bytes)}${extension}`;
  const file = path.join(root, relative);
  fs.mkdirSync(path.dirname(file), { recursive: true });
  if (!fs.existsSync(file)) fs.writeFileSync(file, bytes, { flag: 'wx' });
  else if (!fs.readFileSync(file).equals(bytes)) fail('Evidence hash collision');
  return relative;
}
function copyRelative(sourceRoot, relative, outputRoot, sources = [], role = 'artifact') {
  if (typeof relative !== 'string' || !relative || /[\\:\x00-\x1f]/.test(relative)
      || path.isAbsolute(relative) || relative.split('/').some(part => !part || part === '.' || part === '..')) fail('Unsafe evidence path');
  const file = path.resolve(sourceRoot, relative);
  if (!within(sourceRoot, file)) fail('Evidence is outside its root');
  const bytes = readFile(file), copiedTo = putBytes(outputRoot, bytes, path.extname(file) || '.bin');
  sources.push({ ...sourceIdentity(file, role, bytes), copiedTo });
  return copiedTo;
}
function copyMapping(value, sourceRoot, outputRoot, sources) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) fail('Artifact mapping must be an object');
  return Object.fromEntries(Object.entries(value).map(([key, item]) => [key,
    typeof item === 'string' ? copyRelative(sourceRoot, item, outputRoot, sources) : copyMapping(item, sourceRoot, outputRoot, sources)]));
}
function detectFormat(text) {
  let value; try { value = JSON.parse(text); } catch { /* Stream or text. */ }
  if (value?.corpus === 'research-300' && Array.isArray(value.runs)) return 'capture';
  const nativeEvent = item => item && (item.type === 'artifact_payload_sync'
    || item.type === 'summary_replace' && typeof item.summaryText === 'string'
    || item.type === 'result' && item.content && typeof item.content === 'object');
  const events = Array.isArray(value) ? value : value ? [value] : text.split(/\r?\n/).filter(line => line.trim()).map(line => {
    try { return JSON.parse(line); } catch { return null; }
  });
  if (events.some(nativeEvent)) return 'structureclaw';
  if (/^data:/m.test(text) || value?.snapshots || value?.session || value?.request || value?.modelSnapshot
      || value?.latestResult || value?.analysis || typeof value?.response === 'string') return 'structureclaw';
  return 'codex';
}
function caseContext(caseId, root = ROOT) {
  const corpus = provider.loadCorpus({ corpus: 'research-300', root });
  const record = provider.loadCase(corpus, caseId);
  const inputBinding = provider.getPublicTurnInput(record, 0).inputBinding;
  const { sourceHash } = buildSourceBinding(record);
  return { record, context: { schemaVersion: 1, corpus: 'research-300', caseId, inputBinding, sourceHash,
    turns: record.contract.turns.map(turn => ({ turnId: turn.id, state: turn.state })) } };
}

function assertIdentity(value, context, label) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return;
  for (const field of ['caseId', 'inputBinding', 'sourceHash']) {
    if (own(value, field) && !isDeepStrictEqual(value[field], context[field])) fail(`${label} explicitly declares a different ${field}`);
  }
  if (own(value, 'corpus') && value.corpus !== 'research-300') fail(`${label} explicitly declares a different corpus`);
}
function declaredIdentities(value, context, label = 'Candidate') {
  assertIdentity(value, context, label);
  if (value?.state && typeof value.state === 'object') assertIdentity(value.state, context, `${label} state`);
  if (Array.isArray(value?.turns)) value.turns.forEach((turn, index) => declaredIdentities(turn, context, `${label} turn ${index + 1}`));
}
function fillMissingContext(meta, state, sourceHash) {
  if (!own(meta, 'state')) meta.state = state;
  if (!own(meta, 'sourceHash')) meta.sourceHash = sourceHash;
}
function runSnapshot(result, entries) {
  const capture = clone(result);
  capture.results = Object.fromEntries(entries.map(({ key }) => [key, clone(result.results[key])]));
  return capture;
}
function verifyRunReuse(saved, result, entries, model) {
  if (saved.modelHash !== modelFingerprint(model)) fail('Immutable run ID was reused with a different physical model');
  for (const { key } of entries) {
    const current = result.results[key], original = saved.capture.results[key];
    if (!original) fail('Immutable run ID was reused with a new result selection');
    if (own(original.meta, 'state') && !own(current.meta, 'state')) current.meta.state = original.meta.state;
    if (own(original.meta, 'sourceHash') && !own(current.meta, 'sourceHash')) current.meta.sourceHash = original.meta.sourceHash;
    if (!isDeepStrictEqual(current, original)) fail('Immutable run ID was reused with altered results or metadata');
  }
}

/** Import without consulting numerical reference answers or inventing solver receipts. */
function importResult(options) {
  let created = false;
  try { return importInto({ ...options, created() { created = true; } }); }
  catch (error) {
    if (created) fs.rmSync(path.resolve(options.outputRoot), { recursive: true, force: true });
    throw error;
  }
}
function importInto(options) {
  const source = readInput(options.input);
  const sources = [{ role: 'input', path: path.resolve(options.input), sha256: source.sha256, bytes: source.bytes }];
  const readSidecar = (file, role) => {
    const bytes = readFile(file); sources.push(sourceIdentity(file, role, bytes));
    return JSON.parse(bytes);
  };
  const format = options.format === 'auto' || !options.format ? detectFormat(source.text) : options.format;
  const sourceRoot = path.resolve(options.artifactRoot || path.dirname(options.input));
  const outputRoot = path.resolve(options.outputRoot);
  protectOutput(outputRoot, options.root);
  let context = options.context ? readSidecar(options.context, 'context') : undefined;
  const caseId = options.caseId || context?.caseId;
  if (context && options.caseId && context.caseId !== options.caseId) fail('Context and --case disagree');
  if (format === 'capture') {
    const envelope = JSON.parse(source.text);
    if (envelope.schemaVersion !== 1 || envelope.corpus !== 'research-300' || !Array.isArray(envelope.runs) || !envelope.runs.length) fail('Invalid or empty capture envelope');
    if (options.state || options.states || options.context) fail('Capture envelopes already contain their states and input bindings');
    if (caseId && !envelope.runs.some(run => run.caseId === caseId)) fail('Capture does not contain the selected case');
    fs.mkdirSync(outputRoot); options.created();
    for (const run of envelope.runs) for (const turn of run.turns || []) {
      if (turn.artifacts) turn.artifacts = copyMapping(turn.artifacts, sourceRoot, outputRoot, sources);
      if (turn.figures) turn.figures = turn.figures.map(figure => ({ ...figure, path: copyRelative(sourceRoot, figure.path, outputRoot, sources, 'figure') }));
    }
    return finish(envelope, { adapter: 'capture', inputSha256: source.sha256, binding: 'preserved', warnings: [] });
  }
  if (!caseId) fail('Raw results require --case ID or --context capture-context.json');
  const current = caseContext(caseId, options.root);
  if (context && !isDeepStrictEqual(context, current.context)) fail('Capture context is stale or differs from current public inputs');
  context = current.context;
  let declared;
  try { declared = JSON.parse(source.text); } catch { /* Actual event/fenced answers are checked after extraction. */ }
  if (!Array.isArray(declared)) declaredIdentities(declared, context);
  const extractOptions = { caseId, runsRoot: options.runsRoot, artifactRoot: sourceRoot };
  if (options.state) extractOptions.state = readSidecar(options.state, 'state');
  if (options.states) extractOptions.states = readSidecar(options.states, 'states');
  if (options.state && options.states) fail('Use either --state or --states');
  let extracted;
  if (format === 'codex') extracted = extractCodex(source.text, extractOptions);
  else if (format === 'structureclaw') {
    if (options.state || options.states) fail('StructureClaw input must contain actual per-turn snapshots');
    extracted = extractStructureClaw(source.text, extractOptions);
  } else fail(`Unknown result format: ${format}`);
  if (extracted.turns.length > context.turns.length) fail('Result contains more turns than the selected task');
  for (const archive of extracted.source.archives || []) {
    const identity = sourceIdentity(archive.path, 'analysis-archive');
    if (identity.sha256 !== archive.sha256) fail('Analysis archive changed during import');
    sources.push({ ...identity, runId: archive.runId });
  }
  // Omitted turns remain unknown. A final snapshot is never cloned into earlier turns.
  const used = new Set();
  extracted.turns.forEach((turn, index) => {
    declaredIdentities(turn, context, `Extracted turn ${index + 1}`);
    if (extracted.source.adapter === 'codex') {
      const answer = turn.state?.messages?.at(-1)?.content;
      if (typeof answer === 'string') {
        const blocks = [...answer.matchAll(/```json\s*\n?([\s\S]*?)```/gi)];
        let object;
        try { object = JSON.parse(blocks.length === 1 ? blocks[0][1] : answer); } catch { /* Ordinary delivered prose has no structured declarations. */ }
        if (object) declaredIdentities(object, context, `Codex answer ${index + 1}`);
      }
    }
    turn.turnId ??= context.turns[index].turnId;
    if (!context.turns.some(t => t.turnId === turn.turnId) || used.has(turn.turnId)) fail('Unknown or repeated turn ID');
    used.add(turn.turnId);
  });
  fs.mkdirSync(outputRoot); options.created();
  let warnings = [...(extracted.source.warnings || [])];
  const runContexts = new Map();
  for (const turn of extracted.turns) {
    const expected = context.turns.find(t => t.turnId === turn.turnId);
    if (turn.artifacts) turn.artifacts = copyMapping(turn.artifacts, sourceRoot, outputRoot, sources);
    if (turn.figures) turn.figures = turn.figures.map(figure => ({ ...figure, path: copyRelative(sourceRoot, figure.path, outputRoot, sources, 'figure') }));
    const result = turn.state?.analysisResult;
    if (!result?.results || !turn.state.model) continue;
    const groups = new Map();
    for (const [key, entry] of Object.entries(result.results)) {
      const match = /^(case|combination):(.+)$/.exec(key), runId = entry.meta?.runId;
      if (!match || !runId) continue;
      if (!groups.has(runId)) groups.set(runId, []);
      groups.get(runId).push({ key, selection: { kind: match[1], id: match[2] } });
    }
    for (const [runId, entries] of groups) {
      let saved = runContexts.get(runId);
      // Original mappings stay unchanged. Remember them so query turns can
      // reuse their exact bytes without creating a second capture for one run.
      if (turn.artifacts?.[runId]) {
        if (saved) {
          if (!isDeepStrictEqual(saved.mapping, turn.artifacts[runId])) fail('Immutable run ID was rebound to different artifact bytes');
          verifyRunReuse(saved, result, entries, turn.state.model);
        } else runContexts.set(runId, { mapping: turn.artifacts[runId], capture: runSnapshot(result, entries),
          modelHash: modelFingerprint(turn.state.model) });
        continue;
      }
      if (!saved) {
        const nativeRun = turn.state.analysisRuns?.[runId] || result;
        const native = reconstructOpenSeesArtifacts(nativeRun, { captureRoot: options.captureRoot,
          structureclawRoot: options.structureclawRoot, pythonBin: options.python, outputRoot });
        for (const item of native.sources || []) {
          const identity = sourceIdentity(item.path, item.kind || 'native-capture');
          if (identity.sha256 !== item.sha256) fail('Native evidence source changed during import');
          sources.push(identity);
        }
        warnings.push(...native.diagnostics.map(message => `${runId}: ${message}`));
        const capture = runSnapshot(result, entries);
        for (const { key } of entries) {
          const meta = capture.results[key].meta;
          fillMissingContext(meta, expected.state, context.sourceHash);
          // Identity/model/engine/execution declarations must come from the candidate.
        }
        const selections = Object.fromEntries(entries.map(({ key }) => [key, native.selectionArtifacts[key] || {}]));
        const mapping = { capture: {
          normalizedInput: putBytes(outputRoot, jsonBytes({ model: turn.state.model, selections: entries.map(e => e.selection) })),
          solverResponse: putBytes(outputRoot, jsonBytes(capture)),
        }, selections };
        saved = { mapping, capture, modelHash: modelFingerprint(turn.state.model) };
        runContexts.set(runId, saved);
      }
      verifyRunReuse(saved, result, entries, turn.state.model);
      turn.artifacts = { ...turn.artifacts, [runId]: saved.mapping };
    }
    // Codex extraction precedes canonical recovery. Remove only its exact
    // per-turn missing-files warning once every execution selection has all
    // three original, receipt-matching files; retain all other diagnostics.
    if (extracted.source.adapter === 'codex' && groups.size && [...groups].every(([runId, entries]) => entries.every(({ key }) => {
      const files = turn.artifacts?.[runId]?.selections?.[key];
      const receipt = result.results[key].data?.execution?.artifacts;
      return ['normalizedInput', 'settings', 'solverResponse'].every(name => typeof files?.[name] === 'string'
        && digest(readFile(path.join(outputRoot, files[name]))) === receipt?.[name + 'Sha256']);
    }))) {
      const initial = `Turn ${extracted.turns.indexOf(turn) + 1}: raw execution artifacts are missing; no receipts were generated.`;
      warnings = warnings.filter(message => message !== initial);
    }
  }
  const envelope = { schemaVersion: 1, corpus: 'research-300', runs: [{ caseId, runId: `import-${source.sha256.slice(0, 24)}`,
    inputBinding: context.inputBinding, turns: extracted.turns }] };
  return finish(envelope, { ...extracted.source, warnings: [...new Set(warnings)], inputSha256: source.sha256,
    binding: options.context ? 'prepared-context' : 'operator-declared-current-input',
    benchmarkContextFields: ['state', 'sourceHash'],
    note: 'Input binding records the supplied context or operator case declaration; it does not prove that the agent received those inputs.' });

  function finish(envelope, provenance) {
    const artifactsPath = path.join(outputRoot, 'capture.json');
    fs.writeFileSync(artifactsPath, jsonBytes(envelope), { flag: 'wx' });
    const evidence = [];
    const collectPaths = value => {
      if (typeof value === 'string') {
        const bytes = readFile(path.join(outputRoot, value));
        evidence.push({ path: value, sha256: digest(bytes), bytes: bytes.length });
      } else if (value && typeof value === 'object') Object.values(value).forEach(collectPaths);
    };
    for (const run of envelope.runs) for (const turn of run.turns || []) {
      collectPaths(turn.artifacts);
      for (const figure of turn.figures || []) collectPaths(figure.path);
    }
    provenance.sources = [...new Map(sources.map(item => [`${item.role}:${item.path}`, item])).values()];
    provenance.evidence = [...new Map(evidence.map(item => [item.path, item])).values()];
    provenance.implementation = ['lib/result-import.cjs', 'lib/import-codex.cjs', 'lib/import-structureclaw.cjs',
      'lib/structureclaw-payload-binding.cjs', 'lib/analysis-evidence.cjs', 'lib/research300-evaluation.cjs',
      'scripts/evaluate-results.cjs', 'scripts/run-research300.cjs', 'scripts/research300/reconstruct_structureclaw.py',
      'scripts/research300/capture_structureclaw_worker.py'].map(file => {
      const bytes = readFile(path.join(ROOT, file)); return { path: file, sha256: digest(bytes), bytes: bytes.length };
    });
    fs.writeFileSync(path.join(outputRoot, 'import.json'), jsonBytes(provenance), { flag: 'wx' });
    const caseIds = [...new Set(envelope.runs.map(run => run.caseId))];
    return { artifactsPath, artifactRoot: outputRoot, provenance, caseIds,
      caseId: format === 'capture' ? caseId || (caseIds.length === 1 ? caseIds[0] : undefined) : context.caseId };
  }
}

function prepareEvaluation({ caseId, output, turn, root = ROOT }) {
  if (!caseId) fail('--case is required');
  const { record, context } = caseContext(caseId, root);
  const currentTurn = turn === undefined ? record.contract.turns[0]?.id : turn;
  const turnIndex = record.contract.turns.findIndex(item => item.id === currentTurn);
  if (typeof currentTurn !== 'string' || turnIndex < 0) fail('--turn must be an exact public turn ID for this case');
  const releasedTurns = record.contract.turns.slice(0, turnIndex + 1).map(item => item.id);
  output = path.resolve(output); protectOutput(output, root);
  fs.mkdirSync(output);
  try {
    const selectedProvider = { ...provider, loadCorpus(options) {
      const corpus = provider.loadCorpus(options);
      return { ...corpus, cases: corpus.cases.filter(item => item.id === caseId) };
    } };
    require('../scripts/export-research300-inputs.cjs').exportResearch300Inputs({ root, output: path.join(output, 'agent-input'),
      provider: selectedProvider, expectedCounts: { cases: 1, turns: releasedTurns.length }, throughTurn: currentTurn });
    fs.writeFileSync(path.join(output, 'capture-context.json'), jsonBytes(context), { flag: 'wx' });
    return { caseId, currentTurn, releasedTurns, output, agentInput: path.join(output, 'agent-input'), context: path.join(output, 'capture-context.json'),
      instruction: `Deliver only agent-input for ${currentTurn}; it contains released history through this turn. Keep capture-context.json and later-turn packets in the evaluation harness, outside the agent's accessible workspace.` };
  } catch (error) {
    // Only this invocation's newly created directory is owned by preparation.
    fs.rmSync(output, { recursive: true, force: true });
    throw error;
  }
}

module.exports = { importResult, prepareEvaluation, caseContext, detectFormat, protectOutput, sourceIdentity };
