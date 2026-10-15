/** No paid model calls. Invoke actual registered tools; never load references into tool state. */
import fs from 'node:fs';
import path from 'node:path';
import {createHash,randomUUID} from 'node:crypto';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createRequire} from 'node:module';
import {execFileSync} from 'node:child_process';
const require=createRequire(import.meta.url);
const {compareRequestedQuantities,compareReportQuantities}=require('../lib/requested-quantities.cjs');
const {verifyExecutionEvidence}=require('../lib/analysis-evidence.cjs');
const {comparePhysicalModels}=require('../lib/physical-model-fidelity.cjs');
const {createNormalizedStateEdits,partitionRepresentativeQueries,verifyUnavailableRotationQuery}=require('../lib/representative-tool-contract.cjs');
const here=path.dirname(fileURLToPath(import.meta.url)),bench=path.dirname(here),sut=path.resolve(process.env.SCLAW_ROOT||path.join(bench,'../..'));
const root=path.join(bench,'acceptance/representative-18'),manifest=JSON.parse(fs.readFileSync(path.join(root,'manifest.json'),'utf8'));
process.chdir(sut);
const sha=value=>createHash('sha256').update(value).digest('hex');
const output=process.argv.find(a=>a.startsWith('--output='))?.slice(9);
const outputPath=output?path.resolve(output):null;
const artifactDirectory=outputPath?outputPath.replace(/\.json$/i,'')+'-artifacts':null;
if(artifactDirectory)fs.mkdirSync(artifactDirectory,{recursive:true});
const git=(...args)=>execFileSync('git',['-c','core.safecrlf=false',...args],{cwd:sut,encoding:'utf8'}).trim();
const provenance={sutRevision:git('rev-parse','HEAD'),sutWorkingDiffSha256:sha(git('diff','--no-ext-diff','HEAD')),startedAt:new Date().toISOString(),
  sharedToolContractsSha256:sha(fs.readFileSync(path.join(sut,'backend/dist/agent-langgraph/public-tool-contracts.js'))),
  candidateHarnessSha256:Object.fromEntries(['scripts/check-representative-pack.mjs','lib/representative-tool-contract.cjs'].map(file=>[file,sha(fs.readFileSync(path.join(bench,file)))]))};
const mechanicsFiles=git('ls-files','backend/src/agent-skills/analysis/runtime/opensees_shared','backend/src/agent-skills/analysis/opensees-static','backend/src/agent-skills/analysis/runtime/coordinate_semantics.py').split(/\r?\n/)
  .filter(file=>!file.includes('__tests__'));
mechanicsFiles.push('backend/dist/skill-shared/member-response.js','backend/dist/agent-langgraph/model-tools.js','backend/dist/agent-langgraph/tools.js');
provenance.mechanicsSourceSha256=Object.fromEntries(mechanicsFiles.map(file=>[file,sha(fs.readFileSync(path.join(sut,file)))]));
for(const [name,digest] of Object.entries(manifest.sha256)) if(sha(fs.readFileSync(path.join(root,name)))!==digest) throw Error(`Frozen input/reference changed: ${name}`);
const load=rel=>import(pathToFileURL(path.join(sut,'backend/dist',rel)).href);
const [{AgentSkillRuntime},{LangGraphAgentService},{createRegisteredTools},{normalizeEngineeringModel},{commitModel},{applyPublicToolStateUpdate}]=await Promise.all([
  load('agent-runtime/index.js'),load('agent-langgraph/agent-service.js'),load('agent-langgraph/tool-registry.js'),load('engineering/model-boundary.js'),load('engineering/model-state.js'),load('agent-langgraph/public-tool-contracts.js')]);
