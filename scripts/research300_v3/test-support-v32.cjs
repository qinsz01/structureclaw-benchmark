'use strict';
// Synthetic verifier fixtures, never solver executions or benchmark outcomes.
const fs=require('node:fs'),os=require('node:os'),path=require('node:path'),crypto=require('node:crypto');
const {modelFingerprint}=require('../../lib/analysis-evidence.cjs');
const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
function example(){
 const model={schema_version:'2.2.0',unit_system:'SI',coordinate_system:{dimension:'3d',plane:null,
  semantics:'global-z-up',version:1,dof_order:['ux','uy','uz','rx','ry','rz']},
  nodes:[{id:'A',x:0,y:0,z:0,restraints:[true,true,true,true,true,true]},
   {id:'B',x:2,y:0,z:0,restraints:[false,false,false,false,false,false]}],
  elements:[{id:'E',type:'beam',nodes:['A','B'],material:'M',section:'S'}],
  materials:[{id:'M',type:'steel',E:200000,G:200000/2.6,nu:.3,rho:7850}],
  sections:[{id:'S',type:'custom',properties:{A:.01,Iy:1e-5,Iz:1e-5,J:2e-5}}],
  load_cases:[{id:'D',type:'dead',loads:[{type:'nodal',node:'B',fz:-1}]}],load_combinations:[],
  analysis_control:{self_weight:false,rigid_floor:false,p_delta:false,rigid_offsets:false,construction_stage:false}};
 // Closed-form cantilever tip displacement: -P L^3 / (3 E I), SI kN/m.
 const value=-(2**3)/(3*200000*1000*1e-5),selection={kind:'case',id:'D'};
 const request={id:'tip',selection,location:{kind:'node',id:'B'},component:'uz',unit:'m',value,
  tolerance:{absolute:1e-8,relative:1e-6}};
 const data={units:{displacement:'m',rotation:'rad',force:'kN',moment:'kN.m'},displacements:{B:{uz:value}}};
 const job={jobId:'1'.repeat(32),engine:'OpenSees',verified:true,state:{model:structuredClone(model),
  analysisResult:{meta:{engineId:'builtin-opensees'},results:{'case:D':{selection,data}}}}};
 return {ref:{kind:'static',engine:'OpenSees',model,requests:[request]},jobs:[job],
  answer:{jobIds:[job.jobId],quantities:[{id:'tip',value,unit:'m'}]}};
}
function collection(t,origin='broker'){
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'research300-v32-test-'));
 t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
 const put=(name,value)=>{
  const bytes=Buffer.isBuffer(value)?value:Buffer.from(JSON.stringify(value)+'\n');
  const file=path.join(root,name);fs.mkdirSync(path.dirname(file),{recursive:true});fs.writeFileSync(file,bytes);
  return {path:name,sha256:sha(bytes)};
 };
 const x=example(),caseId='V3-STD-001',turnId='t1',id=x.jobs[0].jobId;
 const options={root,indexPath:'index.json',editionManifestSha256:'a'.repeat(64),sutCommit:'b'.repeat(40),
  inputProtocol:'verbatim-public-v3.2',executionSpecificationSha256:'c'.repeat(64)};
 const state=structuredClone(x.jobs[0].state),model=structuredClone(state.model);
 const request={model:structuredClone(model)},receipt={role:'candidate',ok:true,caseId,engine:'OpenSees'};
 const entry={caseId,turnId,evidenceId:id,engine:'OpenSees',origin,files:{}};
 let archive,proof;
 if(origin==='structureclaw'){
  const runId='12345678-1234-1234-1234-123456789abc',settingsHash='d'.repeat(64);
  entry.runId=runId;
  archive={runId,request,modelHash:modelFingerprint(model),settingsHash,selectedResultKey:'case:D',
   results:structuredClone(state.analysisResult.results)};
  for(const row of Object.values(archive.results))Object.assign(row,{success:true,
   meta:{runId,modelHash:archive.modelHash,settingsHash}});
  Object.assign(state.analysisResult,{runId,results:structuredClone(archive.results)});
  receipt.runId=runId;
  proof={kind:'research300-native-execution-proof',caseId,runId,sutCommit:options.sutCommit,engine:'OpenSees',
   workerExitCode:0,executed:true,solverVersion:'SYNTHETIC-UNIT-TEST',artifacts:[put('synthetic-worker-output.txt',Buffer.from('test only'))]};
 }
 const index={schemaVersion:1,kind:'research300-v3-controlled-evidence-index',...options,root:undefined,indexPath:undefined,
  turns:[{caseId,turnId,captureComplete:true,environmentStatus:'ready',candidateStatus:'completed',currentJobIds:[id]}],entries:[entry]};
 function seal(){
  entry.files.model=put('model.json',model);entry.files.state=put('state.json',state);receipt.stateSha256=entry.files.state.sha256;
  if(archive){
   entry.files.archive=put('archive.json',archive);receipt.archiveSha256=entry.files.archive.sha256;
   proof.modelSha256=entry.files.model.sha256;entry.files.executionProof=put('proof.json',proof);receipt.executionProofSha256=entry.files.executionProof.sha256;
  }else{entry.files.request=put('request.json',request);receipt.requestSha256=entry.files.request.sha256;}
  entry.files.receipt=put('receipt.json',receipt);index.turns[0].answer=put('answer.json',x.answer);
  return pin();
 }
 function pin(){options.indexSha256=put('index.json',index).sha256;return options;}
 seal();return {...x,root,put,options,index,entry,state,model,request,receipt,archive,proof,seal,pin,caseId,turnId};
}
module.exports={example,collection,sha};
