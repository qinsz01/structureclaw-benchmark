'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {grade,codeBinding}=require('./grade_candidate_v32.cjs');
const {collection,sha}=require('./test-support-v32.cjs');
function setup(t){
 const f=collection(t),edition=path.join(f.root,'edition');fs.mkdirSync(edition);
 const ref=Buffer.from(JSON.stringify(f.ref));fs.writeFileSync(path.join(edition,'reference.json'),ref);
 const c={id:f.caseId,engine:'OpenSees',family:'STD',level:'L1',analysis:'static',turns:[{id:'t1',private:'reference.json'}]};
 const manifest={cases:[c],files:[{path:'reference.json',sha256:sha(ref)}]};
 function manifestSeal(){
  const bytes=Buffer.from(JSON.stringify(manifest));fs.writeFileSync(path.join(edition,'manifest.json'),bytes);
  f.index.editionManifestSha256=sha(bytes);f.options.editionManifestSha256=sha(bytes);f.pin();
  return sha(bytes);
 }
 const hash=manifestSeal(),readiness={kind:'research300-v3-static-readiness',schemaVersion:1,editionManifestSha256:hash,
  sutCommit:f.options.sutCommit,inputProtocol:f.options.inputProtocol,executionSpecificationSha256:f.options.executionSpecificationSha256,
  evaluationCode:codeBinding(),cases:[{caseId:f.caseId,status:'conditional',reasonCodes:['SCORING_REVISION_NOT_RUNTIME_QUALIFIED']}],
  formalExperimentReady:false,runtimeQualification:null};
 function run(provisional=false){
  const pin=f.put('readiness.json',readiness);
  return grade({edition,controlRoot:f.root,indexPath:f.options.indexPath,indexSha256:f.options.indexSha256,
   readinessPath:path.join(f.root,pin.path),readinessSha256:pin.sha256,provisional});
 }
 return {...f,edition,manifest,manifestSeal,readiness,run};
}
test('unqualified revision cannot produce a formal score, even with a static readiness flag',t=>{
 const f=setup(t);f.readiness.formalExperimentReady=true;f.readiness.cases[0].status='ready';
 const r=f.run();assert.equal(r.counts.needs_review,1);assert.equal(r.qualifiedPassRate,null);assert.equal(r.formalComparisonScore,false);
});
test('provisional successful evaluation retains the issued denominator without granting qualification',t=>{
 const f=setup(t),r=f.run(true);assert.equal(r.counts.passed,1);assert.equal(r.issuedTurns,1);
 assert.equal(r.formalComparisonScore,false);assert.equal(r.qualifiedPassRate,null);
});
test('blocked and ungradable issued turns stay in the denominator',t=>{
 const f=setup(t);f.manifest.cases[0].turns.push({id:'t2',private:'reference.json'});
 f.readiness.editionManifestSha256=f.manifestSeal();
 const r=f.run(true);assert.equal(r.issuedTurns,2);assert.equal(r.counts.passed,1);assert.equal(r.counts.ungradable_evidence,1);
 f.readiness.cases[0].reasonCodes.push('DESIGNATED_ENGINE_AVAILABILITY_NOT_ATTESTED');
 const blocked=f.run(true);assert.equal(blocked.issuedTurns,2);assert.equal(blocked.counts.blocked_configuration,2);
 assert.equal(blocked.qualifiedPassRate,null);
});
test('a changed frozen reference or scoring dependency invalidates the prepared run',t=>{
 const f=setup(t);f.readiness.evaluationCode['evaluate-v32.cjs']='0'.repeat(64);
 assert.throws(()=>f.run(true),/READINESS_SCORING_CODE_CHANGED/);
 f.readiness.evaluationCode=codeBinding();fs.appendFileSync(path.join(f.edition,'reference.json'),' ');
 assert.throws(()=>f.run(true),/FROZEN_EDITION_CHANGED/);
});
test('index corruption is evidence loss and never charged as candidate failure',t=>{
 const f=setup(t);fs.appendFileSync(path.join(f.root,'index.json'),' ');const r=f.run(true);
 assert.equal(r.counts.ungradable_evidence,1);assert.equal(r.counts.candidate_failure,0);
});
test('a completed malformed answer is an attributable candidate failure',t=>{
 const f=setup(t);f.index.turns[0].answer=f.put('answer.json',Buffer.from('invalid JSON'));f.pin();
 const r=f.run(true);assert.equal(r.counts.candidate_failure,1);assert.equal(r.counts.ungradable_evidence,0);
});
test('old qualification totals cannot qualify modified scorer code',t=>{
 const f=setup(t);f.readiness.runtimeQualification=f.put('old-qualification.json',{
  kind:'research300-v3-policy-qualification',revision:'v3.2',allPassed:true,manifestSha256:f.readiness.editionManifestSha256,
  inputProtocol:f.options.inputProtocol,positiveTurns:560,positivePassed:560,controls:6591,controlsPassed:6591,evaluationCode:{}});
 const r=f.run();assert.equal(r.runtimeQualification,'not-run');assert.equal(r.formalComparisonScore,false);
});
