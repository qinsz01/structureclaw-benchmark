const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const {exportToolContracts}=require('./lib/tool-contracts.cjs');
const {BENCHMARK_TOOL_IDS}=require('./lib/config.cjs');
const sut=path.resolve(process.env.SCLAW_ROOT||path.join(__dirname,'../../../..'));
const {pathToFileURL}=require('node:url');
test('OpenClaw consumes actual current backend schemas, including edits and exact result requests',async t=>{
  if(!fs.existsSync(path.join(sut,'backend/dist/agent-langgraph/public-tool-contracts.js')))return t.skip('Build current SUT before integration check');
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'sclaw-public-contracts-')),file=path.join(dir,'contracts.json');
  try {
    await exportToolContracts(sut,file,BENCHMARK_TOOL_IDS);const defs=JSON.parse(fs.readFileSync(file,'utf8'));
    const properties=name=>defs.find(d=>d.name===name).parameters.properties;
    for(const name of ['query_model','review_input','edit_model','undo_model','query_results'])assert.ok(defs.some(d=>d.name===name));
    assert.ok(properties('edit_model').baseRevision);assert.ok(properties('run_analysis').loadCaseIds);assert.ok(properties('run_analysis').loadCombinationIds);
    assert.ok(properties('analyze_file').pageStart);assert.ok(properties('analyze_file').pageCount);assert.ok(properties('query_results').positionM);
  } finally {fs.unlinkSync(file);fs.rmdirSync(dir);}
});
test('external tools apply canonical reducers and retain all incremental run and quantity records',async()=>{
  const {applyPublicToolStateUpdate}=await import(pathToFileURL(path.join(sut,'backend/dist/agent-langgraph/public-tool-contracts.js')).href);
  let state={analysisRuns:{r1:{id:'r1'}},resultQuantities:{q1:{value:1}},artifacts:{old:'retained'},policy:{engineId:'opensees',analysisType:'static'}};
  state=applyPublicToolStateUpdate(state,{analysisRuns:{r2:{id:'r2'}},resultQuantities:{q2:{value:2}},artifacts:{new:'added'},policy:{analysisType:undefined},analysisRequest:{requestId:'latest'},analysisResult:null,messages:[{content:'external-message'}]});
  assert.deepEqual(Object.keys(state.analysisRuns),['r1','r2']);assert.deepEqual(Object.keys(state.resultQuantities),['q1','q2']);
  assert.deepEqual(state.artifacts,{old:'retained',new:'added'});assert.equal(state.policy.analysisType,'static');
  assert.equal(state.analysisRequest.requestId,'latest');assert.equal(state.analysisResult,null);assert.equal(state.messages,undefined);
});
