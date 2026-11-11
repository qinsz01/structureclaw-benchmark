'use strict';
// Protected broker jobs, not candidate-supplied result JSON, are authoritative.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {comparePhysicalModels,closedPlanarDomain}=require('../challenge/physical-view-v3.cjs');
const {axesFor}=require('../../lib/physical-model-fidelity.cjs');
const {readQuantity,compareRequestedQuantities,compareDerivedQuantities,evaluateDerivedQuantities}=require('../../lib/requested-quantities.cjs');
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const clone=v=>JSON.parse(JSON.stringify(v));
const sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const assert=(ok,msg)=>{if(!ok)throw Error(msg);};
const finite=v=>typeof v==='number'&&Number.isFinite(v);
const close=(a,b,t={absolute:1e-8,relative:1e-6})=>finite(a)&&finite(b)&&Math.abs(a-b)<=t.absolute+t.relative*Math.abs(b);
const units={m:['length',1],mm:['length',.001],rad:['angle',1],mrad:['angle',.001],kN:['force',1],N:['force',.001],
 'kN.m':['moment',1],'kN*m':['moment',1],'kN·m':['moment',1],'N.m':['moment',.001],'N*m':['moment',.001],
 'kN.mm':['moment',.001],'N.mm':['moment',1e-6],s:['time',1],Hz:['frequency',1],tonne:['mass',1],kg:['mass',.001]};
function convert(value,from,to){assert(finite(value)&&units[from]&&units[to]&&units[from][0]===units[to][0],'Invalid value/unit');return value*units[from][1]/units[to][1];}

function activeModel(model,projectSpatial=false){
 const m=clone(model),uses=new Map();
 for(const e of m.elements){if(!uses.has(e.section))uses.set(e.section,[]);uses.get(e.section).push(e);}
 m.sections=m.sections.filter(s=>uses.has(s.id));
 const materials=new Set(m.elements.map(e=>e.material));m.materials=m.materials.filter(v=>materials.has(v.id));
 const planar=m.coordinate_system?.dimension==='2d'||projectSpatial;
 if(m.analysis_control?.self_weight&&m.analysis_control.gravity_direction==null)m.analysis_control.gravity_direction='-z';
 if(m.analysis_control?.mass_source==='nodal')for(const n of m.nodes)if(n.mass===0)delete n.mass;
 for(const s of m.sections)if(uses.get(s.id)?.every(e=>['truss','brace'].includes(e.type))){
  // Diagnostics may retain the authored shape, but bending/torsion cannot
  // become an axial-response gate when every user of this section is axial.
  for(const k of ['Iy','Iz','J','Asy','Asz','Iyz'])delete s.properties[k];
  delete s.shape;delete s.extra;s.type='truss';
 }else if(planar&&uses.has(s.id)){
  // Verified canonical XZ elasticBeamColumn uses E,A and Iy (roll=0),
  // or Iz (roll=90). It has no torsional/out-of-plane DOF or shear term.
  const active=new Set(['A']);
  for(const e of uses.get(s.id))if(['beam','column'].includes(e.type))active.add(Math.round((e.rotation_angle||0)/90)%2?'Iz':'Iy');
  s.properties=Object.fromEntries(Object.entries(s.properties).filter(([k])=>active.has(k)));
  delete s.shape;delete s.extra;s.type='custom';
 }
 if(planar)for(const material of m.materials){material.nu=.3;material.G=material.E/(2*1.3);}
 return m;
}
function canonicalPlanarAxes(model){
 if(model.elements.some(e=>e.releases&&Object.keys(e.releases).length||e.offsets&&Object.keys(e.offsets).length))return false;
 if(model.coordinate_system.dimension==='2d')return true;
 const planar=clone(model);planar.coordinate_system={...planar.coordinate_system,dimension:'2d',plane:'xz'};
 return model.elements.every(e=>{
  const a=axesFor(model,e),b=axesFor(planar,e);
  return a.every((row,i)=>row.every((v,j)=>Math.abs(v-b[i][j])<1e-9));
 });
}
function refinementView(actual,expected){
 // Canonical 2D mesh nodes restrain uy/rx/rz by definition. These are not
 // added physical supports. Preserve every active restraint; the underlying
 // matcher still verifies collinearity, degree two, zero mass and all loads.
 if(![actual,expected].every(m=>m.coordinate_system?.dimension==='2d'&&m.coordinate_system.plane==='xz'
   &&m.nodes.every(n=>n.y===0&&[1,3,5].every(i=>n.restraints?.[i]===true))))return actual;
 const view=clone(actual);
 for(const n of view.nodes)if(!expected.nodes.some(e=>Math.hypot(n.x-e.x,n.y-e.y,n.z-e.z)<=1e-8))
  for(const i of [1,3,5])n.restraints[i]=false;
 return view;
}
function physical(actual,expected){
 const projection=actual.coordinate_system?.dimension!==expected.coordinate_system?.dimension
   &&[actual,expected].every(m=>closedPlanarDomain(m)&&canonicalPlanarAxes(m));
 return comparePhysicalModels(refinementView(activeModel(actual,projection),expected),activeModel(expected,projection),
 {coordinate:1e-8,property:1e-6,load:1e-6,explicitElasticProperties:true,staticTheory:'Euler-Bernoulli'});}

