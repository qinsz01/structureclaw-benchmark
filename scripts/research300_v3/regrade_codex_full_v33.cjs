'use strict';
// An explicit post-hoc policy revision over the original sealed deliveries.
// The frozen v3.2 diagnostic and every original answer remain unchanged.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {isDeepStrictEqual}=require('node:util');
const {context}=require('./audit_codex_full_controls_v32.cjs');
const {readSealed}=require('./controlled-evidence-v32.cjs');
const legacy=require('./evaluate-v32.cjs'),revised=require('./evaluate-v33.cjs');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const assert=(ok,message)=>{if(!ok)throw Error(message);};
function sourceBinding(){return Object.fromEntries(['regrade_codex_full_v33.cjs','evaluate-v33.cjs','test_evaluate_v33.cjs'].map(n=>[n,sha(fs.readFileSync(path.join(__dirname,n)))]));}
function changedControls(ref,saved){
 const controls=[],run=(name,alter,expected='candidate_failure')=>{
  const x=structuredClone({ref,answer:saved.answer,jobs:saved.jobs,current:saved.currentJobIds});alter(x);
  const result=revised.evaluate(x.ref,x.answer,x.jobs,x.current);
  controls.push({name,expected,actual:result.outcome,passed:expected===result.outcome});
 };
 run('original-valid-cache-reuse',()=>{},'passed');
 const cached=saved.jobs.findIndex(j=>!legacy.physical(j.state.model,ref.model).pass);
 assert(cached>=0,'New passing delivery lacks the claimed cached-state boundary');
 run('wrong-cached-stiffness',x=>{for(const m of x.jobs[cached].state.model.materials)m.E*=.8;});
 run('wrong-cached-active-load',x=>{
  const job=x.jobs[cached],key=Object.keys(job.state.analysisResult.results)[0],pos=key.indexOf(':'),selection={kind:key.slice(0,pos),id:key.slice(pos+1)};
  const factors=selection.kind==='case'?{[selection.id]:1}:job.state.model.load_combinations.find(c=>c.id===selection.id).factors;
  for(const c of job.state.model.load_cases)if(factors[c.id])for(const l of c.loads)for(const k of ['fx','fy','fz','mx','my','mz','wx','wy','wz','wx_start','wx_end','wy_start','wy_end','wz_start','wz_end'])if(typeof l[k]==='number')l[k]*=1.1;
 });
 run('wrong-signed-report',x=>{const q=x.answer.quantities.find(q=>Math.abs(q.value)>1e-5);assert(q,'No nonzero report');q.value=-q.value;});
 run('explicit-fresh-execution-required',x=>{x.ref.requireFreshExecution=true;});
 run('no-complete-current-model',x=>{x.jobs=x.jobs.filter((_,i)=>i===cached);x.answer.jobIds=x.jobs.map(j=>j.jobId);});
 run('query-only-hidden-native-attempt',x=>{x.ref.kind='query';x.current=['e'.repeat(32)];});
 run('legal-reordering-of-cached-and-current-evidence',x=>{x.jobs.reverse();x.answer.jobIds.reverse();},'passed');
 return controls;
}
function run({edition,work,pinPath,pinSha256,rawPath,rawSha256,reviewedPath,reviewedSha256}){
 assert(sha(fs.readFileSync(rawPath))===rawSha256&&sha(fs.readFileSync(reviewedPath))===reviewedSha256,'Prior diagnostic hashes differ');
 const x=context({edition,work,pinPath,pinSha256,diagnosticPath:rawPath}),reviewed=JSON.parse(fs.readFileSync(reviewedPath)),sources=sourceBinding();
 assert(reviewed.rawDiagnosticSha256===rawSha256&&reviewed.operatorPinSha256===pinSha256,'Environment review is not bound to raw grading');
 const rows=[],changes=[],controls=[];
 for(const c of x.manifest.cases)for(const t of c.turns){
  const old=x.diagnostic.rows.find(r=>r.caseId===c.id&&r.turnId===t.id),env=reviewed.rows.find(r=>r.caseId===c.id&&r.turnId===t.id);
  assert(old&&env,'Prior full coverage differs');
  const saved=x.reader.readAnswer(c.id,t.id),ref=JSON.parse(readSealed(x.edition,x.manifest.files.find(f=>f.path===t.private)));
  const before=legacy.evaluate(ref,saved.answer,saved.jobs,saved.currentJobIds);
  assert(before.outcome===old.outcome&&isDeepStrictEqual(before.metrics.filter(m=>!m.pass),old.failures)&&saved.originalAnswerSha256===old.originalAnswerSha256,'Frozen original evaluation no longer replays: '+c.id+'/'+t.id);
  const after=revised.evaluate(ref,saved.answer,saved.jobs,saved.currentJobIds);
  const row={...env,evaluationRevision:'v3.3',legacyOutcome:env.outcome};
  if(env.outcome!==old.outcome){
   assert(env.outcome==='blocked_configuration'&&env.environmentReview&&after.outcome!=='passed','Do not override a bound environment attribution');
  }else{
   row.outcome=after.outcome;row.passed=after.outcome==='needs_review'?null:after.passed;
   row.reasonCodes=after.reviewReasons;row.failures=after.metrics.filter(m=>!m.pass);
  }
  if(row.outcome!==env.outcome){
   const check=changedControls(ref,saved);controls.push(...check.map(v=>({caseId:c.id,turnId:t.id,...v})));
   changes.push({caseId:c.id,turnId:t.id,from:env.outcome,to:row.outcome,originalAnswerSha256:saved.originalAnswerSha256,
    reason:'Complete current-model evidence plus unchanged active physics permits cached linear-static execution reuse',
    jobs:saved.jobs.map(j=>({jobId:j.jobId,completeCurrentModel:legacy.physical(j.state.model,ref.model).pass,nativeSelections:Object.keys(j.state.analysisResult.results)}))});
  }
  rows.push(row);
  if(t.id===c.turns.at(-1).id)process.stdout.write(JSON.stringify({regraded:c.id})+'\n');
 }
 assert(isDeepStrictEqual(sources,sourceBinding()),'Revision source changed during regrade');
 const outcomes=['passed','candidate_failure','blocked_configuration','ungradable_evidence','needs_review'];
 const caseRows=x.manifest.cases.map(c=>{const turns=rows.filter(r=>r.caseId===c.id);return {caseId:c.id,engine:c.engine,level:c.level,family:c.family,turns:turns.length,allPassed:turns.every(t=>t.outcome==='passed'),unresolved:turns.some(t=>!['passed','candidate_failure'].includes(t.outcome))};});
 return {...reviewed,kind:'research300-v33-posthoc-static-reuse-diagnostic',evaluationRevision:'v3.3',formalComparisonScore:false,
  counts:Object.fromEntries(outcomes.map(k=>[k,rows.filter(r=>r.outcome===k).length])),caseCounts:{passed:caseRows.filter(r=>r.allPassed).length,unresolved:caseRows.filter(r=>r.unresolved).length},caseRows,rows,
  policyRevision:{postHoc:true,predecessorDiagnosticSha256:reviewedSha256,predecessorRawDiagnosticSha256:rawSha256,
   originalAnswersModified:false,numericalTolerancesChanged:false,candidateInvocations:0,nativeSolverInvocations:0,
   all560LegacyRowsReplayed:true,allPreviouslyPassingRowsRetained:rows.filter(r=>r.legacyOutcome==='passed').every(r=>r.outcome==='passed'),
   completeInventoryVerification:'Performed by the hash-bound original full grader; this revision additionally rechecks each consumed sealed reference/answer/native input and result. Cold full replay independently rechecks the entire inventory.',
   sourceBinding:sources,changes,controls,allControlsPassed:controls.every(c=>c.passed)}};
}
if(require.main===module)try{
 const [edition,work,pinPath,pinSha256,rawPath,rawSha256,reviewedPath,reviewedSha256,output]=process.argv.slice(2);
 assert(output,'Explicit roots, prior diagnostic SHA256s and output required');
 const result=run({edition,work,pinPath,pinSha256,rawPath,rawSha256,reviewedPath,reviewedSha256});
 fs.writeFileSync(output,JSON.stringify(result,null,2)+'\n',{flag:'wx'});
 process.stdout.write(JSON.stringify({counts:result.counts,caseCounts:result.caseCounts,changes:result.policyRevision.changes.length,controls:result.policyRevision.controls.length,allControlsPassed:result.policyRevision.allControlsPassed})+'\n');
 if(!result.policyRevision.allControlsPassed)process.exitCode=1;
}catch(error){process.stderr.write(error.stack+'\n');process.exitCode=2;}
module.exports={run};
