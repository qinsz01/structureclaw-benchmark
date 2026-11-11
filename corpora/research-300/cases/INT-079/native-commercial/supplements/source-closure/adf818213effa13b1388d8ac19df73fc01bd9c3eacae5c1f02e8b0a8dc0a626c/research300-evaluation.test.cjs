const test=require('node:test');
const assert=require('node:assert/strict');
const {createHash}=require('node:crypto');
const {evaluateBoundQuantities,evaluateResearchTurn,scopeTurnState}=require('./research300-evaluation.cjs');
const {evaluateScenario,evaluateInteractionEvidence}=require('./evaluate.cjs');
const {modelFingerprint,resultFingerprint}=require('./analysis-evidence.cjs');
const expectedModel=require('../fixtures/ground-truth-models.json').find(m=>m.id==='beam-simple-6m').model;
const selection={kind:'case',id:expectedModel.load_cases[0].id};
const key=`case:${selection.id}`;
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
function setup() {
  const model=structuredClone(expectedModel),sourceHash=sha('frozen-contract-and-public-inputs');
  const q={id:'deflection',selection,location:{kind:'node',id:model.nodes[1].id},component:'uz',unit:'m',value:-.001,
    tolerance:{absolute:1e-8,relative:1e-6}};
  const input=Buffer.from('normalized independent collector input'),output=Buffer.from('native raw solver response');
  const data={displacements:{[q.location.id]:{uz:q.value}},execution:{executed:true,solver:'OpenSees',solverVersion:'3.7.1',analysisReturnCode:0,
    artifacts:{normalizedInputSha256:sha(input),solverResponseSha256:sha(output)}}};
  const state={model,messages:[],report:{markdown:`| ${q.id} | ${key} | ${q.location.id} | uz | ${q.value} | m |`},analysisResult:{results:{[key]:{selection,status:'success',
    meta:{engineId:'builtin-opensees',state:1,sourceHash,modelHash:modelFingerprint(model),runId:'run-1'},data}}}};
  const referenceEvidence={engineId:'opensees',state:1,sourceHash,modelHash:modelFingerprint(expectedModel),status:'validated'};
  const turnEvidence={turnId:'t1',state:1,messageStartIndex:0,analysisRunIds:['run-1'],reportHash:resultFingerprint(state.report)};
  const artifactEvidence={'run-1':{selection,modelHash:modelFingerprint(model),resultHash:resultFingerprint(data),
    artifactBytes:{normalizedInput:input,solverResponse:output}}};
  return {state,expectedModel:structuredClone(expectedModel),engineId:'builtin-opensees',stateNumber:1,quantities:[q],
    sourceHash,referenceEvidence,turnEvidence,artifactEvidence};
}
function loaded(options) {
  const quantities=options.quantities.map(({value,...q})=>q);
  return {id:'STD-test',models:[options.expectedModel],referenceRequests:{states:[{state:1,quantities,derived:[]}]},
    reference:{toleranceFrozenBeforeCandidate:true,states:[{state:1,quantities:options.quantities}]},
    contract:{evaluationProfile:'engineering-v2.3',plannedEngine:'opensees',modelStates:['model-state-1.json'],
      turns:[{id:'t1',state:1,expectation:'analyze'}],requiredOutputs:[{id:'deflection',state:1,kind:'numerical',quantityIds:['deflection']}]}};
}
const evidence=o=>({sourceHash:o.sourceHash,referenceEvidence:o.referenceEvidence,turnEvidence:o.turnEvidence,artifactEvidence:o.artifactEvidence});

