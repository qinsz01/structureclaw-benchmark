'use strict';
// Diagnostic subset only. This cannot qualify v3.2 or emit a formal score.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {isDeepStrictEqual}=require('node:util');
const {loadControlledIndex,readSealed}=require('./controlled-evidence-v32.cjs');
const evaluator=require('./evaluate-v32.cjs');
const {codeBinding}=require('./code-closure-v32.cjs');
const ROOT=path.resolve(__dirname,'../..');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const read=p=>JSON.parse(fs.readFileSync(p));
const assert=(ok,message)=>{if(!ok)throw Error(message);};
function grade({edition,controlRoot,pinPath,pinSha256}){
 edition=fs.realpathSync(edition);controlRoot=fs.realpathSync(controlRoot);pinPath=fs.realpathSync(pinPath);
 assert(pinPath!==controlRoot&&!pinPath.startsWith(controlRoot+path.sep),'OPERATOR_PIN_MUST_BE_EXTERNAL');
 const pinBytes=fs.readFileSync(pinPath);
 assert(/^[a-f0-9]{64}$/.test(pinSha256||'')&&sha(pinBytes)===pinSha256,'OPERATOR_PIN_REQUIRED');
 const pin=JSON.parse(pinBytes);
 assert(pin.kind==='research300-v32-codex-smoke-operator-pin'&&pin.formalComparisonScore===false,'SMOKE_PIN_REQUIRED');
 const spec=JSON.parse(readSealed(controlRoot,pin.specification)),binding=JSON.parse(readSealed(controlRoot,pin.sourceBinding));
 assert(spec.kind==='research300-v32-codex-smoke-specification'&&spec.formalComparisonScore===false
  &&spec.scope==='selected-development-smoke'&&spec.inputProtocol==='verbatim-public-v3.2','SMOKE_SPECIFICATION_REQUIRED');
 assert(isDeepStrictEqual(spec.sourceBinding,pin.sourceBinding)&&binding.sutCommit===spec.sutCommit,'SOURCE_BINDING_MISMATCH');
 assert(isDeepStrictEqual(binding.evaluationCode,codeBinding()),'SCORING_CODE_CHANGED');
 for(const [file,hash]of Object.entries(binding.controllerCode)){
  assert(!path.isAbsolute(file)&&file.split('/').every(x=>x&&x!=='.'&&x!=='..'),'CONTROLLER_SOURCE_PATH_INVALID');
  assert(sha(fs.readFileSync(path.join(ROOT,file)))===hash,'CONTROLLER_CODE_CHANGED: '+file);
 }
 const inventory=JSON.parse(readSealed(controlRoot,pin.inventory));
 assert(Array.isArray(inventory.files)&&new Set(inventory.files.map(f=>f.path)).size===inventory.files.length,'INVENTORY_INVALID');
 for(const file of inventory.files)readSealed(controlRoot,file);
 const manifestBytes=fs.readFileSync(path.join(edition,'manifest.json')),manifest=JSON.parse(manifestBytes),manifestHash=sha(manifestBytes);
 assert(manifestHash===spec.editionManifestSha256,'EDITION_CHANGED');
 for(const file of manifest.files)readSealed(edition,file);
 assert(Array.isArray(spec.cases)&&spec.cases.length>0&&new Set(spec.cases).size===spec.cases.length,'CASE_SELECTION_INVALID');
 const cases=spec.cases.map(id=>manifest.cases.find(c=>c.id===id));
 assert(cases.every(c=>c&&c.split==='dev'&&c.engine==='OpenSees'),'DEVELOPMENT_OPENSEES_SCOPE_REQUIRED');
 const index=JSON.parse(readSealed(controlRoot,pin.index));
 const expected=cases.flatMap(c=>c.turns.map(t=>c.id+'/'+t.id)).sort();
 assert(isDeepStrictEqual(index.turns.map(t=>t.caseId+'/'+t.turnId).sort(),expected)
  &&spec.plannedTurns===expected.length,'SELECTED_TURN_COVERAGE_MISMATCH');
 const evidence=loadControlledIndex({root:controlRoot,indexPath:pin.index.path,indexSha256:pin.index.sha256,
  editionManifestSha256:manifestHash,sutCommit:spec.sutCommit,inputProtocol:spec.inputProtocol,
  executionSpecificationSha256:pin.specification.sha256});
 const rows=[];
 for(const c of cases)for(const t of c.turns){
  const base={caseId:c.id,turnId:t.id,level:c.level,family:c.family,kind:c.analysis};
  try{
   const captured=evidence.readAnswer(c.id,t.id);
   if(captured.jobs.some(j=>j.engine!==c.engine))throw Object.assign(Error('Wrong designated native engine'),{code:'DESIGNATED_ENGINE_MISMATCH',outcome:'candidate_failure'});
   const result=evaluator.evaluate(read(path.join(edition,t.private)),captured.answer,captured.jobs,captured.currentJobIds);
   rows.push({...base,outcome:result.outcome,passed:result.outcome==='needs_review'?null:result.passed,
    originalAnswerSha256:captured.originalAnswerSha256,evidenceMapping:captured.mapping,
    nativeAttemptsThisTurn:captured.currentJobIds.length,reasonCodes:result.reviewReasons,
    failures:result.metrics.filter(m=>!m.pass)});
  }catch(error){rows.push({...base,outcome:error.outcome||'ungradable_evidence',passed:error.outcome==='candidate_failure'?false:null,
   reasonCodes:[error.code||'EVIDENCE_OR_INTEGRATION_UNRESOLVED'],detail:error.message});}
 }
 return {kind:'research300-v32-codex-smoke-diagnostic',evaluationRevision:'v3.2',formalComparisonScore:false,
  runtimeQualification:'not-qualified',scope:'selected-development-smoke',manifestSha256:manifestHash,
  indexSha256:pin.index.sha256,operatorPinSha256:pinSha256,executionSpecificationSha256:pin.specification.sha256,
  cases:cases.length,plannedTurns:expected.length,counts:Object.fromEntries(
   ['passed','candidate_failure','blocked_configuration','ungradable_evidence','needs_review'].map(k=>[k,rows.filter(r=>r.outcome===k).length])),
  scoreDenominatorPolicy:'Every preselected turn retained; diagnostic only, no formal pass rate',
  candidateInvocations:0,nativeSolverInvocations:0,numericalTolerancesChanged:false,evaluationCode:codeBinding(),rows};
}
if(require.main===module){
 try{
  const args=process.argv.slice(2),options={},names={'--edition':'edition','--control-root':'controlRoot','--pin':'pinPath','--pin-sha256':'pinSha256','--output':'output'};
  for(let i=0;i<args.length;i++){assert(names[args[i]]&&args[i+1],'Invalid grading arguments');options[names[args[i]]]=args[++i];}
  assert(Object.values(names).every(k=>options[k]),'Explicit edition, root, external pin/hash and new output required');
  const output=path.resolve(options.output),parent=fs.realpathSync(path.dirname(output));
  for(const root of [options.edition,options.controlRoot]){const real=fs.realpathSync(root);assert(parent!==real&&!parent.startsWith(real+path.sep),'Output must be outside originals');}
  const result=grade(options);fs.writeFileSync(output,JSON.stringify(result,null,2)+'\n',{flag:'wx'});
  process.stdout.write(JSON.stringify({output,cases:result.cases,plannedTurns:result.plannedTurns,counts:result.counts,formalComparisonScore:false})+'\n');
 }catch(error){process.stderr.write(JSON.stringify({status:'ungradable',message:error.message})+'\n');process.exitCode=2;}
}
module.exports={grade};
