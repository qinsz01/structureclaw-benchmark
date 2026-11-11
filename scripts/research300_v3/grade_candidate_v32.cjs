'use strict';
// Opt-in, unqualified revision. No existing report or candidate answer is edited.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {isDeepStrictEqual}=require('node:util');
const evaluator=require('./evaluate-v32.cjs');
const {loadControlledIndex,readSealed}=require('./controlled-evidence-v32.cjs');
const {codeBinding}=require('./code-closure-v32.cjs');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const read=p=>JSON.parse(fs.readFileSync(p));
function grade({edition,controlRoot,indexPath,indexSha256,readinessPath,readinessSha256,provisional=false}){
 edition=fs.realpathSync(edition);const manifestBytes=fs.readFileSync(path.join(edition,'manifest.json')),manifest=JSON.parse(manifestBytes);
 const readinessBytes=fs.readFileSync(readinessPath);
 if(!/^[a-f0-9]{64}$/.test(readinessSha256)||sha(readinessBytes)!==readinessSha256)throw Error('OPERATOR_READINESS_PIN_REQUIRED');
 const readiness=JSON.parse(readinessBytes),hash=sha(manifestBytes),binding=codeBinding();
 if(readiness.kind!=='research300-v3-static-readiness'||readiness.schemaVersion!==1||readiness.editionManifestSha256!==hash
  ||readiness.inputProtocol!=='verbatim-public-v3.2'||!/^[a-f0-9]{40}$/.test(readiness.sutCommit))throw Error('READINESS_EDITION_MISMATCH');
 if(!isDeepStrictEqual(readiness.evaluationCode,binding))throw Error('READINESS_SCORING_CODE_CHANGED');
 const states=new Map(readiness.cases.map(r=>[r.caseId,r]));
 const issued=new Set(manifest.cases.map(c=>c.id));
 if(readiness.cases.length!==states.size||states.size!==issued.size||[...states.keys()].some(cid=>!issued.has(cid))
  ||readiness.cases.some(row=>!['ready','conditional','blocked'].includes(row.status)||!Array.isArray(row.reasonCodes)))throw Error('READINESS_CASE_COVERAGE_MISMATCH');
 for(const row of manifest.files){
  const file=path.resolve(edition,row.path);
  if(!file.startsWith(edition+path.sep)||fs.realpathSync(file)!==file||sha(fs.readFileSync(file))!==row.sha256)throw Error('FROZEN_EDITION_CHANGED');
 }
 let qualification=null;
 if(readiness.runtimeQualification){
  qualification=JSON.parse(readSealed(fs.realpathSync(controlRoot),readiness.runtimeQualification));
 }
 const qualificationFamilies=['audit-metadata-equivalence','unknown-audit-fields','physical-input-strictness',
  'controlled-capture-identity','native-execution-bindings','failure-attribution','verbatim-public-delivery'];
 const qualified=qualification?.kind==='research300-v3-policy-qualification'&&qualification?.revision==='v3.2'
  &&qualification?.allPassed===true&&isDeepStrictEqual(qualification?.evaluationCode,binding)
  &&qualification?.manifestSha256===hash&&qualification?.inputProtocol===readiness.inputProtocol
  &&qualification?.positiveTurns===560&&qualification?.positivePassed===560
  &&Number.isInteger(qualification?.controls)&&qualification?.controls>=6591&&qualification?.controlsPassed===qualification?.controls
  &&qualificationFamilies.every(name=>Number.isInteger(qualification.controlFamilies?.[name]?.executed)
   &&qualification.controlFamilies[name].executed>0&&qualification.controlFamilies[name].failed===0);
 // Qualification is emitted by the separate controlled acceptance process.
 // A static readiness flag alone never changes this experimental revision into
 // a formally qualified benchmark. This turn does not run that process.
 let evidence,indexError;
 try{evidence=loadControlledIndex({root:controlRoot,indexPath,indexSha256,editionManifestSha256:hash,sutCommit:readiness.sutCommit,
  inputProtocol:readiness.inputProtocol,executionSpecificationSha256:readiness.executionSpecificationSha256});}
 catch(error){indexError=error;}
 const rows=[];
 for(const c of manifest.cases)for(const t of c.turns){
  const base={caseId:c.id,turnId:t.id,level:c.level,family:c.family,kind:c.analysis};
  const ready=states.get(c.id);
  if(ready.status!=='ready'){
   const blocked=ready.reasonCodes.filter(code=>code!=='SCORING_REVISION_NOT_RUNTIME_QUALIFIED');
   if(blocked.length||ready.status==='blocked'){
    rows.push({...base,outcome:'blocked_configuration',passed:null,reasonCodes:ready.reasonCodes});continue;
   }
  }
  if(!qualified&&!provisional){rows.push({...base,outcome:'needs_review',passed:null,reasonCodes:['SCORING_REVISION_NOT_RUNTIME_QUALIFIED']});continue;}
  try{
   if(indexError)throw indexError;
   const captured=evidence.readAnswer(c.id,t.id);
   const ref=read(path.join(edition,t.private));
   if(captured.jobs.some(j=>j.engine!==c.engine))throw Object.assign(Error('Wrong designated native engine'),{outcome:'candidate_failure',code:'DESIGNATED_ENGINE_MISMATCH'});
   const result=evaluator.evaluate(ref,captured.answer,captured.jobs,captured.currentJobIds);
   rows.push({...base,passed:result.outcome==='needs_review'?null:result.passed,outcome:result.outcome,
    originalAnswerSha256:captured.originalAnswerSha256,evidenceMapping:captured.mapping,
    reasonCodes:result.reviewReasons,failures:result.metrics.filter(m=>!m.pass)});
  }catch(error){rows.push({...base,passed:error.outcome==='candidate_failure'?false:null,
   outcome:error.outcome||'ungradable_evidence',reasonCodes:[error.code||'EVIDENCE_OR_INTEGRATION_UNRESOLVED'],detail:error.message});}
 }
 const counts=Object.fromEntries(['passed','candidate_failure','blocked_configuration','ungradable_evidence','needs_review'].map(k=>[k,rows.filter(r=>r.outcome===k).length]));
 const resolved=counts.blocked_configuration+counts.ungradable_evidence+counts.needs_review===0;
 const fullyReady=!provisional&&qualified&&resolved&&readiness.formalExperimentReady===true;
 return {evaluationRevision:'v3.2',formalComparisonScore:fullyReady,
  runtimeQualification:qualified?'qualified':'not-run',provisional,manifestSha256:hash,sutCommit:readiness.sutCommit,
  inputProtocol:readiness.inputProtocol,executionSpecificationSha256:readiness.executionSpecificationSha256,
  readinessSha256,indexSha256,
  cases:manifest.cases.length,issuedTurns:rows.length,counts,
  qualifiedPassRate:fullyReady?counts.passed/rows.length:null,
  scoreDenominatorPolicy:'All issued turns; no headline score while configuration, capture or review is unresolved',
  candidateInvocations:0,nativeSolverInvocations:0,numericalTolerancesChanged:false,evaluationCode:binding,rows};
}
if(require.main===module){
 try{
  const args=process.argv.slice(2),options={};
  const fields={'--edition':'edition','--control-root':'controlRoot','--index':'indexPath','--index-sha256':'indexSha256','--readiness':'readinessPath','--readiness-sha256':'readinessSha256','--output':'output'};
  for(let i=0;i<args.length;i++){
   if(args[i]==='--provisional'){options.provisional=true;continue;}
   if(!fields[args[i]]||!args[i+1])throw Error('Invalid grading option');options[fields[args[i]]]=args[++i];
  }
  if(Object.values(fields).some(key=>!options[key]))throw Error('Explicit edition, controlled index pin, readiness and new output are required');
  const output=path.resolve(options.output),parent=fs.realpathSync(path.dirname(output));
  for(const root of [options.edition,options.controlRoot]){const actual=fs.realpathSync(root);if(parent===actual||parent.startsWith(actual+path.sep))throw Error('Output must be outside original inputs/evidence');}
  const result=grade(options);fs.writeFileSync(output,JSON.stringify(result,null,2)+'\n',{flag:'wx'});
  process.stdout.write(JSON.stringify({output,...result,rows:undefined})+'\n');
 }catch(error){process.stderr.write(JSON.stringify({status:'ungradable',code:error.code||'CONFIGURATION_ERROR',message:error.message})+'\n');process.exitCode=2;}
}
module.exports={grade,codeBinding};
