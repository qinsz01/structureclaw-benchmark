'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { extractCodex } = require('./import-codex.cjs');

const started = () => ({ type: 'turn.started' });
const completed = () => ({ type: 'turn.completed', usage: { input_tokens: 11, output_tokens: 7 } });
const message = (text, id = 'answer') => ({ type: 'item.completed', item: { id, type: 'agent_message', text } });
const events = text => [{ type: 'thread.started', thread_id: 'thread-1' }, started(), message(text), completed()];
const jsonl = values => values.map(value => JSON.stringify(value)).join('\n') + '\n';
const model = { nodes: [{ id: 'n1' }], elements: [] };
const analysisResult = { results: { 'case:D': { data: { displacements: { n1: { uz: -.001 } } } } } };
const sidecar = () => ({ model: structuredClone(model), analysisResult: structuredClone(analysisResult),
  report: { markdown: 'Historical report must not become the current response.' },
  messages: [{ role: 'assistant', content: 'Old sidecar answer.' }] });

const startupWarning=()=>({type:'item.completed',item:{id:'startup',type:'error',message:'Under-development features enabled: skip_host_skill_discovery. Under-development features are incomplete and may behave unpredictably. To suppress this warning, set `suppress_unstable_features_warning = true` in /tmp/codex/config.toml.'}});
test('actual Codex startup advisory survives as a diagnostic without creating activity or an answer',()=>{
  const warning=startupWarning(),input=[{type:'thread.started',thread_id:'actual-cli'},warning,started(),message('Actual final answer'),completed()];
  const result=extractCodex(jsonl(input),{state:sidecar()});
  assert.equal(result.turns.length,1);assert.deepEqual(result.turns[0].state.messages,[{role:'assistant',content:'Actual final answer'}]);
  assert.deepEqual(result.turns[0].toolEvents,[]);assert.equal(result.turns[0].assistantEvents.length,1);
  assert.ok(result.source.warnings.some(text=>text===`Codex startup advisory: ${warning.item.message}`));
});
test('startup handling cannot admit fatal, mistimed, attributed or duplicate error events',()=>{
  const thread={type:'thread.started',thread_id:'actual-cli'},warning=startupWarning();
  const bad=[{...warning,item:{...warning.item,message:'Analysis failed'}},{...warning,turn_id:'t1'},
    {...warning,item:{...warning.item,status:'failed'}},{...warning,item:{...warning.item,type:'command_execution'}}];
  for(const e of bad)assert.throws(()=>extractCodex(jsonl([thread,e,started(),message('answer'),completed()])),{code:'codex_event_outside_turn'});
  assert.throws(()=>extractCodex(jsonl([warning,started(),message('answer'),completed()])),{code:'codex_event_outside_turn'});
  assert.throws(()=>extractCodex(jsonl([thread,started(),message('answer'),completed(),warning])),{code:'codex_event_outside_turn'});
  assert.throws(()=>extractCodex(jsonl([thread,warning,warning,started(),message('answer'),completed()])),{code:'codex_item_duplicate'});
  assert.throws(()=>extractCodex(jsonl([thread,{type:'error',message:'Startup failed'},started(),message('answer'),completed()])),{code:'codex_turn_failed'});
});
test('resumed CLI invocations retain their own startup diagnostics and per-turn state',()=>{
  const thread={type:'thread.started',thread_id:'persistent-thread'};
  const stream=[thread,startupWarning(),started(),message('Which load?'),completed(),
    thread,startupWarning(),started(),message('Actual solved result'),completed()];
  const result=extractCodex(jsonl(stream),{states:[{},sidecar()],turnIds:['t1','t2']});
  assert.equal(result.source.warnings.filter(text=>text.startsWith('Codex startup advisory:')).length,2);
  assert.deepEqual(result.turns.map(t=>t.state.messages.at(-1).content),['Which load?','Actual solved result']);
  assert.ok(result.turns.every(t=>t.toolEvents.length===0));
  assert.equal(result.turns[0].state.model,undefined);assert.deepEqual(result.turns[1].state.model,model);
  assert.throws(()=>extractCodex([thread,started(),thread,message('answer'),completed()]),{code:'codex_turn_incomplete'});
});

