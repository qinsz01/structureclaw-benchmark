'use strict';
// Inspect a completed case without scoring it or communicating with candidates.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {isDeepStrictEqual}=require('node:util');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const read=p=>JSON.parse(fs.readFileSync(p));
const assert=(ok,message)=>{if(!ok)throw Error(message);};
const zero=x=>typeof x==='number'&&x===0?0:Array.isArray(x)?x.map(zero):x&&typeof x==='object'?Object.fromEntries(Object.entries(x).map(([k,v])=>[k,zero(v)])):x;
const equal=(a,b)=>isDeepStrictEqual(zero(a),zero(b));
function safe(root,name){
 assert(typeof name==='string'&&name&&!path.isAbsolute(name)&&!name.includes('\\')&&name.split('/').every(x=>x&&x!=='.'&&x!=='..'),'Unsafe native artifact path');
 let file=root;for(const part of name.split('/')){file=path.join(file,part);assert(!fs.lstatSync(file).isSymbolicLink(),'Symlink in protected artifacts');}
 assert(fs.statSync(file).isFile(),'Protected artifact is not a file');return file;
}
function nativeJob(job,c,t,spec,specSha){
 const attempt=read(path.join(job,'attempt.json')),receipt=read(path.join(job,'broker-receipt.json')),
  raw=fs.readFileSync(path.join(job,'submitted-request.json'));
 assert(attempt.caseId===c.id&&attempt.turnId===t.id&&attempt.evidenceId===path.basename(job)&&attempt.requestSha256===sha(raw),'Attempt ownership differs');
 assert(receipt.role==='candidate'&&receipt.caseId===c.id&&receipt.turnId===t.id&&receipt.engine===c.engine
  &&receipt.requestSha256===sha(raw)&&receipt.sutCommit===spec.sutCommit&&receipt.executionSpecificationSha256===specSha,'Receipt binding differs');
 const result={caseId:c.id,turnId:t.id,evidenceId:attempt.evidenceId,engine:c.engine,ok:receipt.ok,error:receipt.error,
  preExecutionRejection:attempt.preExecutionRejection,requestSha256:sha(raw),workerExecutions:0,originalFiles:[]};
 const remember=file=>{const bytes=fs.readFileSync(file);result.originalFiles.push({path:path.relative(job,file).split(path.sep).join('/'),sha256:sha(bytes),bytes:bytes.length});return bytes;};
 if(c.engine==='OpenSees'){
  const captures=path.join(job,'captures');
  if(fs.existsSync(captures))for(const directory of fs.readdirSync(captures)){
   const root=path.join(captures,directory),capture=read(path.join(root,'capture.json'));remember(path.join(root,'capture.json'));
   result.workerExecutions++;
   for(const [file,hash]of Object.entries(capture.files))assert(sha(remember(safe(root,file)))===hash,'Original worker file changed');
   assert(capture.requestSha256===sha(fs.readFileSync(path.join(root,'request.json'))),'Worker input seal differs');
   assert(equal(read(path.join(root,'request.json')),read(path.join(job,'worker-request.json'))),'Worker dispatch differs');
   for(const record of capture.receipts)for(const [field,file]of Object.entries(record.artifacts)){
    assert(sha(remember(safe(root,file)))===record.receipt[field+'Sha256'],'Native canonical artifact changed');
   }
   if(receipt.ok){
    assert(capture.exitCode===0&&capture.receipts.length>0,'Successful receipt lacks native execution');
    assert(capture.receipts.every(r=>r.solverVersion===spec.solverVersion),'Native OpenSees version differs');
   }
  }
 }else{
  const native=path.join(job,'native');
  if(fs.existsSync(path.join(native,'evidence-manifest.json'))){
   for(const file of read(path.join(native,'evidence-manifest.json'))){
    const bytes=remember(safe(native,file.path));assert(bytes.length===file.bytes&&sha(bytes)===file.sha256,'Native commercial artifact changed');
   }
  }
  if(fs.existsSync(path.join(native,'process-receipt.json')))result.workerExecutions=1;
 }
 if(!receipt.ok)return result;
 const stateBytes=remember(path.join(job,'state.json')),state=JSON.parse(stateBytes),model=read(path.join(job,'model.json')),
  request=JSON.parse(raw),workerRequest=read(path.join(job,'worker-request.json'));
 assert(sha(stateBytes)===receipt.stateSha256&&equal(state.model,model),'Protected native model/state differs');
 assert(equal(workerRequest.input.model,model),'Worker model differs from normalized input');
 assert(result.workerExecutions===1,'Successful job must retain one dispatched worker');
 if(c.engine==='OpenSees'){
  const worker=JSON.parse(remember(path.join(job,'worker.stdout.json')));
  assert(worker.ok&&worker.data.success,'Worker did not succeed');
  if(state.dynamicResult)assert(equal(state.dynamicResult.data,worker.data.data),'Dynamic result changed during packaging');
  else for(const entry of Object.values(state.analysisResult.results))for(const [field,value]of Object.entries(worker.data.data)){
   assert(equal(entry.data[field],value),'Native static field changed: '+field);
  }
  result.solverVersion=spec.solverVersion;
 }else{
  const native=path.join(job,'native'),binding=read(path.join(job,'binding.json')),processReceipt=read(path.join(native,'process-receipt.json')),
   adapter=read(path.join(native,'adapter-receipt.json')),rawResult=read(path.join(native,'result.json')),
   nativeRequestBytes=fs.readFileSync(path.join(native,'request.json')),nativeRequest=JSON.parse(nativeRequestBytes);
  assert(binding.caseId===c.id&&binding.turnId===t.id&&binding.engine===c.engine&&binding.executionRole==='candidate-tool-call'
   &&binding.state===Number(t.id.slice(1))&&binding.sourceHash===spec.editionManifestSha256,'Commercial turn context differs');
  assert(processReceipt.returncode===0&&processReceipt.ownedJobClosed===true&&adapter.status==='completed'&&rawResult.status==='success','Commercial process did not complete');
  assert(adapter.requestSha256===sha(nativeRequestBytes)&&equal(nativeRequest.model,model)&&equal(nativeRequest.parameters,workerRequest.input.parameters),'Native commercial input differs');
  assert(equal(processReceipt,read(path.join(job,'remote-process-receipt.json'))),'Collected process receipt differs');
  const key=request.selection.kind+':'+request.selection.id,entry=state.analysisResult.results[key];
  assert(entry&&equal(entry.selection,{...request.selection,key}),'Commercial selected result differs');
  const wrapped=c.engine==='PKPM'?rawResult.nativeResultSet?.results?.[key]:null;
  const source=wrapped?.data||(request.selection.kind==='case'?rawResult.caseResults?.[request.selection.id]:rawResult.combinationResults?.[request.selection.id]);
  assert(source,'Selected native result missing');
  for(const [field,value]of Object.entries(source))if(field!=='execution')assert(equal(entry.data[field],value),'Native commercial field changed: '+field);
  const mapping=read(path.join(job,'artifact-mapping.json'));
  assert(mapping.runId===state.analysisResult.runId,'Commercial run identity differs');
  for(const [field,file]of Object.entries(mapping.files))assert(sha(remember(safe(job,file)))===entry.data.execution.artifacts[field+'Sha256'],'Commercial source binding differs');
  assert(equal(read(safe(job,mapping.files.normalizedInput)),{model,selection:request.selection}),'Canonical commercial input differs');
  result.solverVersion=rawResult.nativeContext.engineVersion;
  assert(typeof result.solverVersion==='string'&&result.solverVersion.length>0,'Commercial solver version missing');
 }
 result.proofValid=true;return result;
}
function inspect({edition,work,caseId}){
 edition=fs.realpathSync(edition);work=fs.realpathSync(work);
 assert(fs.existsSync(path.join(work,'completed-cases',caseId+'.json')),'Only controller-sealed cases can be inspected');
 const manifestBytes=fs.readFileSync(path.join(edition,'manifest.json')),manifest=JSON.parse(manifestBytes),specBytes=fs.readFileSync(path.join(work,'execution-specification.json')),spec=JSON.parse(specBytes),specSha=sha(specBytes);
 assert(sha(manifestBytes)===spec.editionManifestSha256,'Edition differs');
 const c=manifest.cases.find(c=>c.id===caseId);assert(c,'Unknown case');
 const turns=[],jobs=[],threads=new Set();
 for(const t of c.turns){
  const dir=path.join(work,'runs',c.id,t.id);
  if(!fs.existsSync(path.join(dir,'execution.json'))){turns.push({turnId:t.id,issued:false});continue;}
  const execution=read(path.join(dir,'execution.json')),dispatch=read(path.join(dir,'dispatch.json')),delivery=read(path.join(dir,'input-delivery.json')),
   probe=read(path.join(dir,'isolation.json')),packet=path.join(dir,'issued-packet',t.id),message=fs.readFileSync(path.join(packet,'user-message.txt')),
   prompt=fs.readFileSync(path.join(dir,'prompt.txt'));
  assert(probe.allPassed&&probe.checks.every(r=>r.passed),'Isolation failed');
  assert(sha(prompt)===dispatch.promptSha256&&prompt.toString().endsWith(message.toString())&&sha(message)===delivery.messageSha256,'Actual prompt differs');
  const frozen=manifest.files.filter(f=>f.path.startsWith(t.public+'/'));
  for(const f of frozen){const relative=f.path.slice(t.public.length+1);assert(sha(fs.readFileSync(path.join(packet,relative)))===f.sha256
   &&delivery.files.some(row=>row.path===relative&&row.sha256===f.sha256),'Public input bytes differ');}
  const inline=c.level==='L4'&&t.id==='t1'?['design-catalog.json','engineering-brief.md','primary/section-families.json','upper/section-families.json']:[];
  assert(isDeepStrictEqual(delivery.inlineAttachments,inline),'Inline attachment list differs');
  for(const name of inline)assert(message.includes(fs.readFileSync(path.join(edition,t.public,name))),'Original L4 rules absent');
  const imageArgs=dispatch.command.flatMap((v,i)=>v==='--image'?[dispatch.command[i+1]]:[]),images=frozen.filter(f=>f.path.endsWith('.png'));
  assert(imageArgs.length===images.length&&images.every(f=>imageArgs.some(a=>a.endsWith('/'+f.path.slice(t.public.length+1)))),'Raw images differ');
  if(threads.size)assert(threads.has(dispatch.parentThread)&&threads.has(execution.threadId),'Interactive thread changed');
  threads.add(execution.threadId);
  let observedTools=0;
  for(let i=0;i<execution.actualModelCalls;i++){
   const attempt=path.join(dir,'attempts','a'+String(i+1).padStart(2,'0')),record=read(path.join(attempt,'execution.json')),call=read(path.join(attempt,'dispatch.json'));
   assert(sha(fs.readFileSync(path.join(attempt,'prompt.txt')))===call.promptSha256,'Actual attempt prompt changed');
   assert(record.threadId===execution.threadId,'Recovery thread changed');
   observedTools+=record.toolCallsObserved;
   if(i>0)assert(execution.attempts[i-1].transportRetryEligible===true&&execution.attempts[i-1].candidateStatus==='service_blocked','Non-transport attempt was retried');
  }
  assert(observedTools===execution.toolCallsObserved,'Tool count differs');
  const owned=[];
  for(const identity of fs.existsSync(path.join(work,'solver-jobs',c.id))?fs.readdirSync(path.join(work,'solver-jobs',c.id)):[]){
   const job=path.join(work,'solver-jobs',c.id,identity),attempt=read(path.join(job,'attempt.json'));
   if(attempt.turnId!==t.id)continue;
   owned.push(identity);jobs.push(nativeJob(job,c,t,spec,specSha));
  }
  assert(execution.currentJobIds.every(id=>owned.includes(id)),'Recorded native attempt disappeared');
  const late=owned.filter(id=>!execution.currentJobIds.includes(id));
  for(const id of late)assert(read(path.join(work,'solver-jobs',c.id,id,'attempt.json')).preExecutionRejection==='TURN_CLOSED','Unattributed executable native attempt');
  const answer=path.join(dir,'answer.json');
  turns.push({turnId:t.id,issued:true,candidateStatus:execution.candidateStatus,captureComplete:execution.captureComplete,
   threadId:execution.threadId,modelCalls:execution.actualModelCalls,toolCalls:execution.toolCallsObserved,
   elapsedSeconds:execution.elapsedSeconds,nativeAttempts:owned.length,lateRejectedAttempts:late,publicFiles:frozen.length,rawImages:images.length,
   inlineFiles:inline.length,isolationChecks:probe.checks.length,answerSha256:fs.existsSync(answer)?sha(fs.readFileSync(answer)):null});
 }
 return {kind:'research300-v32-completed-case-inspection',caseId:c.id,engine:c.engine,formalComparisonScore:false,
  candidateInvocations:0,nativeSolverInvocations:0,executionSpecificationSha256:specSha,
  inspectionCodeSha256:sha(fs.readFileSync(__filename)),turns,nativeAttempts:jobs.length,
  nativeSucceeded:jobs.filter(j=>j.ok).length,nativeFailed:jobs.filter(j=>!j.ok).length,
  allSuccessfulNativeProofsValid:jobs.filter(j=>j.ok).every(j=>j.proofValid),jobs};
}
if(require.main===module){
 try{
  const [edition,work,caseId,output]=process.argv.slice(2),result=inspect({edition,work,caseId});
  fs.writeFileSync(output,JSON.stringify(result,null,2)+'\n',{flag:'wx'});
  process.stdout.write(JSON.stringify({caseId,turns:result.turns.length,nativeAttempts:result.nativeAttempts,nativeSucceeded:result.nativeSucceeded})+'\n');
 }catch(e){process.stderr.write(e.stack+'\n');process.exitCode=2;}
}
module.exports={inspect,nativeJob};
