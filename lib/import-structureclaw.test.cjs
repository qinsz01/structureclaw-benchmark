'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const zlib = require('node:zlib');
const { createHash } = require('node:crypto');
const { spawnSync } = require('node:child_process');
const { extractStructureClaw, reconstructOpenSeesArtifacts } = require('./import-structureclaw.cjs');
const { modelFingerprint } = require('./analysis-evidence.cjs');
const runId = '23bfe7dc-195f-4a48-835e-123456789abc';
const model = { schema_version: '2.2.0', unit_system: 'SI', coordinate_system: { dimension: '2d' },
  nodes: [{ id: 'N1', x: 0, y: 0, z: 0 }], elements: [], materials: [], sections: [] };
function run() {
  return { runId, modelSnapshot: structuredClone(model), selectedResultKey: 'case:D', results: {
    'case:D': { success: true, selection: { key: 'case:D', kind: 'case', id: 'D' },
      data: { reactions: { N1: { fz: 10 } } }, meta: { runId, modelHash: modelFingerprint(model), settingsHash: 'settings' } },
  } };
}
function temp(t) { const folder = fs.mkdtempSync(path.join(os.tmpdir(), 'sclaw-import-')); t.after(() => fs.rmSync(folder, { recursive: true, force: true })); return folder; }
function saveArchive(root, value = run()) {
  const archive = { ...value, modelSnapshot: undefined, request: { model }, modelHash: modelFingerprint(model), settingsHash: 'settings' };
  fs.mkdirSync(path.join(root, runId), { recursive: true });
  fs.writeFileSync(path.join(root, runId, 'run.json.gz'), zlib.gzipSync(JSON.stringify(archive)));
  return archive;
}

test('full AgentState preserves physical data and normalizes LangChain messages without inventing benchmark bindings', () => {
  const value = { model, analysisResult: run(), resultQuantities: { q1: { value: 10 } }, messages: [
    { lc: 1, type: 'constructor', id: ['langchain_core', 'messages', 'HumanMessage'], kwargs: { content: 'Analyze' } },
    { lc: 1, type: 'constructor', id: ['langchain_core', 'messages', 'AIMessage'], kwargs: { content: 'Reaction 10 kN', tool_calls: [{ name: 'query_results' }] } },
  ] };
  const before = JSON.stringify(value), result = extractStructureClaw({ state: value }, { caseId: 'STD-001', turnIds: ['t1'] });
  assert.equal(result.turns[0].turnId, 't1');
  assert.equal(result.turns[0].state.messages[1].role, 'assistant');
  assert.equal(result.turns[0].state.messages[1].content, 'Reaction 10 kN');
  assert.equal(result.turns[0].state.resultQuantities.q1.value, 10);
  assert.equal(result.turns[0].state.analysisResult.results['case:D'].meta.sourceHash, undefined);
  assert.equal(JSON.stringify(value), before);
});

test('conversation imports physical session model and full latestResult, never visualization-only geometry', () => {
  const value = { session: { model, modelRevision: 4, modelPending: false }, snapshots: {
    modelSnapshot: { nodes: [{ position: { x: 0, y: 0, z: 0 } }] }, latestResult: { analysis: run(), report: { markdown: 'Report' } } },
    messages: [{ role: 'user', content: 'Analyze' }, { role: 'assistant', content: 'Done' }] };
  const state = extractStructureClaw(value).turns[0].state;
  assert.deepEqual(state.model, model); assert.equal(state.modelRevision, 4); assert.equal(state.report.markdown, 'Report');
  const missing = extractStructureClaw({ snapshots: { modelSnapshot: value.snapshots.modelSnapshot } });
  assert.equal(missing.turns[0].state.model, undefined);
  assert.match(missing.source.warnings.join(' '), /Visualization/);
  assert.throws(() => extractStructureClaw({ snapshots: { staleStructuralData: true } }), /stale_snapshot/);
  const pending = extractStructureClaw({ ...value, session: { ...value.session, runtime: {
    analysis: { current: false, runId }, report: { current: false },
  } } }).turns[0].state;
  assert.equal(pending.analysisResult, null); assert.equal(pending.report, null);
});