test('Codex JSONL separates final assistant text from captured tool events and excludes reasoning', () => {
  const stream = [
    { type: 'thread.started', thread_id: 't' }, started(),
    { type: 'item.completed', item: { id: 'reason', type: 'reasoning', text: 'Private reasoning' } },
    { type: 'item.started', item: { id: 'partial', type: 'agent_message', text: 'Incomplete answer' } },
    { type: 'item.updated', item: { id: 'partial', type: 'agent_message', text: 'Incomplete answer update' } },
    message('Progress update', 'progress'),
    { type: 'item.completed', item: { id: 'shell', type: 'command_execution', command: 'cat output.json',
      aggregated_output: JSON.stringify({ model: { fake: true }, messages: [{ role: 'assistant', content: 'Tool answer' }] }), exit_code: 0 } },
    message('Final answer', 'answer'), completed(),
  ];
  const result = extractCodex(jsonl(stream), { caseId: 'STD-001', state: sidecar(), turnIds: ['t1'] });
  assert.equal(result.source.adapter, 'codex');
  assert.equal(result.source.format, 'jsonl');
  assert.deepEqual(result.turns[0].state.messages, [{ role: 'assistant', content: 'Final answer' }]);
  assert.deepEqual(result.turns[0].state.model, model);
  assert.equal(result.turns[0].turnId, 't1');
  assert.doesNotMatch(JSON.stringify(result.turns[0].state), /Private reasoning|Tool answer|Old sidecar answer/);
  assert.doesNotMatch(JSON.stringify(result), /Private reasoning/);
  assert.deepEqual(result.turns[0].toolEvents, [stream[6]]);
  assert.deepEqual(result.turns[0].assistantEvents, [stream[5], stream[7]]);
});

test('event arrays and JSONL preserve the same completed answer', () => {
  const input = events('| case:D | n1 | uz | -0.001 | m |');
  assert.deepEqual(extractCodex(input).turns, extractCodex(jsonl(input)).turns);
  assert.equal(extractCodex(input).source.format, 'events');
});

test('Codex 0.164.0 MCP metadata, collaboration, declined commands and usage retain their event boundaries', () => {
  // Shapes from openai/codex rust-v0.164.0 codex-rs/exec/src/exec_events.rs.
  const tools = [
    { id: 'mcp', type: 'mcp_tool_call', server: 'solver', tool: 'run_analysis', arguments: { case: 'D' },
      result: { content: [{ type: 'text', text: 'Solver output' }], _meta: { source: 'native' }, structured_content: { ok: true } },
      error: null, status: 'completed' },
    { id: 'collab', type: 'collab_tool_call', tool: 'spawn_agent', sender_thread_id: 'main', receiver_thread_ids: ['worker'],
      prompt: 'Review', agents_states: { worker: { status: 'completed', message: 'Reviewed' } }, status: 'completed' },
    { id: 'declined', type: 'command_execution', command: 'python solver.py', aggregated_output: '', exit_code: null, status: 'declined' },
    { id: 'search', type: 'web_search', query: 'structural units', action: { type: 'search', query: 'structural units' },
      results: [{ title: 'Unit reference', url: 'https://example.com' }] },
  ].map(item => ({ type: 'item.completed', item }));
  const answer = message('Final response'), usage = { input_tokens: 100, cached_input_tokens: 20,
    cache_write_input_tokens: 0, output_tokens: 10, reasoning_output_tokens: 5 };
  const result = extractCodex(jsonl([started(), ...tools, answer, { type: 'turn.completed', usage }]));
  assert.deepEqual(result.turns[0].toolEvents, tools);
  assert.deepEqual(result.turns[0].assistantEvents, [answer]);
  assert.deepEqual(result.turns[0].state.messages, [{ role: 'assistant', content: 'Final response' }]);
  assert.equal(result.turns[0].state.analysisResult, undefined);
});

