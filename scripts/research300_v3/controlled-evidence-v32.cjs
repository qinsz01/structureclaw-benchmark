'use strict';
// Reader for a collector-owned, externally pinned index. This is not a receipt
// generator. Neither an answer nor a Sclaw runId can certify solver execution.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),zlib=require('node:zlib');
const {isDeepStrictEqual}=require('node:util');
const {archiveToRun}=require('../../lib/import-structureclaw.cjs');
const record=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);
const sha=x=>crypto.createHash('sha256').update(x).digest('hex');
const digest=x=>typeof x==='string'&&/^[a-f0-9]{64}$/.test(x);
const uuid=x=>typeof x==='string'&&/^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/i.test(x);
const zero=x=>typeof x==='number'?x===0?0:x:Array.isArray(x)?x.map(zero):record(x)?Object.fromEntries(Object.entries(x).map(([k,v])=>[k,zero(v)])):x;
class EvidenceError extends Error{
 constructor(code,message,outcome='ungradable_evidence'){super(message);this.code=code;this.outcome=outcome;}
}
const requireEvidence=(ok,code,message)=>{if(!ok)throw new EvidenceError(code,message);};
const requireAnswer=(ok,code,message)=>{if(!ok)throw new EvidenceError(code,message,'candidate_failure');};
function rootedFile(root,relative){
 requireEvidence(typeof relative==='string'&&relative&&!path.isAbsolute(relative)&&!relative.includes('\\')
  &&relative.split('/').every(p=>p&&p!=='.'&&p!=='..'),'EVIDENCE_PATH_INVALID','Expected a relative collector path');
 let current=root;for(const part of relative.split('/')){current=path.join(current,part);
  requireEvidence(!fs.lstatSync(current).isSymbolicLink(),'EVIDENCE_SYMLINK','Collector artifacts must not be symlinks');}
 const file=fs.realpathSync(current);
 requireEvidence(file.startsWith(root+path.sep)&&fs.statSync(file).isFile(),'EVIDENCE_OUTSIDE_ROOT','Artifact is outside the collector root');
 return file;
}
function readSealed(root,descriptor){
 requireEvidence(record(descriptor)&&digest(descriptor.sha256),'EVIDENCE_SEAL_MISSING','Artifact digest is required');
 const file=rootedFile(root,descriptor.path);
 requireEvidence(fs.statSync(file).size<=256*1024*1024,'EVIDENCE_TOO_LARGE','Artifact exceeds the reader limit');
 const bytes=fs.readFileSync(file);
 requireEvidence(sha(bytes)===descriptor.sha256,'EVIDENCE_HASH_MISMATCH','Collector artifact changed: '+descriptor.path);
 return bytes;
}
function readJSON(root,descriptor){return JSON.parse(readSealed(root,descriptor));}
function loadControlledIndex({root,indexPath,indexSha256,editionManifestSha256,sutCommit,inputProtocol,executionSpecificationSha256}){
 requireEvidence(digest(indexSha256),'TRUSTED_INDEX_PIN_REQUIRED','Expected index SHA256 must come from the operator, outside candidate data');
 root=fs.realpathSync(root);
 const index=readJSON(root,{path:indexPath,sha256:indexSha256});
 requireEvidence(index.schemaVersion===1&&index.kind==='research300-v3-controlled-evidence-index'
  &&index.editionManifestSha256===editionManifestSha256&&index.sutCommit===sutCommit
  &&index.inputProtocol===inputProtocol&&digest(executionSpecificationSha256)
  &&index.executionSpecificationSha256===executionSpecificationSha256
  &&Array.isArray(index.entries)&&Array.isArray(index.turns),'CAPTURE_INDEX_BINDING_INVALID','Index edition/source identity or turn capture inventory differs');
 const coverage=new Map(),attemptOwners=new Map();
 for(const row of index.turns){
  requireEvidence(record(row)&&/^V3-(STD|MM|INT)-\d{3}$/.test(row.caseId)&&/^t[1-4]$/.test(row.turnId)
   &&typeof row.captureComplete==='boolean'&&['ready','blocked'].includes(row.environmentStatus)
   &&['completed','candidate_failed','service_blocked','interrupted'].includes(row.candidateStatus)
   &&Array.isArray(row.currentJobIds)&&new Set(row.currentJobIds).size===row.currentJobIds.length
   &&row.currentJobIds.every(id=>typeof id==='string'&&/^[a-f0-9]{32}$/.test(id)),
   'CAPTURE_TURN_INVALID','Every issued turn needs an explicit controlled capture status');
  const key=row.caseId+'/'+row.turnId;requireEvidence(!coverage.has(key),'CAPTURE_TURN_REBOUND','Turn capture status was repeated');coverage.set(key,row);
  // The collector inventories every native attempt, including failed and
  // unreported attempts. An answer cannot hide a solve on a query-only turn.
  for(const id of row.currentJobIds){
   requireEvidence(!attemptOwners.has(id),'ATTEMPT_ID_REBOUND','Native attempt identity was reused');attemptOwners.set(id,key);
  }
 }
 function turnStatus(caseId,turnId){
  const row=coverage.get(caseId+'/'+turnId);
  requireEvidence(row,'CAPTURE_TURN_MISSING','Turn collection is missing');
  if(row.environmentStatus==='blocked'||row.candidateStatus==='service_blocked')throw new EvidenceError('ENVIRONMENT_OR_SERVICE_BLOCKED','Collector reports a blocked environment/service','blocked_configuration');
  requireEvidence(row.captureComplete,'CAPTURE_TURN_INCOMPLETE','Turn collection is incomplete');
  if(row.candidateStatus==='interrupted')throw new EvidenceError('TURN_INTERRUPTED','Interrupted turn has no final attributable result');
  if(row.candidateStatus==='candidate_failed')throw new EvidenceError('CANDIDATE_TURN_FAILED','Complete capture records a candidate failure','candidate_failure');
  return row;
 }
 const entries=new Map(),runs=new Map();
 for(const entry of index.entries){
  requireEvidence(record(entry)&&/^V3-(STD|MM|INT)-\d{3}$/.test(entry.caseId)&&/^t[1-4]$/.test(entry.turnId)
   &&/^[a-f0-9]{32}$/.test(entry.evidenceId)&&['OpenSees','PKPM','YJK'].includes(entry.engine)
   &&['broker','structureclaw'].includes(entry.origin),'CAPTURE_ENTRY_INVALID','Invalid controlled capture identity');
  requireEvidence(!entries.has(entry.evidenceId),'CAPTURE_ID_REBOUND','Evidence handles must be globally unique');
  requireEvidence(attemptOwners.get(entry.evidenceId)===entry.caseId+'/'+entry.turnId,
   'CAPTURE_ATTEMPT_UNBOUND','Every published run must occur in the controlled turn attempt inventory');
  if(entry.origin==='structureclaw'){
   requireEvidence(uuid(entry.runId)&&!runs.has(entry.runId),'RUN_ID_REBOUND','Sclaw run UUID is missing or reused');
   runs.set(entry.runId,entry);
  }
  entries.set(entry.evidenceId,entry);
 }
 function entryFor(id,caseId,turnId){
  const entry=entries.get(id)||runs.get(id);
  requireAnswer(entry&&entry.caseId===caseId&&Number(entry.turnId.slice(1))<=Number(turnId.slice(1)),
   'EVIDENCE_NOT_RELEASED','Unknown, cross-case, or future-turn execution reference');
  return entry;
 }
 function load(entry){
  const receipt=readJSON(root,entry.files?.receipt),state=readJSON(root,entry.files?.state),model=readJSON(root,entry.files?.model);
  requireEvidence(receipt.role==='candidate'&&receipt.ok===true&&receipt.caseId===entry.caseId&&receipt.engine===entry.engine
   &&receipt.stateSha256===entry.files.state.sha256,'CANDIDATE_RECEIPT_REQUIRED','A successful same-case collector receipt is required; oracle evidence is forbidden');
  requireEvidence(isDeepStrictEqual(zero(state.model),zero(model)),'STATE_MODEL_MISMATCH','Original protected state/model differ');
  if(entry.origin==='broker'){
   requireEvidence(entry.files.request&&digest(receipt.requestSha256),'REQUEST_SEAL_MISSING','Original broker request must be retained');
   requireEvidence(sha(readSealed(root,entry.files.request))===receipt.requestSha256,'REQUEST_SEAL_MISMATCH','Broker request differs');
  }else{
   const archiveBytes=readSealed(root,entry.files.archive);
   const archive=JSON.parse(entry.files.archive.path.endsWith('.gz')?zlib.gunzipSync(archiveBytes,{maxOutputLength:256*1024*1024}):archiveBytes);
   requireEvidence(record(archive.request)&&record(archive.results)&&digest(archive.modelHash)&&digest(archive.settingsHash),
    'SCLAW_ARCHIVE_INCOMPLETE','Original run request, complete result collections and identity hashes are required');
   try{archiveToRun(archive);}catch(error){throw new EvidenceError('SCLAW_ARCHIVE_IDENTITY_MISMATCH',error.message);}
   const sourceModel=archive.request?.model||archive.modelSnapshot;
   requireEvidence(archive.runId===entry.runId&&isDeepStrictEqual(zero(sourceModel),zero(model))
    &&(!archive.modelSnapshot||isDeepStrictEqual(zero(archive.modelSnapshot),zero(model)))
    &&receipt.runId===entry.runId&&receipt.archiveSha256===entry.files.archive.sha256,
    'SCLAW_ARCHIVE_BINDING_INVALID','Run UUID, original model and collector archive seal must agree');
   const proof=readJSON(root,entry.files.executionProof);
   requireEvidence(proof.kind==='research300-native-execution-proof'&&proof.caseId===entry.caseId
    &&proof.runId===entry.runId&&proof.sutCommit===sutCommit&&proof.engine===entry.engine
    &&proof.modelSha256===entry.files.model.sha256&&proof.workerExitCode===0&&proof.executed===true
    &&typeof proof.solverVersion==='string'&&proof.solverVersion.trim()&&Array.isArray(proof.artifacts)&&proof.artifacts.length>0
    &&receipt.executionProofSha256===entry.files.executionProof.sha256,
    'NATIVE_EXECUTION_PROOF_REQUIRED','Sclaw UUID/archive alone cannot certify native execution');
   for(const artifact of proof.artifacts)readSealed(root,artifact);
   if(state.dynamicResult){
    const selected=archive.results?.[archive.selectedResultKey],dynamic=state.dynamicResult;
    requireEvidence(dynamic.meta?.runId===entry.runId&&selected?.success===true
     &&isDeepStrictEqual(zero(dynamic.data),zero(selected?.data))
     &&isDeepStrictEqual(zero(dynamic.parameters),zero(proof.parameters)),
     'DYNAMIC_ARCHIVE_MISMATCH','Dynamic observations/settings must be original run data');
   }else{
    requireEvidence(state.analysisResult?.runId===entry.runId&&record(archive.results)
     &&isDeepStrictEqual(zero(state.analysisResult.results),zero(archive.results)),
     'STATIC_ARCHIVE_MISMATCH','Static result collections must be unchanged original archive data');
   }
  }
  return {jobId:entry.evidenceId,engine:entry.engine,verified:true,state,
   origin:{kind:entry.origin,runId:entry.runId,indexSha256,originalStateSha256:entry.files.state.sha256}};
 }
 function resolveAnswer(original,caseId,turnId){
  const capture=turnStatus(caseId,turnId);
  requireAnswer(record(original),'ANSWER_OBJECT_REQUIRED','Structured original answer is required');
  const answer=structuredClone(original),mapping=[];
  for(const [source,target]of [['runIds','jobIds'],['runIdsByModel','jobIdsByModel'],['runIdsByScenario','jobIdsByScenario']]){
   if(answer[source]===undefined)continue;
   requireAnswer(answer[target]===undefined,'ANSWER_IDENTITY_AMBIGUOUS','Do not supply both '+source+' and '+target);
   answer[target]=answer[source];delete answer[source];
  }
  const groups=['jobIds','jobIdsByModel','jobIdsByScenario'].filter(k=>answer[k]!==undefined);
  requireAnswer(groups.length===1,'ANSWER_EVIDENCE_GROUP_REQUIRED','Exactly one supported evidence-reference family is required');
  const convert=values=>{
   requireAnswer(Array.isArray(values)&&values.every(v=>typeof v==='string'),'ANSWER_REFERENCES_INVALID','Execution references must be arrays of strings');
   return values.map(value=>{const entry=entryFor(value,caseId,turnId);mapping.push({reported:value,evidenceId:entry.evidenceId,runId:entry.runId});return entry.evidenceId;});
  };
  const key=groups[0];
  if(key==='jobIds')answer[key]=convert(answer[key]);
  else{
   requireAnswer(record(answer[key]),'ANSWER_REFERENCES_INVALID','Model/scenario references must be a map');
   answer[key]=Object.fromEntries(Object.entries(answer[key]).map(([k,v])=>[k,convert(v)]));
  }
  const ids=[...new Set(mapping.map(row=>row.evidenceId))],jobs=ids.map(id=>load(entryFor(id,caseId,turnId)));
  return {answer,jobs,currentJobIds:[...capture.currentJobIds],mapping,
   originalAnswerUnchanged:true,numericAnswerFieldsChanged:false};
 }
 function readAnswer(caseId,turnId){
  const status=turnStatus(caseId,turnId);
  requireAnswer(status.answer,'ANSWER_NOT_SUBMITTED','Complete capture has no structured candidate answer');
  const bytes=readSealed(root,status.answer);
  let original;try{original=JSON.parse(bytes);}catch{throw new EvidenceError('ANSWER_JSON_INVALID','Original candidate answer is not JSON','candidate_failure');}
  return {...resolveAnswer(original,caseId,turnId),originalAnswerSha256:sha(bytes)};
 }
 return {resolveAnswer,readAnswer,turnStatus,entryCount:entries.size,indexSha256,sutCommit,editionManifestSha256};
}
module.exports={loadControlledIndex,EvidenceError,readSealed};