function merged(jobs){
 const state=clone(jobs[0].state);state.analysisResult.results={};
 for(const job of jobs)Object.assign(state.analysisResult.results,job.state.analysisResult?.results||{});
 return state;
}
function requestValue(data,q,map={}){
 let rows=[data];
 for(let i=0;i<q.path.length;i++){
  const key=q.path[i];
  rows=rows.flatMap(v=>key==='*'?(Array.isArray(v)?v:[]):[v?.[(i>0&&['nodes','modeShape'].includes(q.path[i-1]))?(map[key]||key):key]]);
 }
 assert(rows.length&&rows.every(finite),'Missing dynamic observable '+q.id);
 return q.operation==='max_abs'?rows.reduce((a,b)=>Math.abs(b)>Math.abs(a)?b:a):rows[0];
}
function peakTime(data,q,map={}){
 assert(q.operation==='max_abs'&&q.path[0]==='timeHistory'&&q.path[1]==='*','Unsupported peak-time request');
 const rows=data.timeHistory;assert(Array.isArray(rows)&&rows.length,'Missing time history');
 let winner=0;
 for(let i=1;i<rows.length;i++)if(Math.abs(requestValue(data,{...q,operation:undefined,path:['timeHistory',i,...q.path.slice(2)]},map))>
   Math.abs(requestValue(data,{...q,operation:undefined,path:['timeHistory',winner,...q.path.slice(2)]},map)))winner=i;
 assert(finite(rows[winner].time),'Missing peak time');return rows[winner].time;
}
function canonicalParameters(p){
 const r=clone(p);if(r.analysisType==='time_history'){
  const n=Math.floor(r.duration/r.timeStep)+1;
  r.groundMotion=r.groundMotion.slice(0,n).map(v=>v*(r.groundMotionUnit==='g'?9.80665:1));r.groundMotionUnit='m/s2';
 }
 return r;
}
function parametersMatch(actual,expected){
 const a=canonicalParameters(actual),b=canonicalParameters(expected);
 for(const [k,v] of Object.entries(b)){
  if(['monitorNodeIds','monitorElementIds','monitorSupportNodeIds'].includes(k))continue; // Outputs are checked below, via mapped identities.
  if(k==='numModes'){if(!(a[k]>=v))return false;}
  else if(Array.isArray(v)){if(!Array.isArray(a[k])||a[k].length!==v.length||v.some((x,i)=>!close(a[k][i],x,{absolute:1e-12,relative:1e-10})))return false;}
  else if(typeof v==='number'){if(!close(a[k],v,{absolute:1e-12,relative:1e-10}))return false;}
  else if(a[k]!==v)return false;
 }
 return true;
}
function reported(answer,ref){
 const rows=answer.quantities,ids=ref.reportIds||ref.requests.map(q=>q.id);
 assert(Array.isArray(rows)&&new Set(rows.map(r=>r.id)).size===rows.length,'Unique reported quantities required');
 assert(rows.length===ids.length&&ids.every(id=>rows.some(r=>r.id===id)),'Reported request coverage differs');
 for(const id of ids){const q=ref.requests.find(q=>q.id===id),row=rows.find(r=>r.id===id);
  assert(q&&close(convert(row.value,row.unit,q.unit),q.value,q.tolerance),'Reported signed value differs: '+id);
  if(q.time!==undefined)assert(close(row.time,q.time,{absolute:1e-9,relative:0}),'Peak time differs');
 }
}
function staticState(jobs,ref){
 assert(jobs.length,'Actual jobs missing');let mapping;
 for(const j of jobs){assert(j.state?.analysisResult,'Static result missing');const p=physical(j.state.model,ref.model);
  assert(p.pass,'Physical model differs: '+p.failures.join('; '));mapping={...p.diagnostics,model:j.state.model};
  const expected='builtin-'+ref.engine.toLowerCase();assert(j.state.analysisResult.meta?.engineId===expected,'Wrong solver');}
 return {state:merged(jobs),mapping};
}
function mac(a,b,weights){
 const dot=a.reduce((s,x,i)=>s+weights[i]*x*b[i],0),aa=a.reduce((s,x,i)=>s+weights[i]*x*x,0),bb=b.reduce((s,x,i)=>s+weights[i]*x*x,0);
 return aa>0&&bb>0?dot*dot/(aa*bb):0;
}
function volume(model){
 const nodes=new Map(model.nodes.map(n=>[n.id,n])),sections=new Map(model.sections.map(s=>[s.id,s]));
 return model.elements.reduce((total,e)=>{const [a,b]=e.nodes.map(n=>nodes.get(n));
  return total+sections.get(e.section).properties.A*Math.hypot(a.x-b.x,a.y-b.y,a.z-b.z);},0);
}

