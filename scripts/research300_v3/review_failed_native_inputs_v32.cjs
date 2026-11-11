'use strict';
// Reproduce the physical-input check for collector-recorded SSH failures.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),{isDeepStrictEqual}=require('node:util');
const {physical}=require('./evaluate-v32.cjs'),{sshTransportFault}=require('./review_native_environment_v32.cjs');
const read=p=>JSON.parse(fs.readFileSync(p)),sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const [editionArg,workArg,output,...caseIds]=process.argv.slice(2),edition=fs.realpathSync(editionArg),work=fs.realpathSync(workArg),manifest=read(path.join(edition,'manifest.json')),rows=[];
if(!caseIds.length||new Set(caseIds).size!==caseIds.length)throw Error('Explicit unique closed cases required');
for(const cid of caseIds){
 const c=manifest.cases.find(c=>c.id===cid);if(!c||!fs.existsSync(path.join(work,'completed-cases',cid+'.json')))throw Error('Unissued/unclosed case');
 for(const id of fs.readdirSync(path.join(work,'solver-jobs',cid))){
  const job=path.join(work,'solver-jobs',cid,id),receipt=read(path.join(job,'broker-receipt.json'));
  if(!sshTransportFault(receipt))continue;
  const turn=c.turns.find(t=>t.id===receipt.turnId),ref=read(path.join(edition,turn.private)),model=read(path.join(job,'model.json')),request=read(path.join(job,'worker-request.json'));
  const match=physical(model,ref.model);
  rows.push({caseId:cid,turnId:receipt.turnId,jobId:id,rawRequestSha256:sha(path.join(job,'submitted-request.json')),
   receiptRequestBindingMatches:sha(path.join(job,'submitted-request.json'))===receipt.requestSha256,
   workerInputAndNormalizedModelIdentical:isDeepStrictEqual(model,request.input.model),completePhysicalInputMatches:match.pass,physicalFailures:match.failures,
   normalizedModelSha256:sha(path.join(job,'model.json')),privateReferenceSha256:sha(path.join(edition,turn.private)),
   candidateScoreCredit:false,nativeResultWasAvailableToCandidate:false});
 }
}
const result={kind:'failed-native-input-physical-check',candidateInvocations:0,nativeSolverInvocations:0,rows,
 allSubmittedPhysicalInputsMatch:rows.length>0&&rows.every(r=>r.completePhysicalInputMatches&&r.receiptRequestBindingMatches&&r.workerInputAndNormalizedModelIdentical),
 scope:'Protected normalized inputs of the failed SSH attempts against the frozen v3.2 physical problem. No score awarded and no missing native output synthesized.',
 sourceSha256:sha(__filename),manifestSha256:sha(path.join(edition,'manifest.json'))};
fs.writeFileSync(output,JSON.stringify(result,null,2)+'\n',{flag:'wx'});
process.stdout.write(JSON.stringify({requests:rows.length,allSubmittedPhysicalInputsMatch:result.allSubmittedPhysicalInputsMatch})+'\n');
