'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {loadControlledIndex,readSealed}=require('./controlled-evidence-v32.cjs');
const {collection}=require('./test-support-v32.cjs');
const rejected=(fn,code,outcome='ungradable_evidence')=>assert.throws(fn,e=>e.code===code&&e.outcome===outcome);

for(const origin of ['broker','structureclaw'])test('controlled '+origin+' originals retain exact model and answer values',t=>{
 const f=collection(t,origin),before=structuredClone(f.answer);
 if(origin==='structureclaw'){f.answer.runIds=[f.entry.runId];delete f.answer.jobIds;f.seal();}
 const result=loadControlledIndex(f.options).readAnswer(f.caseId,f.turnId);
 assert.deepEqual(result.jobs[0].state,f.state);assert.deepEqual(result.answer.quantities,before.quantities);
 assert.deepEqual(result.answer.jobIds,[f.entry.evidenceId]);assert.deepEqual(result.currentJobIds,[f.entry.evidenceId]);
 assert.deepEqual(JSON.parse(readSealed(f.root,f.index.turns[0].answer)),f.answer);
});
for(const [name,edit,code]of [
 ['missing operator pin',f=>delete f.options.indexSha256,'TRUSTED_INDEX_PIN_REQUIRED'],
 ['wrong edition',f=>f.options.editionManifestSha256='f'.repeat(64),'CAPTURE_INDEX_BINDING_INVALID'],
 ['wrong SUT',f=>f.options.sutCommit='f'.repeat(40),'CAPTURE_INDEX_BINDING_INVALID'],
 ['wrong execution configuration',f=>f.options.executionSpecificationSha256='f'.repeat(64),'CAPTURE_INDEX_BINDING_INVALID'],
 ['duplicate turn',f=>{f.index.turns.push(structuredClone(f.index.turns[0]));f.pin();},'CAPTURE_TURN_REBOUND'],
 ['reused attempt',f=>{f.index.turns.push({...f.index.turns[0],turnId:'t2'});f.pin();},'ATTEMPT_ID_REBOUND'],
 ['unowned published run',f=>{f.index.turns[0].currentJobIds=[];f.pin();},'CAPTURE_ATTEMPT_UNBOUND'],
 ['reused run UUID',f=>{const entry=structuredClone(f.entry);entry.evidenceId='2'.repeat(32);f.index.entries.push(entry);f.index.turns[0].currentJobIds.push(entry.evidenceId);f.pin();},'RUN_ID_REBOUND'],
])test('capture identity rejects '+name,t=>{const f=collection(t,'structureclaw');edit(f);rejected(()=>loadControlledIndex(f.options),code);});

