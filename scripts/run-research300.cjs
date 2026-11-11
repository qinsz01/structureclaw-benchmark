#!/usr/bin/env node
'use strict';

const path = require('node:path');
const fs = require('node:fs');
const { createHash } = require('node:crypto');
const { modelFingerprint } = require('../lib/analysis-evidence.cjs');
const { selectAnalysisResult } = require('../lib/result-selection.cjs');
const { normalizeEngineKey } = require('../lib/engine-ground-truth.cjs');
const { activityFingerprint, figureSetFingerprint, BEHAVIOR_REVIEW_ID, CLARIFICATION_REVIEW_ID } = require('../lib/research300-evaluation.cjs');

const OFFLINE_EXECUTIONS = ['inspect', 'validate', 'evaluate-artifacts'];

class ResearchRunnerError extends Error {
  constructor(code, message, details) {
    super(message);
    this.name = 'ResearchRunnerError';
    this.code = code;
    if (details !== undefined) this.details = details;
  }
}

function parseResearchOptions(args) {
  args = args.flatMap((arg) => arg.startsWith('--') && arg.includes('=')
    ? [arg.slice(0, arg.indexOf('=')), arg.slice(arg.indexOf('=') + 1)] : [arg]);
  const options = { corpus: 'research-300', execution: 'inspect' };
  const valueFlags = {
    '--corpus': 'corpus', '--execution': 'execution', '--root': 'root',
    '--scenario': 'scenarioId', '--case': 'scenarioId', '--cases': 'caseIds', '--turn': 'turn',
    '--artifacts': 'artifactsPath', '--artifact-root': 'artifactRoot', '--output': 'outputPath',
    '--assessments': 'assessmentsPath',
  };
  for (let i = 0; i < args.length; i++) {
    const flag = args[i];
    if (flag === '--help' || flag === '-h') {
      options.help = true;
      continue;
    }
    if (!Object.hasOwn(valueFlags, flag)) {
      throw new ResearchRunnerError('usage_error', `Unsupported research-300 option: ${flag}`);
    }
    if (!args[i + 1] || args[i + 1].startsWith('--')) {
      throw new ResearchRunnerError('usage_error', `${flag} requires a value`);
    }
    options[valueFlags[flag]] = args[++i];
  }
  if (options.corpus !== 'research-300') {
    throw new ResearchRunnerError('usage_error', `Unsupported corpus: ${options.corpus}. This command requires research-300`);
  }
  if (!OFFLINE_EXECUTIONS.includes(options.execution)) {
    throw new ResearchRunnerError('usage_error', `Research-300 supports offline execution only: ${OFFLINE_EXECUTIONS.join(', ')}`);
  }
  if (options.caseIds !== undefined) {
    if (options.execution === 'validate') throw new ResearchRunnerError('usage_error', '--cases supports inspect and evaluate-artifacts; validate accepts --case or the complete corpus');
    if (options.scenarioId !== undefined || options.turn !== undefined) throw new ResearchRunnerError('usage_error', '--cases cannot be combined with --case, --scenario or --turn');
    const ids = options.caseIds.split(',').map(id => id.trim());
    if (!ids.length || ids.some(id => !/^(?:STD|INT|MM)-(?:00[1-9]|0[1-9][0-9]|100)$/.test(id))) {
      throw new ResearchRunnerError('usage_error', '--cases requires comma-separated research case IDs');
    }
    options.caseIds = [...new Set(ids)];
  }
  if (options.turn !== undefined) {
    if (!/^[1-9][0-9]*$/.test(options.turn) || !Number.isSafeInteger(Number(options.turn))) {
      throw new ResearchRunnerError('usage_error', '--turn must be a positive integer (1-based)');
    }
    options.turn = Number(options.turn);
    if (!options.scenarioId) throw new ResearchRunnerError('usage_error', '--turn requires --scenario');
  }
  for (const field of ['root', 'artifactsPath', 'artifactRoot', 'outputPath', 'assessmentsPath']) {
    if (options[field]) options[field] = path.resolve(options[field]);
  }
  if (!options.help && options.execution === 'evaluate-artifacts' && !options.artifactsPath) {
    throw new ResearchRunnerError('usage_error', 'evaluate-artifacts requires --artifacts FILE');
  }
  if (options.execution !== 'evaluate-artifacts' && (options.artifactsPath || options.artifactRoot || options.assessmentsPath)) {
    throw new ResearchRunnerError('usage_error', '--artifacts, --artifact-root and --assessments require evaluate-artifacts');
  }
  return options;
}

const HELP = `Offline research-300 runner (no model calls or SUT setup)
Usage: node runner.cjs --corpus research-300 [options]
       node scripts/run-research300.cjs [options]

  --execution inspect|validate|evaluate-artifacts  Default: inspect
  --root PATH               Benchmark/corpus root; defaults to this checkout
  --scenario ID             Select one case (alias: --case)
  --cases ID,ID             Inspect/evaluate several cases; excludes --case/--turn
  --turn N                  Select a 1-based turn; requires --scenario
  --artifacts FILE          JSON candidate run envelope for offline evaluation
  --artifact-root DIR       Evidence root; defaults to the envelope's directory
  --assessments FILE        Independent benchmark review receipts, outside evidence
  --output FILE             Write a new report file; parent must already exist
  --help                    Show this help

Without --output, reports go only to stdout. Existing output files are never replaced.
Artifact envelope: {"schemaVersion":1,"corpus":"research-300","runs":[
  {"caseId":"STD-001","runId":"actual-run-id","turns":[...]}]}
Each ordered turn is {turnId,state:<cumulative AgentState>,artifacts:{
  <solverRunId>:{normalizedInput:<relative JSON>,solverResponse:<relative JSON>}}}.
normalizedInput contains {model,selection:{kind,id}} or {model,selections:[...]}.
solverResponse contains explicit results keyed by case:ID or combination:ID,
with meta {engineId,runId,modelHash,state,sourceHash} and actual execution details.
State receipts must include SHA256 hashes of the supplied raw artifact bytes.
Selection-specific native receipts may use {capture:{normalizedInput,solverResponse},
selections:{"case:ID":{normalizedInput,settings,solverResponse}}} for each run.
Capture files bind the full result; selection files retain the exact native
bytes hashed by execution.artifacts. Both sets are confined and immutable.
Reports must appear in the current turn's assistant messages. Earlier snapshots
are required for selecting a later turn. Evidence paths must remain inside the
evidence root; run IDs and their captured bytes are immutable across snapshots.
For revised public inputs, each run must include inputBinding copied exactly
from inspect output. Frozen sourceHash remains the native/model truth binding;
inputBinding separately identifies the actual public edition and delivered bytes.
Independent assessments for revised inputs must also include that inputBinding.
Optional figures: [{outputId,state,runId,path:<relative decodable image>}].
Decoding establishes file validity only; figure content requires independent
review bound to figureSha256. Current toolEvents and Codex assistantEvents retain
raw tool lifecycle and all completed visible assistant messages for review.
Reference provenance comes only from benchmark-owned reference-provenance.json.
Optional assessments envelope: {schemaVersion:1,corpus:"research-300",assessments:[
  {caseId,turnId,outputId,state,sourceHash,currentResponseSha256,activitySha256,pass,reason,
   reviewerId,reviewedAt:<ISO timestamp>}]}.
Figure assessments additionally require figureSha256 from the review request.
The currentResponseSha256 exported helper hashes canonical UTF8 JSON of
{schemaVersion:1,messages:[current assistant messages]}, with recursively sorted
object keys and original array order. currentActivitySha256 additionally binds
all current messages, toolEvents and assistantEvents using
{schemaVersion:1,messages,toolEvents,assistantEvents}. Candidate review flags are ignored.
Missing semantic assessments produce review_pending, null scores and bound
reviewRequests in the report. Assessment state may be null for clarification.
Exit codes: 0 inspected/validated/passed; 1 agent failure; 2 runner error;
            3 unknown, native truth pending or semantic review pending.
`;

