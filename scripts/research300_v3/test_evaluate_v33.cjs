'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {example}=require('./test-support-v32.cjs');
const old=require('./evaluate-v32.cjs'),current=require('./evaluate-v33.cjs');
function fixture(){
 const x=example(),model=x.ref.model;
 model.load_cases.push({id:'Q',type:'live',loads:[{type:'nodal',node:'B',fz:-2}]});
 model.load_combinations=[{id:'SERVICE',factors:{D:1,Q:1}}];
 x.jobs[0].state.model=structuredClone(model);
 model.load_cases[1].loads[0].fz=-2.4;
 const base=x.ref.requests[0].value,selection={kind:'combination',id:'SERVICE'};
 x.ref.requests.push({...structuredClone(x.ref.requests[0]),id:'service',selection,value:base*3.4});
 x.ref.reportIds=['tip','service'];x.ref.derived=[];
 const next=structuredClone(x.jobs[0]);next.jobId='2'.repeat(32);next.state.model=structuredClone(model);
 next.state.analysisResult.results={'combination:SERVICE':{selection,data:{units:{displacement:'m'},displacements:{B:{uz:base*3.4}}}}};
 x.jobs.push(next);x.answer.jobIds.push(next.jobId);x.answer.quantities.push({id:'service',value:base*3.4,unit:'m'});
 for(const job of x.jobs)for(const record of Object.values(job.state.analysisResult.results))record.data.meta={execution:{executed:true,analysisReturnCode:0,constitutiveModel:'linear-elastic',solverConfiguration:{algorithm:'Linear',analysis:'Static'}}};
 return x;
}
function grade(x,currentIds=[x.jobs.at(-1).jobId]){return current.evaluate(x.ref,x.answer,x.jobs,currentIds);}
test('unchanged active D can reuse old evidence alongside a complete revised SERVICE model',()=>{
 const x=fixture(),before=JSON.stringify(x);
 assert.equal(old.evaluate(x.ref,x.answer,x.jobs).outcome,'candidate_failure');
 assert.equal(grade(x).outcome,'passed');assert.equal(JSON.stringify(x),before);
});
test('changed active D cannot reuse stale D evidence',()=>{
 const x=fixture();x.ref.model.load_cases[0].loads[0].fz=-1.1;x.jobs[1].state.model=structuredClone(x.ref.model);
 assert.equal(grade(x).outcome,'candidate_failure');
});
test('cached stiffness changes invalidate reuse even when one requested scalar is copied',()=>{
 const x=fixture();x.jobs[0].state.model.materials[0].E*=.8;
 assert.equal(grade(x).outcome,'candidate_failure');
});
test('current state cannot be inferred only from a cached unaffected execution',()=>{
 const x=fixture();x.jobs.pop();x.answer.jobIds.pop();x.ref.requests.pop();x.ref.reportIds.pop();x.answer.quantities.pop();
 assert.equal(grade(x,[]).outcome,'candidate_failure');
});
test('wrong signed report remains a failure after valid physical reuse',()=>{
 const x=fixture();x.answer.quantities[0].value*=-1;
 assert.equal(grade(x).outcome,'candidate_failure');
});
test('explicit fresh-execution requirement still rejects older job identities',()=>{
 const x=fixture();x.ref.requireFreshExecution=true;
 assert.equal(grade(x).outcome,'candidate_failure');
});
test('reuse requires a completed native linear-static execution proof',()=>{
 const x=fixture();delete x.jobs[0].state.analysisResult.results['case:D'].data.meta;
 assert.equal(grade(x).outcome,'candidate_failure');
});
test('changed SERVICE combination cannot be supplied by an old SERVICE run',()=>{
 const x=fixture(),oldModel=structuredClone(x.jobs[0].state.model),currentModel=structuredClone(x.jobs[1].state.model);
 x.jobs[0].state.analysisResult.results=structuredClone(x.jobs[1].state.analysisResult.results);
 x.jobs[0].state.model=oldModel;
 x.jobs[1].state.analysisResult.results=structuredClone(example().jobs[0].state.analysisResult.results);
 x.jobs[1].state.model=currentModel;
 x.jobs[1].state.analysisResult.results['case:D'].data.meta=structuredClone(x.jobs[0].state.analysisResult.results['combination:SERVICE'].data.meta);
 assert.equal(grade(x).outcome,'candidate_failure');
});
test('native numeric corruption is not hidden by a correct final report',()=>{
 const x=fixture();x.jobs[0].state.analysisResult.results['case:D'].data.displacements.B.uz*=2;
 assert.equal(grade(x).outcome,'candidate_failure');
});
test('query-only tasks still reject hidden native attempts',()=>{
 const x=fixture();x.ref.kind='query';
 assert.equal(grade(x,[]).outcome,'passed');assert.equal(grade(x).outcome,'candidate_failure');
});
