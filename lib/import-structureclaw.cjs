'use strict';
const fs = require('node:fs');
const path = require('node:path');
const zlib = require('node:zlib');
const { createHash } = require('node:crypto');
const { spawnSync } = require('node:child_process');
const { isDeepStrictEqual } = require('node:util');
const { modelFingerprint } = require('./analysis-evidence.cjs');

const UPSTREAM = Object.freeze({ repository: 'https://github.com/qinsz01/structureclaw',
  ref: 'work/research-next', commit: '00ecd812a315a75b7714d5fc030ec3652bfaf869' });
const record = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const own = (value, key) => record(value) && Object.hasOwn(value, key);
const clone = value => JSON.parse(JSON.stringify(value));
const digest = bytes => createHash('sha256').update(bytes).digest('hex');
const fail = (code, message) => { throw Object.assign(new Error(`structureclaw_${code}: ${message}`), { code: `structureclaw_${code}` }); };
const physicalModel = value => record(value) && record(value.coordinate_system)
  && ['nodes', 'elements', 'materials', 'sections'].every(key => Array.isArray(value[key]))
  && value.nodes.every(node => record(node) && ['x', 'y', 'z'].every(key => Number.isFinite(node[key])));

function normalizeMessages(messages) {
  return (Array.isArray(messages) ? messages : []).map(message => {
    const fields = record(message.kwargs) ? { ...message, ...message.kwargs } : { ...message };
    const constructor = Array.isArray(message.id) ? message.id.at(-1) : undefined;
    const kind = typeof message._getType === 'function' ? message._getType() : message.type;
    const roles = new Map([['ai', 'assistant'], ['human', 'user'], ['tool', 'tool'], ['system', 'system'],
      ['AIMessage', 'assistant'], ['HumanMessage', 'user'], ['ToolMessage', 'tool'], ['SystemMessage', 'system']]);
    const role = fields.role ?? roles.get(kind) ?? roles.get(constructor);
    return { ...fields, ...(role ? { role } : {}) };
  });
}

function assertCaptureStatus(value, label) {
  if (!record(value)) return;
  if (value.success === false || value.error || ['error', 'failed', 'failure', 'aborted', 'cancelled', 'canceled'].includes(value.status))
    fail('turn_failed', `${label} declares failure${typeof value.error === 'string' ? `: ${value.error}` : ''}`);
  if (value.busy === true || ['running', 'in_progress'].includes(value.status)) fail('turn_incomplete', `${label} is still running`);
}

function interruptedInteraction(value) {
  return record(value) && value.resumeRequired === true && value.conversationStage === 'awaiting_user_input'
    && Array.isArray(value.questions) && value.questions.length > 0
    && value.questions.every(question => record(question) && typeof question.question === 'string' && question.question.trim());
}

function normalizeToolEvents(...sources) {
  const supplied = sources.filter(value => value !== undefined);
  for (const value of supplied) if (!Array.isArray(value) || value.some(event => !record(event)))
    fail('tool_events_invalid', 'Tool events must be an array of objects');
  if (supplied.some(value => !isDeepStrictEqual(value, supplied[0])))
    fail('tool_events_ambiguous', 'Outer and nested tool event captures disagree');
  return supplied.length ? clone(supplied[0]) : undefined;
}

function summaryToolEvent(...sources) {
  const supplied = sources.filter(value => value !== undefined);
  for (const value of supplied) if (!Array.isArray(value) || value.some(call => !record(call)))
    fail('tool_calls_invalid', 'Summary tool calls must be an array of objects');
  if (supplied.some(value => !isDeepStrictEqual(value, supplied[0])))
    fail('tool_calls_ambiguous', 'Outer and nested summary tool call captures disagree');
  // extractResult() collects calls from the entire AgentState transcript. A
  // summary cannot establish which calls happened in the current turn.
  return supplied[0]?.length ? { type: 'summary_tool_calls', scope: 'unverified', toolCalls: clone(supplied[0]) } : undefined;
}