test('multi-turn JSONL needs individual sidecar snapshots and keeps exact cumulative answer prefixes', () => {
  const input = [started(), message('Please supply the span'), completed(), started(), message('The displacement is -0.001 m'), completed()];
  const snapshots = [{ messages: [{ role: 'assistant', content: 'Not this answer' }] }, sidecar()];
  const result = extractCodex(input, { turnIds: ['t1', 't2'], states: snapshots });
  assert.deepEqual(result.turns[1].state.messages.slice(0, 1), result.turns[0].state.messages);
  assert.equal(result.turns[1].state.messages[1].content, 'The displacement is -0.001 m');
  assert.equal(result.turns[0].state.model, undefined);
  assert.deepEqual(result.turns[1].state.model, model);
  assert.equal(snapshots[0].messages[0].content, 'Not this answer');
  assert.throws(() => extractCodex(input, { state: sidecar() }), { code: 'codex_state_ambiguous' });
  assert.throws(() => extractCodex(input, { states: [sidecar()] }), { code: 'codex_state_invalid' });
  assert.throws(() => extractCodex(input, { turnIds: ['t1'] }), { code: 'codex_turn_ids_invalid' });
  assert.throws(() => extractCodex(input, { turnIds: ['t1', 't1'] }), { code: 'codex_turn_ids_invalid' });
});

test('completed turns without agent messages do not reuse old sidecar messages or reports', () => {
  const input = [started(), { type: 'item.completed', item: { id: 'command', type: 'command_execution', aggregated_output: 'Solver says passed' } }, completed()];
  const result = extractCodex(input, { state: sidecar() });
  assert.deepEqual(result.turns[0].state.messages, []);
  assert.match(result.source.warnings.join('\n'), /no completed current assistant answer/);
  assert.equal(result.turns[0].state.report.markdown, sidecar().report.markdown);
});

for (const [name, input, code] of [
  ['turn failure', [started(), message('Premature answer'), { type: 'turn.failed', error: { message: 'rate limit exhausted' } }], 'codex_turn_failed'],
  ['error event', [{ type: 'error', message: 'authentication failed' }], 'codex_turn_failed'],
  ['missing completion', [started(), message('Half answer')], 'codex_turn_incomplete'],
  ['duplicate completion', [started(), message('Answer'), completed(), completed()], 'codex_turn_duplicate'],
  ['overlapping turns', [started(), started(), completed()], 'codex_turn_incomplete'],
  ['item outside a turn', [message('Unbound answer')], 'codex_event_outside_turn'],
  ['duplicate completed item', [started(), message('First'), message('Second'), completed()], 'codex_item_duplicate'],
  ['unknown event', [started(), { type: 'response.finished' }, completed()], 'codex_event_unsupported'],
]) test(`failed or malformed ${name} cannot become a successful imported turn`, () => {
  assert.throws(() => extractCodex(input), { code });
});

test('execution failure diagnostics retain the actual failure reason', () => {
  assert.throws(() => extractCodex([{ type: 'turn.failed', error: { message: 'quota exhausted' } }]), /quota exhausted/);
});

const reconnect = 'Reconnecting... 2/5 (stream disconnected before completion: tls handshake eof)';

test('Codex 0.163.0 completed reconnect progress remains a warning without becoming an answer or engineering evidence', () => {
  // Recorded nonformal connectivity probe shape; no benchmark case or solver
  // state was supplied. The CLI exited 0 after this intermediate error event.
  const stream = [
    { type: 'thread.started', thread_id: 'probe-thread' }, started(), { type: 'error', message: reconnect },
    message('CODEX_CONNECTIVITY_OK', 'item_0'),
    { type: 'turn.completed', usage: { input_tokens: 13734, cached_input_tokens: 12032,
      cache_write_input_tokens: 0, output_tokens: 9, reasoning_output_tokens: 0 } },
  ];
  const result = extractCodex(jsonl(stream));
  assert.deepEqual(result.turns, [{ state: { messages: [{ role: 'assistant', content: 'CODEX_CONNECTIVITY_OK' }] },
    toolEvents: [], assistantEvents: [stream[3]] }]);
  assert.ok(result.source.warnings.some(warning => warning.startsWith('Turn 1: Codex recovered') && warning.endsWith(reconnect)));
  for (const missing of ['physical model is missing', 'analysis result is missing', 'raw execution artifacts are missing']) {
    assert.ok(result.source.warnings.some(warning => warning.includes(missing)));
  }
  assert.deepEqual(extractCodex(stream), { ...result, source: { ...result.source, format: 'events' } });
});