test('SSE applies artifact invalidations and takes the final response without reviving stale runs', () => {
  const events = [{ type: 'artifact_payload_sync', artifact: 'model', model },
    { type: 'artifact_payload_sync', artifact: 'analysis', latestResult: { analysis: run() } },
    { type: 'result', content: { response: 'Old answer' } },
    { type: 'artifact_payload_sync', artifact: 'analysis', invalidated: true },
    { type: 'artifact_payload_sync', artifact: 'report', invalidated: true },
    { type: 'result', content: { response: 'Please provide the missing load' } }, { type: 'done' }];
  const text = events.map(event => `data: ${JSON.stringify(event)}\n\n`).join('');
  const state = extractStructureClaw(text).turns[0].state;
  assert.deepEqual(state.model, model); assert.equal(state.analysisResult, null); assert.equal(state.report, null);
  assert.equal(state.messages[0].content, 'Please provide the missing load');
});

test('current chat SSE resolves deduplicated artifacts only from the latest captured payloads', () => {
  const analysis = run(), report = { markdown: 'Delivered report' };
  const events = [
    { type: 'artifact_payload_sync', artifact: 'model', artifactId: 'model:1', model },
    { type: 'artifact_payload_sync', artifact: 'analysis', artifactId: 'analysis:2', latestResult: { analysis } },
    { type: 'artifact_payload_sync', artifact: 'report', artifactId: 'report:3', latestResult: { report } },
    { type: 'result', content: { response: 'Done', artifactReferences: { model: 'model:1', analysis: 'analysis:2', report: 'report:3' } } },
    { type: 'done' },
  ];
  const before = JSON.stringify(events), state = extractStructureClaw(events).turns[0].state;
  assert.deepEqual(state.model, model); assert.deepEqual(state.analysisResult, analysis); assert.deepEqual(state.report, report);
  assert.equal(JSON.stringify(events), before);
  const replace = edit => { const changed = structuredClone(events); edit(changed); return changed; };
  for (const changed of [
    events.slice(1),
    replace(e => { e[3].content.artifactReferences.analysis = 'analysis:missing'; }),
    replace(e => { e[3].content.analysis = analysis; }),
    replace(e => { e[2].artifactId = 'analysis:2'; }),
    replace(e => { e.splice(3, 0, { type: 'artifact_payload_sync', artifact: 'analysis', invalidated: true }); }),
    replace(e => { e.splice(3, 0, { type: 'result', content: { response: 'Consumed references' } }); }),
  ]) assert.throws(() => extractStructureClaw(changed), /artifact_reference_invalid/);
  const reportInvalidated = replace(e => {
    e.splice(3, 0, { type: 'artifact_payload_sync', artifact: 'analysis', invalidated: true });
    e[4].content.artifactReferences = { report: 'report:3' };
  });
  assert.throws(() => extractStructureClaw(reportInvalidated), /artifact_reference_invalid/);
});

function projectedRun() {
  const full = run(), data = full.results['case:D'].data;
  data.nativeContext = { engine: 'yjk', originalFileSha256: 'a'.repeat(64) };
  const source = { kind: 'native', file: 'original-result' };
  data.memberStations = { B1: [{ N: 10, source }] };
  data.memberResponses = [{ id: 'B1', state: 'native-stations', samples: [{ x: 0, N: 10, source }] }];
  const view = structuredClone(full), projected = view.results['case:D'].data;
  delete projected.nativeContext; delete projected.memberStations;
  projected.memberResponses[0].samples[0].source = { kind: 'run-member-sample', runId,
    resultKey: 'case:D', memberId: 'B1', sampleIndex: 0 };
  view.artifactReference = { kind: 'analysis-run', runId };
  view.selectedDataReference = { resultKey: 'case:D' };
  return { full, view };
}

test('projected chat restores original evidence from its exact archive without changing retained values', t => {
  const root = temp(t), { full, view } = projectedRun(); saveArchive(root, full);
  const input = { session: { model }, snapshots: { latestResult: { analysis: view } } }, before = JSON.stringify(input);
  const result = extractStructureClaw(input, { runsRoot: root }), state = result.turns[0].state;
  assert.deepEqual(state.analysisResult.results, full.results);
  assert.deepEqual(state.analysisResult.data, full.results['case:D'].data);
  assert.equal(state.analysisResult.artifactReference, undefined);
  assert.equal(state.analysisResult.selectedDataReference, undefined);
  assert.equal(result.source.archives.length, 1);
  assert.equal(JSON.stringify(input), before);
  assert.match(extractStructureClaw(input).source.warnings.join(' '), /projected.*--runs-root/);
});