function phaseToolEvents(phases) {
  if (phases === undefined) return [];
  if (!Array.isArray(phases)) fail('tool_events_invalid', 'Presentation phases must be an array');
  return phases.flatMap(phase => {
    if (!record(phase) || phase.steps !== undefined && (!Array.isArray(phase.steps) || phase.steps.some(step => !record(step))))
      fail('tool_events_invalid', 'Presentation tool steps must be an array of objects');
    return (phase.steps ?? []).map(step => ({ type: 'step_upsert',
      ...(phase.phaseId !== undefined ? { phaseId: phase.phaseId } : {}), step: clone(step) }));
  });
}

function withPresentationTools(events, messages) {
  const result = clone(events ?? []);
  for (const message of messages) {
    if (message.role !== 'assistant') continue;
    for (const event of phaseToolEvents(message.metadata?.presentation?.phases)) {
      const latest = [...result].reverse().find(item => item.type === 'step_upsert'
        && typeof event.step.id === 'string' && item.step?.id === event.step.id && item.phaseId === event.phaseId);
      if (latest && !isDeepStrictEqual(latest.step, event.step))
        fail('tool_events_ambiguous', 'Presentation and captured final tool step disagree');
      if (!latest) result.push(event);
    }
  }
  return result;
}

function parseStream(text) {
  const events = [];
  if (/^data:/m.test(text)) {
    for (const frame of text.replace(/\r\n/g, '\n').split(/\n\n+/)) {
      const data = frame.split('\n').filter(line => line.startsWith('data:')).map(line => line.slice(5).trimStart()).join('\n');
      // HTTP [DONE] only closes the transport: upstream also emits it after
      // errors and human-in-the-loop interrupts. It is not graph completion.
      if (data) events.push(data === '[DONE]' ? { type: '__transport_done' } : JSON.parse(data));
    }
  } else {
    for (const line of text.split(/\r?\n/)) if (line.trim()) events.push(JSON.parse(line));
  }
  return events;
}

