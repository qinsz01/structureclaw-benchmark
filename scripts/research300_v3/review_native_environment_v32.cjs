'use strict';
// A separately versioned, conservative environment adjudication. It can only
// remove an invalid capability attribution; it can never turn a failure into a
// pass. Frozen grading, requests, model outputs and native receipts stay intact.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {context}=require('./audit_codex_full_controls_v32.cjs');
const {readSealed}=require('./controlled-evidence-v32.cjs');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const assert=(ok,message)=>{if(!ok)throw Error(message);};
function sshTransportFault(receipt){
 const error=receipt.error;
 return receipt.ok===false&&['PKPM','YJK'].includes(receipt.engine)&&typeof error==='string'
  &&error.startsWith('commercial failed: Traceback (most recent call last):')
  &&error.includes('/codex_trial/remote.py')
  &&/RuntimeError: (?:Numeric file transfer|Windows transport) failed:/.test(error)
  &&error.includes('Permission denied (publickey).');
}
function adjudicate(rows,turns){
 const output=[],decisions=[],pending=new Map();
 for(const row of rows){
  const info=turns.get(row.caseId+'/'+row.turnId);assert(info,'Missing original turn context');
  const faults=info.attempts.filter(a=>sshTransportFault(a.receipt)),prior=pending.get(row.caseId),r=structuredClone(row);
  if(row.outcome==='passed'){
   pending.delete(row.caseId);
   if(faults.length)r.recoveredNativeTransportFaults=faults.map(a=>a.evidenceId);
   output.push(r);continue;
  }
  const failureLike=['candidate_failure','needs_review'].includes(row.outcome);
  const direct=failureLike&&faults.length>0,dependent=failureLike&&!direct&&info.kind==='query'&&!!prior;
  if(direct||dependent){
   const evidence=direct?faults.map(a=>({caseId:row.caseId,turnId:row.turnId,evidenceId:a.evidenceId,receipt:a.descriptor})):prior;
   r.rawEvaluatorOutcome=row.outcome;
   r.outcome='blocked_configuration';r.passed=null;
   r.environmentReview={rule:direct?'SEALED_NATIVE_SSH_TRANSPORT_FAILURE':'QUERY_DEPENDS_ON_BLOCKED_NATIVE_STATE',
    sourceFaults:evidence,rawFailuresPreserved:true,
    note:'Native transport was unavailable. The original delivery still fails its evidence contract; this record cannot support a clean model-capability failure attribution.'};
   decisions.push({caseId:row.caseId,turnId:row.turnId,from:row.outcome,to:r.outcome,...r.environmentReview});
   pending.set(row.caseId,evidence);
  }
  output.push(r);
 }
 return {rows:output,decisions};
}
function review(options){
 const x=context(options),inventory=JSON.parse(readSealed(x.work,x.pin.inventory)),files=new Map(inventory.files.map(f=>[f.path,f])),turns=new Map(),faults=[];
 for(const capture of x.index.turns){
  const c=x.manifest.cases.find(c=>c.id===capture.caseId),t=c.turns.find(t=>t.id===capture.turnId),
   ref=JSON.parse(readSealed(x.edition,x.manifest.files.find(f=>f.path===t.private))),attempts=[];
  for(const id of capture.currentJobIds){
   const descriptor=files.get('solver-jobs/'+c.id+'/'+id+'/broker-receipt.json');
   if(!descriptor)continue; // An incomplete capture stays ungradable in the original diagnostic.
   const receipt=JSON.parse(readSealed(x.work,descriptor));
   assert(receipt.caseId===c.id&&receipt.turnId===t.id&&receipt.engine===c.engine&&receipt.role==='candidate','Native receipt belongs to a different turn');
   const record={evidenceId:id,receipt,descriptor};attempts.push(record);
   if(sshTransportFault(receipt))faults.push({caseId:c.id,turnId:t.id,evidenceId:id,receipt:descriptor,error:receipt.error});
  }
  turns.set(c.id+'/'+t.id,{kind:ref.kind,attempts});
 }
 // Manifest order gives every case's issued turn order, independent of worker
 // completion order. No inferred or candidate-reported failure is trusted.
 const ordered=x.manifest.cases.flatMap(c=>c.turns.map(t=>x.diagnostic.rows.find(r=>r.caseId===c.id&&r.turnId===t.id))),result=adjudicate(ordered,turns);
 const counts=Object.fromEntries(Object.keys(x.diagnostic.counts).map(k=>[k,result.rows.filter(r=>r.outcome===k).length]));
 assert(counts.passed===x.diagnostic.counts.passed&&Object.values(counts).reduce((a,b)=>a+b,0)===560,'Environment review cannot award passes or change denominator');
 const caseRows=x.manifest.cases.map(c=>{const selected=result.rows.filter(r=>r.caseId===c.id);return {caseId:c.id,engine:c.engine,level:c.level,family:c.family,
  turns:selected.length,allPassed:selected.every(r=>r.outcome==='passed'),unresolved:selected.some(r=>!['passed','candidate_failure'].includes(r.outcome))};});
 return {...x.diagnostic,kind:'research300-v32-codex-full-environment-reviewed-diagnostic',rawDiagnosticSha256:sha(fs.readFileSync(options.diagnosticPath)),
  rawCounts:x.diagnostic.counts,counts,rows:result.rows,caseRows,
  caseCounts:{passed:caseRows.filter(r=>r.allPassed).length,unresolved:caseRows.filter(r=>r.unresolved).length},
  environmentAdjudication:{revision:'native-transport-review-v1',postHoc:true,sourceSha256:sha(fs.readFileSync(__filename)),
   appliesTo:'Only sealed collector SSH public-key transport failures and subsequent dependent query turns; candidate text is not evidence',
   physicalScoringChanged:false,originalCapturesChanged:false,newPassingTurns:0,decisions:result.decisions,faults},
  formalComparisonScore:false,runtimeQualification:'not-qualified'};
}
if(require.main===module)try{
 const [edition,work,pinPath,pinSha256,diagnosticPath,output]=process.argv.slice(2),r=review({edition,work,pinPath,pinSha256,diagnosticPath});
 fs.writeFileSync(output,JSON.stringify(r,null,2)+'\n',{flag:'wx'});
 process.stdout.write(JSON.stringify({counts:r.counts,adjudicatedTurns:r.environmentAdjudication.decisions.length,newPassingTurns:0})+'\n');
}catch(error){process.stderr.write(error.stack+'\n');process.exitCode=2;}
module.exports={sshTransportFault,adjudicate,review};