test('archive hydration rejects modified numbers, provenance, selections, metadata and physical models', t => {
  const root = temp(t), { full, view } = projectedRun(); saveArchive(root, full);
  for (const edit of [
    v => { v.results['case:D'].data.reactions.N1.fz += 1; },
    v => { v.results['case:D'].data.memberResponses[0].samples[0].N += 1; },
    v => { v.results['case:D'].data.memberResponses[0].samples[0].source.sampleIndex = 1; },
    v => { v.results['case:D'].meta.settingsHash = 'other'; },
    v => { v.artifactReference.runId = 'other'; },
    v => { v.selectedDataReference.resultKey = 'case:L'; },
    v => { v.results['case:L'] = structuredClone(v.results['case:D']); },
    v => { delete v.results['case:D'].data.reactions; },
  ]) {
    const changed = structuredClone(view); edit(changed);
    assert.throws(() => extractStructureClaw({ model, analysisResult: changed }, { runsRoot: root }), /archive_projection_mismatch/);
  }
  const changedModel = structuredClone(model); changedModel.nodes[0].x = 1;
  assert.throws(() => extractStructureClaw({ model: changedModel, analysisResult: view }, { runsRoot: root }), /archive_projection_mismatch/);
});

const sse = (events, transportDone = false) => events.map(event => `data: ${JSON.stringify(event)}\n\n`).join('') + (transportDone ? 'data: [DONE]\n\n' : '');
const interrupt = () => ({ type: 'interaction_update', content: { resumeRequired: true,
  conversationStage: 'awaiting_user_input', questions: [{ question: 'Please specify the span.', label: 'Span' }],
  pending: { criticalMissing: ['span'] }, options: [{ label: '6 m', value: '6' }] } });

test('SSE distinguishes graph completion from the HTTP terminator', () => {
  const result = extractStructureClaw(sse([{ type: 'presentation_init', presentation: { status: 'streaming' } },
    { type: 'result', content: { response: 'Final answer', model } },
    { type: 'presentation_complete', completedAt: '2026-10-22T00:00:00Z' }, { type: 'done' }], true));
  assert.equal(result.turns[0].state.messages[0].content, 'Final answer');
  assert.deepEqual(result.source.streamStatuses, [{ turn: 1, status: 'completed' }]);
  for (const events of [[], [{ type: 'summary_replace', summaryText: 'Partial answer' }],
    [{ type: 'result', content: { response: 'Partial result', model } }],
    [{ type: 'presentation_complete', completedAt: '2026-10-22T00:00:00Z' }]]) {
    for (const terminated of [false, true]) assert.throws(() => extractStructureClaw(sse(events, terminated)), /stream_incomplete/);
  }
});

test('SSE failures cannot be erased by an answer, completion, or later retry', () => {
  for (const type of ['error', 'presentation_error', 'failure', 'failed', 'turn.failed']) {
    const failed = { type, message: 'Connection lost', error: 'Connection lost', retriable: true };
    assert.throws(() => extractStructureClaw(sse([{ type: 'result', content: { response: 'Old answer', model } }, failed,
      { type: 'result', content: { response: 'Later answer' } }, { type: 'done' }], true)), /turn_failed.*Connection lost/);
  }
  assert.throws(() => extractStructureClaw({ type: 'error', error: 'Failed standalone event' }), /turn_failed/);
  assert.throws(() => extractStructureClaw(sse([{ type: 'result', content: { success: false, response: 'Failed' } }, { type: 'done' }])), /turn_failed/);
  assert.throws(() => extractStructureClaw(sse([{ type: 'done' }, { type: 'result', content: { response: 'Second turn' } }])), /stream_invalid/);
  assert.throws(() => extractStructureClaw([{ type: 'start' }, { type: 'summary_replace', summaryText: 'Truncated first turn' },
    { type: 'start' }, { type: 'result', content: { response: 'Later turn' } }, { type: 'done' }]), /stream_invalid/);
});

test('explicit upstream clarification interrupts preserve questions, options, waiting state and actual tool activity', () => {
  const step = { type: 'step_upsert', phaseId: 'phase-analysis', step: { id: 'tool-1', tool: 'run_analysis', status: 'error', output: 'missing span' } };
  const events = [step, { type: 'summary_replace', summaryText: 'Interim response' }, interrupt()];
  for (const value of [events, sse(events), sse(events, true)]) {
    const result = extractStructureClaw(value), state = result.turns[0].state;
    assert.equal(state.waitingForReply, true); assert.equal(state.resumeRequired, true);
    assert.deepEqual(state.interaction, interrupt().content);
    assert.deepEqual(state.messages, [{ role: 'assistant', content: 'Please specify the span.' }]);
    assert.deepEqual(result.turns[0].toolEvents, [step]);
    assert.deepEqual(result.source.streamStatuses, [{ turn: 1, status: 'waiting' }]);
  }
  for (const bad of [ { ...interrupt().content, resumeRequired: false },
    { ...interrupt().content, questions: [] }, { ...interrupt().content, conversationStage: 'working' } ])
    assert.throws(() => extractStructureClaw([{ type: 'interaction_update', content: bad }]), /stream_invalid/);
  assert.throws(() => extractStructureClaw([interrupt(), { type: 'result', content: { response: 'Work resumed but unfinished' } }]), /stream_incomplete/);
  assert.throws(() => extractStructureClaw([interrupt(), { type: 'done' }]), /stream_invalid/);
  assert.throws(() => extractStructureClaw([interrupt(), { type: 'start' }, { type: 'done' }]), /stream_invalid/);
});

