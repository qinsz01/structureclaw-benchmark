'use strict';
// Synthetic verifier-only records; these are not solver executions.
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {collection,sha}=require('./test-support-v32.cjs'),{codeBinding}=require('./code-closure-v32.cjs');
const {grade}=require('./grade_codex_recovery_v32.cjs');
function fixture(t){
 const f=collection(t),edition=path.join(f.root,'edition');fs.mkdirSync(edition);
 f.ref.engine='PKPM';f.state.analysisResult.meta.engineId='builtin-pkpm';f.entry.engine=f.receipt.engine='PKPM';f.seal();
 fs.writeFileSync(path.join(edition,'ref.json'),JSON.stringify(f.ref));
 const cases=Array.from({length:300},(_,i)=>({id:'V3-STD-'+String(i+1).padStart(3,'0'),engine:'PKPM',family:'STD',level:'L1',analysis:'static',split:'test',turns:[{id:'t1',private:'ref.json'}]}));
 fs.writeFileSync(path.join(edition,'manifest.json'),JSON.stringify({cases,files:[{path:'ref.json',sha256:sha(fs.readFileSync(path.join(edition,'ref.json')))}]}));
 const original=f.index.turns[0];f.index.turns.push({caseId:cases[1].id,turnId:'t1',captureComplete:true,environmentStatus:'ready',candidateStatus:'candidate_failed',currentJobIds:[]});
 const binding=f.put('binding.json',{sutCommit:f.options.sutCommit,evaluationCode:codeBinding(),controllerCode:{}});
 const parent={replacesOriginalScores:false,faults:cases.slice(0,2).map(c=>({caseId:c.id,capturedFaultReceipts:[f.put(c.id+'-prior-fault.json',{
  caseId:c.id,engine:'PKPM',ok:false,error:'Synthetic verifier-only /codex_trial/remote.py Permission denied (publickey).'})]}))};
 const spec={kind:'research300-v32-codex-recovery-specification',formalComparisonScore:false,scope:'environment-recovery-supplement',replacesOriginalScores:false,
  inputProtocol:f.options.inputProtocol,sourceBinding:binding,sutCommit:f.options.sutCommit,editionManifestSha256:sha(fs.readFileSync(path.join(edition,'manifest.json'))),
  cases:cases.slice(0,2).map(c=>c.id),plannedTurns:2};
 const pin={kind:'research300-v32-codex-recovery-operator-pin',formalComparisonScore:false,sourceBinding:binding},pinPath=f.root+'-pin.json';t.after(()=>fs.rmSync(pinPath,{force:true}));
 function seal(){
  spec.parentExperiment=f.put('parent.json',parent);pin.specification=f.put('spec.json',spec);
  f.index.editionManifestSha256=spec.editionManifestSha256;f.index.executionSpecificationSha256=pin.specification.sha256;
  pin.index=f.put('index.json',f.index);pin.inventory=f.put('inventory.json',{files:[...Object.values(f.entry.files),original.answer]});
  fs.writeFileSync(pinPath,JSON.stringify(pin));return {edition,controlRoot:f.root,pinPath,pinSha256:sha(fs.readFileSync(pinPath))};
 }
 return {f,parent,spec,seal};
}
test('separate recovery retains its complete selected denominator without replacing full outcomes',t=>{
 const x=fixture(t),r=grade(x.seal());assert.equal(r.cases,2);assert.equal(r.plannedTurns,2);
 assert.equal(r.counts.passed,1);assert.equal(r.counts.candidate_failure,1);assert.equal(r.replacesOriginalScores,false);assert.equal(r.formalComparisonScore,false);
});
test('case without a sealed original transport failure is ineligible for the recovery scope',t=>{
 const x=fixture(t);x.parent.faults[0].capturedFaultReceipts=[];assert.throws(()=>grade(x.seal()),/Original transport receipt required/);
});
test('missing recovery turn cannot disappear from denominator',t=>{
 const x=fixture(t);x.f.index.turns.pop();assert.throws(()=>grade(x.seal()),/FULL_TURN_COVERAGE_REQUIRED/);
});