function stateFromEvents(events) {
  const state = { messages: [] };
  const toolEvents = [];
  const artifacts = new Map(), artifactIds = new Set();
  let response = '', done = false, transportDone = false, presentationComplete = false, started = false, waiting;
  if (!events.length) fail('stream_incomplete', 'No stream events were captured');
  for (const event of events) {
    if (!record(event) || typeof event.type !== 'string') fail('stream_invalid', 'Stream events require an object and type');
    if (['error', 'presentation_error', 'failure', 'failed', 'turn.failed'].includes(event.type))
      fail('turn_failed', String(event.error?.message ?? event.error ?? event.message ?? 'Stream failed'));
    if (transportDone) fail('stream_invalid', 'Events follow the transport terminator');
    if (event.type === '__transport_done') { transportDone = true; continue; }
    if (done) fail('stream_invalid', 'Events follow graph completion; capture each turn separately');
    if (event.type === 'start') {
      if (started || waiting) fail('stream_invalid', 'Multiple starts or a resumed interaction require separate turn captures');
      started = true;
    }
    if (event.type === 'done') {
      if (waiting) fail('stream_invalid', 'A paused interaction cannot also declare graph completion');
      done = true; continue;
    }
    if (event.type === 'presentation_complete') {
      if (presentationComplete || waiting) fail('stream_invalid', 'Conflicting or duplicate presentation completion');
      presentationComplete = true; continue;
    }
    if (presentationComplete) fail('stream_invalid', 'Output follows presentation completion');
    // A later work/result event cannot borrow an earlier interruption marker.
    waiting = undefined;
    if (event.type === 'artifact_payload_sync') {
      const field = { model: 'model', analysis: 'analysisResult', report: 'report' }[event.artifact];
      if (field && event.invalidated === true) {
        state[field] = null;
        artifacts.delete(event.artifact);
        if (event.artifact === 'analysis') { artifacts.delete('report'); state.report = null; }
      }
      else if (event.artifact === 'model' && record(event.model)) state.model = event.model;
      else if (event.artifact === 'analysis' && record(event.latestResult?.analysis)) state.analysisResult = event.latestResult.analysis;
      else if (event.artifact === 'report' && record(event.latestResult?.report)) state.report = event.latestResult.report;
      if (own(event, 'artifactId')) {
        const payload = event.artifact === 'model' ? event.model : event.latestResult?.[event.artifact];
        if (!field || event.invalidated === true || typeof event.artifactId !== 'string' || !event.artifactId
          || artifactIds.has(event.artifactId) || !record(payload))
          fail('artifact_reference_invalid', 'Artifact IDs require a unique captured payload');
        artifactIds.add(event.artifactId);
        artifacts.set(event.artifact, { id: event.artifactId, value: state[field] });
      } else if (field) artifacts.delete(event.artifact);
    } else if (event.type === 'result' && record(event.content)) {
      const value = { ...event.content };
      assertCaptureStatus(value, 'Stream result');
      if (own(value, 'artifactReferences')) {
        if (!record(value.artifactReferences)) fail('artifact_reference_invalid', 'Artifact references must be a named map');
        for (const [kind, id] of Object.entries(value.artifactReferences)) {
          const artifact = artifacts.get(kind);
          if (!['model', 'analysis', 'report'].includes(kind) || own(value, kind) || !artifact || artifact.id !== id)
            fail('artifact_reference_invalid', 'Result references a missing, stale or conflicting artifact');
          value[kind] = artifact.value;
        }
      }
      artifacts.clear();
      const summary = summaryToolEvent(value.toolCalls);
      if (summary) toolEvents.push(summary);
      if (own(value, 'model')) state.model = value.model;
      if (own(value, 'analysis')) state.analysisResult = value.analysis;
      if (own(value, 'report')) state.report = value.report;
      if (typeof value.response === 'string' || Array.isArray(value.response)) response = value.response;
    } else if (event.type === 'summary_replace' && typeof event.summaryText === 'string') response = event.summaryText;
    else if (event.type === 'interaction_update') {
      if (!record(event.content)) fail('stream_invalid', 'Interaction content is missing');
      state.interaction = clone(event.content);
      if (interruptedInteraction(event.content)) {
        waiting = event.content;
        response = event.content.questions.map(question => question.question).join('\n');
      } else if (event.content.resumeRequired === true || event.content.conversationStage === 'awaiting_user_input') {
        fail('stream_invalid', 'Interrupted clarification requires explicit resume state and concrete questions');
      }
    } else if (event.type === 'step_upsert') {
      if (!record(event.step)) fail('stream_invalid', 'Tool step is missing');
      toolEvents.push(clone(event));
    } else if (event.type === 'presentation_init') {
      assertCaptureStatus(event.presentation, 'Stream presentation');
      toolEvents.push(...phaseToolEvents(event.presentation?.phases));
    } else if (event.type === 'phase_upsert') {
      toolEvents.push(...phaseToolEvents([event.phase]));
    } else if (!['start', 'token', 'artifact_upsert'].includes(event.type)) {
      fail('stream_invalid', `Unsupported or malformed stream event: ${event.type}`);
    }
  }
  if (!done && !waiting) fail('stream_incomplete', 'Stream ended without graph completion or an explicit clarification interrupt');
  if (waiting) Object.assign(state, { waitingForReply: true, resumeRequired: true, conversationStage: waiting.conversationStage });
  if (response) state.messages.push({ role: 'assistant', content: response });
  return { state, toolEvents, streamStatus: waiting ? 'waiting' : 'completed' };
}

function archiveToRun(archive) {
  if (!record(archive.request) || !record(archive.results)) return archive;
  const selected = archive.results[archive.selectedResultKey];
  if (!record(selected) || !physicalModel(archive.request.model)) throw new Error('structureclaw_archive_invalid');
  if (archive.modelHash !== modelFingerprint(archive.request.model)) throw new Error('structureclaw_archive_model_hash_mismatch');
  for (const result of Object.values(archive.results)) {
    if (!record(result) || result.meta?.runId !== archive.runId || result.meta?.modelHash !== archive.modelHash
      || result.meta?.settingsHash !== archive.settingsHash) throw new Error('structureclaw_archive_result_binding_mismatch');
  }
  return { ...selected, runId: archive.runId, requestId: archive.requestId, requestHash: archive.requestHash,
    modelSnapshot: archive.request.model, results: archive.results, selectedResultKey: archive.selectedResultKey,
    success: archive.success, executionStatus: archive.executionStatus, capabilityStatus: archive.capabilityStatus,
    meta: { ...selected.meta, startedAt: archive.startedAt, completedAt: archive.completedAt,
      resultCount: Object.keys(archive.results).length } };
}