test('saved snapshots reject explicit failures and active streams while preserving a declared waiting conversation', () => {
  for (const value of [{ state: { model, status: 'failed' } }, { state: { model, error: 'Agent failed' } },
    { session: { model, runtime: { busy: true } } }, { snapshots: { latestResult: { success: false } } },
    ...['error', 'aborted', 'streaming'].map(status => ({ session: { model, runtime: { busy: false } },
      messages: [{ role: 'assistant', content: 'Partial answer', metadata: { presentation: { status } } }] }))])
    assert.throws(() => extractStructureClaw(value), /turn_failed|turn_incomplete/);
  const waiting = extractStructureClaw({ session: { model, interaction: { state: 'waiting', stage: 'model' },
    runtime: { busy: false, waitingForReply: true, question: 'Please specify the span.', options: [] } },
    messages: [{ role: 'assistant', content: 'Please specify the span.', metadata: { presentation: { status: 'streaming' } } }] });
  assert.equal(waiting.turns[0].state.waitingForReply, true);
  assert.equal(waiting.turns[0].state.interaction.state, 'waiting');
  assert.equal(waiting.turns[0].state.question, 'Please specify the span.');
});

test('explicit multiple turn snapshots retain scheduled IDs and supplied files', () => {
  const result = extractStructureClaw({ turns: [{ turnId: 't1', state: { messages: [] } },
    { turnId: 't2', state: { model, messages: [{ type: 'ai', content: 'Done' }] },
      artifacts: { [runId]: { normalizedInput: 'model.json' } }, figures: [{ path: 'figure.png' }] }] });
  assert.equal(result.turns.length, 2); assert.equal(result.turns[1].turnId, 't2');
  assert.equal(result.turns[1].artifacts[runId].normalizedInput, 'model.json');
  assert.equal(result.turns[1].figures[0].path, 'figure.png');
  const snapshots = extractStructureClaw([{ model, messages: [] }, { model, messages: [] }], { turnIds: ['t1', 't2'] });
  assert.deepEqual(snapshots.turns.map(turn => turn.turnId), ['t1', 't2']);
});

test('separate SSE turns accumulate delivered messages without replacing saved history', () => {
  const completed = text => [{ type: 'summary_replace', summaryText: text }, { type: 'done' }];
  const result = extractStructureClaw({ turns: [completed('A'), completed('A'), [interrupt()]] });
  assert.deepEqual(result.turns.map(turn => turn.state.messages.map(message => message.content)),
    [['A'], ['A', 'A'], ['A', 'A', 'Please specify the span.']]);
  assert.equal(result.turns[2].state.waitingForReply, true);
  const first = { role: 'assistant', content: 'A', metadata: { captured: true } };
  const second = { role: 'assistant', content: 'B' };
  const source = { turns: [{ state: { messages: [first] } }, { state: { messages: [first, second] } }, completed('C')] };
  const before = JSON.stringify(source), mixed = extractStructureClaw(source);
  assert.deepEqual(mixed.turns[1].state.messages, [first, second]);
  assert.deepEqual(mixed.turns[2].state.messages, [first, second, { role: 'assistant', content: 'C' }]);
  assert.equal(JSON.stringify(source), before);
  assert.throws(() => extractStructureClaw({ turns: [{ state: { messages: [first] } },
    { state: { messages: [second] } }] }), /transcript_invalid/);
});

test('nested tool events are promoted, validated and cannot disagree with outer captures', () => {
  const event = { type: 'step_upsert', step: { id: 'call-1', tool: 'run_analysis', status: 'failed' } };
  const state = { messages: [{ role: 'assistant', content: 'Please specify the span.' }], toolEvents: [event] };
  const before = JSON.stringify(state);
  for (const source of [state, { state }, { state, toolEvents: [event] }]) {
    const turn = extractStructureClaw(source).turns[0];
    assert.deepEqual(turn.toolEvents, [event]);
    assert.equal(Object.hasOwn(turn.state, 'toolEvents'), false);
  }
  assert.equal(JSON.stringify(state), before);
  assert.throws(() => extractStructureClaw({ state, toolEvents: [] }), /tool_events_ambiguous/);
  for (const toolEvents of [null, {}, 'events', [null], [1], [[]]]) {
    assert.throws(() => extractStructureClaw({ state: { ...state, toolEvents } }), /tool_events_invalid/);
    assert.throws(() => extractStructureClaw({ state: { messages: [] }, toolEvents }), /tool_events_invalid/);
  }
});