test('explicit retry metadata is honored only after the same active turn completes', () => {
  const first = { type: 'error', willRetry: true, error: { message: 'Transient transport reset' }, turn_id: 'first' };
  const input = [{ type: 'turn.started', turn_id: 'first' }, first, message('First'),
    { ...completed(), turn_id: 'first' }, started(), { type: 'error', message: 'Reconnecting... 5/5 (connection reset)' },
    message('Second'), completed()];
  const result = extractCodex(input, { states: [{}, sidecar()] });
  assert.deepEqual(result.turns[1].state.messages, [{ role: 'assistant', content: 'First' }, { role: 'assistant', content: 'Second' }]);
  const warnings = result.source.warnings.filter(warning => warning.includes('Codex recovered'));
  assert.equal(warnings.length, 2);
  assert.match(warnings[0], /^Turn 1:.*Transient transport reset$/);
  assert.match(warnings[1], /^Turn 2:.*Reconnecting/);
  assert.throws(() => extractCodex(input.slice(0, 3)), error => error.code === 'codex_turn_incomplete' && /Transient transport reset/.test(error.message));
  assert.throws(() => extractCodex([{ type: 'turn.started', turn_id: 'first' }, { ...first, turn_id: 'other' }, completed()]), { code: 'codex_event_turn_mismatch' });
  assert.throws(() => extractCodex([{ type: 'turn.started', turn_id: 'first' }, first, { ...completed(), turn_id: 'other' }]), { code: 'codex_event_turn_mismatch' });
});

test('upstream network-wait and bare bounded retries require successful completion and preserve each diagnostic', () => {
  const progress = ['Reconnecting... waiting for network', 'Reconnecting... 1/1'];
  const input = [started(), ...progress.map(message => ({ type: 'error', message })), message('Recovered'), completed()];
  const result = extractCodex(input);
  assert.deepEqual(result.turns[0].state.messages, [{ role: 'assistant', content: 'Recovered' }]);
  for (const text of progress) assert.ok(result.source.warnings.some(warning => warning.endsWith(text)));
  assert.throws(() => extractCodex(input.slice(0, -1)), { code: 'codex_turn_incomplete' });
  const preserved = extractCodex([started(), { type: 'error', will_retry: true, message: 'Transport interrupted' }, message('Recovered'), completed()]);
  assert.ok(preserved.source.warnings.some(warning => warning.endsWith('Transport interrupted')));
});

test('terminal errors cannot be repaired by later completion or by reconnect-looking text', () => {
  for (const event of [
    { type: 'error', message: 'authentication failed' },
    { type: 'error', message: reconnect, willRetry: false },
    { type: 'error', message: reconnect, will_retry: false },
    { type: 'error', message: reconnect, willRetry: true, will_retry: false },
    { type: 'error', message: reconnect, willRetry: 'true' },
    { type: 'error', message: '', willRetry: true },
    { type: 'turn.failed', error: { message: reconnect }, willRetry: true },
    ...['Reconnecting...', 'Reconnecting... 0/5 (failed)', 'Reconnecting... 6/5 (failed)',
      'Reconnecting... 1/0 (failed)', 'Reconnecting... 1/5 (failed) terminal failure',
      'Reconnecting... waiting for network failed',
      'Reconnecting... 9007199254740993/9007199254740994 (failed)'].map(message => ({ type: 'error', message })),
  ]) assert.throws(() => extractCodex([started(), event, message('Premature answer'), completed()]), { code: 'codex_turn_failed' });
});

test('uncompleted or unbound reconnects remain failures despite answers or later turns', () => {
  const retry = { type: 'error', message: reconnect };
  for (const [input, code] of [
    [[started(), retry, message('Partial answer')], 'codex_turn_incomplete'],
    [[started(), retry, started(), message('Later answer'), completed()], 'codex_turn_incomplete'],
    [[started(), retry, { type: 'turn.failed', error: { message: 'retry limit exhausted' } }], 'codex_turn_failed'],
    [[started(), retry, { type: 'error', message: 'retry limit exhausted' }, completed()], 'codex_turn_failed'],
    [[retry, started(), message('Later answer'), completed()], 'codex_turn_failed'],
    [[...events('Completed earlier'), retry], 'codex_turn_failed'],
  ]) assert.throws(() => extractCodex(input), { code });
});

