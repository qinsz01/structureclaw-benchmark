'use strict';
// Extract exact returned native values. This is a pending reference candidate;
// neither successful execution nor matrix agreement grants qualification.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {createHash}=require('node:crypto');
const {readQuantity}=require('../../lib/requested-quantities.cjs');
const {sourceHash}=require('../../lib/research300-validation.cjs');
const {modelFingerprint}=require('../../lib/analysis-evidence.cjs');
const {comparePhysicalModels}=require('../../lib/physical-model-fidelity.cjs');
const sha=file=>createHash('sha256').update(fs.readFileSync(file)).digest('hex');
const read=file=>JSON.parse(fs.readFileSync(file));
const save=(file,value)=>{fs.mkdirSync(path.dirname(file),{recursive:true});fs.writeFileSync(file,JSON.stringify(value,null,2)+'\n',{flag:'wx'});};
function collect({root,work,output,caseIds}){
 const cases=path.join(root,'corpora/research-300/cases'),rows=[];
 for(const id of fs.readdirSync(cases).sort()){
  if(caseIds&&!caseIds.includes(id))continue;
  const folder=path.join(cases,id),contract=read(path.join(folder,'contract.json'));
  if(!['PKPM','YJK'].includes(contract.plannedEngine))continue;
  const destination=path.join(output,id,'native-candidate.json');
  if(fs.existsSync(destination)){rows.push({id,status:'previously-collected'});continue;}
  const requests=read(path.join(folder,'reference-requests.json'));
  const matrixFile=path.join(folder,fs.existsSync(path.join(folder,'independent-reference-matrix-diagnostic.json'))?'independent-reference-matrix-diagnostic.json':'independent-reference.json');
  const matrix=read(matrixFile);assert.equal(matrix.referenceKind,'independent-elastic-matrix');
  const digest=sourceHash(folder,contract);assert.equal(matrix.sourceHash,digest);
  const states=[],diagnostic=[],jobs=[],artifacts=new Map();let complete=true;
  for(const wanted of requests.states){
   const model=read(path.join(folder,wanted.model)),bySelection=new Map();
   for(const q of wanted.quantities){const key=q.selection.kind+':'+q.selection.id;if(bySelection.has(key))continue;
    const receipt=path.join(work,'executions',id,`state-${wanted.state}-${q.selection.kind}-${q.selection.id}.json`);
    if(!fs.existsSync(receipt)){complete=false;break;}
    const execution=read(receipt);assert.equal(execution.sourceHash,digest);
    if(execution.exitCode!==0){complete=false;break;}
    const job=execution.job,state=read(path.join(job,'state.json')),binding=read(path.join(job,'binding.json'));
    assert.equal(binding.executionRole,'reference-verification');assert.equal(binding.state,wanted.state);
    const mapping=comparePhysicalModels(state.model,model,{coordinate:1e-8,property:1e-6,load:1e-6,explicitElasticProperties:true,staticTheory:'Timoshenko'});
    assert.equal(mapping.pass,true,JSON.stringify(mapping.failures));
    assert.equal(modelFingerprint(state.model),modelFingerprint(read(path.join(job,'model.json'))));
    const selected=state.analysisResult.results[key];assert.ok(selected?.success);assert.equal(selected.execution.analysisReturnCode,0);
    const retained=['request.json','model.json','binding.json','capture-input.json','capture-response.json','native/process-receipt.json','native/adapter-receipt.json','remote-evidence.zip.bin'];
    const bindings=retained.map(name=>{const file=path.join(job,name),relative=path.relative(work,file).split(path.sep).join('/');const d={path:relative,sha256:sha(file)};artifacts.set(relative,d);return d;});
    jobs.push({state:wanted.state,selection:q.selection,job,runId:selected.meta.runId,engineVersion:selected.execution.solverVersion,artifacts:bindings});
    bySelection.set(key,{analysis:state.analysisResult,model:state.model,mapping:mapping.diagnostics,job,runId:selected.meta.runId,artifacts:bindings});
   }
   if(!complete)break;
   const quantities=wanted.quantities.map(q=>{
    const actual=bySelection.get(q.selection.kind+':'+q.selection.id),value=readQuantity(actual.analysis,q,{model:actual.model,...actual.mapping});
    const expected=matrix.states.find(s=>s.state===wanted.state).quantities.find(x=>x.id===q.id&&JSON.stringify(x.selection)===JSON.stringify(q.selection));assert.ok(expected);
    const error=Math.abs(value-expected.value),limit=q.tolerance.absolute+q.tolerance.relative*Math.abs(expected.value);
    diagnostic.push({state:wanted.state,id:q.id,selection:q.selection,component:q.component,unit:q.unit,native:value,matrix:expected.value,error,limit,tolerance:q.tolerance,strictPass:error<=limit});
    return {...q,value,nativeStatus:'candidate-pending-review',rawTrace:{job:path.relative(work,actual.job).split(path.sep).join('/'),runId:actual.runId,capturedResponseSha256:sha(path.join(actual.job,'capture-response.json'))}};
   });
   // Python's existing independent reference arithmetic supplies the derived
   // values after extraction; this file initially records only their requests.
   states.push({state:wanted.state,model:wanted.model,quantities,derived:[],derivedRequests:wanted.derived,
    evidenceArtifacts:[...bySelection.values()].flatMap(x=>x.artifacts)});
  }
  if(!complete){rows.push({id,status:'execution-pending'});continue;}
  const candidate={schemaVersion:1,id,referenceKind:`native-${contract.plannedEngine.toLowerCase()}-candidate`,
   sourceHash:digest,inputHashes:matrix.inputHashes,sourceManifest:matrix.sourceManifest,analysisConvention:contract.analysisConvention,
   method:'retained-actual-production-adapter-native-values',nativeVerified:false,accepted:false,
   notCommercialScoringTruth:true,sameEngineTruthStatus:'pending',toleranceFrozenBeforeCandidate:true,
   states,nativeArtifacts:[...artifacts.values()],independentRawAudit:'pending'};
  save(destination,candidate);save(path.join(output,id,'executions.json'),jobs);
  save(path.join(output,id,'matrix-comparison.json'),{caseId:id,role:'cross-engine-diagnostic',quantities:diagnostic.length,strictPassed:diagnostic.filter(x=>x.strictPass).length,comparisons:diagnostic});
  rows.push({id,status:'pending-independent-review',quantities:diagnostic.length,strictFailed:diagnostic.filter(x=>!x.strictPass).length});
 }
 return rows;
}
module.exports={collect};
if(require.main===module){const [root,work,output]=process.argv.slice(2).map(x=>path.resolve(x));console.log(JSON.stringify(collect({root,work,output}),null,2));}