const runtime=new AgentSkillRuntime(),service=new LangGraphAgentService(runtime),tools=new Map(createRegisteredTools({skillRuntime:runtime}).map(t=>[t.name,t]));
const results=[];const only=process.argv.find(a=>a.startsWith('--case='))?.split('=')[1];
for(const entry of manifest.cases.filter(c=>!only||c.id===only)) {
  const folder=path.join(root,entry.id),read=name=>JSON.parse(fs.readFileSync(path.join(folder,name),'utf8'));
  const contract=read('contract.json'),reference=read('independent-reference.json');
  if(entry.engine!=='OpenSees') {results.push({id:entry.id,status:'native-reference-required',reason:'Commercial direct-stiffness diagnostics are not same-engine truth; native acceptance is managed separately.'});continue;}
  let state={model:null,modelRevision:0,modelHistory:[],analysisRuns:{},messages:[],selectedSkillIds:['opensees-static'],locale:contract.language==='中文'?'zh':'en',analysisType:'static',artifacts:{},modelPending:false};
  const invoke=async(name,input)=>{
    const result=await tools.get(name).invoke(input,{configurable:{skillRuntime:runtime,engineClient:service.engineClient,codeCheckClient:service.codeCheckClient,structureProtocolClient:service.structureProtocolClient,agentState:state,skillScope:state.selectedSkillIds},toolCall:{id:randomUUID()}});
    if(result?.update)state={...applyPublicToolStateUpdate(state,result.update),messages:[...state.messages,...(result.update.messages||[])]};
    const content=typeof result==='string'?result:result?.update?.messages?.at(-1)?.content??result?.content;
    return typeof content==='string'?JSON.parse(content):content;
  };
  for(let i=0;i<contract.modelStates.length;i++) {
    try {
      const physical=read(contract.modelStates[i]);
      if(i===0)state={...state,...commitModel(state,await normalizeEngineeringModel(physical,service.structureProtocolClient),'frozen explicit input')};
      else if((entry.id==='INT-001'||entry.id==='INT-074')&&i===2)await invoke('undo_model',{baseRevision:state.modelRevision});
      else {
        // Both sides of a public edit use the same current schema; the independent
        // physical comparison below still uses the unmodified frozen raw target.
        const edits=await createNormalizedStateEdits(state.model,physical,model=>normalizeEngineeringModel(model,service.structureProtocolClient));
        await invoke('edit_model',{baseRevision:state.modelRevision,edits,label:`${entry.id} state ${i+1}`});
        if(state.analysisResult)throw Error('Edit did not invalidate current result');
      }
      const comparison=comparePhysicalModels(state.model,physical);
      if(!comparison.pass)throw Error(`Physical model mismatch: ${comparison.failures}`);
      const response=await invoke('run_analysis',{analysisType:'static',analysisSkillId:'opensees-static',loadCaseIds:physical.load_cases.map(c=>c.id),...(physical.load_combinations.length?{loadCombinationIds:physical.load_combinations.map(c=>c.id)}:{})});
      if(!state.analysisResult?.success)throw Error(JSON.stringify(state.analysisResult?.error||response||state.analysisResult));
      const quantities=reference.states[i].quantities.map(q=>({...q,id:`${q.selection.kind}:${q.selection.id}/${q.id}`}));
      const copy=structuredClone(state.analysisResult);
      const {queryable,notApplicable}=partitionRepresentativeQueries(physical,quantities);
      const notApplicableQueries=[];
      for(const q of notApplicable) {
        const key=`${q.selection.kind}:${q.selection.id}`;
        notApplicableQueries.push(await verifyUnavailableRotationQuery(q,copy.results[key]?.data,()=>invoke('query_results',
          {resultKey:key,quantityId:q.id,component:q.component,unit:q.unit,nodeId:q.location.id,field:'displacements'})));
      }
      // Query exact member stations through the real tool. Do not take the nearest graph point.
      for(const q of queryable) {
        const key=`${q.selection.kind}:${q.selection.id}`;
        const common={resultKey:key,quantityId:q.id,component:q.component,unit:q.unit};
        if(q.location.kind==='node') {
          await invoke('query_results',{...common,nodeId:q.location.id,field:q.component[0]==='u'||q.component[0]==='r'?'displacements':'reactions'});continue;
        }
        let response;
        try {response=await invoke('query_results',{...common,elementId:q.location.id,positionM:q.location.positionM,side:q.location.side});}
        catch(error){throw Error(`${q.id}: ${error.message}`);}
        const v=response.values;if(!v?.sample)throw Error(`No exact sample ${q.id}`);
        const row=copy.results[key].data.memberResponses.find(r=>r.id===q.location.id);
        row.samples=row.samples.filter(s=>!(Math.abs(s.x-q.location.positionM)<1e-9&&s.side===q.location.side));
        row.samples.push({...v.sample,x:q.location.positionM,side:q.location.side});row.samples.sort((a,b)=>a.x-b.x||(a.side==='left'?-1:1));
      }
      const fullReferenceComparison=compareRequestedQuantities(copy,quantities,comparison.diagnostics);
      const physicalNumerical=compareRequestedQuantities(copy,queryable,comparison.diagnostics);
      const selections=[...new Map(quantities.map(q=>[JSON.stringify(q.selection),q.selection])).values()];
      const execution=selections.map(s=>verifyExecutionEvidence(state,s));
      await invoke('generate_report',{message:'Report the queried engineering quantities / 报告已查询的工程数值',analysisType:'static',locale:state.locale});
      const reportBody=compareReportQuantities(state.report,queryable);
      const queryApplicability={frozenQuantityCount:quantities.length,physicalQueryCount:queryable.length,notApplicable:notApplicableQueries,
        boundary:'All frozen references are evaluated unchanged; missing undefined rotations remain failures in fullReferenceComparison. Physical numerical/report checks cover the applicable quantities only. Free truss rotation zeros require reference-contract review and are never synthesized as solver responses.'};
      let artifact;
      if(artifactDirectory){
        const name=`${entry.id}-state-${i+1}.json`,content=JSON.stringify({model:state.model,modelRevision:state.modelRevision,analysisRequest:state.analysisRequest,analysisRuns:state.analysisRuns,analysisResult:state.analysisResult,resultQuantities:state.resultQuantities,report:state.report,queryApplicability},null,2)+'\n';
        fs.writeFileSync(path.join(artifactDirectory,name),content);artifact={name,sha256:sha(content)};
      }
      const physicalPassed=physicalNumerical.pass&&execution.every(e=>e.pass)&&reportBody.pass;
      const status=!physicalPassed?'failed':notApplicableQueries.length?'reference-review-required':fullReferenceComparison.pass?'tool-mechanics-passed':'failed';
      results.push({id:entry.id,state:i+1,status,runId:state.analysisResult.runId,numerical:fullReferenceComparison,fullReferenceComparison,physicalNumerical,execution,reportBody,queryApplicability,
        artifact,recognitionAcceptance:'not-run-no-model-API'});
    } catch(error) {results.push({id:entry.id,state:i+1,status:'failed',error:error.message});}
  }
}
for(const [name,digest] of Object.entries(manifest.sha256)) if(sha(fs.readFileSync(path.join(root,name)))!==digest)throw Error(`Reference modified during execution: ${name}`);
for(const [name,digest] of Object.entries(provenance.mechanicsSourceSha256)) if(sha(fs.readFileSync(path.join(sut,name)))!==digest)throw Error(`Production mechanics modified during execution: ${name}`);
const report={status:results.some(r=>r.status==='failed')?'failed':results.some(r=>r.status==='reference-review-required')?'reference-review-required':'bounded-tool-acceptance',provenance,frozenManifestSha256:sha(fs.readFileSync(path.join(root,'manifest.json'))),results};
if(outputPath)fs.writeFileSync(outputPath,JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));if(report.status!=='bounded-tool-acceptance')process.exitCode=1;