function errorRecord(error, fallback) {
  return { code: String(error?.code || fallback), message: String(error?.message || error) };
}

function within(root, target) {
  const relative = path.relative(root, target);
  return relative === '' || (!relative.startsWith(`..${path.sep}`) && relative !== '..' && !path.isAbsolute(relative));
}

function canonical(file) {
  return fs.realpathSync(file);
}

const sha256 = (bytes) => createHash('sha256').update(bytes).digest('hex');

function readConfinedFile(root, relative, scope = 'artifact') {
  if (typeof relative !== 'string' || !relative || /[\\:\x00-\x1f]/.test(relative)
      || path.posix.isAbsolute(relative) || relative.split('/').some((part) => !part || part === '.' || part === '..')) {
    throw new ResearchRunnerError(`${scope}_unsafe_path`, 'Unsafe relative evidence path');
  }
  try {
    let current = root;
    for (const part of relative.split('/')) {
      current = path.join(current, part);
      if (fs.lstatSync(current).isSymbolicLink()) throw new ResearchRunnerError(`${scope}_unsafe_path`, 'Symlink evidence paths are forbidden');
    }
    if (!within(canonical(root), canonical(current)) || !fs.statSync(current).isFile()) {
      throw new ResearchRunnerError(`${scope}_unsafe_path`, 'Evidence path must be a regular file inside its root');
    }
    return fs.readFileSync(current);
  } catch (error) {
    if (error instanceof ResearchRunnerError) throw error;
    throw new ResearchRunnerError(`${scope}_unreadable`, `Cannot read ${relative}: ${error.message}`);
  }
}

function buildSourceBinding(caseRecord) {
  const paths = [...new Set(['contract.json', 'prompt.txt', 'reference-requests.json',
    ...caseRecord.contract.modelStates, ...caseRecord.contract.attachments])];
  paths.sort((a, b) => Buffer.compare(Buffer.from(a, 'utf8'), Buffer.from(b, 'utf8')));
  const manifest = { schemaVersion: 1, files: paths.map((name) => ({ path: name, sha256: sha256(readConfinedFile(caseRecord.caseDir, name, 'reference')) })) };
  return { manifest, sourceHash: sha256(Buffer.from(JSON.stringify(manifest), 'utf8')) };
}

function analysisEntries(state) {
  return Object.entries(state?.analysisResult?.results || {}).flatMap(([key, record]) => {
    const match = /^(case|combination):(.+)$/.exec(key);
    return match && typeof record?.meta?.runId === 'string'
      ? [{ key, runId: record.meta.runId, selection: { kind: match[1], id: match[2] } }] : [];
  });
}

function canonicalValue(value) {
  if (Array.isArray(value)) return value.map(canonicalValue);
  if (value && typeof value === 'object') return Object.fromEntries(Object.keys(value).sort().filter((key) => value[key] !== undefined).map((key) => [key, canonicalValue(value[key])]));
  return value;
}

function exportingModule(value) {
  return Object.values(require.cache).find((entry) => entry.exports === value
    || (entry.exports && Object.values(Object.getOwnPropertyDescriptors(entry.exports)).some((descriptor) => descriptor.value === value)));
}

function runtimeProvenance(provider, dependencies) {
  const providerModule = exportingModule(provider);
  let evaluatorModule;
  if (dependencies.evaluateCase || dependencies.evaluateTurn) {
    evaluatorModule = exportingModule(dependencies.evaluateCase || dependencies.evaluateTurn);
  } else {
    const evaluatorPath = path.join(__dirname, '..', 'lib', 'research300-evaluation.cjs');
    if (fs.existsSync(evaluatorPath)) {
      require(evaluatorPath);
      evaluatorModule = require.cache[require.resolve(evaluatorPath)];
    }
  }
  const sources = [];
  for (const [role, entry] of [['runner', module], ['provider', providerModule], ['evaluator', evaluatorModule]]) {
    if (!entry?.filename) continue;
    const root = path.resolve(path.dirname(entry.filename), '..');
    const visited = new Set();
    const visit = (current) => {
      if (!current?.filename || visited.has(current.filename) || !within(root, current.filename)
          || path.relative(root, current.filename).split(path.sep).includes('node_modules')) return;
      visited.add(current.filename);
      sources.push({ role, path: path.relative(root, current.filename).split(path.sep).join('/'),
        sha256: sha256(fs.readFileSync(current.filename)) });
      for (const child of current.children || []) visit(child);
    };
    visit(entry);
  }
  sources.sort((a, b) => Buffer.compare(Buffer.from(`${a.role}:${a.path}`), Buffer.from(`${b.role}:${b.path}`)));
  const evaluator = evaluatorModule?.exports;
  return {
    nodeVersion: process.versions.node,
    providerVersion: provider.RESPONSE_CONTRACT_VERSION || null,
    responseContractVersion: provider.RESPONSE_CONTRACT_VERSION || null,
    evaluatorVersion: evaluator?.EVALUATOR_VERSION || null,
    evaluatorResponseContractVersion: evaluator?.RESPONSE_CONTRACT_VERSION || null,
    providerOrigin: providerModule ? 'module' : 'injected',
    evaluatorOrigin: evaluatorModule ? 'module' : dependencies.evaluateCase || dependencies.evaluateTurn ? 'injected' : 'unavailable',
    sources,
    sourceManifestSha256: sha256(Buffer.from(JSON.stringify(canonicalValue(sources)), 'utf8')),
  };
}