function readArchive(runsRoot, runId) {
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(runId)) throw new Error('structureclaw_run_id_invalid');
  const root = fs.realpathSync(runsRoot);
  const candidates = ['run.json.gz', 'run.json'].map(name => path.join(root, runId, name)).filter(file => fs.existsSync(file));
  if (!candidates.length) return undefined;
  if (candidates.length !== 1) throw new Error('structureclaw_archive_ambiguous');
  const file = fs.realpathSync(candidates[0]);
  if (!file.startsWith(root + path.sep)) throw new Error('structureclaw_archive_outside_root');
  const bytes = fs.readFileSync(file), text = (file.endsWith('.gz') ? zlib.gunzipSync(bytes) : bytes).toString('utf8');
  const archive = JSON.parse(text);
  if (archive.runId !== runId) throw new Error('structureclaw_archive_run_id_mismatch');
  return { run: archiveToRun(archive), path: file, sha256: digest(bytes) };
}

// Chat removes only these audit documents and replaces sample provenance with
// locators. Restore from the identified archive, then compare every retained
// value so an archive cannot silently repair a modified candidate response.
const CHAT_AUDIT_FIELDS = ['pkpm_detailed', 'nativeContext', 'reactionSource', 'reactionObjectSources',
  'boundaryDisplacementSource', 'modelProjection', 'nativeDesignContext'];

function restoreChatData(value, original, runId, resultKey, resultKeys) {
  if (!record(value) || !record(original)) fail('archive_projection_mismatch', 'Projected result data is missing');
  const restored = clone(value);
  for (const key of CHAT_AUDIT_FIELDS) if (!own(restored, key) && own(original, key)) restored[key] = clone(original[key]);
  const members = restored.memberResponses;
  if (Array.isArray(members)) {
    const represented = new Set(members.filter(member => record(member) && Array.isArray(member.samples) && member.samples.length)
      .map(member => member.id));
    if (!own(restored, 'memberStations') && record(original.memberStations)
      && Object.keys(original.memberStations).every(id => represented.has(id))) restored.memberStations = clone(original.memberStations);
    for (const member of members) if (record(member) && Array.isArray(member.samples)) {
      const sourceMember = original.memberResponses?.find(item => item.id === member.id);
      member.samples.forEach((sample, sampleIndex) => {
        if (sample?.source?.kind !== 'run-member-sample') return;
        const expected = { kind: 'run-member-sample', runId, resultKey, memberId: member.id, sampleIndex };
        if (!isDeepStrictEqual(sample.source, expected) || !own(sourceMember?.samples?.[sampleIndex], 'source'))
          fail('archive_projection_mismatch', 'Member sample locator differs from its archive');
        sample.source = clone(sourceMember.samples[sampleIndex].source);
      });
    }
  }
  if (record(original.caseResults)) {
    const cases = Object.keys(original.caseResults);
    if (!own(restored, 'caseResults') && cases.length && cases.every(id => resultKeys.has(`case:${id}`)))
      restored.caseResults = clone(original.caseResults);
    else if (record(restored.caseResults)) for (const [key, data] of Object.entries(restored.caseResults)) {
      if (record(data)) restored.caseResults[key] = restoreChatData(data, original.caseResults[key], runId, resultKey, new Set());
    }
  }
  if (!isDeepStrictEqual(restored, original)) fail('archive_projection_mismatch', 'Chat result differs from the identified archive');
  return restored;
}

