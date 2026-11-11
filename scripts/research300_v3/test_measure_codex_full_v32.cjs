'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const {example}=require('./test-support-v32.cjs');
const {measureTurn}=require('./measure_codex_full_v32.cjs');
function fixture(t,change=()=>{}){
 const data=example();change(data);
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'continuous-observation-test-'));t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
 const c={id:'V3-STD-001',engine:'OpenSees',level:'L1',family:'STD'},turn={id:'t1',private:'reference.json'};
 // Static report projection explicitly follows the issued reporting scope.
 data.ref.reportIds=['tip'];fs.writeFileSync(path.join(root,turn.private),JSON.stringify(data.ref));
 const x={edition:root,diagnostic:{rows:[{caseId:c.id,turnId:turn.id,outcome:'synthetic-test-only'}]},
  reader:{readAnswer:()=>({...data,currentJobIds:[data.jobs[0].jobId]})}};
 return measureTurn(x,c,turn);
}
test('continuous native/report errors are separate, including a wrong report',t=>{
 const row=fixture(t,x=>{x.answer.quantities[0].value*=2;});
 assert.equal(row.observations.find(r=>r.comparison==='native/reference').withinTolerance,true);
 assert.equal(row.observations.find(r=>r.comparison==='report/native').withinTolerance,false);
});
test('physically mismatched evidence is unavailable, not a zero-error measurement',t=>{
 const row=fixture(t,x=>{x.jobs[0].state.model.materials[0].E*=.8;});
 assert.equal(row.observations.length,0);assert.ok(row.unavailable.length);
});
test('legal unit conversion retains the same signed scalar error',t=>{
 const row=fixture(t,x=>{x.answer.quantities[0].value*=1000;x.answer.quantities[0].unit='mm';});
 assert.equal(row.unavailable.length,0);assert.equal(row.observations.every(r=>r.withinTolerance),true);
});
test('zero reference has explicit null relative error and finite tolerance ratio',t=>{
 const row=fixture(t,x=>{x.ref.requests[0].value=0;});
 const native=row.observations.find(r=>r.comparison==='native/reference');
 assert.equal(native.relativeError,null);assert.equal(Number.isFinite(native.errorOverTolerance),true);
 assert.equal(native.withinTolerance,false);
});
