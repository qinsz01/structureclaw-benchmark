'use strict';
// Offline publisher for already collected, operator-owned originals. Never
// starts an agent/worker, invents an answer, reads gold data or grants qualification.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),zlib=require('node:zlib');
const {isDeepStrictEqual}=require('node:util');
const {readSealed,EvidenceError}=require('./controlled-evidence-v32.cjs');
const {archiveToRun}=require('../../lib/import-structureclaw.cjs');
const {modelFingerprint}=require('../../lib/analysis-evidence.cjs');
const {verifyStructureClawPayloadBinding}=require('../../lib/structureclaw-payload-binding.cjs');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const record=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);
const equal=(a,b)=>isDeepStrictEqual(JSON.parse(JSON.stringify(a)),JSON.parse(JSON.stringify(b)));
const must=(ok,code)=>{if(!ok)throw new EvidenceError(code,code);};
const selectors={OpenSees:['builtin-opensees','opensees-static','opensees-dynamic'],PKPM:['builtin-pkpm','pkpm-static'],YJK:['builtin-yjk','yjk-static']};
function commercialStationsMatch(model,native,archived){
 // The host's withGlobalResultLocations adds only derived display coordinates.
 // Check those against the original model exactly before comparing every
 // original station field. Never remove a coordinate already supplied natively.
 if(!record(native)||!record(archived))return false;
 const view=structuredClone(archived);
 for(const [id,rows]of Object.entries(view)){
  if(!Array.isArray(rows)||!Array.isArray(native[id])||rows.length!==native[id].length)return false;
  for(let i=0;i<rows.length;i++){
   const row=rows[i],original=native[id][i];
   if(!record(row)||!record(original))return false;
   if(Object.hasOwn(row,'global')&&!Object.hasOwn(original,'global')){
    const elements=(model.elements||[]).filter(e=>e.id===id);
    if(elements.length!==1||!Array.isArray(elements[0].nodes)||elements[0].nodes.length!==2)return false;
    const endpoints=elements[0].nodes.map(id=>(model.nodes||[]).filter(n=>n.id===id));
    if(endpoints.some(nodes=>nodes.length!==1))return false;
    const [a,b]=endpoints.map(nodes=>nodes[0]),keys=['x','y','z'];
    if(!keys.every(k=>Number.isFinite(a[k])&&Number.isFinite(b[k])))return false;
    const length=Math.hypot(b.x-a.x,b.y-a.y,b.z-a.z),position=row.positionM;
    const roundoff=8*Number.EPSILON*Math.max(1,length);
    if(!length||!Number.isFinite(position)||position < -roundoff||position > length+roundoff)return false;
    const fraction=Math.max(0,Math.min(length,position))/length;
    const expected=Object.fromEntries(keys.map(k=>[k,a[k]+fraction*(b[k]-a[k])]));
    if(!equal(row.global,expected))return false;
    delete row.global;
   }
  }
 }
 return equal(native,view);
}
function hostInputView(model){
 // StructureModelV2 drops these display names and explicitly materializes the
 // documented global load-frame default. Keep the protected originals intact;
 // explicit frames, IDs, loads and every unknown field still bind exactly.
 const value=structuredClone(model);
 for(const row of value.load_cases||[]){
  if(typeof row.name==='string')delete row.name;
  for(const load of row.loads||[])if(['nodal','distributed','point'].includes(load.type)&&load.reference_frame===undefined)load.reference_frame='global';
 }
 for(const row of value.load_combinations||[])if(typeof row.name==='string')delete row.name;
 return value;
}
function physics(model){
 const value=hostInputView(model);
 for(const m of value.materials||[])if(['steel','concrete','rebar','other'].includes(m.type)){
  must(m.category==null||m.category===m.type,'CAPTURE_MATERIAL_ALIAS_CONFLICT');m.category=m.type;delete m.type;
 }
 for(const name of ['materials','sections'])for(const row of value[name]||[])if(record(row.extra)&&!Object.keys(row.extra).length)delete row.extra;
 if(record(value.metadata))for(const key of ['coordinateContractVersion','coordinateSemantics','frameDimension'])delete value.metadata[key];
 return modelFingerprint(value);
}
function publish({sourceRoot,inventoryPath,inventorySha256,edition,output}){
 sourceRoot=fs.realpathSync(sourceRoot);edition=fs.realpathSync(edition);output=path.resolve(output);
 must(![sourceRoot,edition].some(root=>output===root||output.startsWith(root+path.sep)||root.startsWith(output+path.sep)),'PUBLISH_OUTPUT_OVERLAPS_INPUT');
 const inventory=JSON.parse(readSealed(sourceRoot,{path:inventoryPath,sha256:inventorySha256}));
 const manifestBytes=fs.readFileSync(path.join(edition,'manifest.json')),manifest=JSON.parse(manifestBytes);
 must(inventory.kind==='research300-v3-collected-session'&&inventory.schemaVersion===1
  &&inventory.editionManifestSha256===sha(manifestBytes)&&inventory.inputProtocol==='verbatim-public-v3.2'
  &&/^[a-f0-9]{40}$/.test(inventory.sutCommit)&&/^[a-f0-9]{64}$/.test(inventory.executionSpecificationSha256)
  &&Array.isArray(inventory.turns),'COLLECTION_IDENTITY_INVALID');
 const source=JSON.parse(readSealed(sourceRoot,inventory.sourceManifest));
 must(source.kind==='research300-native-source-manifest'&&source.sutCommit===inventory.sutCommit&&Array.isArray(source.files),'PINNED_NATIVE_SOURCE_REQUIRED');
 const workerSha=source.files.find(row=>row.path==='backend/src/agent-skills/analysis/runtime/worker.py')?.sha256;
 must(/^[a-f0-9]{64}$/.test(workerSha),'PINNED_WORKER_REQUIRED');
 must(/^[a-f0-9]{64}$/.test(source.instrumentation?.captureWorkerSha256)
  &&source.files.find(row=>row.path==='collector/capture_structureclaw_worker_v32.py')?.sha256===source.instrumentation.captureWorkerSha256,
  'PINNED_CAPTURE_WRAPPER_REQUIRED');
 const allowed=new Set(manifest.cases.flatMap(c=>c.turns.map(t=>c.id+'/'+t.id))),provided=new Map();
 for(const t of inventory.turns){
  const key=t.caseId+'/'+t.turnId;
  must(allowed.has(key)&&!provided.has(key)&&Array.isArray(t.attempts)&&typeof t.captureComplete==='boolean'
   &&['ready','blocked'].includes(t.environmentStatus)&&['completed','candidate_failed','service_blocked','interrupted'].includes(t.candidateStatus),'COLLECTION_TURN_INVALID');
  provided.set(key,t);
 }
 fs.mkdirSync(output,{recursive:false});
 function save(relative,bytes){const file=path.join(output,relative);fs.mkdirSync(path.dirname(file),{recursive:true});fs.writeFileSync(file,bytes,{flag:'wx'});return {path:relative,sha256:sha(bytes)};}
 function json(relative,obj){return save(relative,Buffer.from(JSON.stringify(obj,null,2)+'\n'));}
 const originals=new Map();
 function keep(descriptor){
  const bytes=readSealed(sourceRoot,descriptor),key=descriptor.path;
  if(!originals.has(key))originals.set(key,save('original/'+key,bytes));
  else must(originals.get(key).sha256===descriptor.sha256,'ORIGINAL_PATH_REBOUND');
  return originals.get(key);
 }
 function originalJSON(descriptor){keep(descriptor);return JSON.parse(readSealed(sourceRoot,descriptor));}
 keep({path:inventoryPath,sha256:inventorySha256});keep(inventory.sourceManifest);
 const entries=[],turns=[],runs=new Set(),ids=new Set(),usedCaptures=new Set(),captureIds=new Set();
 function probeArtifacts(metadata,prefix){
  const probes=metadata.availabilityProbes||[];
  must(Array.isArray(probes),'AVAILABILITY_PROBE_INVENTORY_INVALID');
  return probes.flatMap(probe=>{
   const expected=source.files.find(row=>row.path==='backend/src/agent-skills/analysis/opensees-static/opensees_runtime.py')?.sha256;
   must(probe.kind==='opensees-runtime-availability-probe'&&digestProbe(probe.sourceSha256)&&probe.sourceSha256===expected
    &&(Number.isInteger(probe.returnCode)||typeof probe.exceptionType==='string')
    &&record(probe.artifacts)&&['stdout','stderr'].every(name=>record(probe.artifacts[name])),
    'PINNED_AVAILABILITY_PROBE_REQUIRED');
   return Object.values(probe.artifacts).map(file=>{
    must(['bytes','text-utf8'].includes(file.representation),'PROBE_OUTPUT_REPRESENTATION_INVALID');
    const descriptor={path:(prefix==='.'?'':prefix+'/')+file.path,sha256:file.sha256};keep(descriptor);return descriptor;
   });
  });
 }
 function digestProbe(value){return typeof value==='string'&&/^[a-f0-9]{64}$/.test(value);}
 function capture(descriptor,archive,engine){
  const metadata=originalJSON(descriptor),prefix=path.posix.dirname(descriptor.path);
  must(metadata.kind==='structureclaw-python-worker-capture'&&metadata.schemaVersion===2&&metadata.workerSha256===workerSha
   &&metadata.exitCode===0&&record(metadata.files),'SUCCESSFUL_ORIGINAL_WORKER_CAPTURE_REQUIRED');
  must(typeof metadata.captureId==='string'&&/^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/i.test(metadata.captureId)
   &&!captureIds.has(metadata.captureId),'WORKER_CAPTURE_ID_MISSING_OR_REUSED');captureIds.add(metadata.captureId);
  must(metadata.wrapperSha256===source.instrumentation?.captureWorkerSha256,'CAPTURE_WRAPPER_SOURCE_CHANGED');
  const files={};
  for(const name of ['request.json','stdout.json','stderr.log']){
   const d={path:(prefix==='.'?'':prefix+'/')+name,sha256:metadata.files[name]};keep(d);files[name]=d;
  }
  must(metadata.requestSha256===files['request.json'].sha256,'CAPTURE_REQUEST_HASH_MISMATCH');
  const request=originalJSON(files['request.json']),response=originalJSON(files['stdout.json']);
  must(request.action==='analyze'&&request.input?.engineId===archive.request.engineId&&selectors[engine]?.includes(request.input.engineId)
   &&request.input.type===archive.request.type&&modelFingerprint(request.input.model)===archive.modelHash,
   'WORKER_REQUEST_DIFFERS_FROM_RUN');
  if(archive.request.requestId!==undefined)must(request.input.requestId===archive.request.requestId,'WORKER_REQUEST_ID_CHANGED');
  must(response.ok===true&&response.data?.success===true&&record(response.data.data),'ORIGINAL_WORKER_DID_NOT_SUCCEED');
  return {metadata,prefix,descriptor,request:request.input,response:response.data,artifacts:[...Object.values(files),...probeArtifacts(metadata,prefix)]};
 }
 function bindRecord(archive,key,row,captures,engine){
  const matches=captures.filter(c=>engine==='OpenSees'?(row.selection?.kind==='case'?
   c.request.parameters?.loadCaseIds?.length===1&&c.request.parameters.loadCaseIds[0]===row.selection.id:
   row.selection?.kind==='combination'?c.request.parameters?.loadCombinationId===row.selection.id:
   row.selection?.kind==='analysis') : c.response.data.nativeResultSet?.results?.[key]);
  must(matches.length===1,'RESULT_WORKER_BINDING_AMBIGUOUS');const c=matches[0];
  c.used=true;
  if(engine==='OpenSees'){
   const data=c.response.data,execution=data.execution||data.meta?.execution;
   must(execution?.executed===true&&String(execution.solver).toLowerCase()==='opensees'
    &&execution.artifacts?.hashFormat==='sha256:python-json-sort-keys-utf8-compact-v1','OPENSEES_NATIVE_RECEIPT_REQUIRED');
   const receipts=(c.metadata.receipts||[]).filter(r=>['normalizedInput','settings','solverResponse'].every(n=>r.receipt?.[n+'Sha256']===execution.artifacts[n+'Sha256']));
   must(receipts.length===1,'CANONICAL_RECEIPT_BINDING_AMBIGUOUS');const canonical={},parsed={};
   for(const name of ['normalizedInput','settings','solverResponse']){
    const d={path:(c.prefix==='.'?'':c.prefix+'/')+receipts[0].artifacts[name],sha256:execution.artifacts[name+'Sha256']};
    const bytes=readSealed(sourceRoot,d);canonical[name]=bytes;parsed[name]=JSON.parse(bytes);keep(d);c.artifacts.push(d);
   }
   must(equal(c.request.parameters||{},row.meta?.effectiveParameters||{})
    &&physics(parsed.normalizedInput)===physics(archive.request.model),'NATIVE_INPUT_OR_SETTINGS_CHANGED');
   if(archive.request.type!=='static'){
    // Dynamic workers emit the executed settings, rather than echoing the
    // host's method/mass-source/selector JSON. Bind that documented projection
    // without pretending that it is byte-identical to the request object.
    const requested=c.request.parameters||{},actual=parsed.settings.parameters||{};
    must(['modal','time_history'].includes(requested.method)&&actual.analysisType===requested.method,'DYNAMIC_NATIVE_METHOD_CHANGED');
    for(const name of ['numModes','direction','timeStep','duration','dampingRatio','groundMotionUnit']){
     if(requested[name]!==undefined)must(equal(requested[name],actual[name]),'DYNAMIC_NATIVE_SETTING_CHANGED: '+name);
    }
    for(const name of ['monitorNodeIds','monitorElementIds','monitorSupportNodeIds'])if(requested[name]!==undefined){
     must(Array.isArray(requested[name])&&Array.isArray(actual[name])
      &&equal([...new Set(requested[name].map(String))].sort(),[...new Set(actual[name].map(String))].sort()),'DYNAMIC_NATIVE_MONITORS_CHANGED: '+name);
    }
    const massSources={'nodal':'explicit-node-mass','member-density':'member-density-lumped-half-to-endpoints','floor-seismic':'story-gravity-representative-weight'};
    if(requested.massSource!==undefined)must(massSources[requested.massSource]&&execution.massSource===massSources[requested.massSource],'DYNAMIC_NATIVE_MASS_SOURCE_CHANGED');
    const keys=execution.artifacts.solverResponseKeys;
    must(Array.isArray(keys)&&equal([...keys].sort(),Object.keys(parsed.solverResponse).sort())
     &&keys.every(k=>equal(parsed.solverResponse[k],row.data[k])),'DYNAMIC_NATIVE_PAYLOAD_CHANGED');
   }else{
    const binding=verifyStructureClawPayloadBinding({model:hostInputView(archive.request.model),selection:row.selection,data:row.data,
     meta:row.meta,execution,artifactBytes:canonical});must(binding.pass,'STATIC_NATIVE_PAYLOAD_UNBOUND: '+binding.failures.join('; '));
   }
   must(equal(row.data.meta?.execution?.artifacts,execution.artifacts),'ARCHIVED_EXECUTION_RECEIPT_CHANGED');
   return execution.solverVersion;
  }
  const raw=c.response.data.nativeResultSet.results[key];
  must(raw.success===true&&raw.data?.selectedResult?.kind===row.selection.kind&&raw.data.selectedResult.id===row.selection.id,'COMMERCIAL_NATIVE_SELECTION_INVALID');
  const native=raw.data;
  must(native.nativeContext?.engine===engine.toLowerCase()&&native.nativeContext.linearStatic===true
   &&native.nativeContext.effectiveSettingsVerified===true&&native.nativeContext.stationConventionsVerified===true,'COMMERCIAL_NATIVE_CONTEXT_UNVERIFIED');
  for(const field of ['displacements','reactions','forces','memberStations','nativeContext','forceSemantics','units','selectedResult']){
   must(native[field]!==undefined&&(field==='memberStations'?
    commercialStationsMatch(archive.request.model,native[field],row.data[field]):equal(native[field],row.data[field])),
    'COMMERCIAL_NATIVE_FIELD_CHANGED: '+field);
  }
  return native.nativeContext.engineVersion;
 }
 for(const c of manifest.cases)for(const t of c.turns){
  const collected=provided.get(c.id+'/'+t.id);
  if(!collected){turns.push({caseId:c.id,turnId:t.id,captureComplete:false,environmentStatus:'ready',candidateStatus:'interrupted',currentJobIds:[]});continue;}
  const turn={caseId:c.id,turnId:t.id,captureComplete:collected.captureComplete,environmentStatus:collected.environmentStatus,
   candidateStatus:collected.candidateStatus,currentJobIds:[],nativeWorkerAttempts:0};
  if(collected.answer)turn.answer=keep(collected.answer);
  for(const attempt of collected.attempts){
   must(typeof attempt.attemptId==='string'&&attempt.attemptId.length>0&&['succeeded','failed','blocked','incomplete'].includes(attempt.status),'NATIVE_ATTEMPT_INVALID');
   const id=sha(inventorySha256+'\n'+c.id+'\n'+t.id+'\n'+attempt.attemptId).slice(0,32);
   must(!ids.has(id),'ATTEMPT_ID_REUSED');ids.add(id);turn.currentJobIds.push(id);
   for(const file of attempt.rawArtifacts||[])keep(file);
   const descriptors=attempt.captures||[];must(Array.isArray(descriptors),'NATIVE_CAPTURE_LIST_INVALID');
   turn.nativeWorkerAttempts+=descriptors.length;
   for(const d of descriptors){must(!usedCaptures.has(d.path),'NATIVE_CAPTURE_REUSED_ACROSS_RUNS');usedCaptures.add(d.path);}
   if(attempt.status!=='succeeded'){
    if(attempt.archive)keep(attempt.archive);
    for(const file of attempt.nativeArtifacts||[])keep(file);
    for(const d of descriptors){
     const meta=originalJSON(d),prefix=path.posix.dirname(d.path);
     must(meta.schemaVersion===2&&typeof meta.captureId==='string'&&!captureIds.has(meta.captureId),'FAILED_CAPTURE_ID_MISSING_OR_REUSED');captureIds.add(meta.captureId);
     for(const name of ['request.json','stdout.json','stderr.log'])keep({path:(prefix==='.'?'':prefix+'/')+name,sha256:meta.files?.[name]});
     for(const receipt of meta.receipts||[])for(const [name,file]of Object.entries(receipt.artifacts||{})){
      keep({path:(prefix==='.'?'':prefix+'/')+file,sha256:receipt.receipt?.[name+'Sha256']});
     }
     probeArtifacts(meta,prefix);
    }
    must(!collected.captureComplete||descriptors.length>0||attempt.rawArtifacts?.length>0,'FAILED_ATTEMPT_LOGS_REQUIRED');
    continue;
   }
   must(Array.isArray(attempt.captures)&&attempt.captures.length>0,'WORKER_CAPTURES_REQUIRED');
   const archiveBytes=readSealed(sourceRoot,attempt.archive);keep(attempt.archive);
   const archive=JSON.parse(attempt.archive.path.endsWith('.gz')?zlib.gunzipSync(archiveBytes,{maxOutputLength:256*1024*1024}):archiveBytes);
   must(archive.success===true&&/^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/i.test(archive.runId)&&!runs.has(archive.runId),'ORIGINAL_SUCCESSFUL_RUN_REQUIRED');runs.add(archive.runId);
   const run=archiveToRun(archive);must(run!==archive&&Object.keys(archive.results).length>0,'ORIGINAL_RUN_ARCHIVE_REQUIRED');
   const engine=attempt.engine;must(Object.hasOwn(selectors,engine),'UNKNOWN_NATIVE_ENGINE');
   const captures=descriptors.map(d=>capture(d,archive,engine));
   const versions=Object.entries(archive.results).map(([key,row])=>bindRecord(archive,key,row,captures,engine));
   must(captures.every(x=>x.used)&&versions.every(v=>typeof v==='string'&&v.trim()&&v===versions[0]),'UNUSED_CAPTURE_OR_CONFLICTING_NATIVE_VERSION');
   const nativeFiles=(attempt.nativeArtifacts||[]).map(d=>{keep(d);return d;});
   if(engine!=='OpenSees')must(nativeFiles.length>0&&nativeFiles.some(d=>JSON.stringify(captures.map(x=>x.response.data)).includes(d.sha256)),'ORIGINAL_VENDOR_ARTIFACT_BINDING_REQUIRED');
   const prefix='runs/'+id+'/',model=json(prefix+'model.json',archive.request.model),selected=archive.results[archive.selectedResultKey];
   const method=archive.request.parameters?.method,kind=method==='modal'?'modal':method==='time_history'?'transient':null;
   must(archive.request.type==='static'||kind,'UNSUPPORTED_DYNAMIC_METHOD');
   const state=json(prefix+'state.json',{model:archive.request.model,...(kind?{
    dynamicResult:{analysis:kind,data:selected.data,parameters:selected.meta.effectiveParameters,meta:selected.meta}
   }:{analysisResult:run})});
   const originalsForRun=[keep(attempt.archive),...captures.flatMap(x=>[keep(x.descriptor),...x.artifacts.map(keep)]),...nativeFiles.map(keep)];
   const proof=json(prefix+'execution-proof.json',{kind:'research300-native-execution-proof',caseId:c.id,runId:archive.runId,
    sutCommit:inventory.sutCommit,engine,modelSha256:model.sha256,workerExitCode:0,executed:true,solverVersion:versions[0],
    parameters:kind?selected.meta.effectiveParameters:undefined,nativeWorkerAttempts:captures.length,artifacts:originalsForRun,
    collectorRevision:'v3.2',qualification:'not-run',sourceInventorySha256:inventorySha256});
   const receipt=json(prefix+'receipt.json',{role:'candidate',ok:true,caseId:c.id,engine,runId:archive.runId,
    stateSha256:state.sha256,archiveSha256:attempt.archive.sha256,executionProofSha256:proof.sha256});
   entries.push({caseId:c.id,turnId:t.id,evidenceId:id,runId:archive.runId,engine,origin:'structureclaw',
    files:{model,state,receipt,archive:keep(attempt.archive),executionProof:proof}});
  }
  turns.push(turn);
 }
 const index={schemaVersion:1,kind:'research300-v3-controlled-evidence-index',editionManifestSha256:sha(manifestBytes),
  sutCommit:inventory.sutCommit,inputProtocol:inventory.inputProtocol,executionSpecificationSha256:inventory.executionSpecificationSha256,
  sourceInventorySha256:inventorySha256,turns,entries,collectorRevision:'v3.2',runtimeQualification:'not-run'};
 const descriptor=json('index.json',index);
 return {...descriptor,output,turns:turns.length,entries:entries.length,candidateInvocations:0,nativeSolverInvocations:0,runtimeQualified:false};
}
if(require.main===module){
 try{
  const opts={},fields={'--source-root':'sourceRoot','--inventory':'inventoryPath','--inventory-sha256':'inventorySha256','--edition':'edition','--output':'output'},args=process.argv.slice(2);
  for(let i=0;i<args.length;i++){must(fields[args[i]]&&args[i+1],'INVALID_PUBLISH_OPTION');opts[fields[args[i]]]=args[++i];}
  must(Object.values(fields).every(k=>opts[k]),'EXPLICIT_TRUSTED_COLLECTION_AND_NEW_OUTPUT_REQUIRED');
  process.stdout.write(JSON.stringify(publish(opts))+'\n');
 }catch(error){process.stderr.write(JSON.stringify({outcome:'ungradable_evidence',code:error.code||'COLLECTION_INVALID',message:error.message})+'\n');process.exitCode=2;}
}
module.exports={publish,commercialStationsMatch};
