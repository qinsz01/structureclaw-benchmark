'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const {publish}=require('./publish_capture_v32.cjs'),{loadControlledIndex}=require('./controlled-evidence-v32.cjs');
const {example,sha}=require('./test-support-v32.cjs'),{modelFingerprint}=require('../../lib/analysis-evidence.cjs');

// A synthetic worker/archive pair exercises the offline publisher contract.
// It is kept in a temporary directory and is never a native qualification run.
function setup(t){
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'research300-publisher-test-'));
 t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
 const sourceRoot=path.join(root,'source'),edition=path.join(root,'edition'),output=path.join(root,'published');
 fs.mkdirSync(sourceRoot);fs.mkdirSync(edition);
 const put=(name,value)=>{
  const bytes=Buffer.isBuffer(value)?value:Buffer.from(JSON.stringify(value)+'\n');
  const target=path.join(sourceRoot,name);fs.mkdirSync(path.dirname(target),{recursive:true});fs.writeFileSync(target,bytes);
  return {path:name,sha256:sha(bytes)};
 };
 const manifest={cases:[{id:'V3-STD-001',turns:[{id:'t1'}]}]},manifestBytes=Buffer.from(JSON.stringify(manifest));
 fs.writeFileSync(path.join(edition,'manifest.json'),manifestBytes);
 const sutCommit='b'.repeat(40),executionSpecificationSha256='c'.repeat(64),workerSha='d'.repeat(64),wrapperSha='e'.repeat(64);
 const model=example().ref.model,parameters={method:'modal',numModes:1,massSource:'nodal'};
 model.analysis_control.mass_source='nodal';model.nodes[1].mass=1;
 const request={action:'analyze',input:{engineId:'builtin-opensees',type:'dynamic',model,parameters}};
 const payload={status:'success',periods:[.1]},canonical={normalizedInput:model,settings:{parameters:{analysisType:'modal',numModes:1}},solverResponse:payload};
 const execution={executed:true,solver:'OpenSees',solverVersion:'SYNTHETIC-UNIT-TEST',massSource:'explicit-node-mass',
  artifacts:{hashFormat:'sha256:python-json-sort-keys-utf8-compact-v1',solverResponseKeys:Object.keys(payload)}};
 const runId='12345678-1234-1234-1234-123456789abc';
 const archive={success:true,runId,request:structuredClone(request.input),modelHash:modelFingerprint(model),settingsHash:'f'.repeat(64),
  selectedResultKey:'analysis:modal',results:{'analysis:modal':{success:true,selection:{kind:'analysis',id:'modal'},data:{},
   meta:{runId,modelHash:modelFingerprint(model),settingsHash:'f'.repeat(64),effectiveParameters:structuredClone(parameters)}}}};
 const sourceManifest={kind:'research300-native-source-manifest',sutCommit,
  instrumentation:{captureWorkerSha256:wrapperSha},files:[
   {path:'backend/src/agent-skills/analysis/runtime/worker.py',sha256:workerSha},
   {path:'collector/capture_structureclaw_worker_v32.py',sha256:wrapperSha}]};
 const inventory={kind:'research300-v3-collected-session',schemaVersion:1,editionManifestSha256:sha(manifestBytes),sutCommit,
  inputProtocol:'verbatim-public-v3.2',executionSpecificationSha256,turns:[{caseId:'V3-STD-001',turnId:'t1',captureComplete:true,
   environmentStatus:'ready',candidateStatus:'completed',attempts:[{attemptId:'attempt-1',status:'succeeded',engine:'OpenSees'}]}]};
 let afterSeal=()=>{};
 function seal(){
  const artifacts={};for(const [key,value]of Object.entries(canonical)){
   const d=put('worker/'+key+'.json',value);execution.artifacts[key+'Sha256']=d.sha256;artifacts[key]=key+'.json';
  }
  archive.results['analysis:modal'].data={...structuredClone(payload),meta:{execution:structuredClone(execution)}};
  const response={ok:true,data:{success:true,data:{...structuredClone(payload),meta:{execution:structuredClone(execution)}}}};
  afterSeal({archive,response,request,execution});
  const requestFile=put('worker/request.json',request),stdout=put('worker/stdout.json',response),stderr=put('worker/stderr.log',Buffer.from(''));
  const capture=put('worker/capture.json',{kind:'structureclaw-python-worker-capture',schemaVersion:2,
   captureId:'87654321-1234-1234-1234-123456789abc',workerSha256:workerSha,wrapperSha256:wrapperSha,exitCode:0,
   files:{'request.json':requestFile.sha256,'stdout.json':stdout.sha256,'stderr.log':stderr.sha256},requestSha256:requestFile.sha256,
   receipts:[{receipt:execution.artifacts,artifacts}]});
  Object.assign(inventory.turns[0].attempts[0],{archive:put('run.json',archive),captures:[capture]});
  inventory.turns[0].answer=put('answer.json',{runIds:[runId],quantities:[]});
  inventory.sourceManifest=put('source-manifest.json',sourceManifest);
  const inventoryFile=put('inventory.json',inventory);
  return {sourceRoot,edition,output,inventoryPath:inventoryFile.path,inventorySha256:inventoryFile.sha256};
 }
 return {inventory,canonical,archive,request,execution,root,put,seal,setAfterSeal:fn=>afterSeal=fn};
}
test('offline publisher binds exact worker input, settings and output before readback',t=>{
 const f=setup(t),result=publish(f.seal());assert.equal(result.entries,1);assert.equal(result.runtimeQualified,false);
 const reader=loadControlledIndex({root:result.output,indexPath:result.path,indexSha256:result.sha256,
  editionManifestSha256:f.inventory.editionManifestSha256,sutCommit:f.inventory.sutCommit,inputProtocol:f.inventory.inputProtocol,
  executionSpecificationSha256:f.inventory.executionSpecificationSha256});
 const answer=reader.readAnswer('V3-STD-001','t1');assert.deepEqual(answer.jobs[0].state.dynamicResult.data.periods,[.1]);
});
for(const [name,change,pattern]of [
 ['changed reported period',f=>f.setAfterSeal(({archive})=>archive.results['analysis:modal'].data.periods[0]=10),/DYNAMIC_NATIVE_PAYLOAD_CHANGED/],
 ['changed native mode count',f=>f.canonical.settings.parameters.numModes=2,/DYNAMIC_NATIVE_SETTING_CHANGED/],
 ['changed normalized stiffness',f=>{f.canonical.normalizedInput=structuredClone(f.canonical.normalizedInput);f.canonical.normalizedInput.materials[0].E*=2;},/NATIVE_INPUT_OR_SETTINGS_CHANGED/],
 ['worker returned failure',f=>f.setAfterSeal(({response})=>response.ok=false),/ORIGINAL_WORKER_DID_NOT_SUCCEED/],
 ['wrong request engine',f=>f.setAfterSeal(({request})=>request.input.engineId='builtin-yjk'),/WORKER_REQUEST_DIFFERS_FROM_RUN/],
 ['unexecuted payload',f=>f.execution.executed=false,/OPENSEES_NATIVE_RECEIPT_REQUIRED/],
])test('publisher rejects '+name,t=>{const f=setup(t);change(f);assert.throws(()=>publish(f.seal()),pattern);});
test('completed capture cannot hide a failed native attempt without its original logs',t=>{
 const f=setup(t);f.inventory.turns[0].attempts.push({attemptId:'attempt-2',status:'failed'});
 assert.throws(()=>publish(f.seal()),/FAILED_ATTEMPT_LOGS_REQUIRED/);
});
function withAvailabilityProbe(f,options){
 const meta=JSON.parse(fs.readFileSync(path.join(options.sourceRoot,'worker/capture.json')));
 const source=JSON.parse(fs.readFileSync(path.join(options.sourceRoot,'source-manifest.json'))),probeSha='a'.repeat(64);
 source.files.push({path:'backend/src/agent-skills/analysis/opensees-static/opensees_runtime.py',sha256:probeSha});
 const artifacts={};for(const name of ['stdout','stderr']){
  const file=f.put('worker/probes/0-'+name+'.txt',Buffer.from(name==='stdout'?'available\n':''));
  artifacts[name]={path:'probes/0-'+name+'.txt',sha256:file.sha256,representation:'text-utf8'};
 }
 meta.availabilityProbes=[{kind:'opensees-runtime-availability-probe',sourceSha256:probeSha,returnCode:0,artifacts}];
 f.inventory.sourceManifest=f.put('source-manifest.json',source);
 f.inventory.turns[0].attempts[0].captures=[f.put('worker/capture.json',meta)];
 options.inventorySha256=f.put('inventory.json',f.inventory).sha256;
 return options;
}
test('availability solves retain their pinned source and original probe output',t=>{
 const f=setup(t),options=withAvailabilityProbe(f,f.seal()),result=publish(options);
 assert.equal(fs.readFileSync(path.join(result.output,'original/worker/probes/0-stdout.txt'),'utf8'),'available\n');
 const proof=JSON.parse(fs.readFileSync(path.join(result.output,'runs',fs.readdirSync(path.join(result.output,'runs'))[0],'execution-proof.json')));
 assert(proof.artifacts.some(file=>file.path==='original/worker/probes/0-stdout.txt'));
});
test('a recorded availability solve cannot use an unpinned source',t=>{
 const f=setup(t),options=withAvailabilityProbe(f,f.seal());
 const file=path.join(options.sourceRoot,'worker/capture.json'),meta=JSON.parse(fs.readFileSync(file));
 meta.availabilityProbes[0].sourceSha256='f'.repeat(64);
 f.inventory.turns[0].attempts[0].captures=[f.put('worker/capture.json',meta)];
 options.inventorySha256=f.put('inventory.json',f.inventory).sha256;
 assert.throws(()=>publish(options),/PINNED_AVAILABILITY_PROBE_REQUIRED/);
});
test('a recorded availability solve cannot lose its original output seal',t=>{
 const f=setup(t),options=withAvailabilityProbe(f,f.seal());
 fs.appendFileSync(path.join(options.sourceRoot,'worker/probes/0-stdout.txt'),'tampered');
 assert.throws(()=>publish(options),{code:'EVIDENCE_HASH_MISMATCH'});
});
