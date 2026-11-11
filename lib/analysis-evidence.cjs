const {createHash}=require('node:crypto');
const {selectAnalysisResult,selectionKey}=require('./result-selection.cjs');
const isRecord=v=>v&&typeof v==='object'&&!Array.isArray(v);
function ordered(value) {
  if(Array.isArray(value)) {
    const values=value.map(ordered);
    return values.length&&values.every(v=>isRecord(v)&&typeof v.id==='string')?values.sort((a,b)=>a.id.localeCompare(b.id)):values;
  }
  if(isRecord(value)) return Object.fromEntries(Object.keys(value).sort().filter(k=>value[k]!==undefined).map(k=>[k,ordered(value[k])]));
  return value;
}
// Response array order (stations, modes, time samples) is meaningful. Sort keys
// only, unlike the physical model fingerprint's ID-set normalization.
function resultFingerprint(value) {
  function canonical(item) {
    if(Array.isArray(item)) return item.map(canonical);
    if(isRecord(item)) return Object.fromEntries(Object.keys(item).sort().filter(k=>item[k]!==undefined).map(k=>[k,canonical(item[k])]));
    return item;
  }
  // The response cannot contain the SHA256 of its own bytes. Execution receipts
  // are verified separately; retain all other response content and nested keys.
  const response=isRecord(value)?Object.fromEntries(Object.entries(value).filter(([key])=>key!=='execution')):value;
  return createHash('sha256').update(JSON.stringify(canonical(response))).digest('hex');
}
function modelFingerprint(model) {
  const physical={};
  for(const key of ['schema_version','unit_system','coordinate_system','nodes','elements','materials','sections','stories',
    'load_cases','load_combinations','analysis_control','site_seismic','structure_system','wind','wall_openings','slab_openings'])
    if(model[key]!==undefined) physical[key]=model[key];
  physical.load_cases??=model.loadCases;physical.load_combinations??=model.loadCombinations;
  if(isRecord(model.metadata)) {
    const metadata=Object.fromEntries(Object.entries(model.metadata).filter(([key])=>!
      ['title','name','description','source','inputEvidence','createdAt','updatedAt','physicalModel','inferredType'].includes(key)));
    if(Object.keys(metadata).length) physical.metadata=metadata;
  }
  return createHash('sha256').update(JSON.stringify(ordered(physical))).digest('hex');
}
const validSha256=value=>typeof value==='string'&&/^[a-f0-9]{64}$/i.test(value);
const own=(value,key)=>isRecord(value)&&Object.hasOwn(value,key);
function receiptArtifactHashes(artifacts,failures) {
  const hashes=new Map();
  function add(name,hash) {
    if(typeof name!=='string'||!name.trim()) {failures.push('artifact receipt identifier is missing');return;}
    if(hashes.has(name)) failures.push(`artifact ${name} has duplicate receipt identifiers`);
    hashes.set(name,hash);
    if(!validSha256(hash)) failures.push(`artifact ${name} receipt SHA256 is missing or invalid`);
  }
  if(Array.isArray(artifacts)) {
    for(const artifact of artifacts) add(artifact?.name??artifact?.path,artifact?.sha256);
  } else if(isRecord(artifacts)) {
    // Existing solver receipts use normalizedInputSha256/solverResponseSha256.
    for(const [key,hash] of Object.entries(artifacts)) if(key.endsWith('Sha256')) add(key.slice(0,-6),hash);
  }
  if(!hashes.size) failures.push('artifact hash receipt is missing');
  return hashes;
}
/**
 * Pure verification: the benchmark caller supplies run-keyed artifact evidence.
 * artifactBytes contains Buffer/Uint8Array values. trustedArtifactHashes is only
 * for digests computed by the trusted benchmark collector, never candidate data.
 * Artifact names (including native receipt paths) are opaque keys, never read.
 * Every receipt and every supplied artifact must match; bytes always get hashed.
 */