test('certified PKPM precision applies to execution and converted current reports while retaining strict results',()=>{
  const o=setup(),q=o.quantities[0],terms=[.25,-.24,.20,-.21573248237696908],u=2**-24;
  const scale=terms.reduce((a,b)=>a+Math.abs(b),0),observed=-.005732482376969078;
  Object.assign(q,{location:{kind:'member',id:o.expectedModel.elements[0].id,positionM:0,side:'right'},component:'M2',
    rawTrace:{origin:'raw-sdk-member-end-cut',nativeRun:'native-test',sourceModelSha256:'b'.repeat(64),
      sourceSelection:structuredClone(q.selection),sourceFactors:{[q.selection.id]:1},nativeBasicFactors:{DL:1},
      raw:[{nativeCase:'DL',factor:1}],end:0,sourceEndNodes:o.expectedModel.elements[0].nodes},
    unit:'kN.m',value:-.005732506513595581,engineeringPrecision:{policy:'native-f32-recovery-scale-v1',
      kind:'analytical-recovery-scale',nativeArithmeticBound:false,acceptanceRegionChanges:true,unit:'kN.m',unitRoundoff:u,
      terms,structuralTermCount:4,recoveryScale:scale,absoluteAllowance:7*u/(1-7*u)*scale,certificateSha256:'a'.repeat(64)}});
  o.engineId='pkpm';o.referenceEvidence.engineId='pkpm';o.referenceEvidence.status='native-verified';
  const record=o.state.analysisResult.results[key];record.meta.engineId='pkpm';record.data.execution.solver='PKPM';
  record.data.memberResponses=[{id:q.location.id,state:'recovered',samples:[{x:0,side:'right',M2:observed}]}];
  o.artifactEvidence['run-1'].resultHash=resultFingerprint(record.data);
  o.state.report={markdown:`| ${q.id} | ${key} | ${q.location.id}@0:right | M2 | ${observed*1000} | N.m |`};
  o.turnEvidence.reportHash=resultFingerprint(o.state.report);
  const c=loaded(o);c.contract.plannedEngine='PKPM';c.contract.turns[0].outputUnits={M2:'N.m'};
  c.reference.notCommercialScoringTruth=false;delete c.referenceRequests.states[0].quantities[0].engineeringPrecision;
  const result=evaluateResearchTurn({caseRecord:c,state:o.state,evidence:evidence(o)});
  assert.equal(result.allPassed,true,JSON.stringify(result));assert.equal(result.evaluatorVersion,'research300-evaluator-v2');
  for(const name of ['requested_quantities','requested_output_body']){
    const metric=result.metrics.find(m=>m.metric===name);assert.equal(metric.precision.strictPass,false);assert.equal(metric.pass,true);
  }
  o.engineId='opensees';o.referenceEvidence.engineId='opensees';o.referenceEvidence.status='validated';
  const invalid=evaluateBoundQuantities(o);assert.equal(invalid.status,'configuration_error');assert.match(JSON.stringify(invalid),/requires PKPM/);
});