for(const [name,edit,code]of [
 ['oracle receipt',f=>f.receipt.role='oracle','CANDIDATE_RECEIPT_REQUIRED'],
 ['different model',f=>f.state.model.nodes[1].x+=1,'STATE_MODEL_MISMATCH'],
 ['wrong model fingerprint',f=>f.archive.modelHash='e'.repeat(64),'SCLAW_ARCHIVE_IDENTITY_MISMATCH'],
 ['wrong settings identity',f=>f.archive.results['case:D'].meta.settingsHash='e'.repeat(64),'SCLAW_ARCHIVE_IDENTITY_MISMATCH'],
 ['changed native number',f=>f.state.analysisResult.results['case:D'].data.displacements.B.uz*=2,'STATIC_ARCHIVE_MISMATCH'],
 ['wrong run UUID',f=>f.receipt.runId='87654321-1234-1234-1234-123456789abc','SCLAW_ARCHIVE_BINDING_INVALID'],
 ['wrong execution SUT',f=>f.proof.sutCommit='e'.repeat(40),'NATIVE_EXECUTION_PROOF_REQUIRED'],
 ['no native execution',f=>f.proof.executed=false,'NATIVE_EXECUTION_PROOF_REQUIRED'],
 ['worker failure',f=>f.proof.workerExitCode=1,'NATIVE_EXECUTION_PROOF_REQUIRED'],
 ['no native artifacts',f=>f.proof.artifacts=[],'NATIVE_EXECUTION_PROOF_REQUIRED'],
])test('sealed original bindings reject '+name,t=>{
 const f=collection(t,'structureclaw');edit(f);f.seal();
 rejected(()=>loadControlledIndex(f.options).readAnswer(f.caseId,f.turnId),code);
});
for(const [name,edit,code,outcome]of [
 ['blocked engine',r=>r.environmentStatus='blocked','ENVIRONMENT_OR_SERVICE_BLOCKED','blocked_configuration'],
 ['blocked model service',r=>r.candidateStatus='service_blocked','ENVIRONMENT_OR_SERVICE_BLOCKED','blocked_configuration'],
 ['incomplete capture',r=>r.captureComplete=false,'CAPTURE_TURN_INCOMPLETE','ungradable_evidence'],
 ['interrupted turn',r=>r.candidateStatus='interrupted','TURN_INTERRUPTED','ungradable_evidence'],
 ['recorded candidate failure',r=>r.candidateStatus='candidate_failed','CANDIDATE_TURN_FAILED','candidate_failure'],
 ['missing submission',r=>delete r.answer,'ANSWER_NOT_SUBMITTED','candidate_failure'],
])test('failure attribution distinguishes '+name,t=>{
 const f=collection(t);edit(f.index.turns[0]);f.pin();
 rejected(()=>loadControlledIndex(f.options).readAnswer(f.caseId,f.turnId),code,outcome);
});
test('missing or invalid original answers differ from corrupted stored bytes',t=>{
 const f=collection(t);f.index.turns[0].answer=f.put('answer.json',Buffer.from('not json'));f.pin();
 rejected(()=>loadControlledIndex(f.options).readAnswer(f.caseId,f.turnId),'ANSWER_JSON_INVALID','candidate_failure');
 fs.appendFileSync(path.join(f.root,'answer.json'),'changed');
 rejected(()=>loadControlledIndex(f.options).readAnswer(f.caseId,f.turnId),'EVIDENCE_HASH_MISMATCH');
});
test('cross-case, unknown and future references fail while prior issued runs remain usable',t=>{
 const f=collection(t),row=f.index.turns[0];
 f.index.turns.push({...row,turnId:'t2',currentJobIds:[]},{...row,caseId:'V3-STD-002',currentJobIds:[]});f.pin();
 const reader=loadControlledIndex(f.options);
 assert.equal(reader.resolveAnswer(f.answer,f.caseId,'t2').jobs.length,1);
 rejected(()=>reader.resolveAnswer(f.answer,'V3-STD-002','t1'),'EVIDENCE_NOT_RELEASED','candidate_failure');
 rejected(()=>reader.resolveAnswer({...f.answer,jobIds:['0'.repeat(32)]},f.caseId,'t1'),'EVIDENCE_NOT_RELEASED','candidate_failure');
 row.turnId='t3';f.entry.turnId='t3';f.index.turns.push({...row,turnId:'t1',currentJobIds:[]});f.pin();
 rejected(()=>loadControlledIndex(f.options).resolveAnswer(f.answer,f.caseId,'t1'),'EVIDENCE_NOT_RELEASED','candidate_failure');
});
test('identity aliases are exclusive and unreferenced failed attempts stay in the turn inventory',t=>{
 const f=collection(t,'structureclaw');f.index.turns[0].currentJobIds.push('9'.repeat(32));f.pin();
 const reader=loadControlledIndex(f.options);
 rejected(()=>reader.resolveAnswer({...f.answer,runIds:[f.entry.runId]},f.caseId,'t1'),'ANSWER_IDENTITY_AMBIGUOUS','candidate_failure');
 rejected(()=>reader.resolveAnswer({...f.answer,jobIdsByModel:{upper:[f.entry.evidenceId]}},f.caseId,'t1'),'ANSWER_EVIDENCE_GROUP_REQUIRED','candidate_failure');
 assert.equal(reader.readAnswer(f.caseId,'t1').currentJobIds.length,2);
});
test('artifact paths cannot escape the controller or follow a symlink',t=>{
 const f=collection(t);for(const name of ['../model.json','/model.json','a\\model.json','./model.json'])
  rejected(()=>readSealed(f.root,{...f.entry.files.model,path:name}),'EVIDENCE_PATH_INVALID');
 fs.symlinkSync(path.join(f.root,'model.json'),path.join(f.root,'model-link.json'));
 rejected(()=>readSealed(f.root,{...f.entry.files.model,path:'model-link.json'}),'EVIDENCE_SYMLINK');
});