test('saved presentation tool steps bind current activity without reusing prior-turn attempts', () => {
  const { currentActivitySha256, currentResponseSha256 } = require('../scripts/run-research300.cjs');
  const { evaluateResearchTurn, activityFingerprint } = require('./research300-evaluation.cjs');
  const step = { id: 'analysis-1', phase: 'analysis', tool: 'run_analysis', status: 'error', args: { loadCaseId: 'D' } };
  const event = { type: 'step_upsert', phaseId: 'phase-analysis', step };
  const first = { role: 'assistant', content: 'Please specify the span.', metadata: { presentation: { status: 'done',
    phases: [{ phaseId: 'phase-analysis', phase: 'analysis', status: 'error', steps: [step] }] } } };
  const next = { role: 'assistant', content: 'Please specify the load.' };
  const result = extractStructureClaw({ turns: [
    { session: { runtime: { busy: false, waitingForReply: true } }, messages: [first], toolEvents: [] },
    { session: { runtime: { busy: false, waitingForReply: true } }, messages: [first, next] },
  ] });
  assert.deepEqual(result.turns[0].toolEvents, [event]);
  assert.deepEqual(result.turns[1].toolEvents ?? [], []);
  const turn = result.turns[0], hash = currentActivitySha256(turn.state.messages, 0, turn.toolEvents);
  assert.equal(hash, activityFingerprint(turn.state.messages, [event]));
  assert.notEqual(hash, currentActivitySha256(turn.state.messages, 0, []));
  const caseRecord = { contract: { evaluationProfile: 'engineering-v2.3', turns: [
    { id: 't1', state: null, expectation: 'clarify', unresolvedFields: ['span'] },
    { id: 't2', state: null, expectation: 'clarify', unresolvedFields: ['load'] },
  ] } };
  const evaluate = (candidate, index, boundary) => evaluateResearchTurn({ caseRecord, turnIndex: index, state: candidate.state,
    evidence: { sourceHash: 'a'.repeat(64), turnEvidence: { turnId: `t${index + 1}`, state: null,
      messageStartIndex: boundary, analysisRunIds: [], toolEvents: candidate.toolEvents ?? [],
      currentResponseSha256: currentResponseSha256(candidate.state.messages, boundary),
      activitySha256: currentActivitySha256(candidate.state.messages, boundary, candidate.toolEvents ?? []) } } });
  const attempted = evaluate(turn, 0, 0);
  assert.equal(attempted.status, 'agent_failure');
  assert.equal(attempted.metrics.find(metric => metric.metric === 'should_not_analyze').pass, false);
  const clean = evaluate(result.turns[1], 1, 1);
  assert.equal(clean.status, 'review_pending');
  assert.equal(clean.metrics.find(metric => metric.metric === 'should_not_analyze').pass, true);
  const explicit = extractStructureClaw({ messages: [first], toolEvents: [event] }).turns[0];
  assert.deepEqual(explicit.toolEvents, [event]);
  assert.throws(() => extractStructureClaw({ messages: [first], toolEvents: [{ ...event, step: { ...step, tool: 'query_model' } }] }),
    /tool_events_ambiguous/);
});

test('SSE presentation and phase snapshots retain their actual tool steps before a clarification interrupt', () => {
  const step = { id: 'analysis-1', tool: 'run_analysis', status: 'error' };
  const phase = { phaseId: 'phase-analysis', steps: [step] };
  for (const snapshot of [{ type: 'presentation_init', presentation: { status: 'streaming', phases: [phase] } },
    { type: 'phase_upsert', phase }]) {
    const turn = extractStructureClaw([snapshot, interrupt()]).turns[0];
    assert.equal(turn.state.waitingForReply, true);
    assert.deepEqual(turn.toolEvents, [{ type: 'step_upsert', phaseId: phase.phaseId, step }]);
  }
});