test('v2.3 quantities pass only with complete independently bound model/engine/state/source/results/artifacts',()=>{
  const o=setup(),r=evaluateBoundQuantities(o);assert.equal(r.allPassed,true,JSON.stringify(r));
  assert.equal(evaluateResearchTurn({caseRecord:loaded(o),state:o.state,evidence:evidence(o)}).status,'pass');
});
for(const [name,change] of [
  ['frozen model',o=>delete o.expectedModel],['target engine',o=>delete o.engineId],
  ['reference',o=>delete o.referenceEvidence],['state',o=>delete o.stateNumber],['source',o=>delete o.sourceHash],
  ['quantity list',o=>o.quantities=[]],['frozen value',o=>delete o.quantities[0].value],
  ['tolerance',o=>delete o.quantities[0].tolerance],['reference model',o=>o.referenceEvidence.modelHash=sha('other')],
  ['reference state',o=>o.referenceEvidence.state=2],['reference engine',o=>o.referenceEvidence.engineId='pkpm'],
  ['reference source',o=>o.referenceEvidence.sourceHash=sha('other')],['turn boundary',o=>delete o.turnEvidence],
  ['turn state',o=>o.turnEvidence.state=2],['duplicate quantities',o=>o.quantities.push({...o.quantities[0]})],
  ['undeclared reference case',o=>o.quantities[0].selection={kind:'case',id:'absent'}],
]) test(`missing/wrong ${name} is a configuration error, never a candidate score`,()=>{
  const o=setup();change(o);const r=evaluateBoundQuantities(o);assert.equal(r.status,'configuration_error',JSON.stringify(r));assert.equal(r.score,null);
});
for(const [name,change] of [
  ['model geometry',o=>o.state.model.nodes[1].x+=1],
  ['engine',o=>o.state.analysisResult.results[key].meta.engineId='yjk'],
  ['state',o=>o.state.analysisResult.results[key].meta.state=2],
  ['source',o=>o.state.analysisResult.results[key].meta.sourceHash=sha('wrong-source')],
  ['selected kind',o=>o.state.analysisResult.results[key].selection={kind:'combination',id:selection.id}],
  ['selected case',o=>o.state.analysisResult.results[key].selection={kind:'case',id:'L'}],
  ['selection result',o=>delete o.state.analysisResult.results[key]],
  ['execution',o=>delete o.state.analysisResult.results[key].data.execution],
  ['current run',o=>o.turnEvidence.analysisRunIds=[]],
  ['artifact bytes',o=>o.artifactEvidence['run-1'].artifactBytes.solverResponse=Buffer.from('tampered')],
  ['result extraction',o=>delete o.artifactEvidence['run-1'].resultHash],
  ['stale hash',o=>o.state.analysisResult.results[key].meta.modelHash=sha('old')],
  ['pending edit',o=>o.state.modelPending=true],
  ['missing displacement',o=>delete o.state.analysisResult.results[key].data.displacements],
]) test(`candidate ${name} mismatch fails closed`,()=>{
  const o=setup();change(o);const r=evaluateBoundQuantities(o);assert.equal(r.status,'agent_failure',JSON.stringify(r));assert.equal(r.allPassed,false);
});
test('valid receipt cannot bless different selected response data',()=>{
  const o=setup();o.state.analysisResult.results[key].data.extraResponse=4;
  const r=evaluateBoundQuantities(o);assert.equal(r.allPassed,false);assert.match(JSON.stringify(r),/trusted artifact extraction/);
});
test('a query may use a bound previous-state run, but an edit requires a current run',()=>{
  const o=setup();o.turnEvidence.analysisRunIds=[];
  assert.equal(evaluateBoundQuantities(o).allPassed,false);
  assert.equal(evaluateBoundQuantities({...o,requireCurrentTurn:false}).allPassed,true);
});
test('same-name case and combination never substitute even if numeric values match',()=>{
  const o=setup();o.expectedModel.load_combinations=[{id:selection.id,factors:{[selection.id]:1}}];
  o.state.model=structuredClone(o.expectedModel);
  o.referenceEvidence.modelHash=modelFingerprint(o.expectedModel);
  o.quantities[0].selection={kind:'combination',id:selection.id};
  const r=evaluateBoundQuantities(o);assert.equal(r.allPassed,false);assert.match(JSON.stringify(r),/Required result combination/);
});
test('commercial reference absence remains pending, not an agent failure',()=>{
  const o=setup();o.engineId='pkpm';delete o.referenceEvidence;
  assert.equal(evaluateBoundQuantities(o).status,'native_truth_pending');
  o.referenceEvidence={engineId:'pkpm',state:1,modelHash:modelFingerprint(o.expectedModel),sourceHash:o.sourceHash,status:'validated'};
  assert.equal(evaluateBoundQuantities(o).status,'native_truth_pending');
});
test('diagnostic commercial matrix values cannot be promoted by a native status flag',()=>{
  const o=setup(),c=loaded(o);c.contract.plannedEngine='yjk';c.reference.notCommercialScoringTruth=true;
  o.referenceEvidence.engineId='yjk';o.referenceEvidence.status='native-verified';
  assert.equal(evaluateResearchTurn({caseRecord:c,state:o.state,evidence:evidence(o)}).status,'native_truth_pending');
});
test('all requested outputs need independent values and exact frozen request signatures',()=>{
  for(const change of [c=>c.reference.states[0].quantities=[],c=>c.reference.states[0].quantities[0].location.id='other',
    c=>c.contract.requiredOutputs[0].quantityIds.push('omitted'),c=>delete c.reference.toleranceFrozenBeforeCandidate]) {
    const o=setup(),c=loaded(o);c.reference=structuredClone(c.reference);change(c);
    const r=evaluateResearchTurn({caseRecord:c,state:o.state,evidence:evidence(o)});assert.equal(r.status,'configuration_error',JSON.stringify(r));
  }
});
test('numeric output cannot satisfy a figure requirement',()=>{
  const o=setup(),c=loaded(o);c.contract.requiredOutputs.push({id:'diagram',state:1,kind:'figure',quantityIds:[]});
  assert.equal(evaluateResearchTurn({caseRecord:c,state:o.state,evidence:evidence(o)}).allPassed,false);
  const e={...evidence(o),figureEvidence:[{outputId:'diagram',state:1,sourceHash:o.sourceHash,sha256:sha('image'),runId:'run-1',verified:true}]};
  assert.equal(evaluateResearchTurn({caseRecord:c,state:o.state,evidence:e}).allPassed,true);
});
test('correct solver values cannot satisfy an omitted or mislabelled requested answer',()=>{
  for(const change of [o=>delete o.state.report,o=>o.state.report.markdown=o.state.report.markdown.replace(' m |',' mm |'),
    o=>o.state.report.markdown=o.state.report.markdown.replace(' -0.001 |',' 0.001 |')]) {
    const o=setup();change(o);
    const r=evaluateResearchTurn({caseRecord:loaded(o),state:o.state,evidence:evidence(o)});
    assert.equal(r.status,'agent_failure');assert.equal(r.metrics.find(m=>m.metric==='requested_output_body').pass,false);
  }
});
test('later clarification uses current events, not earlier successful analysis/questions',async()=>{
  const o=setup(),historical={role:'assistant',tool_calls:[{name:'run_analysis',args:{}}]},
    question={role:'assistant',tool_calls:[{name:'ask_user_clarification',args:{question:'Please specify stiffness',field:'stiffness'}}]};
  o.state.messages=[historical,question];o.turnEvidence={turnId:'t2',state:null,messageStartIndex:1,analysisRunIds:[]};
  const c=loaded(o);c.contract.turns.push({id:'t2',state:null,expectation:'clarify',unresolvedFields:['stiffness']});
  assert.equal(evaluateResearchTurn({caseRecord:c,turnIndex:1,state:o.state,evidence:evidence(o)}).allPassed,true);
  let judged;
  const answer=await evaluateInteractionEvidence(o.state,async(_,s)=>{judged=s;return {pass:true};},o.turnEvidence);
  assert.equal(answer.pass,true);assert.equal(judged.analysisResult,null);assert.equal(judged.messages.length,1);
  const scoped=await evaluateScenario({id:'later-clarify',evaluationProfile:'engineering-v2.3',turnExpectation:'clarify',
    expect:{assertions:[{type:'should_not_analyze'}]}},o.state,0,evidence(o));assert.equal(scoped.allPassed,true);
  o.turnEvidence.messageStartIndex=2;
  assert.equal(evaluateResearchTurn({caseRecord:c,turnIndex:1,state:o.state,evidence:evidence(o)}).allPassed,false);
});
test('current attempted analysis rejects clarification even if the current result is missing',()=>{
  const o=setup(),c=loaded(o);c.contract.turns[0]={id:'t1',state:1,expectation:'clarify',unresolvedFields:[]};
  o.state.messages=[{role:'assistant',tool_calls:[{name:'ask_user_clarification',args:{question:'Which section?'}}]}];
  assert.equal(evaluateResearchTurn({caseRecord:c,state:o.state,evidence:evidence(o)}).allPassed,false);
  o.turnEvidence.analysisRunIds=[];o.state.messages.push({name:'run_analysis'});
  assert.equal(evaluateResearchTurn({caseRecord:c,state:o.state,evidence:evidence(o)}).allPassed,false);
});
test('turn evidence is benchmark input and cannot be spoofed on candidate state',()=>{
  const o=setup();o.state.turnEvidence=o.turnEvidence;
  assert.throws(()=>scopeTurnState(o.state,undefined),/benchmark turnEvidence/);
  assert.equal(evaluateResearchTurn({caseRecord:loaded(o),state:o.state,evidence:{}}).status,'configuration_error');
});
test('evaluateScenario forwards strict profile evidence and preserves unavailable-reference status',async()=>{
  const o=setup(),scenario={id:'profile',evaluationProfile:'engineering-v2.3',analysisEngineTarget:o.engineId,
    expect:{assertions:[{type:'numerical_matches',expectedModel:o.expectedModel,state:1,quantities:o.quantities}]}};
  assert.equal((await evaluateScenario(scenario,o.state,0,evidence(o))).allPassed,true);
  scenario.analysisEngineTarget='pkpm';delete o.referenceEvidence;
  const r=await evaluateScenario(scenario,o.state,0,evidence(o));assert.equal(r.status,'native_truth_pending');assert.equal(r.passed,null);
});

