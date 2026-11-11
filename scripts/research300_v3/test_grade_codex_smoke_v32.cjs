'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const {collection,sha}=require('./test-support-v32.cjs');
const {grade}=require('./grade_codex_smoke_v32.cjs');
const {codeBinding}=require('./code-closure-v32.cjs');
function fixture(t){
 const f=collection(t),edition=path.join(f.root,'edition');fs.mkdirSync(edition);
 fs.writeFileSync(path.join(edition,'ref.json'),JSON.stringify(f.ref));
 const manifest={files:[{path:'ref.json',sha256:sha(fs.readFileSync(path.join(edition,'ref.json')))}],cases:[{
  id:f.caseId,split:'dev',engine:'OpenSees',level:'L1',family:'STD',analysis:'static',turns:[{id:'t1',private:'ref.json'}]}]};
 fs.writeFileSync(path.join(edition,'manifest.json'),JSON.stringify(manifest));
 const binding=f.put('binding.json',{sutCommit:f.options.sutCommit,evaluationCode:codeBinding(),controllerCode:{}});
 const spec={kind:'research300-v32-codex-smoke-specification',formalComparisonScore:false,scope:'selected-development-smoke',
  inputProtocol:f.options.inputProtocol,sourceBinding:binding,sutCommit:f.options.sutCommit,
  editionManifestSha256:sha(fs.readFileSync(path.join(edition,'manifest.json'))),cases:[f.caseId],plannedTurns:1};
 const pin={kind:'research300-v32-codex-smoke-operator-pin',formalComparisonScore:false,sourceBinding:binding};
 const pinPath=f.root+'-pin.json';t.after(()=>fs.rmSync(pinPath,{force:true}));
 function seal(){
  pin.specification=f.put('specification.json',spec);
  f.index.editionManifestSha256=spec.editionManifestSha256;f.index.executionSpecificationSha256=pin.specification.sha256;
  pin.index=f.put('index.json',f.index);
  pin.inventory=f.put('inventory.json',{files:[...Object.values(f.entry.files),...f.index.turns.map(t=>t.answer)]});
  fs.writeFileSync(pinPath,JSON.stringify(pin));
  return {edition,controlRoot:f.root,pinPath,pinSha256:sha(fs.readFileSync(pinPath))};
 }
 return {f,spec,pin,seal};
}
test('diagnostic uses actual evaluator and cannot become a formal score',t=>{
 const x=fixture(t),r=grade(x.seal());assert.equal(r.counts.passed,1);assert.equal(r.formalComparisonScore,false);assert.equal(r.runtimeQualification,'not-qualified');
});
test('external operator digest is mandatory',t=>{
 const x=fixture(t);assert.throws(()=>grade({...x.seal(),pinSha256:undefined}),/OPERATOR_PIN_REQUIRED/);
});
test('planned turn omission is rejected before grading',t=>{
 const x=fixture(t);x.f.index.turns=[];assert.throws(()=>grade(x.seal()),/SELECTED_TURN_COVERAGE_MISMATCH/);
});
test('unsupported delivery protocol is rejected',t=>{
 const x=fixture(t);x.spec.inputProtocol='old-attachment-only';assert.throws(()=>grade(x.seal()),/SMOKE_SPECIFICATION_REQUIRED/);
});
test('unknown evidence cannot pass through the new entry',t=>{
 const x=fixture(t);x.f.answer.jobIds=['f'.repeat(32)];x.f.seal();
 const r=grade(x.seal());assert.equal(r.counts.candidate_failure,1);assert.equal(r.rows[0].reasonCodes[0],'EVIDENCE_NOT_RELEASED');
});
test('sealed original answer mutation is evidence failure, never scored as model error',t=>{
 const x=fixture(t),options=x.seal();fs.appendFileSync(path.join(x.f.root,'answer.json'),' ');
 assert.throws(()=>grade(options),/Collector artifact changed/);
});