test('truncated JSON, repeated object keys and duplicate structured turn IDs are rejected', () => {
  for (const input of ['{"model":', '{"type":"turn.started"}\n{"type":', '```json\n{"model":{}}',
    'Answer:\n```json\n{}', '```json\n{}\n```\n```json\n{}']) {
    assert.throws(() => extractCodex(input), { code: 'codex_json_invalid' });
  }
  assert.throws(() => extractCodex('{"model":{},"model":{"x":1}}'), { code: 'codex_json_duplicate_key' });
  assert.throws(() => extractCodex('{"state":{"messages":[],"mess\\u0061ges":[]}}'), { code: 'codex_json_duplicate_key' });
  assert.throws(() => extractCodex('{"type":"turn.started"}\n{"type":"turn.completed","type":"turn.failed"}'), { code: 'codex_json_duplicate_key' });
  assert.throws(() => extractCodex({ turns: [{ turnId: 't1', state: {} }, { turnId: 't1', state: {} }] }), { code: 'codex_turn_ids_invalid' });
});

test('plain Markdown can be evaluated with explicit sidecar state without inventing solver evidence', () => {
  const answer = '| case:D | n1 | uz | -0.001 | m |';
  const input = sidecar(), result = extractCodex(answer, { state: input });
  assert.equal(result.source.format, 'last-message-markdown');
  assert.deepEqual(result.turns[0].state.messages, [{ role: 'assistant', content: answer }]);
  assert.deepEqual(result.turns[0].state.analysisResult, analysisResult);
  assert.equal(input.messages[0].content, 'Old sidecar answer.');
  assert.match(result.source.warnings.join('\n'), /raw execution artifacts are missing/);
  assert.equal(result.turns[0].artifacts, undefined);
});

test('text alone returns its answer and explicit missing-state diagnostics without fake model or receipts', () => {
  const result = extractCodex('Please supply the force unit.');
  assert.deepEqual(result.turns, [{ state: { messages: [{ role: 'assistant', content: 'Please supply the force unit.' }] } }]);
  assert.match(result.source.warnings.join('\n'), /physical model is missing/);
  assert.match(result.source.warnings.join('\n'), /analysis result is missing/);
  assert.match(result.source.warnings.join('\n'), /no receipts were generated/);
});

test('complete figure descriptors in outputs retain their exact candidate-supplied run binding',()=>{
  const figure={outputId:'plot',state:1,runId:'actual-run',path:'plot.png'};
  const input={...sidecar(),outputs:[{value:3,unit:'m'},figure]},before=structuredClone(input);
  for(const state of [input,{state:input}]) {
    const got=extractCodex(events('Actual figure linked in the answer'),{state});
    assert.deepEqual(got.turns[0].figures,[figure]);
    assert.deepEqual(got.turns[0].state.outputs,input.outputs);
  }
  assert.deepEqual(input,before);
  for(const key of ['outputId','state','runId','path']) {
    const incomplete=structuredClone(figure);delete incomplete[key];
    assert.equal(extractCodex(events('No inferred binding'),{state:{...sidecar(),outputs:[incomplete]}}).turns[0].figures,undefined);
  }
  assert.throws(()=>extractCodex(events('Conflict'),{state:{...input,figures:[{...figure,runId:'different-run'}]}}),{code:'codex_figures_ambiguous'});
});
test('raw structured states retain actual model, results, messages, artifacts and figures', () => {
  const artifacts = { run: { normalizedInput: 'input.json', solverResponse: 'response.json' } };
  const figures = [{ outputId: 'plot', path: 'figure.png' }];
  const input = { turnId: 't1', state: sidecar(), artifacts, figures };
  const result = extractCodex(input);
  assert.equal(result.source.format, 'structured');
  assert.deepEqual(result.turns, [input]);
  result.turns[0].state.model.nodes[0].id = 'changed';
  assert.equal(input.state.model.nodes[0].id, 'n1');
  const bare = extractCodex(sidecar());
  assert.deepEqual(bare.turns[0].state, sidecar());
});

