const {createHash}=require('node:crypto');
const {selectAnalysisResult}=require('./result-selection.cjs');
const isRecord=v=>v&&typeof v==='object'&&!Array.isArray(v);
function ordered(value) {
  if(Array.isArray(value)) {
    const values=value.map(ordered);
    return values.length&&values.every(v=>isRecord(v)&&typeof v.id==='string')?values.sort((a,b)=>a.id.localeCompare(b.id)):values;
  }
  if(isRecord(value)) return Object.fromEntries(Object.keys(value).sort().filter(k=>value[k]!==undefined).map(k=>[k,ordered(value[k])]));
  return value;
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
function verifyExecutionEvidence(state,selection) {
  const failures=[];
  if(!state.model) return {pass:false,failures:['model missing']};
  try {
    const selected=selectAnalysisResult(state.analysisResult,selection);
    const meta=selected.record.meta||{}, execution=selected.data.execution||selected.record.execution||meta.execution;
    if(!execution||execution.executed!==true) failures.push('actual solver execution evidence is missing');
    if(!execution?.solverVersion) failures.push('actual solver version is missing');
    if(!meta.runId) failures.push('immutable run identifier is missing');
    if(meta.modelHash!==modelFingerprint(state.model)) failures.push('result is stale or not bound to the current physical model');
    if(state.modelPending) failures.push('model has unresolved pending changes');
    if(execution?.analysisReturnCode!==undefined&&execution.analysisReturnCode!==0) failures.push('solver return code is nonzero');
    return {pass:failures.length===0,failures,runId:meta.runId,solver:execution?.solver,solverVersion:execution?.solverVersion};
  } catch(error) {return {pass:false,failures:[error.message]};}
}
module.exports={verifyExecutionEvidence,modelFingerprint};