function restoreChatAnalysis(value, archive, model) {
  if (!record(value?.artifactReference)) return value;
  if (value.artifactReference.kind !== 'analysis-run' || value.artifactReference.runId !== value.runId
    || value.runId !== archive.runId || model && modelFingerprint(model) !== modelFingerprint(archive.modelSnapshot)
    || value.modelSnapshot && modelFingerprint(value.modelSnapshot) !== modelFingerprint(archive.modelSnapshot))
    fail('archive_projection_mismatch', 'Chat artifact identity or physical model differs from its archive');
  if (!record(value.results) || !record(archive.results)
    || !isDeepStrictEqual(Object.keys(value.results).sort(), Object.keys(archive.results).sort()))
    fail('archive_projection_mismatch', 'Chat result selections differ from their archive');
  const result = clone(value), keys = new Set(Object.keys(archive.results));
  for (const [key, entry] of Object.entries(result.results)) {
    const original = archive.results[key];
    if (!record(entry) || !record(original)) fail('archive_projection_mismatch', 'Invalid chat result entry');
    if (record(entry.data)) entry.data = restoreChatData(entry.data, original.data, result.runId, key, keys);
    if (!isDeepStrictEqual(entry, original)) fail('archive_projection_mismatch', 'Chat result metadata differs from its archive');
  }
  if (own(result, 'selectedDataReference')) {
    if (!isDeepStrictEqual(result.selectedDataReference, { resultKey: result.selectedResultKey })
      || !record(result.results[result.selectedResultKey]?.data) || own(result, 'data'))
      fail('archive_projection_mismatch', 'Selected data reference is missing or conflicting');
    result.data = clone(result.results[result.selectedResultKey].data);
    delete result.selectedDataReference;
  } else if (record(result.data)) {
    const selected = archive.results[result.selectedResultKey];
    result.data = restoreChatData(result.data, selected?.data, result.runId, result.selectedResultKey, keys);
  }
  delete result.artifactReference;
  return result;
}