test('structured turn-local messages are accumulated while existing cumulative prefixes are retained exactly once', () => {
  const first = { role: 'assistant', content: 'First' }, second = { role: 'assistant', content: 'Second' }, third = { role: 'assistant', content: 'Third' };
  const result = extractCodex({ turns: [
    { turnId: 't1', state: { messages: [first] } },
    { turnId: 't2', state: { messages: [first, second] } },
    { turnId: 't3', state: { messages: [third] } },
  ] });
  assert.equal(result.source.format, 'structured-turns');
  assert.deepEqual(result.turns.map(turn => turn.state.messages), [[first], [first, second], [first, second, third]]);
});

test('raw or fenced structured final JSON provides actual state and keeps the emitted JSON answer', () => {
  const output = JSON.stringify({ model, analysisResult });
  for (const answer of [output, `\`\`\`json\n${output}\n\`\`\``]) {
    const direct = extractCodex(answer);
    const streamed = extractCodex(jsonl(events(answer)));
    for (const result of [direct, streamed]) {
      assert.deepEqual(result.turns[0].state.model, model);
      assert.deepEqual(result.turns[0].state.analysisResult, analysisResult);
      assert.equal(result.turns[0].state.messages[0].content, answer);
    }
  }
});

test('ambiguous JSON blocks, nested transcripts and conflicting emitted/sidecar states are rejected', () => {
  assert.throws(() => extractCodex('```json\n{}\n```\n```json\n{}\n```'), { code: 'codex_output_ambiguous' });
  assert.throws(() => extractCodex(events(JSON.stringify({ turns: [{ state: {} }] }))), { code: 'codex_output_ambiguous' });
  assert.throws(() => extractCodex(JSON.stringify({ model: { nodes: [] } }), { state: sidecar() }), { code: 'codex_state_conflict' });
  assert.throws(() => extractCodex('Answer', { state: {}, states: [{}] }), { code: 'codex_state_ambiguous' });
});

test('sidecar artifacts and figures are supplied per turn without sharing a final snapshot', () => {
  const input = [started(), message('First'), completed(), started(), message('Second'), completed()];
  const artifacts = [{ first: { normalizedInput: 'first.json' } }, { second: { normalizedInput: 'second.json' } }];
  const figures = [[{ path: 'first.png' }], [{ path: 'second.png' }]];
  const result = extractCodex(input, { artifacts, figures });
  assert.deepEqual(result.turns.map(turn => turn.artifacts), artifacts);
  assert.deepEqual(result.turns.map(turn => turn.figures), figures);
  assert.throws(() => extractCodex(input, { artifacts: artifacts[1] }), { code: 'codex_artifacts_invalid' });
  assert.throws(() => extractCodex({ state: {}, artifacts: artifacts[0] }, { artifacts: artifacts[1] }), { code: 'codex_artifacts_ambiguous' });
});

test('sidecar state descriptors are lifted without inventing files and conflicts are rejected', () => {
  const artifacts = { run: { normalizedInput: 'input.json', solverResponse: 'response.json' } };
  const figures = [{ outputId: 'plot', path: 'figure.svg' }];
  const bare = { ...sidecar(), artifacts, figures };
  for (const snapshot of [bare, { state: sidecar(), artifacts, figures }, { state: bare }]) {
    const result = extractCodex(events('Current answer'), { state: snapshot });
    assert.deepEqual(result.turns[0].artifacts, artifacts);
    assert.deepEqual(result.turns[0].figures, figures);
    assert.equal(result.turns[0].state.artifacts, undefined);
    assert.equal(result.turns[0].state.figures, undefined);
    assert.equal(result.turns[0].state.messages[0].content, 'Current answer');
    result.turns[0].artifacts.run.normalizedInput = 'changed.json';
    assert.equal(artifacts.run.normalizedInput, 'input.json');
  }
  assert.throws(() => extractCodex(events('Answer'), { state: bare, artifacts: { other: {} } }), { code: 'codex_artifacts_ambiguous' });
  assert.throws(() => extractCodex({ state: {}, figures }, { state: { state: {}, figures: [] } }), { code: 'codex_figures_ambiguous' });
  assert.throws(() => extractCodex('Answer', { state: { state: {}, artifacts: null } }), { code: 'codex_artifacts_invalid' });
  assert.throws(() => extractCodex('Answer', { state: { turnId: 't2', state: {} }, turnIds: ['t1'] }), { code: 'codex_turn_ids_invalid' });
  const turns = extractCodex([...events('First'), ...events('Second')], { states: [{ state: {}, artifacts }, { ...sidecar(), figures }] }).turns;
  assert.deepEqual(turns[0].artifacts, artifacts); assert.equal(turns[1].artifacts, undefined);
  assert.equal(turns[0].figures, undefined); assert.deepEqual(turns[1].figures, figures);
});