test('summary toolCalls remain unscoped review evidence and cannot be erased by wrappers or later summaries', () => {
  const { evaluateResearchTurn } = require('./research300-evaluation.cjs');
  const calls = [{ id: 'call-1', name: 'run_analysis', args: { loadCaseId: 'D' } }];
  const message = { role: 'assistant', content: 'Please specify the span.' };
  const expected = { type: 'summary_tool_calls', scope: 'unverified', toolCalls: calls };
  const state = { messages: [message], toolCalls: calls };
  for (const source of [state, { state }, { state, toolCalls: calls },
    { response: message.content, toolCalls: calls },
    { session: {}, snapshots: { latestResult: { response: message.content, toolCalls: calls } } },
    { latestResult: { response: message.content, toolCalls: calls } },
    [{ type: 'result', content: { response: message.content, toolCalls: calls } },
      { type: 'result', content: { response: message.content, toolCalls: [] } }, { type: 'done' }]]) {
    const before = JSON.stringify(source), turn = extractStructureClaw(source).turns[0];
    assert.deepEqual(turn.toolEvents, [expected]);
    assert.equal(Object.hasOwn(turn.state, 'toolCalls'), false);
    assert.equal(JSON.stringify(source), before);
    const result = evaluateResearchTurn({ state: turn.state,
      caseRecord: { contract: { evaluationProfile: 'engineering-v2.3', turns: [{ id: 't1', state: null, expectation: 'clarify' }] } },
      evidence: { turnEvidence: { turnId: 't1', state: null, messageStartIndex: 0, analysisRunIds: [], toolEvents: turn.toolEvents } } });
    assert.equal(result.status, 'review_pending');
    assert.equal(result.metrics.find(metric => metric.metric === 'should_not_analyze').status, 'review_pending');
  }
  assert.throws(() => extractStructureClaw({ state, toolCalls: [] }), /tool_calls_ambiguous/);
  assert.throws(() => extractStructureClaw({ latestResult: { toolCalls: calls }, toolCalls: [] }), /tool_calls_ambiguous/);
  for (const toolCalls of [null, {}, 'calls', [null], [1], [[]]]) {
    assert.throws(() => extractStructureClaw({ state: { ...state, toolCalls } }), /tool_calls_invalid/);
    assert.throws(() => extractStructureClaw({ state: { messages: [] }, toolCalls }), /tool_calls_invalid/);
    assert.throws(() => extractStructureClaw([{ type: 'result', content: { toolCalls } }, { type: 'done' }]), /tool_calls_invalid/);
  }
  assert.deepEqual(extractStructureClaw({ response: message.content, toolCalls: [] }).turns[0].toolEvents ?? [], []);
});

test('compressed archive attaches by the advertised immutable run ID and verifies model/result binding', t => {
  const root = temp(t), archive = saveArchive(root);
  const result = extractStructureClaw({ session: { model, runtime: { analysis: { current: true, runId } } } }, { runsRoot: root });
  assert.equal(result.turns[0].state.analysisResult.runId, runId); assert.equal(result.source.archives.length, 1);
  assert.equal(result.source.archives[0].sha256.length, 64);
  assert.deepEqual(extractStructureClaw(archive).turns[0].state.model, model);
  archive.results['case:D'].meta.modelHash = 'wrong';
  assert.throws(() => extractStructureClaw(archive), /result_binding/);
});

test('archive lookup rejects traversal, symlinks and ambiguous plain/compressed copies', t => {
  const root = temp(t); saveArchive(root);
  const state = { model, analysisResult: run(), messages: [] };
  fs.writeFileSync(path.join(root, runId, 'run.json'), '{}');
  assert.throws(() => extractStructureClaw(state, { runsRoot: root }), /archive_ambiguous/);
  fs.unlinkSync(path.join(root, runId, 'run.json'));
  assert.throws(() => extractStructureClaw({ ...state, analysisResult: { runId: '../escape' } }, { runsRoot: root }), /run_id_invalid/);
  const outside = temp(t); saveArchive(outside);
  fs.rmSync(path.join(root, runId), { recursive: true }); fs.symlinkSync(path.join(outside, runId), path.join(root, runId));
  assert.throws(() => extractStructureClaw(state, { runsRoot: root }), /outside_root/);
});