test('profile cannot bypass mandatory numerical gates with a has_analysis-only assertion',async()=>{
  const o=setup();
  const r=await evaluateScenario({id:'gate-omission',evaluationProfile:'engineering-v2.3',expect:{assertions:[{type:'has_analysis'}]}},o.state,0,evidence(o));
  assert.equal(r.status,'configuration_error');
});
test('current-turn execution events invalidate clarification even without a returned artifact',async()=>{
  const o=setup();o.state.analysisResult=null;o.state.messages=[{role:'assistant',content:'Please supply the modulus?'}];
  const r=await evaluateInteractionEvidence(o.state,async()=>{throw Error('must reject before judge');},o.turnEvidence);
  assert.equal(r.pass,false);
  const evaluated=await evaluateScenario({id:'attempt',evaluationProfile:'engineering-v2.3',turnExpectation:'clarify',expect:{assertions:[{type:'should_not_analyze'}]}},o.state,0,evidence(o));
  assert.equal(evaluated.allPassed,false);
});
test('one immutable solver run can bind multiple distinct selections and response digests',()=>{
  const o=setup(),other={kind:'combination',id:o.expectedModel.load_combinations[0].id},otherKey=`combination:${other.id}`;
  const row=structuredClone(o.state.analysisResult.results[key]);row.selection=other;
  row.data.displacements[o.quantities[0].location.id].uz=-.002;o.state.analysisResult.results[otherKey]=row;
  o.quantities.push({...o.quantities[0],selection:other,value:-.002});
  const proof=o.artifactEvidence['run-1'];delete proof.selection;delete proof.resultHash;
  proof.selections=[selection,other];proof.resultHashes={[key]:resultFingerprint(o.state.analysisResult.results[key].data),[otherKey]:resultFingerprint(row.data)};
  assert.equal(evaluateBoundQuantities(o).allPassed,true);
  delete proof.resultHashes[otherKey];assert.equal(evaluateBoundQuantities(o).allPassed,false);
});
test('independently frozen numeric values still reject a fully evidenced wrong response',()=>{
  const o=setup(),data=o.state.analysisResult.results[key].data;
  data.displacements[o.quantities[0].location.id].uz=.001;
  o.artifactEvidence['run-1'].resultHash=resultFingerprint(data);
  const r=evaluateBoundQuantities(o);assert.equal(r.metrics.find(m=>m.metric==='requested_quantities').pass,false);
});
test('derived output preserves signed value and governing selection independently of candidate reporting',()=>{
  const o=setup(),c=loaded(o);
  c.referenceRequests.states[0].derived=[{id:'envelope',operation:'max_abs',operands:['deflection'],unit:'m'}];
  c.contract.requiredOutputs.push({id:'envelope',state:1,kind:'derived',quantityIds:['envelope']});
  let r=evaluateResearchTurn({caseRecord:c,state:o.state,evidence:evidence(o)});
  assert.equal(r.allPassed,false);assert.match(JSON.stringify(r),/Reported derived quantity is missing/);
  o.state.report.derivedQuantities=[{id:'envelope',value:-.001,unit:'m',governingOperand:'deflection',governingSelection:selection}];
  o.turnEvidence.reportHash=resultFingerprint(o.state.report);
  assert.equal(evaluateResearchTurn({caseRecord:c,state:o.state,evidence:evidence(o)}).allPassed,true);
  o.state.report.derivedQuantities[0].value=.001;
  assert.equal(evaluateResearchTurn({caseRecord:c,state:o.state,evidence:evidence(o)}).allPassed,false);
  c.referenceRequests.states[0].derived[0].operands=['missing'];
  assert.equal(evaluateResearchTurn({caseRecord:c,state:o.state,evidence:evidence(o)}).status,'configuration_error');
});
test('a query requires a current answer instead of a persisted historical report',()=>{
  const o=setup(),c=loaded(o);c.contract.turns[0].expectation='query';o.turnEvidence.analysisRunIds=[];delete o.turnEvidence.reportHash;
  assert.equal(evaluateResearchTurn({caseRecord:c,state:o.state,evidence:evidence(o)}).allPassed,false);
  o.state.messages=[{role:'assistant',content:o.state.report.markdown}];
  assert.equal(evaluateResearchTurn({caseRecord:c,state:o.state,evidence:evidence(o)}).allPassed,true);
});
test('locale-aware expected clarification can be asked without exposing internal field paths',()=>{
  const o=setup(),c=loaded(o);c.contract.locale='zh';
  c.contract.turns[0]={id:'t1',state:1,expectation:'clarify',unresolvedFields:['/materials/0/E'],expectedQuestions:['请提供材料弹性模量？']};
  o.turnEvidence.analysisRunIds=[];o.state.messages=[{role:'assistant',content:'请提供材料弹性模量?'}];
  assert.equal(evaluateResearchTurn({caseRecord:c,state:o.state,evidence:evidence(o)}).allPassed,true);
  o.state.messages[0].content='请提供其他信息？';
  assert.equal(evaluateResearchTurn({caseRecord:c,state:o.state,evidence:evidence(o)}).allPassed,false);
});
test('query figures must belong to an actual verified selection run',()=>{
  const o=setup(),c=loaded(o);c.contract.turns[0].expectation='query';o.turnEvidence.analysisRunIds=[];
  c.contract.requiredOutputs.push({id:'diagram',state:1,kind:'figure',quantityIds:[]});
  const e={...evidence(o),figureEvidence:[{outputId:'diagram',state:1,sourceHash:o.sourceHash,sha256:sha('image'),runId:'unrelated',verified:true}]};
  assert.equal(evaluateResearchTurn({caseRecord:c,state:o.state,evidence:e}).allPassed,false);
  e.figureEvidence[0].runId='run-1';assert.equal(evaluateResearchTurn({caseRecord:c,state:o.state,evidence:e}).allPassed,true);
});
test('raw response hashes exclude only the top-level execution envelope and preserve array order',()=>{
  assert.equal(resultFingerprint({value:1}),resultFingerprint({execution:{receipt:'external'},value:1}));
  assert.notEqual(resultFingerprint({value:1}),resultFingerprint({value:2}));
  assert.notEqual(resultFingerprint({value:{execution:1}}),resultFingerprint({value:{execution:2}}));
  assert.notEqual(resultFingerprint([{id:'a'},{id:'b'}]),resultFingerprint([{id:'b'},{id:'a'}]));
});
test('current-turn selectors avoid grading future outputs and apply explicit query output units',()=>{
  const o=setup(),c=loaded(o),future={...o.quantities[0],id:'future-deflection',location:{kind:'node',id:o.expectedModel.nodes[0].id}};
  c.referenceRequests.states[0].quantities.push((({value,...q})=>q)(future));
  c.contract.requiredOutputs.push({id:'future',state:1,kind:'numerical',quantityIds:['future-deflection'],turnIds:['t2']});
  c.contract.requiredOutputs[0].turnIds=['t1'];
  c.contract.turns[0].requiredQuantityIds=['deflection'];
  c.contract.turns[0].requiredOutputIds=['deflection'];
  // Future solver value/reference/report is absent, but is not requested yet.
  assert.equal(evaluateResearchTurn({caseRecord:c,state:o.state,evidence:evidence(o)}).allPassed,true);
  c.contract.turns[0].outputUnits={uz:'mm'};c.contract.turns[0].expectation='query';
  assert.equal(evaluateResearchTurn({caseRecord:c,state:o.state,evidence:evidence(o)}).allPassed,false);
  o.state.report.markdown=o.state.report.markdown.replace('-0.001 | m','-1 | mm');
  o.turnEvidence.reportHash=resultFingerprint(o.state.report);
  assert.equal(evaluateResearchTurn({caseRecord:c,state:o.state,evidence:evidence(o)}).allPassed,true);
});
test('nested derived operands are verified without inventing intermediate reporting requirements',()=>{
  const o=setup(),c=loaded(o);c.referenceRequests.states[0].derived=[
    {id:'total',operation:'sum',operands:['deflection','deflection'],unit:'m'},
    {id:'envelope',operation:'max_abs',operands:['total'],unit:'m'}];
  c.contract.requiredOutputs=[{id:'envelope',state:1,kind:'derived',quantityIds:['envelope']}];
  c.contract.turns[0].requiredOutputIds=['envelope'];
  o.state.report={derivedQuantities:[{id:'envelope',value:-.002,unit:'m',governingOperand:'total',governingSelection:selection}]};
  o.turnEvidence.reportHash=resultFingerprint(o.state.report);
  assert.equal(evaluateResearchTurn({caseRecord:c,state:o.state,evidence:evidence(o)}).allPassed,true);
  o.state.analysisResult.results[key].data.displacements[o.quantities[0].location.id].uz=-2;
  assert.equal(evaluateResearchTurn({caseRecord:c,state:o.state,evidence:evidence(o)}).allPassed,false);
});
test('v2.3 execution cannot omit success codes or hide behind unknown/pending solver metadata',()=>{
  for(const change of [e=>delete e.analysisReturnCode,e=>e.solver='unrecognized',e=>e.solverVersion={},e=>e.status='pending']) {
    const o=setup();change(o.state.analysisResult.results[key].data.execution);
    assert.equal(evaluateBoundQuantities(o).allPassed,false);
  }
});
test('derived values have a public current-message JSON or markdown path without a reportHash',()=>{
  for(const format of ['json','markdown']) {
    const o=setup(),c=loaded(o);delete o.turnEvidence.reportHash;
    c.referenceRequests.states[0].derived=[{id:'envelope',operation:'max_abs',operands:['deflection'],unit:'m'}];
    c.contract.requiredOutputs.push({id:'envelope',state:1,kind:'derived',quantityIds:['envelope']});
    const derived={id:'envelope',value:-.001,unit:'m',governingOperand:'deflection',governingSelection:selection};
    const answer=format==='json'?'```json\n'+JSON.stringify({derivedQuantities:[derived]})+'\n```':
      `| derived | envelope | -0.001 | m | deflection | ${key} |`;
    o.state.messages=[{role:'assistant',content:o.state.report.markdown+'\n'+answer}];
    assert.equal(evaluateResearchTurn({caseRecord:c,state:o.state,evidence:evidence(o)}).allPassed,true,format);
    o.state.messages[0].content=o.state.messages[0].content.replaceAll('-0.001','0.001');
    assert.equal(evaluateResearchTurn({caseRecord:c,state:o.state,evidence:evidence(o)}).allPassed,false,format);
  }
});
test('non-blocking output ambiguity requires both current analysis and a current question',()=>{
  const o=setup(),c=loaded(o);Object.assign(c.contract.turns[0],{clarificationBlocksAnalysis:false,
    unresolvedFields:['/requestedOutputs/maximum/scope'],expectedQuestions:['Which members should the maximum cover?']});
  assert.equal(evaluateResearchTurn({caseRecord:c,state:o.state,evidence:evidence(o)}).allPassed,false);
  o.state.messages=[{role:'assistant',content:'Which members should the maximum cover?'}];
  assert.equal(evaluateResearchTurn({caseRecord:c,state:o.state,evidence:evidence(o)}).allPassed,true);
  o.turnEvidence.analysisRunIds=[];
  assert.equal(evaluateResearchTurn({caseRecord:c,state:o.state,evidence:evidence(o)}).allPassed,false);
  c.contract.turns[0].unresolvedFields=['/materials/0/E'];
  assert.equal(evaluateResearchTurn({caseRecord:c,state:o.state,evidence:evidence(o)}).status,'configuration_error');
});
test('trusted current-answer assessment accepts a real clarification paraphrase without hidden field names',()=>{
  const o=setup(),c=loaded(o);c.contract.turns[0]={id:'t1',state:null,expectation:'clarify',requiredOutputIds:['scope-question'],
    unresolvedFields:['/loads/crane/verticalMultiplier'],expectedQuestions:['Should the twenty-percent increase apply to the vertical crane load only?']};
  c.contract.requiredOutputs=[{id:'scope-question',state:null,kind:'interaction',quantityIds:[]}];
  o.turnEvidence.state=null;o.turnEvidence.analysisRunIds=[];
  o.state.messages=[{role:'assistant',content:'Do you want me to scale just the downward crane force, leaving the horizontal force unchanged?'}];
  const assessed={outputId:'scope-question',turnId:'t1',state:null,sourceHash:o.sourceHash,pass:true,reason:'offline reviewer confirmed missing load scope question'};
  const e={...evidence(o),interactionEvidence:[assessed]};
  assert.equal(evaluateResearchTurn({caseRecord:c,state:o.state,evidence:e}).allPassed,true);
  for(const change of [a=>a.pass=false,a=>a.turnId='t2',a=>a.outputId='unrelated',a=>a.sourceHash=sha('stale')]) {
    const bad=structuredClone(assessed);change(bad);
    assert.equal(evaluateResearchTurn({caseRecord:c,state:o.state,evidence:{...e,interactionEvidence:[bad]}}).allPassed,false);
  }
  assert.equal(evaluateResearchTurn({caseRecord:c,state:o.state,evidence:evidence(o)}).allPassed,false);
  o.state.interactionEvidence=[assessed];
  assert.equal(evaluateResearchTurn({caseRecord:c,state:o.state,evidence:evidence(o)}).allPassed,false);
  o.turnEvidence.analysisRunIds=['run-1'];
  assert.equal(evaluateResearchTurn({caseRecord:c,state:o.state,evidence:e}).allPassed,false);
});
test('per-turn established moment spellings work without permitting incompatible dimensions',()=>{
  const o=setup(),q=o.quantities[0];q.component='My';q.unit='kN.m';q.value=-2;
  const data=o.state.analysisResult.results[key].data;data.reactions={[q.location.id]:{my:-2}};
  o.artifactEvidence['run-1'].resultHash=resultFingerprint(data);
  const c=loaded(o);c.contract.turns[0].outputUnits={My:'N*m'};
  o.state.report.markdown=`| ${q.id} | ${key} | ${q.location.id} | My | -2000 | N*m |`;
  o.turnEvidence.reportHash=resultFingerprint(o.state.report);
  assert.equal(evaluateResearchTurn({caseRecord:c,state:o.state,evidence:evidence(o)}).allPassed,true);
  c.contract.turns[0].outputUnits.My='mm';
  assert.equal(evaluateResearchTurn({caseRecord:c,state:o.state,evidence:evidence(o)}).status,'configuration_error');
});
test('any-tie envelope accepts a current public physical governor only with that governor signed value',()=>{
  const o=setup();o.quantities[0].id='private-negative';
  const second={...o.quantities[0],id:'private-positive',location:{kind:'node',id:o.expectedModel.nodes[0].id},value:.001};
  o.quantities.push(second);
  const data=o.state.analysisResult.results[key].data;data.displacements[second.location.id]={uz:.001};
  o.artifactEvidence['run-1'].resultHash=resultFingerprint(data);
  const c=loaded(o);c.referenceRequests.states[0].derived=[{id:'envelope',operation:'max_abs',operands:['private-negative','private-positive'],unit:'m',tiePolicy:'any'}];
  c.contract.requiredOutputs=[{id:'envelope',kind:'derived',state:1,quantityIds:['envelope']}];
  c.contract.turns[0].requiredOutputIds=['envelope'];delete o.turnEvidence.reportHash;
  const row={id:'envelope',value:.001,unit:'m',governingOperand:second.location.id,governingSelection:selection};
  const answer=()=>{o.state.messages=[{role:'assistant',content:'```json\n'+JSON.stringify({derivedQuantities:[row]})+'\n```'}];};
  answer();assert.equal(evaluateResearchTurn({caseRecord:c,state:o.state,evidence:evidence(o)}).allPassed,true);
  row.value=-.001;answer();assert.equal(evaluateResearchTurn({caseRecord:c,state:o.state,evidence:evidence(o)}).allPassed,false);
  row.value=.001;c.referenceRequests.states[0].derived[0].tiePolicy='first';answer();
  assert.equal(evaluateResearchTurn({caseRecord:c,state:o.state,evidence:evidence(o)}).allPassed,false);
});
test('malformed frozen output references are configuration errors',()=>{
  for(const change of [o=>o.quantities[0].unit='kN',o=>o.quantities[0].location.id='absent',o=>o.quantities[0].component='N',
    o=>o.expectedModel.nodes[0].x=NaN]) {
    const o=setup();change(o);assert.equal(evaluateBoundQuantities(o).status,'configuration_error');
  }
});
test('semantic interaction outputs require an explicit benchmark assessment',()=>{
  const o=setup(),c=loaded(o);c.contract.requiredOutputs.push({id:'explanation',state:1,kind:'interaction',quantityIds:[]});
  assert.equal(evaluateResearchTurn({caseRecord:c,state:o.state,evidence:evidence(o)}).status,'configuration_error');
  const e={...evidence(o),interactionEvidence:[{outputId:'explanation',turnId:'t1',state:1,sourceHash:o.sourceHash,pass:true,reason:'independently assessed'}]};
  assert.equal(evaluateResearchTurn({caseRecord:c,state:o.state,evidence:e}).allPassed,true);
  e.interactionEvidence[0].pass=false;
  assert.equal(evaluateResearchTurn({caseRecord:c,state:o.state,evidence:e}).status,'agent_failure');
});