function extractOne(value, options, warnings, archives) {
  let state, format, toolEvents, streamStatus, latestToolCalls;
  if (record(value)) assertCaptureStatus(value, 'Capture');
  if (Array.isArray(value) || record(value) && typeof value.type === 'string') {
    ({ state, toolEvents, streamStatus } = stateFromEvents(Array.isArray(value) ? value : [value])); format = 'stream';
  }
  else if (!record(value)) throw new Error('structureclaw_result_invalid');
  else if (record(value.state)) { state = value.state; format = 'state'; }
  else if (record(value.snapshots) || record(value.session)) {
    const snapshots = value.snapshots ?? {};
    if (snapshots.staleStructuralData === true) throw new Error('structureclaw_stale_snapshot');
    const latest = snapshots.latestResult ?? value.latestResult ?? {};
    latestToolCalls = latest.toolCalls;
    const session = value.session ?? {};
    assertCaptureStatus(latest, 'Latest result');
    assertCaptureStatus(session.runtime, 'Conversation runtime');
    state = { messages: normalizeMessages(value.messages),
      ...(own(session, 'modelRevision') ? { modelRevision: session.modelRevision } : {}),
      ...(own(session, 'modelPending') ? { modelPending: session.modelPending } : {}) };
    const model = session.model ?? latest.model;
    if (model !== undefined) state.model = model;
    if (own(latest, 'analysis')) state.analysisResult = latest.analysis;
    if (own(latest, 'report')) state.report = latest.report;
    if (record(session.draft)) state.draftState = session.draft;
    if (record(session.interaction)) state.interaction = clone(session.interaction);
    if (session.runtime?.waitingForReply === true) {
      state.waitingForReply = true;
      state.question = session.runtime.question;
      state.options = clone(session.runtime.options ?? []);
    }
    if (!state.messages.length && typeof latest.response === 'string') state.messages = [{ role: 'assistant', content: latest.response }];
    if (!state.model && physicalModel(snapshots.modelSnapshot)) state.model = snapshots.modelSnapshot;
    if (!state.model && snapshots.modelSnapshot) warnings.push('Visualization snapshots omit physical model inputs; supply session.model or a full AgentState.');
    const currentRun = session.runtime?.analysis;
    if (currentRun?.current === false) state.analysisResult = null;
    if (session.runtime?.report?.current === false) state.report = null;
    if (!own(state, 'analysisResult') && currentRun?.current === true && typeof currentRun.runId === 'string' && options.runsRoot) {
      const archive = readArchive(options.runsRoot, currentRun.runId);
      if (archive) { state.analysisResult = archive.run; archives.push({ path: archive.path, sha256: archive.sha256, runId: currentRun.runId }); }
    }
    format = 'conversation';
  } else if (record(value.request) && record(value.results) || record(value.modelSnapshot) && record(value.results)) {
    const analysis = archiveToRun(value); state = { model: analysis.modelSnapshot, analysisResult: analysis, messages: [] }; format = 'analysis-run';
  } else if (record(value.latestResult)) {
    const latest = value.latestResult;
    latestToolCalls = latest.toolCalls;
    assertCaptureStatus(latest, 'Latest result');
    state = { ...value, model: value.model ?? latest.model, analysisResult: latest.analysis,
      report: latest.report, messages: value.messages ?? (typeof latest.response === 'string' ? [{ role: 'assistant', content: latest.response }] : []) };
    format = 'latest-result';
  } else if (own(value, 'analysis') || typeof value.response === 'string') {
    state = { ...value, ...(own(value, 'analysis') ? { analysisResult: value.analysis } : {}),
      messages: value.messages ?? [{ role: 'assistant', content: value.response ?? '' }] }; format = 'agent-result';
  } else { state = value; format = 'state'; }
  toolEvents = normalizeToolEvents(toolEvents, value?.toolEvents, state.toolEvents);
  const summary = summaryToolEvent(value?.toolCalls, state.toolCalls, latestToolCalls);
  if (summary) {
    toolEvents = [...(toolEvents ?? []), summary];
    warnings.push('Summary tool calls may cover earlier turns; their scope requires independent behavior review.');
  }
  state = clone({ ...state, messages: normalizeMessages(state.messages) });
  delete state.toolEvents;
  delete state.toolCalls;
  assertCaptureStatus(state, 'Agent state');
  const lastAssistant = [...state.messages].reverse().find(message => message.role === 'assistant');
  assertCaptureStatus(lastAssistant?.metadata, 'Latest assistant metadata');
  const presentation = lastAssistant?.metadata?.presentation;
  assertCaptureStatus(presentation, 'Latest assistant presentation');
  if (presentation?.status === 'streaming' && state.waitingForReply !== true)
    fail('turn_incomplete', 'Latest assistant presentation is still streaming');
  if (state.model && !physicalModel(state.model)) throw new Error('structureclaw_physical_model_required');
  if (!state.model && physicalModel(state.analysisResult?.modelSnapshot)) state.model = state.analysisResult.modelSnapshot;
  const runIds = new Set([...Object.keys(state.analysisRuns ?? {}), state.analysisResult?.runId].filter(Boolean));
  if (options.runsRoot) for (const id of runIds) {
    const archive = readArchive(options.runsRoot, id);
    if (archive) {
      if (state.analysisResult?.runId === id) state.analysisResult = restoreChatAnalysis(state.analysisResult, archive.run, state.model);
      const saved = state.analysisRuns?.[id];
      state.analysisRuns = { ...state.analysisRuns, [id]: saved ? restoreChatAnalysis(saved, archive.run) : archive.run };
      archives.push({ path: archive.path, sha256: archive.sha256, runId: id });
    } else warnings.push(`Analysis archive unavailable: ${id}`);
  }
  if (state.analysisResult?.artifactReference) warnings.push('Chat analysis is projected; supply --runs-root to restore original audit documents and sample provenance.');
  for (const result of Object.values(state.analysisResult?.results ?? {})) {
    const execution = result.data?.execution ?? result.execution ?? result.meta?.execution;
    if (!execution?.artifacts) warnings.push(`Native solver receipt unavailable for ${result.selection?.key ?? result.selection?.id ?? 'selected result'}.`);
  }
  if (!state.messages.length) warnings.push('No assistant response was supplied; an analysis archive alone does not establish answer or report delivery.');
  return { state, format, toolEvents, streamStatus };
}