test('native canonical payloads are accepted only when each digest matches and original files stay untouched', t => {
  const root = temp(t), result = run(), data = result.results['case:D'].data;
  const canonical = value => {
    const child = spawnSync('python3', ['-c', 'import json,sys; print(json.dumps(json.load(sys.stdin),sort_keys=True,separators=(",",":"),ensure_ascii=False),end="")'], { input: JSON.stringify(value), encoding: 'utf8' });
    assert.equal(child.status, 0); return child.stdout;
  };
  const settings = { parameters: { loadCaseIds: ['D'] } };
  const payloads = { normalizedInput: model, settings, solverResponse: { reactions: data.reactions } };
  const hash = value => createHash('sha256').update(canonical(value)).digest('hex');
  data.execution = { solver: 'OpenSees', artifacts: { hashFormat: 'sha256:python-json-sort-keys-utf8-compact-v1',
    settings, solverResponseKeys: ['reactions'], ...Object.fromEntries(Object.entries(payloads).map(([key, value]) => [key + 'Sha256', hash(value)])) } };
  const before = JSON.stringify(result);
  const reconstructed = reconstructOpenSeesArtifacts(result, { outputRoot: root });
  assert.equal(reconstructed.selections['case:D'].complete, true);
  assert.deepEqual(reconstructed.diagnostics, []);
  for (const [key, file] of Object.entries(reconstructed.selectionArtifacts['case:D'])) assert.equal(fs.readFileSync(path.join(root, file), 'utf8'), canonical(payloads[key]));
  assert.equal(JSON.stringify(result), before);
  data.reactions.N1.fz = 999;
  const altered = reconstructOpenSeesArtifacts(result, { outputRoot: root });
  assert.equal(altered.selections['case:D'].complete, false);
  assert.equal(altered.selectionArtifacts['case:D'].solverResponse, undefined);
  assert.match(altered.diagnostics.join(' '), /solverResponse canonical bytes could not be reproduced/);
});

test('missing commercial execution receipt stays missing', t => {
  const value = run(); value.results['case:D'].data.nativeContext = { engine: 'pkpm', artifacts: [{ path: 'DATA.SAT', sha256: '0'.repeat(64) }] };
  const result = reconstructOpenSeesArtifacts(value, { outputRoot: temp(t) });
  assert.deepEqual(result.selectionArtifacts, {}); assert.match(result.diagnostics.join(' '), /receipt unavailable/);
});

test('transparent worker capture preserves float and negative-zero bytes through host JSON and rejects changed capture bytes', t => {
  const root = temp(t), runtime = path.join(root, 'analysis', 'runtime'), captureRoot = path.join(root, 'captures');
  fs.mkdirSync(path.join(runtime, 'opensees_shared'), { recursive: true });
  fs.writeFileSync(path.join(runtime, 'opensees_shared', 'evidence.py'), `import hashlib,json

def artifact_sha256(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()

def attach_execution_artifacts(result, model, parameters):
    settings={'parameters':parameters,'number':0.0}
    result['execution']={'solver':'OpenSees','solverVersion':'test','artifacts':{
      'hashFormat':'sha256:python-json-sort-keys-utf8-compact-v1',
      'normalizedInputSha256':artifact_sha256(model),
      'settingsSha256':artifact_sha256(settings),
      'solverResponseSha256':artifact_sha256({'reactions':result['reactions']}),
      'settings':settings,'solverResponseKeys':['reactions']}}
    return result
`);
  const worker = path.join(runtime, 'worker.py');
  fs.writeFileSync(worker, `import sys,json
from opensees_shared.evidence import attach_execution_artifacts
request=json.load(sys.stdin)['input']
result=attach_execution_artifacts({'reactions':{'A':{'fz':-0.0,'fx':10.0}}},request['model'],request['parameters'])
print(json.dumps({'ok':True,'data':result}))
`);
  const request = { action: 'analyze', input: { model, parameters: { loadCaseIds: ['D'] }, requestId: runId } };
  const wrapper = path.join(__dirname, '..', 'scripts/research300/capture_structureclaw_worker.py');
  const env = { ...process.env, SCLAW_BENCH_CAPTURE_ROOT: captureRoot }; delete env.SCLAW_BENCH_PYTHON;
  const direct = spawnSync('python3', [worker], { input: JSON.stringify(request), encoding: 'utf8' });
  const captured = spawnSync('python3', [wrapper, worker], { input: JSON.stringify(request), encoding: 'utf8', env });
  assert.equal(captured.status, 0, captured.stderr); assert.equal(captured.stdout, direct.stdout);
  const host = { modelSnapshot: model, requestId: runId, results: { 'case:D': { data: JSON.parse(captured.stdout).data } } };
  const lost = reconstructOpenSeesArtifacts(host);
  assert.equal(lost.selections['case:D'].complete, false);
  const restored = reconstructOpenSeesArtifacts(host, { captureRoot, outputRoot: path.join(root, 'artifacts') });
  assert.equal(restored.selections['case:D'].complete, true); assert.deepEqual(restored.diagnostics, []);
  assert.equal(restored.sources.length, 7);
  for (const source of restored.sources) assert.equal(createHash('sha256').update(fs.readFileSync(source.path)).digest('hex'), source.sha256);
  const responseFile = path.join(root, 'artifacts', restored.selectionArtifacts['case:D'].solverResponse);
  assert.match(fs.readFileSync(responseFile, 'utf8'), /"fz":-0\.0/);
  const stale = reconstructOpenSeesArtifacts({ ...host, requestId: 'other-request' }, { captureRoot });
  assert.equal(stale.selections['case:D'].complete, false);
  const folder = path.join(captureRoot, fs.readdirSync(captureRoot)[0]);
  const capture = JSON.parse(fs.readFileSync(path.join(folder, 'capture.json'), 'utf8'));
  fs.writeFileSync(path.join(folder, capture.receipts[0].artifacts.solverResponse), '{}');
  const altered = reconstructOpenSeesArtifacts(host, { captureRoot });
  assert.equal(altered.selections['case:D'].complete, false); assert.match(altered.diagnostics.join(' '), /SHA256 mismatch/);
});

