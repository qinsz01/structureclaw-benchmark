const test=require('node:test');
const assert=require('node:assert/strict');
const {modelFingerprint,verifyExecutionEvidence}=require('./analysis-evidence.cjs');
const model={nodes:[{id:'a',x:0,y:0,z:0}],load_cases:[{id:'D',loads:[]}],metadata:{elementReferenceVectors:{b:[0,0,1]}}};
const selection={kind:'case',id:'D'};
function state(){return {model:structuredClone(model),analysisResult:{results:{'case:D':{selection,status:'success',
  meta:{runId:'immutable-run',modelHash:modelFingerprint(model)},data:{execution:{executed:true,solver:'OpenSees',solverVersion:'test',analysisReturnCode:0}}}}}};}
test('complete versioned execution is tied to the selected current model',()=>assert.equal(verifyExecutionEvidence(state(),selection).pass,true));
for(const [name,change] of [
  ['stale geometry',s=>s.model.nodes[0].z=1],
  ['stale local axes',s=>s.model.metadata.elementReferenceVectors.b=[0,1,0]],
  ['pending update',s=>s.modelPending=true],
  ['declared engine without execution',s=>delete s.analysisResult.results['case:D'].data.execution],
  ['unversioned solver',s=>delete s.analysisResult.results['case:D'].data.execution.solverVersion],
  ['missing immutable run',s=>delete s.analysisResult.results['case:D'].meta.runId],
  ['failed convergence',s=>s.analysisResult.results['case:D'].data.execution.analysisReturnCode=-3],
  ['partial computation',s=>s.analysisResult.results['case:D'].status='partial'],
]) test(`${name} cannot count as actual engineering verification`,()=>{const s=state();change(s);assert.equal(verifyExecutionEvidence(s,selection).pass,false);});
test('other cases and display annotations do not substitute the requested case',()=>{
  const s=state();s.model.metadata.title='New title';assert.equal(verifyExecutionEvidence(s,selection).pass,true);
  assert.equal(verifyExecutionEvidence(s,{kind:'case',id:'L'}).pass,false);
});
