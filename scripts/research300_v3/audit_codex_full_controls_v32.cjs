'use strict';
// Post-run evaluator controls over copies. This never dispatches a candidate,
// runs a solver, modifies original answers, or feeds a result back to a run.
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),crypto=require('node:crypto');
const {isDeepStrictEqual}=require('node:util');
const {loadControlledIndex,readSealed}=require('./controlled-evidence-v32.cjs');
const {codeBinding}=require('./code-closure-v32.cjs');
const {evaluate}=require('./evaluate-v32.cjs');
const {controls}=require('./controls-v32.cjs');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const read=p=>JSON.parse(fs.readFileSync(p));
const assert=(ok,message)=>{if(!ok)throw Error(message);};
function context({edition,work,pinPath,pinSha256,diagnosticPath}){
 edition=fs.realpathSync(edition);work=fs.realpathSync(work);
 const pinBytes=fs.readFileSync(pinPath);assert(sha(pinBytes)===pinSha256,'External pin differs');
 const pin=JSON.parse(pinBytes),spec=JSON.parse(readSealed(work,pin.specification)),index=JSON.parse(readSealed(work,pin.index)),
  manifestBytes=fs.readFileSync(path.join(edition,'manifest.json')),manifest=JSON.parse(manifestBytes),diagnostic=read(diagnosticPath);
 assert(pin.kind==='research300-v32-codex-full-operator-pin'&&manifest.cases.length===300,'Sealed full run required');
 assert(sha(manifestBytes)===spec.editionManifestSha256&&diagnostic.manifestSha256===spec.editionManifestSha256
  &&diagnostic.operatorPinSha256===pinSha256&&diagnostic.indexSha256===pin.index.sha256
  &&diagnostic.executionSpecificationSha256===pin.specification.sha256&&diagnostic.plannedTurns===560,'Diagnostic binding differs');
 assert(isDeepStrictEqual(diagnostic.evaluationCode,codeBinding()),'Evaluation source changed');
 const options={root:work,indexPath:pin.index.path,indexSha256:pin.index.sha256,
  editionManifestSha256:spec.editionManifestSha256,sutCommit:spec.sutCommit,inputProtocol:spec.inputProtocol,
  executionSpecificationSha256:pin.specification.sha256};
 return {edition,work,pin,spec,index,manifest,diagnostic,options,reader:loadControlledIndex(options)};
}
function replaceRefs(answer,id){
 const b=structuredClone(answer);
 for(const key of ['jobIds','runIds'])if(b[key])b[key]=b[key].map(()=>id);
 for(const key of ['jobIdsByScenario','jobIdsByModel','runIdsByScenario','runIdsByModel'])if(b[key]){
  for(const name of Object.keys(b[key]))b[key][name]=b[key][name].map(()=>id);
 }
 return b;
}
function testCase(x,c){
 const rows=[],skipped=[];
 for(const t of c.turns){
  const score=x.diagnostic.rows.find(r=>r.caseId===c.id&&r.turnId===t.id);
  assert(score,'Diagnostic turn missing');
  if(score.outcome!=='passed'){skipped.push({turnId:t.id,outcome:score.outcome,reason:'Controls need a passing original; no repaired answer is used'});continue;}
  const saved=x.reader.readAnswer(c.id,t.id),ref=JSON.parse(readSealed(x.edition,x.manifest.files.find(f=>f.path===t.private)));
  const baseline=evaluate(ref,saved.answer,saved.jobs,saved.currentJobIds);
  assert(baseline.outcome==='passed'&&saved.originalAnswerSha256===score.originalAnswerSha256,'Positive original no longer passes unchanged');
  const add=row=>rows.push({caseId:c.id,turnId:t.id,originalAnswerSha256:saved.originalAnswerSha256,...row});
  for(const row of controls(ref,saved.answer,saved.jobs,saved.currentJobIds))add(row);
  const ordered=structuredClone(saved.jobs);
  for(const job of ordered){
   for(const key of ['nodes','elements','materials','sections','load_cases','load_combinations'])job.state.model[key]?.reverse();
   for(const loadCase of job.state.model.load_cases||[])loadCase.loads.reverse();
  }
  const permutation=evaluate(ref,saved.answer,ordered,saved.currentJobIds);
  add({name:'legal-entity-and-load-list-permutation',scope:'full-evaluator',expected:'passed',actual:permutation.outcome,
   passed:permutation.outcome==='passed',failures:permutation.metrics.filter(m=>!m.pass)});
  const ids=[['unknown-execution','f'.repeat(32)],['preflight-cannot-be-candidate','preflight-native']];
  const cross=x.index.entries.find(e=>e.caseId!==c.id),future=x.index.entries.find(e=>e.caseId===c.id&&Number(e.turnId.slice(1))>Number(t.id.slice(1)));
  if(cross)ids.push(['cross-case-execution',cross.evidenceId]);
  if(future)ids.push(['future-turn-execution',future.evidenceId]);
  for(const [name,id]of ids){
   let actual='accepted';try{x.reader.resolveAnswer(replaceRefs(saved.answer,id),c.id,t.id);}catch(error){actual=error.code||error.message;}
   add({name,scope:'controlled-evidence-reader',expected:'EVIDENCE_NOT_RELEASED',actual,passed:actual==='EVIDENCE_NOT_RELEASED'});
  }
  if(ref.kind==='query'){
   const result=evaluate(ref,saved.answer,saved.jobs,[...saved.currentJobIds,'e'.repeat(32)]);
   add({name:'unreported-native-attempt-on-query-only-turn',scope:'full-evaluator-with-collector-attempt-ledger',
    expected:'candidate_failure',actual:result.outcome,passed:result.outcome==='candidate_failure',failures:result.metrics.filter(m=>!m.pass)});
  }else if(c.family==='INT'&&Number(t.id.slice(1))>1){
   const previous='t'+(Number(t.id.slice(1))-1),priorScore=x.diagnostic.rows.find(r=>r.caseId===c.id&&r.turnId===previous);
   if(priorScore?.outcome==='passed'){
    const prior=x.reader.readAnswer(c.id,previous),answer=structuredClone(saved.answer),key=['jobIds','jobIdsByScenario','jobIdsByModel'].find(k=>answer[k]!==undefined);
    if(prior.answer[key]!==undefined){
     answer[key]=structuredClone(prior.answer[key]);
     const old=x.reader.resolveAnswer(answer,c.id,t.id),result=evaluate(ref,old.answer,old.jobs,old.currentJobIds);
     add({name:'stale-evidence-after-issued-physical-change',scope:'reader-and-full-evaluator',previousTurn:previous,
      priorIdentityAccepted:true,expected:'candidate_failure',actual:result.outcome,passed:result.outcome==='candidate_failure',
      failures:result.metrics.filter(m=>!m.pass)});
    }
   }
  }
 }
 return {caseId:c.id,engine:c.engine,level:c.level,skipped,controls:rows.length,
  controlsPassed:rows.filter(r=>r.passed).length,allPassed:rows.every(r=>r.passed),rows};
}
function tamperChecks(x){
 const rows=[];
 for(const engine of ['OpenSees','PKPM','YJK']){
  const score=x.diagnostic.rows.find(r=>r.outcome==='passed'&&r.engine===engine&&r.evidenceMapping?.length);
  if(!score){rows.push({engine,skipped:true,reason:'No passing original with native evidence'});continue;}
  const temporary=fs.mkdtempSync(path.join(os.tmpdir(),'codex-full-control-'));
  try{
   const copy=file=>{const target=path.join(temporary,file);fs.mkdirSync(path.dirname(target),{recursive:true});fs.copyFileSync(path.join(x.work,file),target);};
   copy(x.pin.index.path);
   const turn=x.index.turns.find(t=>t.caseId===score.caseId&&t.turnId===score.turnId);copy(turn.answer.path);
   const ids=new Set(score.evidenceMapping.map(m=>m.evidenceId)),entries=x.index.entries.filter(e=>ids.has(e.evidenceId));
   for(const entry of entries)for(const file of Object.values(entry.files))copy(file.path);
   for(const [name,descriptor]of [['native-request',entries[0].files.request],['native-state',entries[0].files.state],
    ['native-model',entries[0].files.model],['collector-receipt',entries[0].files.receipt],['original-answer',turn.answer],['capture-index',x.pin.index]]){
    assert(descriptor,'Missing tamper target');
    fs.appendFileSync(path.join(temporary,descriptor.path),' ');
    let actual='accepted';try{loadControlledIndex({...x.options,root:temporary}).readAnswer(score.caseId,score.turnId);}catch(error){actual=error.code||error.message;}
    rows.push({caseId:score.caseId,turnId:score.turnId,engine,name:'tampered-'+name,scope:'controlled-evidence-reader',
     expected:'EVIDENCE_HASH_MISMATCH',actual,passed:actual==='EVIDENCE_HASH_MISMATCH'});
    copy(descriptor.path);
   }
  }finally{fs.rmSync(temporary,{recursive:true,force:true});}
 }
 return rows;
}
function main(){
 const [edition,work,pinPath,pinSha256,diagnosticPath,shardText,output]=process.argv.slice(2),match=/^(\d+)\/(\d+)$/.exec(shardText||'');
 assert(match,'Explicit zero-based shard/total required');const shard=Number(match[1]),total=Number(match[2]);
 assert(total>=1&&shard>=0&&shard<total,'Invalid shard');
 const x=context({edition,work,pinPath,pinSha256,diagnosticPath}),cases=x.manifest.cases.filter((c,i)=>i%total===shard),caseRows=[];
 for(const c of cases){const row=testCase(x,c);caseRows.push(row);process.stdout.write(JSON.stringify({caseId:c.id,controls:row.controls,controlsPassed:row.controlsPassed})+'\n');}
 const tamper=shard===0?tamperChecks(x):[],allRows=[...caseRows.flatMap(c=>c.rows),...tamper.filter(r=>!r.skipped)];
 const result={kind:'research300-v32-full-actual-delivery-controls',formalComparisonScore:false,candidateInvocations:0,nativeSolverInvocations:0,
  originalAnswersModified:false,operatorPinSha256:pinSha256,diagnosticSha256:sha(fs.readFileSync(diagnosticPath)),
  shard,total,cases:cases.length,controls:allRows.length,controlsPassed:allRows.filter(r=>r.passed).length,
  allPassed:allRows.every(r=>r.passed),caseRows,tamper,
  source:{'audit_codex_full_controls_v32.cjs':sha(fs.readFileSync(__filename)),
   'controls-v32.cjs':sha(fs.readFileSync(path.join(__dirname,'controls-v32.cjs')))}};
 fs.writeFileSync(output,JSON.stringify(result,null,2)+'\n',{flag:'wx'});
 process.stdout.write(JSON.stringify({shard,total,controls:result.controls,controlsPassed:result.controlsPassed})+'\n');
 if(!result.allPassed)process.exitCode=1;
}
if(require.main===module)try{main();}catch(error){process.stderr.write(error.stack+'\n');process.exitCode=2;}
module.exports={context,testCase,tamperChecks};