function verifyArtifactEvidence(execution,meta,key,currentModelHash,artifactEvidence) {
  const failures=[],receipt=receiptArtifactHashes(execution?.artifacts,failures);
  const evidence=own(artifactEvidence,meta.runId)?artifactEvidence[meta.runId]:undefined;
  if(!isRecord(evidence)) return {artifactsVerified:0,failures:[...failures,'trusted artifact evidence is missing for the selected run']};
  if(typeof meta.runId!=='string'||!meta.runId.trim()) failures.push('artifact evidence requires an immutable string run identifier');
  if(evidence.modelHash!==currentModelHash||evidence.modelHash!==meta.modelHash)
    failures.push('artifact evidence is stale or bound to a different model');
  const selections=evidence.selections===undefined?[evidence.selection]:evidence.selections;
  if(!Array.isArray(selections)||!selections.length||selections.some(s=>!['case','combination'].includes(s?.kind)||typeof s.id!=='string'||!s.id)||
    new Set(selections.map(selectionKey)).size!==selections.length||!key||!selections.some(s=>selectionKey(s)===key))
    failures.push('artifact evidence is bound to a different or missing selection');
  // A host capture binds the complete model and result. Native solvers may
  // hash a different canonical payload for each load selection; verify those
  // original bytes without confusing them with the host capture envelope.
  let selectedEvidence=evidence;
  if(evidence.selectionArtifacts!==undefined) {
    if(!isRecord(evidence.selectionArtifacts)||!own(evidence.selectionArtifacts,key)||
      !isRecord(evidence.selectionArtifacts[key]))
      return {artifactsVerified:0,failures:[...failures,'native artifact evidence is missing for the selected load case or combination']};
    selectedEvidence=evidence.selectionArtifacts[key];
  }
  const bytes=selectedEvidence.artifactBytes, trusted=selectedEvidence.trustedArtifactHashes;
  for(const [field,value] of [['artifactBytes',bytes],['trustedArtifactHashes',trusted]])
    if(value!==undefined&&!isRecord(value)) failures.push(`artifact evidence ${field} must be a map`);
  const names=new Set([...receipt.keys(),...Object.keys(isRecord(bytes)?bytes:{}),...Object.keys(isRecord(trusted)?trusted:{})]);
  let artifactsVerified=0;
  for(const name of names) {
    const before=failures.length,expected=receipt.get(name);
    if(!receipt.has(name)) failures.push(`artifact ${name} receipt hash is missing`);
    const hasBytes=own(bytes,name),hasTrusted=own(trusted,name);
    let actual;
    if(hasBytes) {
      if(!(bytes[name] instanceof Uint8Array)) failures.push(`artifact ${name} bytes must be a Buffer or Uint8Array`);
      else actual=createHash('sha256').update(bytes[name]).digest('hex');
    }
    if(hasTrusted) {
      if(!validSha256(trusted[name])) failures.push(`artifact ${name} trusted SHA256 is missing or invalid`);
      else {
        const digest=trusted[name].toLowerCase();
        if(actual!==undefined&&actual!==digest) failures.push(`artifact ${name} bytes and trusted hash mismatch`);
        if(!hasBytes) actual=digest;
      }
    }
    if(!hasBytes&&!hasTrusted) failures.push(`artifact ${name} evaluator bytes or trusted hash are missing`);
    if(actual!==undefined&&validSha256(expected)&&actual!==expected.toLowerCase()) failures.push(`artifact ${name} hash mismatch`);
    if(failures.length===before&&actual!==undefined&&validSha256(expected)) artifactsVerified++;
  }
  return {artifactsVerified,failures};
}
function verifyExecutionEvidence(state,selection,options={}) {
  const failures=[];
  if(!state.model) return {pass:false,failures:['model missing']};
  try {
    const selected=selectAnalysisResult(state.analysisResult,selection);
    const meta=selected.record.meta||{}, execution=selected.data.execution||selected.record.execution||meta.execution;
    if(!execution||execution.executed!==true) failures.push('actual solver execution evidence is missing');
    if(!execution?.solverVersion) failures.push('actual solver version is missing');
    if(!meta.runId) failures.push('immutable run identifier is missing');
    const currentModelHash=modelFingerprint(state.model);
    if(meta.modelHash!==currentModelHash) failures.push('result is stale or not bound to the current physical model');
    if(state.modelPending) failures.push('model has unresolved pending changes');
    if(execution?.analysisReturnCode!==undefined&&execution.analysisReturnCode!==0) failures.push('solver return code is nonzero');
    let artifacts;
    if(options.evaluationProfile==='engineering-v2.3'||options.requireArtifactHashes===true) {
      if(typeof execution?.solver!=='string'||!execution.solver.trim()) failures.push('actual solver identity is missing');
      if(typeof execution?.solverVersion!=='string'||!execution.solverVersion.trim()) failures.push('actual solver version must be a nonempty string');
      if(execution?.analysisReturnCode!==0) failures.push('explicit successful solver return code is required');
      for(const record of [selected.record,selected.data,execution]) if(record?.status!==undefined&&
        !['success','succeeded','complete','completed','ok'].includes(String(record.status).toLowerCase()))
        failures.push('selected result or execution has an unsuccessful/incomplete status');
      artifacts=verifyArtifactEvidence(execution,meta,selected.key,currentModelHash,options.artifactEvidence);
      failures.push(...artifacts.failures);
    }
    return {pass:failures.length===0,failures,runId:meta.runId,solver:execution?.solver,solverVersion:execution?.solverVersion,
      ...(artifacts?{artifactsVerified:artifacts.artifactsVerified}:{})};
  } catch(error) {return {pass:false,failures:[error.message]};}
}
module.exports={verifyExecutionEvidence,modelFingerprint,resultFingerprint};
