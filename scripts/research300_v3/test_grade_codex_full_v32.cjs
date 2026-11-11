'use strict';
// Synthetic coverage records, never native executions or benchmark outcomes.
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {collection,sha}=require('./test-support-v32.cjs');
const {grade}=require('./grade_codex_full_v32.cjs');
const {codeBinding}=require('./code-closure-v32.cjs');
function fixture(t){
 const f=collection(t),edition=path.join(f.root,'edition');fs.mkdirSync(edition);
 fs.writeFileSync(path.join(edition,'ref.json'),JSON.stringify(f.ref));
 const cases=[];
 for(const family of ['STD','MM','INT'])for(let i=1;i<=100;i++){
  const count=family==='INT'?(i<=60?4:3):1;
  cases.push({id:'V3-'+family+'-'+String(i).padStart(3,'0'),engine:'OpenSees',split:'test',family,level:'L1',analysis:'static',
   turns:Array.from({length:count},(_,j)=>({id:'t'+(j+1),private:'ref.json'}))});
 }
 const manifest={files:[{path:'ref.json',sha256:sha(fs.readFileSync(path.join(edition,'ref.json')))}],cases};
 fs.writeFileSync(path.join(edition,'manifest.json'),JSON.stringify(manifest));
 const original=f.index.turns[0];
 f.index.turns=cases.flatMap(c=>c.turns.map(t=>c.id===f.caseId&&t.id==='t1'?original:{caseId:c.id,turnId:t.id,
  captureComplete:true,environmentStatus:'ready',candidateStatus:'candidate_failed',currentJobIds:[]}));
 const binding=f.put('binding.json',{sutCommit:f.options.sutCommit,evaluationCode:codeBinding(),controllerCode:{}});
 const spec={kind:'research300-v32-codex-full-specification',formalComparisonScore:false,scope:'full-frozen-regression',
  inputProtocol:f.options.inputProtocol,sourceBinding:binding,sutCommit:f.options.sutCommit,
  editionManifestSha256:sha(fs.readFileSync(path.join(edition,'manifest.json'))),cases:cases.map(c=>c.id),plannedTurns:560};
 const pin={kind:'research300-v32-codex-full-operator-pin',formalComparisonScore:false,sourceBinding:binding};
 const pinPath=f.root+'-pin.json';t.after(()=>fs.rmSync(pinPath,{force:true}));
 function seal(){
  pin.specification=f.put('specification.json',spec);
  f.index.editionManifestSha256=spec.editionManifestSha256;f.index.executionSpecificationSha256=pin.specification.sha256;
  pin.index=f.put('index.json',f.index);
  pin.inventory=f.put('inventory.json',{files:[...Object.values(f.entry.files),original.answer]});
  fs.writeFileSync(pinPath,JSON.stringify(pin));
  return {edition,controlRoot:f.root,pinPath,pinSha256:sha(fs.readFileSync(pinPath))};
 }
 return {f,spec,pin,seal};
}
test('full diagnostic retains all 560 turns and never becomes formal',t=>{
 const x=fixture(t),r=grade(x.seal());assert.equal(r.rows.length,560);assert.equal(r.caseRows.length,300);
 assert.equal(r.counts.passed,1);assert.equal(r.counts.candidate_failure,559);assert.equal(r.formalComparisonScore,false);
});
test('partial index cannot masquerade as full coverage',t=>{
 const x=fixture(t);x.f.index.turns.pop();assert.throws(()=>grade(x.seal()),/FULL_TURN_COVERAGE_REQUIRED/);
});
test('selected case list cannot be shortened to inflate scores',t=>{
 const x=fixture(t);x.spec.cases.pop();assert.throws(()=>grade(x.seal()),/FULL_SCOPE_COVERAGE_REQUIRED/);
});
test('infrastructure blockage and capture interruption are separate from model errors',t=>{
 const x=fixture(t);x.f.index.turns[1].candidateStatus='service_blocked';
 x.f.index.turns[2].candidateStatus='interrupted';x.f.index.turns[2].captureComplete=false;
 const r=grade(x.seal());assert.equal(r.counts.blocked_configuration,1);assert.equal(r.counts.ungradable_evidence,1);
 assert.equal(r.counts.candidate_failure,557);assert.equal(r.rows.length,560);
});
test('external pin remains mandatory',t=>{
 const x=fixture(t);assert.throws(()=>grade({...x.seal(),pinSha256:'0'.repeat(64)}),/OPERATOR_PIN_REQUIRED/);
});