function evaluate(ref,answer,jobs,currentJobIds=[]){
 const metrics=[],diagnostics={},add=(name,pass,detail)=>metrics.push({name,pass:!!pass,detail});
 try{
  assert(answer&&typeof answer==='object','Current answer missing');
  const fields=ref.clarificationFields||[],questions=answer.clarifications||[];
  add('clarification',questions.length===fields.length&&new Set(questions.map(q=>q.field)).size===fields.length
      &&fields.every(f=>questions.some(q=>q.field===f&&typeof q.question==='string'&&/[\p{L}\p{N}]/u.test(q.question))),fields);
  if(ref.kind==='clarify'){
   add('no_premature_execution',jobs.length===0&&currentJobIds.length===0&&!answer.quantities?.length,'Unresolved physical input');
   return {passed:metrics.every(m=>m.pass),metrics};
  }
  assert(jobs.length&&jobs.every(j=>j.verified&&j.engine===ref.engine),'Actual private broker jobs are required');
  assert(Array.isArray(answer.jobIds)&&new Set(answer.jobIds).size===answer.jobIds.length
    &&answer.jobIds.length===jobs.length&&jobs.every(j=>answer.jobIds.includes(j.jobId)),'Reported job binding differs');
  if(ref.kind==='query')add('query_reuses_jobs',currentJobIds.length===0,'No new solve on explicit query-only turn');
  if(['static','query'].includes(ref.kind)){
   const {state,mapping}=staticState(jobs,ref);
   const full=comparePhysicalModels(refinementView(state.model,ref.model),ref.model,{coordinate:1e-8,property:1e-6,load:1e-6,explicitElasticProperties:true,staticTheory:'Euler-Bernoulli'});
   diagnostics.fullInputReconstruction={pass:full.pass,failures:full.failures};
   const q=compareRequestedQuantities(state.analysisResult,ref.requests,mapping);add('actual_requested_response',q.pass,q.failures);
   reported(answer,ref);add('reported_response',true);
   if(ref.derived?.length){const d=compareDerivedQuantities(state.analysisResult,ref.requests,ref.derived,mapping,answer.derived,ref.derived.map(d=>d.id));add('derived',d.pass,d.failures);}
  }else if(['modal','transient'].includes(ref.kind)){
   assert(jobs.length===1,'One dynamic execution required');const result=jobs[0].state.dynamicResult;
   assert(result&&result.analysis===ref.kind&&result.data.status==='success','Actual dynamic result missing');
   const p=physical(jobs[0].state.model,ref.model);add('physical_model',p.pass,p.failures);
   assert(p.pass,'Dynamic model differs');
   add('analysis_parameters',parametersMatch(result.parameters,ref.parameters),'Explicit mass/record/units/step/damping');
   for(const q of ref.requests){
    add('actual:'+q.id,close(requestValue(result.data,q,p.diagnostics.nodeMapping),q.value,q.tolerance));
    if(q.time!==undefined)add('actual_peak_time:'+q.id,close(peakTime(result.data,q,p.diagnostics.nodeMapping),q.time,{absolute:1e-9,relative:0}));
   }
   reported(answer,ref);add('reported_response',true);
   if(ref.requireShapes){
    assert(Array.isArray(answer.modeShapes)&&answer.modeShapes.length===ref.parameters.numModes,'Mode shapes missing');
    const ns=Object.keys(ref.modalTruth.masses).filter(n=>ref.modalTruth.masses[n]>0),w=ns.map(n=>ref.modalTruth.masses[n]);
    for(let i=0;i<ref.parameters.numModes;i++){
     const row=answer.modeShapes.find(r=>r.modeNumber===i+1);assert(row,'Modal identity missing');
     const a=ns.map(n=>row.values[n]),b=ns.map(n=>ref.modalTruth.shape[n][i]);
     const native=ns.map(n=>result.data.modes[i]?.modeShape?.[p.diagnostics.nodeMapping[n]||n]?.[0]);
     assert(a.every(finite)&&native.every(finite),'Finite native and reported shapes required');
     add('actual_shape_MAC:'+i,mac(native,b,w)>=1-1e-6,'Native shape against independent eigenvectors');
     add('shape_MAC:'+i,mac(a,b,w)>=1-1e-6&&mac(a,native,w)>=1-1e-6,'Sign and normalization invariant');
    }
   }
  }else if(ref.kind==='scheme'){
   assert(Array.isArray(answer.schemes)&&answer.schemes.length===ref.schemes.length,'All finite schemes must be evaluated');
   assert(new Set(answer.schemes.map(s=>s.id)).size===ref.schemes.length,'Duplicate schemes');
   const computed=[];
   for(const truth of ref.schemeTruth){
    const row=answer.schemes.find(s=>s.id===truth.id);assert(row&&Array.isArray(row.jobIds),'Scheme execution missing');
    const selected=row.jobIds.map(id=>jobs.find(j=>j.jobId===id));assert(selected.every(Boolean),'Untrusted scheme job');
    const {state,mapping}=staticState(selected,{...ref,model:truth.model});let maximum=0;
    for(const id of ref.schemeSelections)for(const nid of ref.constraint.nodes){
     const q={id:'constraint',selection:{kind:'combination',id},location:{kind:'node',id:nid},component:ref.constraint.component,unit:'m'};
     maximum=Math.max(maximum,Math.abs(readQuantity(state.analysisResult,q,mapping)));
    }
    const objective=volume(state.model);
    add('actual_scheme:'+truth.id,close(maximum,truth.maximum)&&close(objective,truth.volume),'Independent response and geometric volume');
    assert(close(row.maximum,maximum)&&close(row.volume,objective),'Scheme response/volume report differs');
    const feasible=maximum<=ref.constraint.absoluteLimit;assert(row.feasible===feasible,'Scheme feasibility differs');
    computed.push({id:truth.id,volume:objective,feasible});
   }
   const feasible=computed.filter(s=>s.feasible),best=feasible.length?Math.min(...feasible.map(s=>s.volume)):null;
   add('optimal_feasible_choice',best===null?answer.selectedScheme===null:
       computed.some(s=>s.id===answer.selectedScheme&&s.feasible&&close(s.volume,best,{absolute:1e-12,relative:1e-10})),computed);
  }else throw Error('Unknown reference kind');
 }catch(e){add('complete_valid_evidence',false,e.message);}
 return {passed:metrics.every(m=>m.pass),metrics,diagnostics};
}