function numericalResultHash(data) {
  const { execution, ...numerical } = data;
  return sha256(Buffer.from(JSON.stringify(canonicalValue(numerical)), 'utf8'));
}

function currentResponseSha256(messages, messageStartIndex) {
  if (!Array.isArray(messages) || !Number.isInteger(messageStartIndex) || messageStartIndex < 0 || messageStartIndex > messages.length) {
    throw new ResearchRunnerError('artifact_transcript_invalid', 'Current response binding requires an exact message boundary');
  }
  const assistantMessages = messages.slice(messageStartIndex).filter((message) => message &&
    (message.role === 'assistant' || message.type === 'ai' || (Array.isArray(message.id) && message.id.at(-1) === 'AIMessage')));
  return sha256(Buffer.from(JSON.stringify(canonicalValue({ schemaVersion: 1, messages: assistantMessages })), 'utf8'));
}

function currentActivitySha256(messages, messageStartIndex, toolEvents = [], assistantEvents = []) {
  currentResponseSha256(messages, messageStartIndex);
  if (!Array.isArray(toolEvents) || toolEvents.some(event => !event || typeof event !== 'object' || Array.isArray(event))) {
    throw new ResearchRunnerError('artifact_activity_invalid', 'Current tool events must be an array of captured objects');
  }
  if (!Array.isArray(assistantEvents) || assistantEvents.some(event => !event || event.type !== 'item.completed'
      || event.item?.type !== 'agent_message' || typeof event.item.text !== 'string')) {
    throw new ResearchRunnerError('artifact_activity_invalid', 'Current assistant events must contain completed Codex agent messages');
  }
  return activityFingerprint(messages.slice(messageStartIndex), toolEvents, assistantEvents);
}

