'use strict';

const { isDeepStrictEqual } = require('node:util');
const record = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const own = (value, key) => record(value) && Object.hasOwn(value, key);
const clone = value => structuredClone(value);

function fail(code, message) {
  throw Object.assign(new Error(message), { code: `codex_${code}` });
}

// JSON.parse accepts repeated keys. Reject them before choosing a transcript or
// model so two consumers cannot select different values from the same capture.
function parseJson(text, context) {
  let parsed;
  try { parsed = JSON.parse(text); } catch { fail('json_invalid', `${context} contains incomplete or invalid JSON`); }
  const containers = [];
  for (let index = 0; index < text.length; index++) {
    const char = text[index];
    if (char === '{') containers.push(new Set());
    else if (char === '[') containers.push(null);
    else if (char === '}' || char === ']') containers.pop();
    else if (char === '"') {
      const start = index++;
      while (text[index] !== '"') { if (text[index] === '\\') index++; index++; }
      let next = index + 1;
      while (/\s/.test(text[next] || 'x')) next++;
      if (text[next] === ':') {
        const key = JSON.parse(text.slice(start, index + 1)), keys = containers.at(-1);
        if (keys.has(key)) fail('json_duplicate_key', `${context} contains duplicate object key ${key}`);
        keys.add(key);
      }
    }
    if (containers.length > 64) fail('json_invalid', `${context} exceeds the supported JSON nesting depth`);
  }
  return parsed;
}