function loadJobs(work,cid,ids){return ids.map(id=>{
 assert(/^[a-f0-9]{32}$/.test(id),'Unsafe job ID');const p=path.join(work,'solver-jobs',cid,id),receipt=read(path.join(p,'broker-receipt.json'));
 assert(receipt.ok&&receipt.caseId===cid,'Unsuccessful/wrong-case job');
 if(receipt.role==='candidate')assert(receipt.stateSha256,'Candidate jobs require a broker state seal');
 if(receipt.stateSha256)assert(sha(path.join(p,'state.json'))===receipt.stateSha256,'Broker state changed');
 const request=read(path.join(p,'request.json')),state=read(path.join(p,'state.json'));
 assert(require('node:util').isDeepStrictEqual(state.model,read(path.join(p,'model.json'))),'State/model identity differs');
 return {jobId:id,engine:receipt.engine,verified:true,state};
});}
function oracleAnswer(ref,jobs,schemeJobs={}){
 const answer={jobIds:jobs.map(j=>j.jobId),quantities:[],clarifications:(ref.clarificationFields||[]).map(field=>({field,question:'请确认 '+field}))};
 if(ref.kind==='clarify')return answer;
 if(['static','query'].includes(ref.kind)){
  const {state,mapping}=staticState(jobs,ref);
  answer.quantities=ref.requests.filter(q=>(ref.reportIds||[]).includes(q.id)).map(q=>({id:q.id,value:readQuantity(state.analysisResult,q,mapping),unit:q.unit}));
  answer.derived=evaluateDerivedQuantities(ref.requests.map(q=>({...q,value:readQuantity(state.analysisResult,q,mapping)})),ref.derived||[]).values;
 }else if(['modal','transient'].includes(ref.kind)){
  const result=jobs[0].state.dynamicResult,p=physical(jobs[0].state.model,ref.model);
  answer.quantities=ref.requests.map(q=>({id:q.id,value:requestValue(result.data,q,p.diagnostics.nodeMapping),unit:q.unit,...(q.time!==undefined?{time:peakTime(result.data,q,p.diagnostics.nodeMapping)}:{})}));
  if(ref.requireShapes)answer.modeShapes=result.data.modes.slice(0,ref.parameters.numModes).map((m,i)=>({modeNumber:i+1,
    values:Object.fromEntries(Object.keys(ref.modalTruth.shape).map(n=>[n,m.modeShape[p.diagnostics.nodeMapping[n]||n][0]]))}));
 }else if(ref.kind==='scheme'){
  answer.schemes=ref.schemeTruth.map(s=>{
   const group=jobs.filter(j=>(schemeJobs[s.id]||[]).includes(j.jobId));const {state,mapping}=staticState(group,{...ref,model:s.model});let maximum=0;
   for(const id of ref.schemeSelections)for(const nid of ref.constraint.nodes)maximum=Math.max(maximum,Math.abs(readQuantity(state.analysisResult,
      {selection:{kind:'combination',id},location:{kind:'node',id:nid},component:ref.constraint.component,unit:'m'},mapping)));
   return {id:s.id,jobIds:group.map(j=>j.jobId),maximum,volume:volume(state.model),feasible:maximum<=ref.constraint.absoluteLimit};
  });const f=answer.schemes.filter(s=>s.feasible).sort((a,b)=>a.volume-b.volume);answer.selectedScheme=f[0]?.id||null;
 }
 return answer;
}
module.exports={evaluate,oracleAnswer,loadJobs,physical,requestValue,parametersMatch};