function readAssessments(options, artifactRoot, caseIds) {
  if (!options.assessmentsPath) return [];
  let envelope;
  try {
    const file = canonical(options.assessmentsPath);
    if (within(artifactRoot, file) || !fs.statSync(file).isFile()) {
      throw new ResearchRunnerError('reference_assessment_path', 'Independent assessment file must be outside the candidate evidence root');
    }
    envelope = JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch (error) {
    if (error instanceof ResearchRunnerError) throw error;
    throw new ResearchRunnerError('reference_assessment_unreadable', `Cannot read independent assessments: ${error.message}`);
  }
  if (envelope?.schemaVersion !== 1 || envelope.corpus !== 'research-300' || !Array.isArray(envelope.assessments)) {
    throw new ResearchRunnerError('reference_assessment_schema', 'Independent assessments require schemaVersion 1, corpus research-300 and an assessments array');
  }
  const keys = new Set();
  for (const assessment of envelope.assessments) {
    const strings = ['caseId', 'turnId', 'outputId', 'reason', 'reviewerId', 'reviewedAt'];
    if (!assessment || strings.some((field) => typeof assessment[field] !== 'string' || !assessment[field].trim())
        || !caseIds.has(assessment.caseId) || !(assessment.state === null || (Number.isInteger(assessment.state) && assessment.state >= 1))
        || typeof assessment.pass !== 'boolean' || !/^[a-f0-9]{64}$/.test(assessment.sourceHash || '')
        || !/^[a-f0-9]{64}$/.test(assessment.currentResponseSha256 || '')
        || !/^[a-f0-9]{64}$/.test(assessment.activitySha256 || '')
        || !/^\d{4}-\d\d-\d\dT/.test(assessment.reviewedAt) || !Number.isFinite(Date.parse(assessment.reviewedAt))) {
      throw new ResearchRunnerError('reference_assessment_schema', 'Independent assessment has invalid identity, hashes, verdict or reviewer metadata');
    }
    const key = JSON.stringify([assessment.caseId, assessment.turnId, assessment.outputId]);
    if (keys.has(key)) throw new ResearchRunnerError('reference_assessment_duplicate', 'Independent output assessment is duplicated');
    keys.add(key);
  }
  return envelope.assessments;
}

function bindAssessments(assessments, caseRecord, contractTurn, sourceHash, responseHash, activityHash, figures, inputBinding) {
  return assessments.filter((assessment) => assessment.caseId === caseRecord.id && assessment.turnId === contractTurn.id).map((assessment) => {
    const output = caseRecord.contract.requiredOutputs?.find((item) => item.id === assessment.outputId && ['interaction', 'figure'].includes(item.kind)
      && item.state === contractTurn.state && (!item.turnIds || item.turnIds.includes(contractTurn.id))
      && (!contractTurn.requiredOutputIds || contractTurn.requiredOutputIds.includes(item.id)));
    const behavior = assessment.outputId === BEHAVIOR_REVIEW_ID && ['clarify','clarify-or-analyze'].includes(contractTurn.expectation);
    const clarification = assessment.outputId === CLARIFICATION_REVIEW_ID && (['clarify','clarify-or-analyze'].includes(contractTurn.expectation) || contractTurn.clarificationBlocksAnalysis === false)
      && !caseRecord.contract.requiredOutputs?.some(item => item.kind === 'interaction' && item.state === contractTurn.state
        && (!item.turnIds || item.turnIds.includes(contractTurn.id)) && (!contractTurn.requiredOutputIds || contractTurn.requiredOutputIds.includes(item.id)));
    if ((!output && !behavior && !clarification) || assessment.state !== contractTurn.state || assessment.sourceHash !== sourceHash
        || assessment.currentResponseSha256 !== responseHash || assessment.activitySha256 !== activityHash) {
      throw new ResearchRunnerError('reference_assessment_binding', 'Independent assessment does not match the current case, source, turn, output and assistant response');
    }
    if (output?.kind === 'figure' && !figures.some(figure => figure.outputId === output.id && figure.state === contractTurn.state
        && figure.decoded && figure.sha256 === assessment.figureSha256)) {
      throw new ResearchRunnerError('reference_assessment_binding', 'Independent figure assessment does not match the actual decoded figure SHA256');
    }
    if (inputBinding && JSON.stringify(canonicalValue(assessment.inputBinding)) !== JSON.stringify(canonicalValue(inputBinding))) {
      throw new ResearchRunnerError('reference_assessment_input_binding', 'Independent assessment does not match the current public input edition');
    }
    return { outputId: assessment.outputId, turnId: assessment.turnId, state: assessment.state,
      sourceHash, currentResponseSha256: responseHash, activitySha256: activityHash,
      ...(output?.kind === 'figure' ? { figureSha256: assessment.figureSha256 } : {}),
      ...(inputBinding ? { inputBinding } : {}), pass: assessment.pass, reason: assessment.reason };
  });
}

function selectedStatuses(response, selected, execution) {
  return [response.status, response.meta?.status, selected.record.status, selected.record.meta?.status,
    selected.data.status, selected.data.meta?.status, execution.status].filter((status) => status !== undefined);
}

function successfulStatuses(statuses) {
  return statuses.every((status) => typeof status === 'string'
    && ['success', 'succeeded', 'ok', 'completed', 'complete', 'passed'].includes(status.toLowerCase()));
}

function collectRunArtifacts(run, artifactRoot, contractTurns) {
  const collected = new Map();
  let previousIndex = -1;
  for (const turn of run.turns) {
    const turnIndex = contractTurns.findIndex((expected) => expected.id === turn.turnId);
    if (turnIndex <= previousIndex) throw new ResearchRunnerError('artifact_turn_invalid', 'Candidate turn snapshots must follow contract order');
    previousIndex = turnIndex;
    if (turn.artifacts === undefined) continue;
    if (!turn.artifacts || typeof turn.artifacts !== 'object' || Array.isArray(turn.artifacts)) {
      throw new ResearchRunnerError('artifact_schema_invalid', 'Turn artifacts must map run IDs to file paths');
    }
    for (const [runId, paths] of Object.entries(turn.artifacts)) {
      if (!runId.trim() || !paths || typeof paths !== 'object' || Array.isArray(paths)) {
        throw new ResearchRunnerError('artifact_schema_invalid', 'Each immutable run ID must map to named artifact paths');
      }
      const readArtifacts = mapping => {
        if (!mapping || typeof mapping !== 'object' || Array.isArray(mapping) || !Object.keys(mapping).length) {
          throw new ResearchRunnerError('artifact_schema_invalid', 'Artifact paths must be a nonempty named map');
        }
        const artifactBytes = Object.create(null), trustedArtifactHashes = Object.create(null);
        for (const [name, relative] of Object.entries(mapping)) {
          artifactBytes[name] = readConfinedFile(artifactRoot, relative);
          trustedArtifactHashes[name] = sha256(artifactBytes[name]);
        }
        return { artifactBytes, trustedArtifactHashes };
      };
      const structured = Object.hasOwn(paths, 'capture');
      if (structured && (Object.keys(paths).some(name => !['capture', 'selections'].includes(name))
          || !paths.selections || typeof paths.selections !== 'object' || Array.isArray(paths.selections))) {
        throw new ResearchRunnerError('artifact_schema_invalid', 'Structured artifacts require capture and a selection artifact map');
      }
      const { artifactBytes, trustedArtifactHashes } = readArtifacts(structured ? paths.capture : paths);
      if (!artifactBytes.normalizedInput || !artifactBytes.solverResponse) {
        throw new ResearchRunnerError('artifact_schema_invalid', 'Each run requires normalizedInput and solverResponse files');
      }
      let input, response;
      try {
        input = JSON.parse(artifactBytes.normalizedInput.toString('utf8'));
        response = JSON.parse(artifactBytes.solverResponse.toString('utf8'));
      } catch {
        throw new ResearchRunnerError('artifact_schema_invalid', 'Normalized input and solver response must be JSON');
      }
      const selections = input?.selections || (input?.selection ? [input.selection] : []);
      if (!input?.model || !Array.isArray(selections) || !selections.length || selections.some((s) => !s || !['case', 'combination'].includes(s.kind) || typeof s.id !== 'string' || !s.id)) {
        throw new ResearchRunnerError('artifact_schema_invalid', 'Normalized input requires the actual model and exact selection or selections');
      }
      const resultHashes = Object.create(null), contexts = Object.create(null);
      const selectionArtifacts = Object.create(null);
      if (structured) {
        const selectionKeys = new Set(selections.map(selection => `${selection.kind}:${selection.id}`));
        if (Object.keys(paths.selections).length !== selectionKeys.size
            || Object.keys(paths.selections).some(key => !selectionKeys.has(key))) {
          throw new ResearchRunnerError('artifact_schema_invalid', 'Native selection artifacts must cover exactly the captured selections');
        }
        for (const [key, mapping] of Object.entries(paths.selections)) selectionArtifacts[key] = readArtifacts(mapping);
      }
      for (const selection of selections) {
        const key = `${selection.kind}:${selection.id}`;
        try {
          const selected = selectAnalysisResult(response, selection);
          resultHashes[key] = numericalResultHash(selected.data);
          const execution = selected.data.execution || selected.record.execution || selected.record.meta?.execution || {};
          contexts[key] = { meta: selected.record.meta || response.meta || {}, execution, statuses: selectedStatuses(response, selected, execution),
            engineDeclarations: [selected.record.engineId, selected.data.engineId, selected.data.meta?.engineId, execution.engineId].filter((value) => value !== undefined) };
          if (structured) {
            // A native receipt may hash only a solver payload, whereas the host
            // envelope also carries derived fields. Bind every graded field to
            // those native bytes before authorizing numerical evaluation.
            contexts[key].payloadBinding = require('../lib/structureclaw-payload-binding.cjs').verifyStructureClawPayloadBinding({
              model: input.model, selection, data: selected.data, meta: selected.record.meta,
              execution, artifactBytes: selectionArtifacts[key].artifactBytes,
            });
          }
        }
        catch { /* Missing/failed solver selections remain unavailable to the evaluator. */ }
      }
      const binding = { selections, modelHash: modelFingerprint(input.model), artifactBytes, trustedArtifactHashes, resultHashes, contexts,
        ...(structured ? { selectionArtifacts } : {}) };
      if (selections.length === 1) {
        binding.selection = selections[0];
        binding.resultHash = resultHashes[`${selections[0].kind}:${selections[0].id}`];
      }
      const prior = collected.get(runId);
      const immutableHashes = evidence => canonicalValue({ capture: evidence.trustedArtifactHashes,
        selections: evidence.selectionArtifacts && Object.fromEntries(Object.entries(evidence.selectionArtifacts).map(([key, value]) => [key, value.trustedArtifactHashes])) });
      if (prior && JSON.stringify(immutableHashes(prior.evidence)) !== JSON.stringify(immutableHashes(binding))) {
        throw new ResearchRunnerError('artifact_run_rebound', 'An immutable analysis run ID was rebound to different artifact bytes');
      }
      if (!prior) collected.set(runId, { firstTurn: turnIndex, evidence: binding });
    }
  }
  return collected;
}

function capturedContextFailures(state, artifactEvidence, plannedEngine, sourceHash) {
  const failures = [];
  for (const entry of analysisEntries(state)) {
    const evidence = artifactEvidence[entry.runId];
    if (!evidence) continue;
    const raw = evidence.contexts[entry.key];
    if (!raw) { failures.push(`${entry.key}: no successful raw solver selection`); continue; }
    if (raw.payloadBinding?.pass === false) {
      failures.push(...raw.payloadBinding.failures.map(message => `${entry.key}: native payload binding: ${message}`));
    }
    let selected;
    try { selected = selectAnalysisResult(state.analysisResult, entry.selection); }
    catch { failures.push(`${entry.key}: candidate does not contain a successful selected result`); continue; }
    const candidate = selected.record.meta || {};
    const execution = selected.data.execution || selected.record.execution || candidate.execution || {};
    if (!successfulStatuses(raw.statuses) || !successfulStatuses(selectedStatuses(state.analysisResult, selected, execution))) {
      failures.push(`${entry.key}: raw or candidate response declares an unsuccessful or unknown status`);
    }
    if (raw.meta.runId !== entry.runId || normalizeEngineKey(raw.meta.engineId) !== normalizeEngineKey(plannedEngine)
        || !Number.isInteger(raw.meta.state) || raw.meta.state < 1 || raw.meta.sourceHash !== sourceHash || raw.meta.modelHash !== evidence.modelHash) {
      failures.push(`${entry.key}: raw solver engine/run/state/source/model context differs from the required run`);
    }
    if (raw.engineDeclarations.some((engine) => normalizeEngineKey(engine) !== normalizeEngineKey(plannedEngine))) failures.push(`${entry.key}: raw solver contains conflicting engine declarations`);
    for (const field of ['runId', 'state', 'sourceHash', 'modelHash']) {
      if (candidate[field] !== raw.meta[field]) failures.push(`${entry.key}: candidate ${field} differs from raw solver metadata`);
    }
    if (normalizeEngineKey(candidate.engineId) !== normalizeEngineKey(raw.meta.engineId)) failures.push(`${entry.key}: candidate engine differs from raw solver metadata`);
    if (raw.execution.executed !== true || !raw.execution.solverVersion || raw.execution.analysisReturnCode !== 0
        || normalizeEngineKey(raw.execution.solver) !== normalizeEngineKey(plannedEngine)) failures.push(`${entry.key}: raw solver execution did not complete successfully with the planned engine`);
    for (const field of ['executed', 'solverVersion', 'analysisReturnCode']) {
      if (execution[field] !== raw.execution[field]) failures.push(`${entry.key}: candidate execution ${field} differs from raw solver evidence`);
    }
    if (normalizeEngineKey(execution.solver) !== normalizeEngineKey(raw.execution.solver)) failures.push(`${entry.key}: candidate execution solver differs from raw solver evidence`);
  }
  return failures;
}

async function figureEvidence(figures, artifactRoot, sourceHash) {
  if (figures === undefined) return [];
  if (!Array.isArray(figures)) throw new ResearchRunnerError('artifact_figure_invalid', 'Figure descriptors must be an array');
  const sharp = require('sharp');
  const identities = new Set();
  const decodedFigures=await Promise.all(figures.map(async (figure) => {
    const identity=JSON.stringify([figure?.outputId,figure?.state,figure?.path]);
    if (!figure || typeof figure.outputId !== 'string' || identities.has(identity)) {
      throw new ResearchRunnerError('artifact_figure_invalid', 'Figure descriptors require distinct files within each output and state');
    }
    identities.add(identity);
    const bytes = readConfinedFile(artifactRoot, figure.path);
    const text = bytes.toString('utf8');
    const unsafeSvg = /<svg\b/i.test(text) && /<!DOCTYPE|<!ENTITY|<\s*(?:script|foreignObject)\b|\bon\w+\s*=|(?:href\s*=\s*["'](?:https?:|file:|data:))|url\s*\(\s*["']?(?:https?:|file:|data:)/i.test(text);
    let decoded = false, width, height;
    if (!unsafeSvg) {
      try {
        const decoder = sharp(bytes, { failOn: 'error', limitInputPixels: 40_000_000 });
        const metadata = await decoder.metadata();
        const pixels = await decoder.raw().toBuffer();
        decoded = metadata.width > 0 && metadata.height > 0 && pixels.length > 0;
        if (decoded) { width = metadata.width; height = metadata.height; }
      } catch { /* Invalid or unsupported documents do not satisfy a figure output. */ }
    }
    return { outputId: figure.outputId, state: figure.state, runId: figure.runId,
      ...(figure.runIds!==undefined?{runIds:figure.runIds}:{}),
      path: figure.path, sourceHash, sha256: sha256(bytes), decoded, ...(decoded ? { width, height } : {}) };
  }));
  const groups=new Map();
  for(const figure of decodedFigures) {
    const key=JSON.stringify([figure.outputId,figure.state]);
    if(!groups.has(key))groups.set(key,[]);
    groups.get(key).push(figure);
  }
  return [...groups.values()].map(members=>members.length===1?members[0]:{
    outputId:members[0].outputId,state:members[0].state,sourceHash,
    decoded:members.every(f=>f.decoded),sha256:figureSetFingerprint(members),figures:members});
}

function loadReference(caseRecord, sourceHash, dependencies = {}) {
  const referencePath = path.join(caseRecord.caseDir, 'independent-reference.json');
  if (!fs.existsSync(referencePath)) return {};
  const bytes = readConfinedFile(caseRecord.caseDir, 'independent-reference.json', 'reference');
  let reference;
  try { reference = JSON.parse(bytes.toString('utf8')); }
  catch { throw new ResearchRunnerError('reference_schema_invalid', 'Independent reference must be valid JSON'); }
  const provenancePath = path.join(caseRecord.caseDir, 'reference-provenance.json');
  const validateCase = dependencies.validateCase || require('../lib/research300-validation.cjs').validateResearchCase;
  if (!fs.existsSync(provenancePath)) {
    // Qualified commercial installations retain source/reference bindings and
    // independently reviewed raw evidence in acceptance.json. Validate that
    // complete chain before deriving the evaluator's reference receipt. Input
    // blind review is a separate gate and cannot invalidate native provenance.
    if (!['pkpm', 'yjk'].includes(normalizeEngineKey(caseRecord.contract.plannedEngine))) return { reference };
    const validation = validateCase({ root: caseRecord.root, caseDir: caseRecord.caseDir, stage: 'reference-ready' });
    if (!validation.referenceReady) throw new ResearchRunnerError('reference_invalid', 'Reference validation failed');
    if (validation.nativeVerified !== true) {
      if (reference.nativeVerified === true || reference.sameEngineTruthStatus === 'verified') {
        throw new ResearchRunnerError('reference_native_unreviewed', 'Installed native reference failed independent evidence verification');
      }
      return { reference };
    }
    const evidenceByState = new Map();
    for (const entry of reference.states || []) {
      const model = caseRecord.models[entry.state - 1];
      if (!model || evidenceByState.has(entry.state)) throw new ResearchRunnerError('reference_provenance_invalid', 'Native reference has an invalid or duplicate model state');
      evidenceByState.set(entry.state, { state: entry.state, engineId: caseRecord.contract.plannedEngine,
        modelHash: modelFingerprint(model), sourceHash, status: 'native-verified' });
    }
    return { reference, evidenceByState };
  }
  let provenance;
  const provenanceBytes = readConfinedFile(caseRecord.caseDir, 'reference-provenance.json', 'reference');
  try { provenance = JSON.parse(provenanceBytes.toString('utf8')); }
  catch { throw new ResearchRunnerError('reference_provenance_invalid', 'Reference provenance must be valid JSON'); }
  if (provenance?.schemaVersion !== 1 || provenance.caseId !== caseRecord.id || provenance.sourceHash !== sourceHash
      || provenance.referenceSha256 !== sha256(bytes) || !Array.isArray(provenance.states)) {
    throw new ResearchRunnerError('reference_provenance_invalid', 'Reference provenance is stale or does not bind this case and reference file');
  }
  const validation = validateCase({ root: caseRecord.root, caseDir: caseRecord.caseDir, stage: 'reference-ready' });
  if (!validation.referenceReady) throw new ResearchRunnerError('reference_invalid', 'Reference validation failed');
  const evidenceByState = new Map();
  for (const entry of provenance.states) {
    const model = caseRecord.models[entry.state - 1];
    if (!model || entry.modelHash !== modelFingerprint(model) || entry.engineId !== caseRecord.contract.plannedEngine
        || !['validated', 'native-verified'].includes(entry.status) || evidenceByState.has(entry.state)) {
      throw new ResearchRunnerError('reference_provenance_invalid', 'Reference provenance has an invalid model, engine, state, or status');
    }
    if (entry.status === 'native-verified' && validation.nativeVerified !== true) {
      throw new ResearchRunnerError('reference_native_unreviewed', 'Native truth requires independently reviewed native evidence');
    }
    evidenceByState.set(entry.state, { state: entry.state, engineId: entry.engineId,
      modelHash: entry.modelHash, sourceHash, status: entry.status });
  }
  return { reference, evidenceByState };
}

function assertInputBinding(run, inputBinding) {
  if (!inputBinding) return;
  if (!run.inputBinding) throw new ResearchRunnerError('artifact_input_binding_missing', 'Candidate run is missing the current public input edition binding; historical trials cannot evaluate revised prompts');
  if (JSON.stringify(canonicalValue(run.inputBinding)) !== JSON.stringify(canonicalValue(inputBinding))) {
    throw new ResearchRunnerError('artifact_input_binding_stale', 'Candidate run public input edition binding is stale or does not match delivered inputs');
  }
}

async function evaluateCandidateCase({ caseRecord, run, artifactRoot, turnIndex, assessments = [] }, dependencies = {}) {
  const inputBinding = caseRecord.corpus === 'research-300'
    ? (await (dependencies.provider || require('../lib/corpus-provider.cjs')).getPublicTurnInput(caseRecord, 0)).inputBinding : undefined;
  assertInputBinding(run, inputBinding);
  const evaluateTurn = dependencies.evaluateTurn || require('../lib/research300-evaluation.cjs').evaluateResearchTurn;
  const { sourceHash } = buildSourceBinding(caseRecord);
  const { reference, evidenceByState } = loadReference(caseRecord, sourceHash, dependencies);
  const supplied = new Map(run.turns.map((turn) => [turn.turnId, turn]));
  const expectedIds = new Set(caseRecord.contract.turns.map((turn) => turn.id));
  if (run.turns.some((turn) => !expectedIds.has(turn.turnId))) throw new ResearchRunnerError('artifact_turn_invalid', 'Candidate run contains an unknown turn');
  const collected = collectRunArtifacts(run, artifactRoot, caseRecord.contract.turns);
  const indices = turnIndex === undefined ? caseRecord.contract.turns.map((_, i) => i) : [turnIndex];
  const turns = [];
  for (const index of indices) {
    const contractTurn = caseRecord.contract.turns[index];
    const candidate = supplied.get(contractTurn.id);
    const previous = index > 0 ? supplied.get(caseRecord.contract.turns[index - 1].id) : null;
    if (!candidate?.state || (index > 0 && !previous?.state)) {
      turns.push({ turn: index + 1, turnId: contractTurn.id, status: 'unknown', reason: 'Candidate state or previous turn snapshot is missing' });
      continue;
    }
    const previousMessages = previous?.state?.messages || [];
    const messages = candidate.state.messages || [];
    if (!Array.isArray(messages) || !Array.isArray(previousMessages)
        || JSON.stringify(messages.slice(0, previousMessages.length)) !== JSON.stringify(previousMessages)) {
      throw new ResearchRunnerError('artifact_transcript_invalid', 'Candidate snapshots must retain the cumulative message prefix');
    }
    const priorMessageRanges=[];let priorEnd=0;
    for(const priorTurn of caseRecord.contract.turns.slice(0,index)) {
      const captured=supplied.get(priorTurn.id)?.state?.messages;
      if(captured===undefined){priorMessageRanges.length=0;break;}
      if(!Array.isArray(captured)||captured.length<priorEnd||captured.length>previousMessages.length
        ||JSON.stringify(messages.slice(0,captured.length))!==JSON.stringify(captured)) {
        throw new ResearchRunnerError('artifact_transcript_invalid','Historical turn snapshots must retain the captured cumulative prefix');
      }
      priorMessageRanges.push({turnId:priorTurn.id,start:priorEnd,end:captured.length});priorEnd=captured.length;
    }
    const entries = analysisEntries(candidate.state);
    const artifactEvidence = Object.create(null);
    for (const entry of entries) {
      const saved = collected.get(entry.runId);
      if (saved && saved.firstTurn <= index) artifactEvidence[entry.runId] = saved.evidence;
    }
    const responseHash = currentResponseSha256(messages, previousMessages.length);
    const toolEvents = candidate.toolEvents === undefined ? [] : candidate.toolEvents;
    const assistantEvents = candidate.assistantEvents === undefined ? [] : candidate.assistantEvents;
    const activityHash = currentActivitySha256(messages, previousMessages.length, toolEvents, assistantEvents);
    const figures = await figureEvidence(candidate.figures, artifactRoot, sourceHash);
    const evidence = { sourceHash, ...(inputBinding ? { inputBinding } : {}), artifactEvidence,
      interactionEvidence: bindAssessments(assessments, caseRecord, contractTurn, sourceHash, responseHash, activityHash, figures, inputBinding),
      figureEvidence: figures,
      turnEvidence: { turnId: contractTurn.id, state: contractTurn.state,
      messageStartIndex: previousMessages.length, priorMessageRanges, currentResponseSha256: responseHash, activitySha256: activityHash, toolEvents, assistantEvents,
      analysisRunIds: [...collected].filter(([, saved]) => saved.firstTurn === index).map(([id]) => id) } };
    if (evidenceByState?.has(contractTurn.state)) evidence.referenceEvidence = evidenceByState.get(contractTurn.state);
    if (contractTurn.expectation !== 'clarify') {
      const failures = capturedContextFailures(candidate.state, artifactEvidence, caseRecord.contract.plannedEngine, sourceHash);
      if (failures.length) {
        turns.push({ turn: index + 1, turnId: contractTurn.id, currentResponseSha256: responseHash, activitySha256: activityHash, status: 'agent_failure',
          evaluation: { status: 'agent_failure', allPassed: false, metrics: [{ metric: 'captured_execution_context', pass: false, actual: failures.join('; ') }] } });
        continue;
      }
    }
    const evaluation = await evaluateTurn({ caseRecord: { ...caseRecord, reference }, turnIndex: index, state: candidate.state, evidence });
    const status = evaluation.status === 'pass' ? 'passed' : evaluation.status === 'configuration_error' ? 'corpus_error' : evaluationStatus(evaluation);
    if (status === 'passed' && evaluation.allPassed !== true) throw new ResearchRunnerError('evaluation_result_invalid', 'Passing evaluator status requires allPassed=true');
    const pendingIds = [...new Set((evaluation.metrics || []).filter(metric => metric.status === 'review_pending').flatMap(metric => metric.outputIds || []))];
    const reviewRequests = pendingIds.map(outputId => ({ caseId: caseRecord.id, turnId: contractTurn.id, outputId,
      state: contractTurn.state, sourceHash, currentResponseSha256: responseHash, activitySha256: activityHash, ...(inputBinding ? { inputBinding } : {}),
      instruction: contractTurn.instruction,
      description: outputId === BEHAVIOR_REVIEW_ID ? 'Determine whether this current-turn tool activity attempted engineering analysis before clarification. Do not infer successful execution from assistant claims.'
        : outputId === CLARIFICATION_REVIEW_ID ? 'Determine whether the current answer resolves the requested clarification without assuming the missing engineering information.'
          : caseRecord.contract.requiredOutputs.find(output => output.id === outputId)?.description,
      ...(contractTurn.expectedQuestions ? { expectedQuestions: contractTurn.expectedQuestions } : {}),
      ...(figures.some(figure => figure.outputId === outputId) ? {
        figureSha256: figures.find(figure => figure.outputId === outputId).sha256,
        figure: figures.find(figure => figure.outputId === outputId), artifactRoot,
        model: candidate.state.model, analysisResult: candidate.state.analysisResult } : {}),
      messages: messages.slice(previousMessages.length), toolEvents, assistantEvents }));
    turns.push({ turn: index + 1, turnId: contractTurn.id, currentResponseSha256: responseHash, activitySha256: activityHash, status, evaluation,
      ...(reviewRequests.length ? { reviewRequests } : {}) });
  }
  return { status: overallStatus(turns), allPassed: turns.length > 0 && turns.every((turn) => turn.status === 'passed'), sourceHash, ...(inputBinding ? { inputBinding } : {}), turns,
    reviewRequests: turns.flatMap(turn => turn.reviewRequests || []) };
}

function readArtifacts(options, caseIds) {
  let envelope;
  try {
    if (!fs.statSync(options.artifactsPath).isFile()) throw new Error('Candidate artifacts must be a JSON file');
    envelope = JSON.parse(fs.readFileSync(options.artifactsPath, 'utf8'));
  } catch (error) {
    throw new ResearchRunnerError('artifact_unreadable', `Cannot read candidate artifacts: ${error.message}`);
  }
  if (envelope?.schemaVersion !== 1 || envelope?.corpus !== 'research-300' || !Array.isArray(envelope?.runs)) {
    throw new ResearchRunnerError('artifact_schema_invalid', 'Expected schemaVersion 1, corpus research-300 and a runs array');
  }
  const root = canonical(options.artifactRoot || path.dirname(options.artifactsPath));
  if (!fs.statSync(root).isDirectory()) throw new ResearchRunnerError('artifact_root_invalid', 'Artifact root must be a directory');
  const runs = new Map();
  for (const run of envelope.runs) {
    if (!run || typeof run !== 'object' || !caseIds.has(run.caseId) || !Array.isArray(run.turns)) {
      throw new ResearchRunnerError('artifact_run_invalid', 'Every run requires a known caseId and a turns array');
    }
    if (runs.has(run.caseId)) throw new ResearchRunnerError('artifact_duplicate_case', `Multiple candidate runs for ${run.caseId}`);
    if (typeof run.runId !== 'string' || !run.runId.trim()) {
      throw new ResearchRunnerError('artifact_run_id_missing', `Candidate run for ${run.caseId} requires runId`);
    }
    const turnIds = new Set();
    for (const turn of run.turns) {
      if (!turn || typeof turn.turnId !== 'string' || turnIds.has(turn.turnId)) {
        throw new ResearchRunnerError('artifact_turn_invalid', `Run ${run.runId} requires unique turnId values`);
      }
      turnIds.add(turn.turnId);
    }
    runs.set(run.caseId, run);
  }
  return { runs, root };
}

function evaluationStatus(evaluation) {
  const status = evaluation?.status;
  if (['passed', 'agent_failure', 'unknown', 'native_truth_pending', 'review_pending', 'corpus_error', 'artifact_error', 'evaluation_error'].includes(status)) {
    return status;
  }
  throw new ResearchRunnerError('evaluation_result_invalid', 'Evaluator must return an explicit engineering-v2.3 status');
}

function overallStatus(cases) {
  for (const status of ['corpus_error', 'artifact_error', 'evaluation_error', 'agent_failure', 'unknown', 'native_truth_pending', 'review_pending']) {
    if (cases.some((record) => record.status === status)) return status;
  }
  return cases.length ? 'passed' : 'unknown';
}

function writeReport(outputPath, report, options, records) {
  // Existing parents only: the offline runner never creates directory trees.
  const destination = path.join(canonical(path.dirname(outputPath)), path.basename(outputPath));
  const protectedDirectories = records.map((record) => record.caseDir).filter(Boolean);
  protectedDirectories.push(path.join(options.root || path.resolve(__dirname, '..'), 'corpora', 'research-300'));
  if (options.artifactsPath) protectedDirectories.push(options.artifactRoot || path.dirname(options.artifactsPath));
  if (process.env.SCLAW_ROOT) protectedDirectories.push(process.env.SCLAW_ROOT);
  for (const directory of protectedDirectories) {
    if (fs.existsSync(directory) && within(canonical(directory), destination)) {
      throw new ResearchRunnerError('output_path_protected', 'Output path is inside protected corpus, evidence, or SUT input');
    }
  }
  if (options.artifactsPath && destination === canonical(options.artifactsPath)) {
    throw new ResearchRunnerError('output_path_protected', 'Output cannot replace candidate artifacts');
  }
  if (options.assessmentsPath && fs.existsSync(options.assessmentsPath) && destination === canonical(options.assessmentsPath)) {
    throw new ResearchRunnerError('output_path_protected', 'Output cannot replace independent assessments');
  }
  for (let directory = path.dirname(destination); ; directory = path.dirname(directory)) {
    if (fs.existsSync(path.join(directory, 'backend', 'package.json'))) {
      throw new ResearchRunnerError('output_path_protected', 'Output cannot write inside a SUT checkout');
    }
    if (directory === path.dirname(directory)) break;
  }
  fs.writeFileSync(destination, `${JSON.stringify(report, null, 2)}\n`, { encoding: 'utf8', flag: 'wx' });
}

async function runResearch300(args, dependencies = {}) {
  const stdout = dependencies.stdout || ((data) => process.stdout.write(data));
  let options;
  const report = {
    schemaVersion: 'research300-runner/v1', corpus: 'research-300', evaluationProfile: 'engineering-v2.3',
    execution: null, agentExecution: 'not-run', runtime: null, status: 'unknown', cases: [],
  };
  let phase = 'usage_error';
  let records = [];
  try {
    options = parseResearchOptions(args);
    if (options.help) {
      stdout(HELP);
      return { ...report, status: 'inspected', execution: 'help' };
    }
    report.execution = options.execution;
    report.selection = { caseId: options.scenarioId || null, turn: options.turn || null,
      ...(options.caseIds ? { caseIds: options.caseIds } : {}) };
    phase = 'corpus_error';
    const provider = dependencies.provider || require('../lib/corpus-provider.cjs');
    report.runtime = runtimeProvenance(provider, dependencies);
    const corpus = await provider.loadCorpus({ corpus: 'research-300', root: options.root });
    const ids = corpus.cases.map((record) => typeof record === 'string' ? record : record.id);
    if (ids.length === 0) throw new ResearchRunnerError('corpus_empty', 'The research-300 corpus contains no cases');
    const selectedIds = options.scenarioId ? [options.scenarioId] : options.caseIds || ids;
    records = await Promise.all(selectedIds.map((id) => provider.loadCase(corpus, id)));
    for (let i = 0; i < records.length; i++) {
      const record = records[i];
      const turnIndices = options.turn === undefined ? record.contract.turns.map((_, index) => index) : [options.turn - 1];
      const turns = [];
      for (const turnIndex of turnIndices) {
        turns.push({ turn: turnIndex + 1, input: await provider.getPublicTurnInput(record, turnIndex) });
      }
      const inputBinding = turns[0]?.input?.inputBinding;
      report.cases.push({ caseId: selectedIds[i], ...(inputBinding ? { inputBinding } : {}), turns });
    }
    if (options.execution === 'inspect') {
      report.status = 'inspected';
    } else if (options.execution === 'validate') {
      const validateCorpus = dependencies.validateCorpus || require('../lib/research300-validation.cjs').validateResearchCorpus;
      report.validation = await validateCorpus({ root: corpus.root, caseId: options.scenarioId, stage: 'authored' });
      report.status = report.validation.valid === true ? 'validated' : 'corpus_error';
    } else {
      phase = 'artifact_error';
      const artifacts = readArtifacts(options, new Set(ids));
      phase = 'corpus_error';
      const assessments = readAssessments(options, artifacts.root, new Set(ids));
      for (let i = 0; i < records.length; i++) {
        const result = report.cases[i];
        const run = artifacts.runs.get(result.caseId);
        if (!run) {
          Object.assign(result, { status: 'unknown', reason: 'No candidate run supplied for this case' });
          continue;
        }
        try {
          assertInputBinding(run, result.inputBinding);
          const evaluateCase = dependencies.evaluateCase || ((input) => evaluateCandidateCase(input, dependencies));
          const evaluation = await evaluateCase({ caseRecord: records[i], run, artifactRoot: artifacts.root, assessments, turnIndex: options.turn === undefined ? undefined : options.turn - 1 });
          Object.assign(result, { runId: run.runId, status: evaluationStatus(evaluation), evaluation });
        } catch (error) {
          const status = error.code?.startsWith('artifact_') ? 'artifact_error' : error.code?.startsWith('reference_') ? 'corpus_error' : 'evaluation_error';
          Object.assign(result, { status, error: errorRecord(error, status) });
        }
      }
      report.status = overallStatus(report.cases);
      report.reviewRequests = report.cases.flatMap(record => record.evaluation?.reviewRequests || []);
    }
  } catch (error) {
    report.status = phase;
    report.error = errorRecord(error, phase);
  }
  if (options?.outputPath) {
    try {
      writeReport(options.outputPath, report, options, records);
    } catch (error) {
      report.status = 'output_error';
      report.error = errorRecord(error, 'output_error');
    }
  }
  stdout(`${JSON.stringify(report, null, 2)}\n`);
  return report;
}

function researchExitCode(report) {
  if (['inspected', 'validated', 'passed'].includes(report.status)) return 0;
  if (report.status === 'agent_failure') return 1;
  if (['unknown', 'native_truth_pending', 'review_pending'].includes(report.status)) return 3;
  return 2;
}

module.exports = { ResearchRunnerError, parseResearchOptions, runResearch300, researchExitCode, buildSourceBinding, currentResponseSha256, currentActivitySha256, evaluateCandidateCase, loadReference };

if (require.main === module) {
  runResearch300(process.argv.slice(2)).then((report) => { process.exitCode = researchExitCode(report); }).catch((error) => {
    process.stderr.write(`${JSON.stringify({ status: 'runner_error', error: errorRecord(error, 'runner_error') })}\n`);
    process.exitCode = 2;
  });
}