function parseInput(value) {
  if (Buffer.isBuffer(value)) {
    try { value = new TextDecoder('utf-8', { fatal: true }).decode(value); }
    catch { fail('output_invalid', 'Codex output must contain valid UTF-8'); }
  }
  if (typeof value !== 'string') return { value, format: Array.isArray(value) ? 'events' : 'structured' };
  const text = value.trim();
  if (!text) fail('output_empty', 'Codex output is empty');
  if (/^[{[]/.test(text)) {
    try {
      const parsed = parseJson(text, 'Codex output');
      return { value: parsed, format: Array.isArray(parsed) ? 'events' : 'last-message-json', answer: value };
    } catch (error) {
      if (error.code !== 'codex_json_invalid') throw error;
      const lines = text.split(/\r?\n/).filter(line => line.trim());
      if (lines.length < 2 || !lines.every(line => line.trim().startsWith('{'))) throw error;
      return { value: lines.map((line, index) => parseJson(line, `Codex JSONL line ${index + 1}`)), format: 'jsonl' };
    }
  }
  const fences = [...text.matchAll(/```json\s*\n?([\s\S]*?)```/gi)];
  if ([...text.matchAll(/```json\b/gi)].length !== fences.length) fail('json_invalid', 'Codex final JSON block is incomplete');
  if (fences.length > 1) fail('output_ambiguous', 'Codex output contains more than one JSON block');
  if (fences.length === 1) {
    const parsed = parseJson(fences[0][1], 'Codex final JSON block');
    if (!record(parsed)) fail('output_invalid', 'Codex final JSON block must contain an object');
    return { value: parsed, format: 'last-message-json', answer: value };
  }
  return { value: null, format: 'last-message-markdown', answer: value };
}

function retryableError(event) {
  // Codex rust-v0.163.0 exec's event_processor_with_jsonl_output.rs discards
  // ErrorNotification.willRetry and emits reconnect progress as type:error.
  // Recognize only its bounded retry/network-wait forms; completion is checked
  // separately. Capture wrappers may retain the original retry metadata.
  // A false or malformed retry flag must never be overridden by text matching.
  const message = event.error?.message ?? event.message;
  if (typeof message !== 'string' || !message.trim()) return false;
  const flags = ['willRetry', 'will_retry'].filter(key => own(event, key));
  if (flags.length) return flags.every(key => event[key] === true);
  const reconnect = /^Reconnecting\.\.\. (?:([1-9][0-9]*)\/([1-9][0-9]*)|waiting for network)(?: \([^\r\n]+\))?$/.exec(message);
  return reconnect !== null && (reconnect[1] === undefined
    || Number.isSafeInteger(Number(reconnect[1])) && Number.isSafeInteger(Number(reconnect[2]))
      && Number(reconnect[1]) <= Number(reconnect[2]));
}

function startupAdvisory(event) {
  const item=event.item;
  return event.type==='item.completed' && event.turn_id===undefined && event.turn===undefined
    && record(item) && typeof item.id==='string' && item.id.length>0 && item.type==='error'
    && Object.keys(item).every(key=>['id','type','message'].includes(key))
    && typeof item.message==='string'
    && /^Under-development features enabled: [a-z0-9_]+(?:, [a-z0-9_]+)*\. Under-development features are incomplete and may behave unpredictably\. To suppress this warning, set `suppress_unstable_features_warning = true` in [^\r\n]+\.toml\.$/.test(item.message);
}

function eventTurns(events, warnings) {
  if (!events.length) fail('events_empty', 'Codex event stream is empty');
  const turns = [], turnIds = new Set();
  let active,threadStarted=false;
  const startupItems=new Set();
  for (const event of events) {
    if (!record(event) || typeof event.type !== 'string') fail('event_invalid', 'Codex events require an object and a type');
    if (event.type === 'error' || event.type === 'turn.failed') {
      const message = event.error?.message ?? event.message ?? 'No failure details supplied';
      if (event.type === 'error' && active && retryableError(event)) {
        const id = event.turn_id ?? event.turn?.id;
        if (id !== undefined && id !== active.id) fail('event_turn_mismatch', 'Codex retry event does not belong to the active turn');
        active.retryErrors.push(message);
        continue;
      }
      fail('turn_failed', `Codex execution failed: ${message}`);
    }
    if (event.type === 'turn.started') {
      if (active) fail('turn_incomplete', 'Codex started a new turn before completing the previous one');
      threadStarted=false;
      const id = event.turn_id ?? event.turn?.id;
      if (id !== undefined && (typeof id !== 'string' || !id || turnIds.has(id))) fail('turn_duplicate', 'Codex turn IDs must be nonempty and unique');
      if (id !== undefined) turnIds.add(id);
      active = { id, completedItems: new Set(), answer: undefined, retryErrors: [], toolEvents: [], assistantEvents: [] };
    } else if (event.type === 'turn.completed') {
      if (!active) fail('turn_duplicate', 'Codex completed a missing or already completed turn');
      const id = event.turn_id ?? event.turn?.id;
      if (id !== undefined && id !== active.id) fail('event_turn_mismatch', 'Codex completion does not belong to the active turn');
      warnings.push(...active.retryErrors.map(message => `Turn ${turns.length + 1}: Codex recovered a retryable error before turn.completed: ${message}`));
      turns.push({ answer: active.answer, fromEvents: true, toolEvents: active.toolEvents, assistantEvents: active.assistantEvents }); active = undefined;
    } else if (event.type.startsWith('item.')) {
      // Codex 0.164.0 emits this specific informational warning after
      // thread.started but before turn.started. It is neither a solver action
      // nor an assistant answer; preserve it as a source diagnostic. Other
      // out-of-turn events and all fatal errors remain rejected.
      if(!active && threadStarted && startupAdvisory(event)) {
        if(startupItems.has(event.item.id))fail('item_duplicate','Codex startup advisory was completed more than once');
        startupItems.add(event.item.id);warnings.push(`Codex startup advisory: ${event.item.message}`);continue;
      }
      if (!active) fail('event_outside_turn', 'Codex item event occurs outside a started turn');
      if (!record(event.item) || typeof event.item.id !== 'string' || !event.item.id || typeof event.item.type !== 'string') {
        fail('item_invalid', 'Codex item events require an ID and type');
      }
      const id = event.turn_id ?? event.turn?.id;
      if (id !== undefined && id !== active.id) fail('event_turn_mismatch', 'Codex item event does not belong to the active turn');
      // Keep actual tool lifecycle facts, including failed or unfinished calls.
      // Their stdout is evidence for review, never an assistant answer or state.
      if (!['agent_message', 'reasoning'].includes(event.item.type)) active.toolEvents.push(clone(event));
      if (event.type !== 'item.completed') continue;
      if (active.completedItems.has(event.item.id)) fail('item_duplicate', `Codex item ${event.item.id} was completed more than once`);
      active.completedItems.add(event.item.id);
      if (event.item.type === 'agent_message') {
        if (typeof event.item.text !== 'string') fail('item_invalid', 'Completed Codex agent messages require text');
        active.assistantEvents.push(clone(event));
        active.answer = event.item.text;
      }
    } else if (event.type === 'thread.started') {
      if(active)fail('turn_incomplete','Codex started a thread during an active turn');
      threadStarted=typeof event.thread_id==='string'&&event.thread_id.length>0;
      startupItems.clear();
    } else {
      fail('event_unsupported', `Unsupported Codex event: ${event.type}`);
    }
  }
  if (active) fail('turn_incomplete', `Codex event stream ended before turn.completed${active.retryErrors.length ? ` after retryable error: ${active.retryErrors.join('; ')}` : ''}`);
  if (!turns.length) fail('turn_missing', 'Codex event stream contains no completed turns');
  return turns;
}

const isEvent = value => record(value) && typeof value.type === 'string'
  && /^(?:thread\.|turn\.|item\.|error$)/.test(value.type);
const stateKeys = ['model', 'analysisResult', 'messages', 'report', 'modelPending', 'analysisRuns'];

function declaredFigures(value) {
  // Accept complete figure descriptors emitted under the generic outputs list.
  // No path or run identity is inferred from prose, filenames or numeric truth.
  const outputFigures=Array.isArray(value.outputs)?value.outputs.filter(item=>record(item)
    &&typeof item.outputId==='string'&&item.outputId.trim()
    &&Number.isInteger(item.state)&&item.state>0
    &&(typeof item.runId==='string'&&item.runId.trim()||Array.isArray(item.runIds)&&item.runIds.length&&item.runIds.every(id=>typeof id==='string'&&id.trim()))
    &&typeof item.path==='string'&&/\.(?:png|svg|jpe?g)$/i.test(item.path)):[];
  // One composite image may explicitly cite several native runs in separate
  // descriptors. Combine only their stated run identities; all other fields
  // must agree. No run is inferred from the answer or the expected result.
  const combined=[];
  for(const item of outputFigures) {
    const {runId,runIds,...fields}=item;
    const ids=[...(runId?[runId]:[]),...(runIds||[])];
    const prior=combined.find(row=>row.outputId===item.outputId&&row.state===item.state&&row.path===item.path);
    if(!prior){combined.push(clone(item));continue;}
    const {runId:oldId,runIds:oldIds,...oldFields}=prior;
    if(!isDeepStrictEqual(fields,oldFields))fail('figures_ambiguous','Composite figure descriptors disagree');
    delete prior.runId;
    prior.runIds=[...new Set([...(oldId?[oldId]:[]),...(oldIds||[]),...ids])];
  }
  return mergeDescriptor('figures',value.figures,combined.length?combined:undefined);
}

function structuredTurn(value, answer) {
  if (!record(value)) fail('output_invalid', 'Structured Codex output must be an object');
  if (own(value, 'state') && !record(value.state)) fail('state_invalid', 'Codex state must be an object');
  if (own(value, 'turnId') && (typeof value.turnId !== 'string' || !value.turnId)) fail('turn_ids_invalid', 'Captured turn IDs must be nonempty strings');
  const hasState = record(value.state) || stateKeys.some(key => own(value, key));
  const rawState = record(value.state) ? value.state : hasState ? value : {};
  const state = Object.fromEntries(Object.entries(rawState).filter(([key]) => !['turnId', 'artifacts', 'figures', 'toolEvents', 'assistantEvents'].includes(key)));
  const artifacts = mergeDescriptor('artifacts', value.artifacts, rawState.artifacts);
  const figures = mergeDescriptor('figures', declaredFigures(value), declaredFigures(rawState));
  if (value.toolEvents !== undefined && rawState.toolEvents !== undefined && !isDeepStrictEqual(value.toolEvents, rawState.toolEvents)) {
    fail('tool_events_ambiguous', 'Outer and nested state tool events disagree');
  }
  const toolEvents = value.toolEvents !== undefined ? value.toolEvents : rawState.toolEvents;
  if (value.assistantEvents !== undefined && rawState.assistantEvents !== undefined && !isDeepStrictEqual(value.assistantEvents, rawState.assistantEvents)) {
    fail('assistant_events_ambiguous', 'Outer and nested state assistant events disagree');
  }
  const assistantEvents = value.assistantEvents !== undefined ? value.assistantEvents : rawState.assistantEvents;
  return { state, ...(typeof value.turnId === 'string' ? { turnId: value.turnId } : {}),
    ...(artifacts !== undefined ? { artifacts } : {}),
    ...(figures !== undefined ? { figures } : {}),
    ...(toolEvents !== undefined ? { toolEvents } : {}),
    ...(assistantEvents !== undefined ? { assistantEvents } : {}),
    // A raw final answer may itself be structured. A saved state object carries
    // only its captured messages; a persisted report does not become an answer.
    ...(answer !== undefined ? { answer } : {}) };
}

function sidecarStates(options, count) {
  if (options.state !== undefined && options.states !== undefined) fail('state_ambiguous', 'Supply either state or per-turn states');
  if (options.state !== undefined) {
    if (count !== 1) fail('state_ambiguous', 'A final state cannot be reused for multiple Codex turns; supply per-turn states');
    if (!record(options.state)) fail('state_invalid', 'Sidecar state must be an object');
    return [structuredTurn(options.state)];
  }
  if (options.states !== undefined) {
    if (!Array.isArray(options.states) || options.states.length !== count || options.states.some(state => !record(state))) {
      fail('state_invalid', 'Sidecar states must contain exactly one object for each Codex turn');
    }
    return options.states.map(state => structuredTurn(state));
  }
  return Array(count).fill(undefined);
}

function sidecarArtifacts(value, count) {
  if (value === undefined) return Array(count).fill(undefined);
  if (count === 1 && record(value)) return [value];
  if (Array.isArray(value) && value.length === count && value.every(record)) return value;
  fail('artifacts_invalid', 'Artifacts require one named map or one map per turn');
}

function sidecarFigures(value, count) {
  if (value === undefined) return Array(count).fill(undefined);
  if (count === 1 && Array.isArray(value) && value.every(record)) return [value];
  if (Array.isArray(value) && value.length === count && value.every(figures => Array.isArray(figures) && figures.every(record))) return value;
  fail('figures_invalid', 'Figures require one descriptor array or one descriptor array per turn');
}

function mergeDescriptor(name, input, sidecar) {
  if (input !== undefined && sidecar !== undefined && !isDeepStrictEqual(input, sidecar)) {
    fail(`${name}_ambiguous`, `Captured and sidecar ${name} disagree`);
  }
  const value = sidecar !== undefined ? sidecar : input;
  if (value !== undefined && (name === 'artifacts' ? !record(value) : !Array.isArray(value) || value.some(item => !record(item)))) {
    fail(`${name}_invalid`, `Invalid Codex ${name}`);
  }
  return value;
}

function cumulativeMessages(messages, previous) {
  if (messages === undefined) return clone(previous);
  if (!Array.isArray(messages) || messages.some(message => !record(message))) fail('messages_invalid', 'Codex messages must be an array of objects');
  const hasPrefix = messages.length >= previous.length && previous.every((message, index) => isDeepStrictEqual(message, messages[index]));
  return clone(hasPrefix ? messages : [...previous, ...messages]);
}

function hasToolMessage(message) {
  return message.name !== undefined || message.kwargs?.name !== undefined || message.role === 'tool' || message.type === 'tool'
    || message.id?.at?.(-1) === 'ToolMessage' || (message.tool_calls ?? message.kwargs?.tool_calls ?? []).length > 0;
}

/** Extract actual Codex delivery only. Binding cases, bytes and references is the caller's responsibility. */
function extractCodex(value, options = {}) {
  if (!record(options)) fail('options_invalid', 'Codex import options must be an object');
  const parsed = parseInput(value), warnings = [];
  let inputs, format = parsed.format;
  if (Array.isArray(parsed.value) || isEvent(parsed.value)) {
    inputs = eventTurns(Array.isArray(parsed.value) ? parsed.value : [parsed.value], warnings);
    if (format !== 'jsonl') format = 'events';
    // An explicitly emitted structured final JSON can carry its actual state.
    inputs = inputs.map(input => {
      if (input.answer === undefined) return input;
      const answer = parseInput(input.answer);
      if (record(answer.value) && !isEvent(answer.value)) {
        if (own(answer.value, 'turns')) fail('output_ambiguous', 'A single Codex turn cannot contain a second turn envelope');
        const structured = structuredTurn(answer.value, input.answer);
        if (structured.toolEvents !== undefined && !isDeepStrictEqual(structured.toolEvents, input.toolEvents)) {
          fail('tool_events_ambiguous', 'Emitted tool events disagree with the actual Codex event stream');
        }
        if (structured.assistantEvents !== undefined && !isDeepStrictEqual(structured.assistantEvents, input.assistantEvents)) {
          fail('assistant_events_ambiguous', 'Emitted assistant events disagree with the actual Codex event stream');
        }
        return { ...structured, fromEvents: true, toolEvents: input.toolEvents, assistantEvents: input.assistantEvents };
      }
      if (Array.isArray(answer.value) || isEvent(answer.value)) fail('output_ambiguous', 'A Codex final answer cannot contain another event stream');
      return input;
    });
  } else if (record(parsed.value) && own(parsed.value, 'turns')) {
    if (!Array.isArray(parsed.value.turns) || !parsed.value.turns.length) fail('turns_invalid', 'Codex turns must be a nonempty array');
    inputs = parsed.value.turns.map(input => structuredTurn(input));
    format = 'structured-turns';
  } else if (record(parsed.value)) inputs = [structuredTurn(parsed.value, parsed.answer)];
  else if (parsed.answer !== undefined && parsed.value === null) inputs = [{ answer: parsed.answer }];
  else fail('output_invalid', 'Codex output must be text, a state object or an event stream');

  const count = inputs.length, states = sidecarStates(options, count), artifacts = sidecarArtifacts(options.artifacts, count), figures = sidecarFigures(options.figures, count);
  if (options.turnIds !== undefined && (!Array.isArray(options.turnIds) || options.turnIds.length !== count)) {
    fail('turn_ids_invalid', 'turnIds must name exactly the imported turns');
  }
  const ids = new Set();
  let previous = [], previousSnapshotMessages;
  const turns = inputs.map((input, index) => {
    const sidecar = states[index];
    const turnId = options.turnIds?.[index] ?? input.turnId ?? sidecar?.turnId;
    if (turnId !== undefined && (typeof turnId !== 'string' || !turnId || ids.has(turnId))) fail('turn_ids_invalid', 'Imported turn IDs must be nonempty and unique');
    if (turnId !== undefined) ids.add(turnId);
    if (options.turnIds?.[index] !== undefined && input.turnId !== undefined && options.turnIds[index] !== input.turnId) {
      fail('turn_ids_invalid', 'Sidecar and captured turn IDs disagree');
    }
    if (sidecar?.turnId !== undefined && sidecar.turnId !== turnId) fail('turn_ids_invalid', 'Sidecar and captured turn IDs disagree');
    const state = clone(sidecar?.state ?? input.state ?? {});
    if (sidecar && input.state && ['model', 'analysisResult'].some(key => own(input.state, key) && own(sidecar.state, key)
        && !isDeepStrictEqual(input.state[key], sidecar.state[key]))) fail('state_conflict', 'Emitted and sidecar structural states disagree');
    const snapshotMessages = state.messages, snapshotActivities = [];
    if (snapshotMessages !== undefined && (!Array.isArray(snapshotMessages) || snapshotMessages.some(message => !record(message)))) {
      fail('messages_invalid', 'Codex sidecar messages must be an array of captured objects');
    }
    if ((input.answer !== undefined || input.fromEvents) && snapshotMessages) {
      const hasPrefix = previousSnapshotMessages !== undefined && snapshotMessages.length >= previousSnapshotMessages.length
        && previousSnapshotMessages.every((message, position) => isDeepStrictEqual(message, snapshotMessages[position]));
      const currentSnapshot = hasPrefix ? snapshotMessages.slice(previousSnapshotMessages.length) : snapshotMessages;
      if (currentSnapshot.some(hasToolMessage)) snapshotActivities.push({ type: 'snapshot_messages',
        scope: index === 0 || hasPrefix ? 'current' : 'unverified', messages: clone(currentSnapshot) });
    }
    previousSnapshotMessages = snapshotMessages === undefined ? undefined : clone(snapshotMessages);
    state.messages = input.answer !== undefined || input.fromEvents
      ? [...clone(previous), ...(input.answer !== undefined ? [{ role: 'assistant', content: input.answer }] : [])]
      : cumulativeMessages(state.messages, previous);
    const current = state.messages.slice(previous.length);
    previous = state.messages;
    if (!state.model) warnings.push(`Turn ${index + 1}: physical model is missing; text alone cannot establish modeling or solver evidence.`);
    if (!state.analysisResult) warnings.push(`Turn ${index + 1}: analysis result is missing; no solver execution or values were inferred.`);
    if (!current.some(message => message.role === 'assistant' || message.type === 'ai')) warnings.push(`Turn ${index + 1}: no completed current assistant answer was captured.`);
    const files = mergeDescriptor('artifacts', mergeDescriptor('artifacts', input.artifacts, sidecar?.artifacts), artifacts[index]);
    const images = mergeDescriptor('figures', mergeDescriptor('figures', input.figures, sidecar?.figures), figures[index]);
    if (input.toolEvents !== undefined && sidecar?.toolEvents !== undefined && !isDeepStrictEqual(input.toolEvents, sidecar.toolEvents)) {
      fail('tool_events_ambiguous', 'Captured and sidecar tool events disagree');
    }
    const capturedToolEvents = input.toolEvents !== undefined ? input.toolEvents : sidecar?.toolEvents;
    if (capturedToolEvents !== undefined && (!Array.isArray(capturedToolEvents) || capturedToolEvents.some(event => !record(event)))) {
      fail('tool_events_invalid', 'Codex tool events must be an array of objects');
    }
    const toolEvents = capturedToolEvents !== undefined || snapshotActivities.length ? [...(capturedToolEvents || []), ...snapshotActivities] : undefined;
    if (input.assistantEvents !== undefined && sidecar?.assistantEvents !== undefined && !isDeepStrictEqual(input.assistantEvents, sidecar.assistantEvents)) {
      fail('assistant_events_ambiguous', 'Captured and sidecar assistant events disagree');
    }
    const assistantEvents = input.assistantEvents !== undefined ? input.assistantEvents : sidecar?.assistantEvents;
    if (assistantEvents !== undefined && (!Array.isArray(assistantEvents) || assistantEvents.some(event =>
      !record(event) || event.type !== 'item.completed' || event.item?.type !== 'agent_message' || typeof event.item.text !== 'string'))) {
      fail('assistant_events_invalid', 'Codex assistant events must contain actual completed agent messages');
    }
    if (!files || !Object.keys(files).length) warnings.push(`Turn ${index + 1}: raw execution artifacts are missing; no receipts were generated.`);
    return { ...(turnId !== undefined ? { turnId } : {}), state,
      ...(toolEvents !== undefined ? { toolEvents: clone(toolEvents) } : {}),
      ...(assistantEvents !== undefined ? { assistantEvents: clone(assistantEvents) } : {}),
      ...(files !== undefined ? { artifacts: clone(files) } : {}), ...(images !== undefined ? { figures: clone(images) } : {}) };
  });
  return { turns, source: { adapter: 'codex', format, warnings } };
}

module.exports = { extractCodex };
