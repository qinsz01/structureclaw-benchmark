'use strict';
// Separate environment-recovery experiment. Never replaces original full-run outcomes.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {isDeepStrictEqual}=require('node:util');
const {loadControlledIndex,readSealed}=require('./controlled-evidence-v32.cjs');
const evaluator=require('./evaluate-v32.cjs');
const {codeBinding}=require('./code-closure-v32.cjs');
const ROOT=path.resolve(__dirname,'../..'),sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const assert=(ok,message)=>{if(!ok)throw Error(message);};
const outcomes=['passed','candidate_failure','blocked_configuration','ungradable_evidence','needs_review'];
function grade({edition,controlRoot,pinPath,pinSha256}){
 edition=fs.realpathSync(edition);controlRoot=fs.realpathSync(controlRoot);pinPath=fs.realpathSync(pinPath);
 assert(!pinPath.startsWith(controlRoot+path.sep),'OPERATOR_PIN_MUST_BE_EXTERNAL');
 const pinBytes=fs.readFileSync(pinPath);
 assert(/^[a-f0-9]{64}$/.test(pinSha256||'')&&sha(pinBytes)===pinSha256,'OPERATOR_PIN_REQUIRED');
 const pin=JSON.parse(pinBytes);
 assert(pin.kind==='research300-v32-codex-recovery-operator-pin'&&pin.formalComparisonScore===false,'FULL_PIN_REQUIRED');
 const spec=JSON.parse(readSealed(controlRoot,pin.specification)),binding=JSON.parse(readSealed(controlRoot,pin.sourceBinding));
 assert(spec.kind==='research300-v32-codex-recovery-specification'&&spec.formalComparisonScore===false
  &&spec.scope==='environment-recovery-supplement'&&spec.replacesOriginalScores===false&&spec.inputProtocol==='verbatim-public-v3.2','FULL_SPECIFICATION_REQUIRED');
 assert(isDeepStrictEqual(spec.sourceBinding,pin.sourceBinding)&&binding.sutCommit===spec.sutCommit,'SOURCE_BINDING_MISMATCH');
 assert(isDeepStrictEqual(binding.evaluationCode,codeBinding()),'SCORING_CODE_CHANGED');
 for(const [file,hash]of Object.entries(binding.controllerCode)){
  assert(!path.isAbsolute(file)&&file.split('/').every(x=>x&&x!=='.'&&x!=='..'),'CONTROLLER_SOURCE_PATH_INVALID');
  assert(sha(fs.readFileSync(path.join(ROOT,file)))===hash,'CONTROLLER_CODE_CHANGED: '+file);
 }
 const inventory=JSON.parse(readSealed(controlRoot,pin.inventory));
 assert(Array.isArray(inventory.files)&&new Set(inventory.files.map(f=>f.path)).size===inventory.files.length,'INVENTORY_INVALID');
 for(const file of inventory.files)readSealed(controlRoot,file);
 const manifestBytes=fs.readFileSync(path.join(edition,'manifest.json')),manifest=JSON.parse(manifestBytes),hash=sha(manifestBytes);
 assert(hash===spec.editionManifestSha256,'EDITION_CHANGED');
 for(const file of manifest.files)readSealed(edition,file);
 const cases=manifest.cases.filter(c=>spec.cases.includes(c.id)),expected=cases.flatMap(c=>c.turns.map(t=>c.id+'/'+t.id)).sort();
 assert(manifest.cases.length===300&&cases.length>0&&cases.length<300&&spec.plannedTurns===expected.length
  &&cases.every(c=>['PKPM','YJK'].includes(c.engine))
  &&isDeepStrictEqual([...spec.cases].sort(),cases.map(c=>c.id).sort()),'RECOVERY_SCOPE_COVERAGE_REQUIRED');
 const parent=JSON.parse(readSealed(controlRoot,spec.parentExperiment));
 assert(parent.replacesOriginalScores===false&&isDeepStrictEqual(parent.faults.map(f=>f.caseId).sort(),[...spec.cases].sort()),'ORIGINAL_FAULT_CASES_REQUIRED');
 for(const row of parent.faults){
  assert(row.capturedFaultReceipts?.length,'Original transport receipt required');
  for(const descriptor of row.capturedFaultReceipts){
   const receipt=JSON.parse(readSealed(controlRoot,descriptor));
   assert(receipt.caseId===row.caseId&&receipt.engine===cases.find(c=>c.id===row.caseId).engine&&receipt.ok===false&&receipt.error?.includes('codex_trial/remote.py')
    &&receipt.error.includes('Permission denied (publickey)'),'ORIGINAL_TRANSPORT_FAILURE_REQUIRED');
  }
 }
 const index=JSON.parse(readSealed(controlRoot,pin.index));
 assert(isDeepStrictEqual(index.turns.map(t=>t.caseId+'/'+t.turnId).sort(),expected),'FULL_TURN_COVERAGE_REQUIRED');
 const evidence=loadControlledIndex({root:controlRoot,indexPath:pin.index.path,indexSha256:pin.index.sha256,
  editionManifestSha256:hash,sutCommit:spec.sutCommit,inputProtocol:spec.inputProtocol,
  executionSpecificationSha256:pin.specification.sha256});
 const rows=[];
 for(const c of cases)for(const t of c.turns){
  const base={caseId:c.id,turnId:t.id,level:c.level,family:c.family,engine:c.engine,kind:c.analysis,split:c.split};
  try{
   const captured=evidence.readAnswer(c.id,t.id);
   if(captured.jobs.some(j=>j.engine!==c.engine))throw Object.assign(Error('Wrong designated native engine'),{code:'DESIGNATED_ENGINE_MISMATCH',outcome:'candidate_failure'});
   const ref=JSON.parse(fs.readFileSync(path.join(edition,t.private)));
   const result=evaluator.evaluate(ref,captured.answer,captured.jobs,captured.currentJobIds);
   rows.push({...base,outcome:result.outcome,passed:result.outcome==='needs_review'?null:result.passed,
    originalAnswerSha256:captured.originalAnswerSha256,evidenceMapping:captured.mapping,
    nativeAttemptsThisTurn:captured.currentJobIds.length,reasonCodes:result.reviewReasons,
    failures:result.metrics.filter(m=>!m.pass)});
  }catch(error){rows.push({...base,outcome:error.outcome||'ungradable_evidence',passed:error.outcome==='candidate_failure'?false:null,
   reasonCodes:[error.code||'EVIDENCE_OR_INTEGRATION_UNRESOLVED'],detail:error.message});}
 }
 const counts=Object.fromEntries(outcomes.map(k=>[k,rows.filter(r=>r.outcome===k).length]));
 const caseRows=cases.map(c=>{const turns=rows.filter(r=>r.caseId===c.id);return {caseId:c.id,engine:c.engine,level:c.level,family:c.family,
  turns:turns.length,allPassed:turns.every(r=>r.outcome==='passed'),unresolved:turns.some(r=>!['passed','candidate_failure'].includes(r.outcome))};});
 return {kind:'research300-v32-codex-recovery-diagnostic',evaluationRevision:'v3.2',formalComparisonScore:false,
  runtimeQualification:'not-qualified',scope:'environment-recovery-supplement',replacesOriginalScores:false,manifestSha256:hash,
  indexSha256:pin.index.sha256,operatorPinSha256:pinSha256,executionSpecificationSha256:pin.specification.sha256,
  cases:cases.length,plannedTurns:expected.length,counts,caseCounts:{passed:caseRows.filter(r=>r.allPassed).length,unresolved:caseRows.filter(r=>r.unresolved).length},
  scoreDenominatorPolicy:'All selected recovery cases and their full turn sequences; original full-run results retained separately',
  candidateInvocations:0,nativeSolverInvocations:0,numericalTolerancesChanged:false,evaluationCode:codeBinding(),caseRows,rows};
}
if(require.main===module){
 try{
  const options={},args=process.argv.slice(2),fields={'--edition':'edition','--control-root':'controlRoot','--pin':'pinPath','--pin-sha256':'pinSha256','--output':'output'};
  for(let i=0;i<args.length;i++){assert(fields[args[i]]&&args[i+1],'Invalid options');options[fields[args[i]]]=args[++i];}
  assert(Object.values(fields).every(k=>options[k]),'Explicit paths and external pin required');
  const output=path.resolve(options.output),parent=fs.realpathSync(path.dirname(output));
  for(const root of [options.edition,options.controlRoot]){const actual=fs.realpathSync(root);assert(parent!==actual&&!parent.startsWith(actual+path.sep),'Output must be outside original inputs/evidence');}
  const result=grade(options);fs.writeFileSync(output,JSON.stringify(result,null,2)+'\n',{flag:'wx'});
  process.stdout.write(JSON.stringify({output,counts:result.counts,caseCounts:result.caseCounts,formalComparisonScore:false})+'\n');
 }catch(e){process.stderr.write(JSON.stringify({status:'ungradable',message:e.message})+'\n');process.exitCode=2;}
}
module.exports={grade};
