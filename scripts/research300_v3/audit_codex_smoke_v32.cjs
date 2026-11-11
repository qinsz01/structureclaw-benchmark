'use strict';
// Independent post-run inspection and synthetic controls on COPIES of actual
// candidate deliveries. No solver/model calls and no edits to original evidence.
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),crypto=require('node:crypto');
const {isDeepStrictEqual}=require('node:util');
const {grade}=require('./grade_codex_smoke_v32.cjs');
const {loadControlledIndex}=require('./controlled-evidence-v32.cjs');
const {controls}=require('./controls-v32.cjs');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const read=p=>JSON.parse(fs.readFileSync(p));
const assert=(v,m)=>{if(!v)throw Error(m);};
const zero=x=>typeof x==='number'&&x===0?0:Array.isArray(x)?x.map(zero):x&&typeof x==='object'?Object.fromEntries(Object.entries(x).map(([k,v])=>[k,zero(v)])):x;
function audit({edition,controlRoot,pinPath,pinSha256}){
 edition=fs.realpathSync(edition);controlRoot=fs.realpathSync(controlRoot);
 const diagnostic=grade({edition,controlRoot,pinPath,pinSha256}),pin=read(pinPath),index=read(path.join(controlRoot,pin.index.path)),spec=read(path.join(controlRoot,pin.specification.path));
 const manifest=read(path.join(edition,'manifest.json')),seals=new Map(manifest.files.map(f=>[f.path,f.sha256]));
 const evidenceOptions={root:controlRoot,indexPath:pin.index.path,indexSha256:pin.index.sha256,
  editionManifestSha256:spec.editionManifestSha256,sutCommit:spec.sutCommit,inputProtocol:spec.inputProtocol,
  executionSpecificationSha256:pin.specification.sha256};
 const reader=loadControlledIndex(evidenceOptions),inputs=[],threads=new Map(),native=[];
 for(const turn of index.turns){
  const c=manifest.cases.find(c=>c.id===turn.caseId),t=c.turns.find(t=>t.id===turn.turnId),dir=path.join(controlRoot,'runs',c.id,t.id);
  if(!fs.existsSync(path.join(dir,'dispatch.json')))continue;
  const delivery=read(path.join(dir,'input-delivery.json')),dispatch=read(path.join(dir,'dispatch.json')),
   execution=read(path.join(dir,'execution.json')),probe=read(path.join(dir,'isolation.json')),
   prompt=fs.readFileSync(path.join(dir,'prompt.txt'),'utf8'),packet=path.join(dir,'issued-packet',t.id),message=fs.readFileSync(path.join(packet,'user-message.txt'));
  assert(probe.allPassed&&probe.checks.every(r=>r.passed),'Isolation check did not pass');
  assert(sha(Buffer.from(prompt))===dispatch.promptSha256&&prompt.endsWith(message.toString())&&sha(message)===delivery.messageSha256,'Actual prompt differs from verbatim message');
  const frozen=manifest.files.filter(f=>f.path.startsWith(t.public+'/'));
  for(const f of frozen){
   const relative=f.path.slice(t.public.length+1),bytes=fs.readFileSync(path.join(packet,relative));
   assert(sha(bytes)===f.sha256&&delivery.files.some(row=>row.path===relative&&row.sha256===f.sha256),'Public bytes differ');
  }
  const inline=c.level==='L4'&&t.id==='t1'?['design-catalog.json','engineering-brief.md','primary/section-families.json','upper/section-families.json']:[];
  assert(isDeepStrictEqual(inline,delivery.inlineAttachments),'L4 inline source list differs');
  for(const name of inline)assert(message.includes(fs.readFileSync(path.join(edition,t.public,name))),'Original L4 rules not verbatim');
  const imageArgs=dispatch.command.flatMap((v,i)=>v==='--image'?[dispatch.command[i+1]]:[]);
  const imageFiles=frozen.filter(f=>f.path.endsWith('.png'));
  assert(imageArgs.length===imageFiles.length&&imageFiles.every(f=>imageArgs.some(a=>a.endsWith('/'+f.path.slice(t.public.length+1)))),'Raw image dispatch differs');
  if(threads.has(c.id))assert(dispatch.parentThread===threads.get(c.id)&&execution.threadId===threads.get(c.id),'Interactive thread identity differs');
  threads.set(c.id,execution.threadId);
  inputs.push({caseId:c.id,turnId:t.id,publicFiles:frozen.length,inlineFiles:inline.length,rawImages:imageArgs.length,
   isolationChecks:probe.checks.length,allPassed:true,threadId:execution.threadId,toolCallsObserved:execution.toolCallsObserved});
  for(const id of turn.currentJobIds){
   const job=path.join(controlRoot,'solver-jobs',c.id,id),attempt=read(path.join(job,'attempt.json')),receipt=read(path.join(job,'broker-receipt.json')),
    raw=fs.readFileSync(path.join(job,'submitted-request.json'));
   assert(attempt.evidenceId===id&&attempt.caseId===c.id&&attempt.turnId===t.id&&attempt.requestSha256===sha(raw),'Attempt ownership/input mismatch');
   assert(receipt.caseId===c.id&&receipt.turnId===t.id&&receipt.role==='candidate'&&receipt.requestSha256===sha(raw)
    &&receipt.sutCommit===spec.sutCommit&&receipt.executionSpecificationSha256===pin.specification.sha256,'Native receipt binding differs');
   const captures=[];
   if(fs.existsSync(path.join(job,'captures')))for(const name of fs.readdirSync(path.join(job,'captures'))){
    const base=path.join(job,'captures',name),capture=read(path.join(base,'capture.json'));
    for(const [file,hash]of Object.entries(capture.files))assert(sha(fs.readFileSync(path.join(base,file)))===hash,'Original worker output seal differs');
    for(const record of capture.receipts)for(const [field,file]of Object.entries(record.artifacts)){
     assert(sha(fs.readFileSync(path.join(base,file)))===record.receipt[field+'Sha256'],'Native canonical artifact differs');
    }
    assert(capture.requestSha256===sha(fs.readFileSync(path.join(base,'request.json'))),'Captured worker input differs');
    assert(isDeepStrictEqual(read(path.join(job,'worker-request.json')),read(path.join(base,'request.json'))),'Dispatched/captured worker request differs');
    captures.push({exitCode:capture.exitCode,receipts:capture.receipts.length,solverVersions:[...new Set(capture.receipts.map(r=>r.solverVersion))]});
   }
   if(receipt.ok){
    const state=fs.readFileSync(path.join(job,'state.json'));
    assert(sha(state)===receipt.stateSha256&&captures.length===1&&captures[0].exitCode===0&&captures[0].receipts>0,'Successful native evidence incomplete');
    assert(captures[0].solverVersions.every(v=>v===spec.solverVersion),'Native solver version differs');
    const actual=JSON.parse(state),worker=read(path.join(job,'worker.stdout.json'));
    assert(worker.ok&&worker.data.success,'Successful receipt lacks successful worker output');
    if(actual.dynamicResult)assert(isDeepStrictEqual(zero(actual.dynamicResult.data),zero(worker.data.data)),'Dynamic result changed after native execution');
    else for(const result of Object.values(actual.analysisResult.results))for(const [field,value]of Object.entries(worker.data.data)){
     assert(isDeepStrictEqual(zero(result.data[field]),zero(value)),'Static native field changed during packaging: '+field);
    }
   }
   native.push({caseId:c.id,turnId:t.id,evidenceId:id,ok:receipt.ok,error:receipt.error,
    preExecutionRejection:attempt.preExecutionRejection,captures});
  }
 }
 const controlRows=[];
 const replaceRefs=(answer,id)=>{
  const b=structuredClone(answer);
  for(const key of ['jobIds','runIds'])if(b[key])b[key]=b[key].map(()=>id);
  for(const key of ['jobIdsByScenario','jobIdsByModel','runIdsByScenario','runIdsByModel'])if(b[key])for(const k of Object.keys(b[key]))b[key][k]=b[key][k].map(()=>id);
  return b;
 };
 for(const row of diagnostic.rows.filter(r=>r.outcome==='passed')){
  const c=manifest.cases.find(c=>c.id===row.caseId),t=c.turns.find(t=>t.id===row.turnId),captured=reader.readAnswer(c.id,t.id),ref=read(path.join(edition,t.private));
  for(const result of controls(ref,captured.answer,captured.jobs,captured.currentJobIds))controlRows.push({caseId:c.id,turnId:t.id,...result});
  const identities=[['unknown-execution','f'.repeat(32)],['preflight-cannot-be-candidate','preflight-native']];
  const cross=index.entries.find(e=>e.caseId!==c.id),future=index.entries.find(e=>e.caseId===c.id&&Number(e.turnId.slice(1))>Number(t.id.slice(1)));
  if(cross)identities.push(['cross-case-execution',cross.evidenceId]);
  if(future)identities.push(['future-turn-execution',future.evidenceId]);
  for(const [name,id]of identities){
   let actual='accepted';try{reader.resolveAnswer(replaceRefs(captured.answer,id),c.id,t.id);}catch(e){actual=e.code;}
   controlRows.push({caseId:c.id,turnId:t.id,name,scope:'controlled-evidence-reader',expected:'EVIDENCE_NOT_RELEASED',actual,passed:actual==='EVIDENCE_NOT_RELEASED'});
  }
 }
 // Alter request bytes only in a temporary copy, keeping the original seal.
 const passed=diagnostic.rows.find(r=>r.outcome==='passed'&&r.evidenceMapping.length);
 if(passed){
  const temp=fs.mkdtempSync(path.join(os.tmpdir(),'codex-smoke-tamper-'));
  try{
   const copy=file=>{const target=path.join(temp,file);fs.mkdirSync(path.dirname(target),{recursive:true});fs.copyFileSync(path.join(controlRoot,file),target);};
   copy(pin.index.path);
   const turn=index.turns.find(t=>t.caseId===passed.caseId&&t.turnId===passed.turnId);copy(turn.answer.path);
   const ids=new Set(passed.evidenceMapping.map(m=>m.evidenceId)),entries=index.entries.filter(e=>ids.has(e.evidenceId));
   for(const entry of entries)for(const file of Object.values(entry.files))copy(file.path);
   fs.appendFileSync(path.join(temp,entries[0].files.request.path),' ');
   let actual='accepted';try{loadControlledIndex({...evidenceOptions,root:temp}).readAnswer(passed.caseId,passed.turnId);}catch(e){actual=e.code;}
   controlRows.push({name:'tampered-actual-native-request',scope:'controlled-evidence-reader',expected:'EVIDENCE_HASH_MISMATCH',actual,passed:actual==='EVIDENCE_HASH_MISMATCH'});
  }finally{fs.rmSync(temp,{recursive:true,force:true});}
 }
 return {kind:'research300-v32-codex-smoke-inspection',formalComparisonScore:false,candidateInvocations:0,nativeSolverInvocations:0,
  operatorPinSha256:pinSha256,inputs,nativeAttempts:native.length,nativeSuccessful:native.filter(r=>r.ok).length,
  nativeFailed:native.filter(r=>!r.ok).length,native,controls:controlRows.length,controlsPassed:controlRows.filter(r=>r.passed).length,
  allControlsPassed:controlRows.length>0&&controlRows.every(r=>r.passed),controlRows,
  inspectionCode:{'audit_codex_smoke_v32.cjs':sha(fs.readFileSync(__filename)),
   'controls-v32.cjs':sha(fs.readFileSync(path.join(__dirname,'controls-v32.cjs')))},
  scope:'Transport/native/input consistency and synthetic corruption checks; not independent engineering-expert validation'};
}
if(require.main===module){
 try{
  const names={'--edition':'edition','--control-root':'controlRoot','--pin':'pinPath','--pin-sha256':'pinSha256','--output':'output'},options={},args=process.argv.slice(2);
  for(let i=0;i<args.length;i++){assert(names[args[i]]&&args[i+1],'Invalid arguments');options[names[args[i]]]=args[++i];}
  const result=audit(options);fs.writeFileSync(options.output,JSON.stringify(result,null,2)+'\n',{flag:'wx'});
  process.stdout.write(JSON.stringify({output:options.output,inputs:result.inputs.length,nativeAttempts:result.nativeAttempts,controls:result.controls,controlsPassed:result.controlsPassed})+'\n');
 }catch(e){process.stderr.write(e.stack+'\n');process.exitCode=2;}
}
module.exports={audit};
