const test=require('node:test');
const assert=require('node:assert/strict');
const {evaluateScenario}=require('./evaluate.cjs');
const modelTruth=require('../fixtures/ground-truth-models.json');
const numericalTruth=require('../fixtures/opensees-ground-truth.json').models;
const entry=modelTruth.find(x=>x.id==='beam-simple-6m');
const oracle=numericalTruth.find(x=>x.modelId===entry.id);
const {modelFingerprint}=require('./analysis-evidence.cjs');
const selection={kind:'combination',id:'ULS'};
function state() {return {model:structuredClone(entry.model),analysisResult:{results:{'combination:ULS':{status:'success',selection,data:structuredClone(oracle.result)}}},messages:[]};}
function scenario(extra=[]) {return {id:'physical-evaluator-contract',expect:{assertions:[{type:'model_matches',groundTruthId:entry.id},{type:'numerical_matches',groundTruthId:entry.id,selection},...extra]}};}
test('frozen independently checked truth remains readable through the physical evaluator',async()=>{
  const result=await evaluateScenario(scenario(),state(),0);assert.equal(result.allPassed,true,JSON.stringify(result.metrics));
});
test('new evaluation rejects a stale model, reversed load, missing case and incomplete analysis',async()=>{
  for(const change of [s=>s.model.load_cases[0].loads[0].wz=20,s=>delete s.analysisResult.results['combination:ULS'],s=>s.analysisResult.results['combination:ULS'].status='partial']) {
    const s=state();change(s);assert.equal((await evaluateScenario(scenario(),s,0)).allPassed,false);
  }
});
test('execution evidence is opt-in and cannot be fabricated by loading reference values',async()=>{
  const s=state();assert.equal((await evaluateScenario(scenario(),s,0)).allPassed,true);
  const result=await evaluateScenario(scenario([{type:'execution_evidence',selection}]),s,0);
  assert.equal(result.allPassed,false);assert.equal(result.metrics.find(m=>m.metric==='execution_evidence').pass,false);
});
test('historical v2 accepts its frozen flat artifact without rewriting it',async()=>{
  const s=state();s.analysisResult=structuredClone(oracle.result);
  const old=scenario();old.expect.assertions.forEach(x=>x.matcherVersion='v2');
  const result=await evaluateScenario(old,s,0);assert.equal(result.allPassed,true,JSON.stringify(result.metrics));
});
test('new engineering profile cannot bypass execution evidence by omitting its assertion',async()=>{
  const task=scenario();task.evaluationProfile='engineering-v2.2';
  const result=await evaluateScenario(task,state(),0);
  assert.equal(result.allPassed,false);
  assert.match(result.metrics.find(m=>m.metric==='numerical_matches').actual,/execution evidence/);
});

test('execution binding follows a physically verified combination rename for full results and quantities',async()=>{
  const s=state();
  s.model.load_combinations.find(row=>row.id==='ULS').id='renamed-ULS';
  const record=s.analysisResult.results['combination:ULS'];
  record.selection={kind:'combination',id:'renamed-ULS'};
  record.meta={runId:'test-contract-run',modelHash:modelFingerprint(s.model),execution:{executed:true,solverVersion:'test-contract-version'}};
  s.analysisResult.results={'combination:renamed-ULS':record};
  const task=scenario();task.evaluationProfile='engineering-v2.2';
  let result=await evaluateScenario(task,s,0);
  assert.equal(result.allPassed,true,JSON.stringify(result.metrics));
  const node=Object.keys(record.data.displacements)[0];
  const quantity={id:'node-displacement',selection,location:{kind:'node',id:node},component:'ux',unit:'m',
    value:record.data.displacements[node].ux,tolerance:{absolute:1e-10,relative:1e-8}};
  task.expect.assertions=[{type:'numerical_matches',expectedModel:entry.model,quantities:[quantity]}];
  result=await evaluateScenario(task,s,0);assert.equal(result.allPassed,true,JSON.stringify(result.metrics));
  record.meta.modelHash='stale';
  assert.equal((await evaluateScenario(task,s,0)).allPassed,false);
});
