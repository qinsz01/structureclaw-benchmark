'use strict';
// Benchmark-owned capture declarations come only from verified fresh native
// process/stage evidence. Candidate answers and expected quantities are not read.
const fs=require('fs'),path=require('path'),assert=require('assert/strict'),{createHash,randomUUID}=require('crypto');
const ROOT=path.resolve(__dirname,'../../..'),{modelFingerprint}=require(path.join(ROOT,'lib/analysis-evidence.cjs'));
const sha=b=>createHash('sha256').update(b).digest('hex');
const job=process.argv[2],read=n=>JSON.parse(fs.readFileSync(path.join(job,n),'utf8')),save=(n,v)=>{fs.writeFileSync(path.join(job,n),JSON.stringify(v,null,2)+'\n',{flag:'wx'});return n;};
const raw=read('native/result.json'),request=read('request.json'),model=read('model.json'),binding=read('binding.json'),receipt=read('native/process-receipt.json');
assert.equal(receipt.returncode,0);assert.equal(receipt.ownedJobClosed,true);assert.equal(raw.status,'success');
const key=request.selection.kind+':'+request.selection.id,selection={...request.selection,key},runId=randomUUID();
const meta={engineId:'builtin-'+binding.engine.toLowerCase(),runId,modelHash:modelFingerprint(model),state:binding.state,sourceHash:binding.sourceHash};
let data,settings,log,extra={},provenance={kind:'benchmark-owned-commercial-capture',processReceipt:'native/process-receipt.json',ownedJobClosed:true};
const files=[];function walk(dir){for(const e of fs.readdirSync(dir,{withFileTypes:true})){const f=path.join(dir,e.name);if(e.isDirectory())walk(f);else files.push(f);}}walk(path.join(job,'native/projects'));
if(binding.engine==='PKPM'){
 assert.equal(raw.nativeContext.engine,'pkpm');
 for(const field of ['linearStatic','effectiveSettingsVerified','stationConventionsVerified'])assert.equal(raw.nativeContext[field],true);
 for(const field of ['physicalModelHash','stiffnessHash','settingsHash'])assert.match(raw.nativeContext[field],/^[a-f0-9]{64}$/);
 const stage=files.find(f=>f.endsWith('native-stage-evidence.json'));assert.ok(stage);const stages=JSON.parse(fs.readFileSync(stage));assert.equal(stages.status,'completed');assert.ok(stages.phases.length>0&&stages.phases.every(p=>p.returncode===0));
 log=files.find(f=>f.endsWith('CommonInfoOut.log'));assert.ok(log);assert.ok(new TextDecoder('gb18030').decode(fs.readFileSync(log)).includes('全部完成'));
 const wrapped=raw.nativeResultSet?.results?.[key];
 if(wrapped){assert.equal(wrapped.success,true);data=wrapped.data;}
 else {const source=request.selection.kind==='case'?raw.caseResults?.[request.selection.id]:raw.combinationResults?.[request.selection.id];assert.equal(source?.status,'success');data=source;}
 settings=save('capture-settings.json',raw.summary.effectiveNativeSettings);extra.nativeStageEvidence=path.relative(job,stage);provenance.nativePhaseReturnCodes=stages.phases.map(p=>p.returncode);
}else{
 assert.equal(raw.nativeContext.verification,'verified');
 log=files.find(f=>f.includes('Yjkcombine_M0')&&f.endsWith('fea-debug.log'));assert.ok(log);
 const lines=new TextDecoder('gb18030').decode(fs.readFileSync(log)).split(/\r?\n/),i=lines.findIndex(l=>l.includes('启动求解器:')&&l.includes('YJKMain.exe')&&l.includes('M0'));assert.ok(i>=0);const exit=/进程\[(\d+)\]结束\[(-?\d+)\]/.exec(lines[i+1]);assert.ok(exit);assert.equal(Number(exit[2]),0);
 const source=request.selection.kind==='case'?raw.caseResults?.[request.selection.id]:raw.combinationResults?.[request.selection.id];assert.equal(source?.status,'success');data=source;
 settings=files.find(f=>f.endsWith('native-settings-readback.json'));assert.ok(settings);settings=path.relative(job,settings);provenance.nativeProcessId=Number(exit[1]);provenance.analysisStage='M0';provenance.allNativeStagesSucceeded=null;
}
const execution={solver:binding.engine,solverVersion:raw.nativeContext.engineVersion,executed:true,analysisReturnCode:0,provenance};
const entry={success:true,selection,meta,data,execution};
const normalizedInput=save('capture-input.json',{model,selection:request.selection}),solverResponse=save('capture-response.json',{results:{[key]:entry}});
const mapping={normalizedInput,solverResponse,settings,processReceipt:'native/process-receipt.json',analysisLog:path.relative(job,log),rawAdapterResult:'native/result.json',...extra};
const artifacts=Object.fromEntries(Object.entries(mapping).map(([k,file])=>[k+'Sha256',sha(fs.readFileSync(path.join(job,file)))]));entry.data={...data,execution:{...execution,artifacts}};
const state={model,analysisResult:{...entry,runId,modelSnapshot:model,selectedResultKey:key,results:{[key]:entry}}};
save('state.json',state);save('artifact-mapping.json',{runId,files:mapping});
process.stdout.write(JSON.stringify({runId,selection,engine:binding.engine,nativeVerified:true})+'\n');