test('started, updated, failed and unfinished tool activity stays within its actual turn', () => {
  const tool = (type, itemType = 'command_execution') => ({ type, item: { id: 'tool', type: itemType,
    command: 'python solver.py', status: 'failed', aggregated_output: 'not an assistant answer' } });
  const activity = [tool('item.started'), tool('item.updated'), tool('item.failed')];
  const input = [started(), ...activity, message('Please supply the span.'), completed(),
    started(), message(JSON.stringify({ state: { model } })), completed()];
  const result = extractCodex(input);
  assert.deepEqual(result.turns[0].toolEvents, activity);
  assert.deepEqual(result.turns[1].toolEvents, []);
  assert.equal(result.turns[1].state.messages.length, 2);
  assert.doesNotMatch(JSON.stringify(result.turns.map(t => t.state.messages)), /not an assistant answer/);
  const falsified = [started(), tool('item.started'), message(JSON.stringify({ state: {}, toolEvents: [] })), completed()];
  assert.throws(() => extractCodex(falsified), { code: 'codex_tool_events_ambiguous' });
  assert.throws(() => extractCodex(input, { states: [{ toolEvents: [] }, {}] }), { code: 'codex_tool_events_ambiguous' });
  assert.equal(result.turns[0].assistantEvents.length, 1);
  assert.equal(result.turns[1].assistantEvents.length, 1);
  assert.throws(() => extractCodex(input, { states: [{ assistantEvents: [] }, {}] }), { code: 'codex_assistant_events_ambiguous' });
});

test('sidecar tool messages survive final answers and cumulative snapshots isolate current activity', () => {
  const call = { role: 'assistant', content: '', tool_calls: [{ name: 'run_analysis', args: {} }] };
  const result = { role: 'tool', name: 'run_analysis', content: 'solver failed' };
  const messages = [call, result];
  for (const input of ['Please supply the span.', events('Please supply the span.')]) {
    const turn = extractCodex(input, { state: { messages } }).turns[0];
    assert.deepEqual(turn.state.messages, [{ role: 'assistant', content: 'Please supply the span.' }]);
    assert.deepEqual(turn.toolEvents.at(-1), { type: 'snapshot_messages', scope: 'current', messages });
  }
  const later = { role: 'assistant', tool_calls: [{ name: 'ask_user_clarification', args: { question: 'Which modulus?' } }] };
  const turns = extractCodex([...events('Done'), ...events('Which modulus?')], { states: [{ messages }, { messages: [...messages, later] }] }).turns;
  assert.deepEqual(turns[1].toolEvents, [{ type: 'snapshot_messages', scope: 'current', messages: [later] }]);
  const uncertain = extractCodex([...events('First'), ...events('Second')], { states: [{ messages: [later] }, { messages }] }).turns;
  assert.deepEqual(uncertain[1].toolEvents.at(-1), { type: 'snapshot_messages', scope: 'unverified', messages });
});


test('composite output figures preserve every explicitly declared run without duplicate files',()=>{
  const descriptor={outputId:'figures',state:1,path:'combined.png'};
  const outputs=[{...descriptor,runId:'run-D'},{...descriptor,runId:'run-L'}];
  const input={outputs},before=JSON.stringify(input);
  const result=extractCodex('Answer',{state:input});
  assert.deepEqual(result.turns[0].figures,[{...descriptor,runIds:['run-D','run-L']}]);
  assert.equal(JSON.stringify(input),before);
  assert.throws(()=>extractCodex('Answer',{state:{outputs:[outputs[0],{...outputs[1],caption:'different metadata'}]}}),{code:'codex_figures_ambiguous'});
  const different=extractCodex('Answer',{state:{outputs:[outputs[0],{...outputs[1],state:2}]}});
  assert.equal(different.turns[0].figures.length,2);
});