test('AgentState artifact UI metadata is not mistaken for external solver file paths', () => {
  const imported = extractStructureClaw({ model, messages: [], artifacts: { model: { status: 'available' } } });
  assert.equal(imported.turns[0].artifacts, undefined);
  assert.deepEqual(imported.turns[0].state.artifacts, { model: { status: 'available' } });
});

test('direct executable worker capture selects the requested symlinked venv and its site packages', { skip: process.platform === 'win32' }, t => {
  const root = temp(t), venv = path.join(root, 'venv');
  const created = spawnSync('python3', ['-m', 'venv', '--without-pip', '--symlinks', venv], { encoding: 'utf8' });
  assert.equal(created.status, 0, created.stderr);
  const interpreter = path.join(venv, 'bin', 'python');
  const probe = spawnSync(interpreter, ['-c', 'import json,sys,sysconfig; print(json.dumps({"prefix":sys.prefix,"base":sys._base_executable,"purelib":sysconfig.get_path("purelib")}))'], { encoding: 'utf8' });
  assert.equal(probe.status, 0, probe.stderr);
  const info = JSON.parse(probe.stdout);
  assert.equal(fs.realpathSync(interpreter), fs.realpathSync(info.base));
  fs.writeFileSync(path.join(info.purelib, 'sclaw_environment_probe.py'), 'TOKEN="venv-only-package"\n');
  const runtime = path.join(root, 'analysis', 'runtime');
  fs.mkdirSync(path.join(runtime, 'opensees_shared'), { recursive: true });
  fs.writeFileSync(path.join(runtime, 'opensees_shared', 'evidence.py'), 'def artifact_sha256(value): return "unused"\ndef attach_execution_artifacts(*args): return args[0]\n');
  const worker = path.join(runtime, 'worker.py');
  fs.writeFileSync(worker, 'import json,sys,sclaw_environment_probe\nprint(json.dumps({"prefix":sys.prefix,"token":sclaw_environment_probe.TOKEN,"request":json.load(sys.stdin)}))\n');
  const wrapper = path.join(__dirname, '..', 'scripts/research300/capture_structureclaw_worker.py');
  // Mirror PythonWorkerRunner.spawn(analysis.pythonBin, [workerPath]). The
  // shebang starts the base interpreter, not the venv selected in this setting.
  const shebangDir = path.join(root, 'shebang-bin'); fs.mkdirSync(shebangDir);
  fs.symlinkSync(info.base, path.join(shebangDir, 'python3'));
  const env = { ...process.env, PATH: shebangDir + path.delimiter + process.env.PATH,
    SCLAW_BENCH_PYTHON: interpreter, SCLAW_BENCH_CAPTURE_ROOT: path.join(root, 'captures') };
  const result = spawnSync(wrapper, [worker], { input: '{"action":"probe"}', env, encoding: 'utf8', timeout: 10000 });
  assert.equal(result.status, 0, result.stderr || result.error?.message);
  assert.deepEqual(JSON.parse(result.stdout), { prefix: info.prefix, token: 'venv-only-package', request: { action: 'probe' } });
  const capture = path.join(env.SCLAW_BENCH_CAPTURE_ROOT, fs.readdirSync(env.SCLAW_BENCH_CAPTURE_ROOT)[0]);
  assert.equal(JSON.parse(fs.readFileSync(path.join(capture, 'capture.json'))).exitCode, 0);
  assert.equal(fs.readFileSync(path.join(capture, 'stdout.json'), 'utf8'), result.stdout);
});
