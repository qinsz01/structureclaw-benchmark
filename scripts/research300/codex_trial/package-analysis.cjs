'use strict';
// Package actual native outputs using the unchanged production recovery module.
const fs=require('fs'),path=require('path'),{pathToFileURL}=require('url'),{randomUUID,createHash}=require('crypto');
const ROOT=path.resolve(__dirname,'../../..');
(async()=>{
 const job=process.argv[2],SUT=process.argv[3],request=JSON.parse(fs.readFileSync(path.join(job,'request.json'))),native=JSON.parse(fs.readFileSync(path.join(job,'worker.stdout.json')));
 if(!native.ok||!native.data?.success)throw Error(JSON.stringify(native));
 const model=JSON.parse(fs.readFileSync(path.join(job,'model.json'))),selection=request.selection,parameters=JSON.parse(fs.readFileSync(path.join(job,'worker-request.json'))).input.parameters;
 const recovery=await import(pathToFileURL(path.join(SUT,'backend/dist/engineering/member-response-query.js')).href);
 const factors=selection.kind==='case'?{[selection.id]:1}:model.load_combinations.find(c=>c.id===selection.id).factors;
 const result=native.data,data={...result.data,memberResponses:recovery.recoverAnalysisMembers(model,result.data,'opensees',factors)};
 const runId=randomUUID(),settingsHash=createHash('sha256').update(JSON.stringify(parameters)).digest('hex');
 const {modelFingerprint}=require(path.join(ROOT,'lib/analysis-evidence.cjs'));
 const key=selection.kind+':'+selection.id,meta={...result.meta,engineId:'builtin-opensees',runId,modelHash:modelFingerprint(model),settingsHash};
 const entry={...result,data,selection:{...selection,key},meta};
 const state={model,analysisResult:{...entry,runId,selectedResultKey:key,modelSnapshot:model,results:{[key]:entry}}};
 fs.writeFileSync(path.join(job,'state.json'),JSON.stringify(state,null,2)+'\n',{flag:'wx'});
})().catch(e=>{process.stderr.write(e.stack+'\n');process.exitCode=1;});