/** Import actual emitted fields. Case/state/source bindings belong to the benchmark capture context. */
function extractStructureClaw(value, options = {}) {
  if (typeof value === 'string' || Buffer.isBuffer(value)) {
    const text = value.toString();
    try { value = JSON.parse(text); } catch { value = parseStream(text); }
  }
  const warnings = [], archives = [];
  const snapshots = Array.isArray(value) && value.length > 0 && value.every(item => record(item)
    && ['state', 'model', 'messages', 'analysisResult', 'session', 'snapshots'].some(key => own(item, key))
    && !['artifact_payload_sync', 'result'].includes(item.type));
  const inputs = record(value) && Array.isArray(value.turns) ? value.turns : snapshots ? value : [value];
  const formats = new Set(), streamStatuses = [];
  let previousMessages = [];
  const turns = inputs.map((input, index) => {
    const extracted = extractOne(input, options, warnings, archives); formats.add(extracted.format);
    if (extracted.streamStatus) streamStatuses.push({ turn: index + 1, status: extracted.streamStatus });
    // Each SSE capture contains only this turn's delivered answer. Saved states
    // and conversations already own their history: never rewrite their prefix.
    if (extracted.format === 'stream') extracted.state.messages = [...clone(previousMessages), ...extracted.state.messages];
    const messages = extracted.state.messages;
    const hasPrefix = messages.length >= previousMessages.length
      && previousMessages.every((message, offset) => isDeepStrictEqual(message, messages[offset]));
    if (!hasPrefix) fail('transcript_invalid', 'Saved snapshots must retain the cumulative message prefix');
    const toolEvents = withPresentationTools(extracted.toolEvents, messages.slice(previousMessages.length));
    previousMessages = clone(messages);
    const turnId = options.turnIds?.[index] ?? input?.turnId;
    return { ...(turnId ? { turnId } : {}), state: extracted.state,
      ...(toolEvents.length || extracted.toolEvents !== undefined ? { toolEvents } : {}),
      ...(Array.isArray(input?.figures) ? { figures: clone(input.figures) } : {}),
      ...(record(input?.state) && record(input?.artifacts) ? { artifacts: clone(input.artifacts) } : {}) };
  });
  return { turns, source: { adapter: 'structureclaw', compatibility: UPSTREAM, format: [...formats].join(','),
    warnings: [...new Set(warnings)], archives: [...new Map(archives.map(item => [item.path, item])).values()],
    ...(streamStatuses.length ? { streamStatuses } : {}) } };
}

/** Reproduce native canonical payloads and accept only bytes matching the recorded SHA256. No solver is run. */
function reconstructOpenSeesArtifacts(run, options = {}) {
  const helper = path.join(__dirname, '..', 'scripts', 'research300', 'reconstruct_structureclaw.py');
  const request = { run, structureclawRoot: options.structureclawRoot, captureRoot: options.captureRoot };
  const result = spawnSync(options.pythonBin ?? 'python3', [helper], { input: JSON.stringify(request), encoding: 'utf8', maxBuffer: 128 * 1024 * 1024 });
  if (result.error || result.status !== 0) return { selectionArtifacts: {}, diagnostics: [result.error?.message || result.stderr?.trim() || 'StructureClaw artifact reconstruction failed'] };
  const response = JSON.parse(result.stdout), selectionArtifacts = {};
  if (options.outputRoot) {
    fs.mkdirSync(options.outputRoot, { recursive: true });
    const root = fs.realpathSync(options.outputRoot);
    for (const [key, entry] of Object.entries(response.selections ?? {})) {
      const paths = {};
      for (const [name, data] of Object.entries(entry.payloads ?? {})) {
        const bytes = Buffer.from(data.base64, 'base64');
        if (digest(bytes) !== data.sha256) throw new Error('structureclaw_reconstructed_artifact_corrupt');
        const relative = path.join('native-artifacts', data.sha256 + '.json');
        const file = path.join(root, relative); fs.mkdirSync(path.dirname(file), { recursive: true });
        if (!fs.realpathSync(path.dirname(file)).startsWith(root + path.sep)) throw new Error('structureclaw_artifact_outside_root');
        if (fs.existsSync(file) && !fs.realpathSync(file).startsWith(root + path.sep)) throw new Error('structureclaw_artifact_outside_root');
        if (fs.existsSync(file)) { if (!fs.readFileSync(file).equals(bytes)) throw new Error('structureclaw_artifact_collision'); }
        else fs.writeFileSync(file, bytes, { flag: 'wx' });
        paths[name] = relative;
      }
      if (Object.keys(paths).length) selectionArtifacts[key] = paths;
    }
  }
  return { selectionArtifacts, selections: response.selections, diagnostics: response.diagnostics ?? [], sources: response.sources ?? [] };
}
module.exports = { extractStructureClaw, reconstructOpenSeesArtifacts, normalizeMessages, archiveToRun, UPSTREAM };
