// v3.2 opt-in comparison policy; v3.1 remains frozen for historical replay.
// v3.1 review of full-suite evidence; frozen predecessor evaluate.cjs SHA256 d4c23fa2f4832a712cfb2e18f11c5575c2d7a9aeb7dd4fca416f76cb8b4b543c.
'use strict';
// Protected native jobs are evidence. Independent truth is never used to
// synthesize the observed response or to repair a candidate's physical input.
const v2=require('../research300_v2/evaluate.cjs');
const pilot=require('../pilot30/evaluate.cjs');
const {readQuantity,UNITS}=require('../../lib/requested-quantities.cjs');
const {selectAnalysisResult,selectionKey}=require('../../lib/result-selection.cjs');
const {readNativeStation,axes,samePosition}=require('../../lib/commercial-stations.cjs');
const {axesFor}=require('../../lib/physical-model-fidelity.cjs');
const clone=structuredClone,finite=x=>typeof x==='number'&&Number.isFinite(x);
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),util=require('node:util');
const assert=(pass,message)=>{if(!pass)throw Error(message);};
const close=(a,b,absolute=1e-8,relative=1e-6)=>finite(a)&&finite(b)&&Math.abs(a-b)<=absolute+relative*Math.abs(b);
const units={m:['length',1],mm:['length',.001],kN:['force',1],N:['force',.001],
 'kN.m':['moment',1],'kN*m':['moment',1],'kN·m':['moment',1],'N.m':['moment',.001],
 'kN.mm':['moment',.001],'N.mm':['moment',1e-6],'m^3':['volume',1],m3:['volume',1],tonne:['mass',1],kg:['mass',.001]};
function convert(row,to){assert(row&&finite(row.value)&&units[row.unit]&&units[to]&&units[row.unit][0]===units[to][0],'Finite, dimensionally correct value/unit required');return row.value*units[row.unit][1]/units[to][1];}
function emptyDefaults(model){
 const m={...model};for(const key of ['wall_openings','slab_openings'])if(Array.isArray(m[key])&&m[key].length===0)delete m[key];
 if(m.extensions&&typeof m.extensions==='object'&&!Array.isArray(m.extensions)&&Object.keys(m.extensions).length===0)delete m.extensions;return m;
}
function physical(actual,expected,analysis='static'){
 const compare=require('./physical-v32.cjs')[analysis==='dynamic'?'physical':'staticPhysical'];
 return compare(emptyDefaults(actual),emptyDefaults(expected));
}
const explicitZeroOffsets=e=>e.offsets&&typeof e.offsets==='object'&&!Array.isArray(e.offsets)
 &&Object.keys(e.offsets).every(k=>['i_x','i_y','i_z','j_x','j_y','j_z'].includes(k)&&e.offsets[k]===0);

function evidenceViews(jobs){return jobs.map(job=>{
 const model=emptyDefaults(job.state.model),result=job.state.analysisResult;
 if(!result)return {...job,state:{...job.state,model}};
 const results={};for(const [key,record]of Object.entries(result.results||{})){
  let data=record.data;
  const affected=model.elements.some(e=>explicitZeroOffsets(e)&&data.memberResponses?.some(r=>r.id===e.id&&r.state==='interpolated'&&r.reason==='consistency'));
  if(affected&&!data.memberStations){
   assert(data.meta?.forceConvention==='element-end-resisting-actions','Explicit native end-action convention required');
   const stations={},lengths={};
   for(const element of model.elements){
    const row=data.memberResponses?.find(r=>r.id===element.id);if(!row||!['recovered','interpolated'].includes(row.state))continue;const localAxes=axes(row.axes),expectedAxes=axesFor(model,element);
    assert(localAxes.every((a,i)=>a.every((v,j)=>Math.abs(v-expectedAxes[i][j])<1e-9)),'Native end cut axes differ');
    lengths[element.id]=length(model,element);
    if(row.state==='recovered')stations[element.id]=row.samples.filter(s=>['left','right','continuous'].includes(s.side)).map(s=>({positionM:s.x,side:s.side,referenceFrame:'element-local',localAxes,components:{N:s.N,Vy:s.V2,Vz:s.V3,T:s.T,My:s.M2,Mz:s.M3}}));
    else if(explicitZeroOffsets(element)&&row.state==='interpolated'&&row.reason==='consistency'){
     const force=data.forces?.[element.id];assert(force?.responseCoordinateConvention==='global-xyz'&&force.referenceFrame==='element-local'&&force.source?.kind==='solver-direct','Direct, explicitly framed solver end actions required');
     const end=(values,sign)=>{const names={N:'N',Vy:'V2',Vz:'V3',T:'T',My:'M2',Mz:'M3'},out={};for(const [to,from]of Object.entries(names)){assert(finite(values?.[from]),'Complete native end vector required');out[to]=sign*values[from];}return out;};
     stations[element.id]=[{positionM:0,side:'right',referenceFrame:'element-local',localAxes,components:end(force.n1,-1)},
      {positionM:lengths[element.id],side:'left',referenceFrame:'element-local',localAxes,components:end(force.n2,1)}];
    }
   }
   // These are exact solver end cuts, not a recovered/interpolated curve.
   // The protected original state and its checksum are never modified.
   const execution=data.meta?.execution;
   assert(execution?.executed===true&&execution.analysisReturnCode===0&&execution.constitutiveModel==='linear-elastic'&&execution.solverConfiguration?.algorithm==='Linear','Verified completed linear static native execution required');
   assert(typeof record.meta?.modelHash==='string'&&typeof record.meta?.settingsHash==='string','Protected physical/settings identity required');
   data={...data,memberStations:stations,memberLengths:lengths,forceSemantics:'simultaneous-signed-stations',
    nativeContext:{engine:'OpenSees',engineVersion:data.meta.solverVersion,physicalModelHash:record.meta.modelHash,
     stiffnessHash:crypto.createHash('sha256').update(JSON.stringify([model.materials,model.sections,model.elements])).digest('hex'),settingsHash:record.meta.settingsHash,
     effectiveSettingsVerified:true,stationConventionsVerified:true,linearStatic:true},
    endCutEvidence:'solver-direct end resisting vector; i face negated, j face retained; empty offsets only'};
  }
  results[key]={...record,data};
 }
 return {...job,state:{...job.state,model,analysisResult:{...result,results}}};
});}
function activeView(model,selection){
 const m=clone(model),factors=selection.kind==='case'?{[selection.id]:1}:m.load_combinations.find(c=>c.id===selection.id)?.factors;
 assert(factors,'Undeclared executed selection');
 const loads=[];for(const [id,factor]of Object.entries(factors)){
  assert(finite(factor),'Invalid combination factor');const c=m.load_cases.find(c=>c.id===id);assert(c,'Missing selected load case');
  if(!factor)continue;
  for(const load of c.loads){
   assert(['nodal','distributed'].includes(load.type),'High-level tasks require the issued nodal/distributed mechanical loads');
   const row=clone(load);for(const k of ['fx','fy','fz','mx','my','mz','wx','wy','wz','wx_start','wx_end','wy_start','wy_end','wz_start','wz_end'])if(row[k]!==undefined)row[k]*=factor;
   row.id='active-'+loads.length;loads.push(row);
  }
 }
 m.load_cases=[{id:'ACTIVE',type:'other',loads}];m.load_combinations=[];return m;
}
function readMapped(job,q,mapping){
 if(q.location.kind!=='member')return readQuantity(job.state.analysisResult,q,mapping);
 const selected=mapping.selectionMapping[selectionKey(q.selection)];
 const {data,record}=selectAnalysisResult(job.state.analysisResult,selected);
 if(data.memberStations)return readQuantity(job.state.analysisResult,q,mapping);
 let id=mapping.elementMapping?.[q.location.id]||q.location.id;
 const segments=mapping.elementSegments?.[q.location.id];
 if(segments?.length){
  const x=q.location.positionM,matching=segments.filter(s=>(x>=s.start||samePosition(x,s.start))&&(x<=s.end||samePosition(x,s.end)));
  const segment=q.location.side==='left'?matching[0]:matching.at(-1);assert(segment,'No physical member at cut');id=segment.id;
 }
 const row=data.memberResponses?.find(r=>r.id===id);
 if(row?.state!=='recovered')return readQuantity(job.state.analysisResult,q,mapping);
 const e=job.state.model.elements.find(e=>e.id===id);assert(e,'Recovered cut lacks executed member');
 const actualAxes=axes(row.axes),modelAxes=axesFor(job.state.model,e);
 assert(actualAxes.every((a,i)=>a.every((v,j)=>Math.abs(v-modelAxes[i][j])<1e-9)),'Recovered cut axes differ from executed convention');
 const samples=row.samples.filter(s=>['left','right','continuous'].includes(s.side)).map(s=>({positionM:s.x,side:s.side,referenceFrame:'element-local',localAxes:actualAxes,
  components:{N:s.N,Vy:s.V2,Vz:s.V3,T:s.T,My:s.M2,Mz:s.M3}}));
 const cut=readNativeStation({memberStations:{[id]:samples},memberLengths:{[id]:row.length}},q.location.id,q.location.positionM,q.location.side,mapping);
 const value=cut[{N:'N',V2:'Vy',V3:'Vz',T:'T',M2:'My',M3:'Mz'}[q.component]];
 const publicData={units:data.units||data.meta?.units||record.meta?.units,memberResponses:[{id:q.location.id,state:'recovered',samples:[{x:q.location.positionM,side:q.location.side,[q.component]:value}]}]};
 return readQuantity({results:{[selectionKey(q.selection)]:{selection:q.selection,data:publicData}}},q);
}
function staticViews(ref,jobs){
 assert(jobs.length,'Actual static jobs missing');const maps=jobs.map(job=>{
  assert(job.verified&&job.engine===ref.engine&&job.state.analysisResult?.meta?.engineId==='builtin-'+ref.engine.toLowerCase(),'Verified designated-engine static job required');
  const result=physical(job.state.model,ref.model);assert(result.pass,'Physical model differs: '+result.failures.join('; '));
  const selectionMapping=Object.fromEntries(ref.requests.map(q=>[selectionKey(q.selection),{kind:q.selection.kind,id:(q.selection.kind==='case'?result.diagnostics.caseMapping:result.diagnostics.combinationMapping)?.[q.selection.id]||q.selection.id}]));
  return {...result.diagnostics,model:job.state.model,selectionMapping};
 });
 const views=jobs.map(job=>({...job,state:{...job.state,model:ref.model,analysisResult:{...job.state.analysisResult,results:{}}}})),groups=new Map();
 for(const q of ref.requests){const key=selectionKey(q.selection);if(!groups.has(key))groups.set(key,[]);groups.get(key).push(q);}
 for(const [key,requests]of groups){let chosen=-1,values,last;
  for(let i=0;i<jobs.length;i++)try{const observed=requests.map(q=>readMapped(jobs[i],{...q,unit:UNITS[q.component]},maps[i]));chosen=i;values=observed;break;}catch(error){last=error;}
  assert(chosen>=0,'No actual job supplies '+key+': '+last?.message);
  const data={units:{displacement:'m',rotation:'rad',force:'kN',moment:'kN.m'},displacements:{},reactions:{},memberResponses:[]};
  for(let i=0;i<requests.length;i++){
   const q=requests[i],loc=q.location;if(loc.kind==='node'){
    const table=/^[ur]/.test(q.component)?data.displacements:data.reactions;(table[loc.id]||={})[q.component.toLowerCase()]=values[i];
   }else{
    let row=data.memberResponses.find(r=>r.id===loc.id);if(!row)data.memberResponses.push(row={id:loc.id,state:'recovered',samples:[]});
    let sample=row.samples.find(s=>s.x===loc.positionM&&s.side===loc.side);if(!sample)row.samples.push(sample={x:loc.positionM,side:loc.side});sample[q.component]=values[i];
   }
  }
  views[chosen].state.analysisResult.results[key]={selection:requests[0].selection,data};
 }
 return views;
}
function dynamicPhysicalView(model){
 const m=clone(model),c=m.analysis_control;
 // Explicit nodal inertia and linear base excitation do not execute static
 // source cases. Their D/Q conversion is checked through every nodal mass.
 if(c?.mass_source==='nodal'&&['self_weight','p_delta','rigid_floor','rigid_offsets','construction_stage'].every(k=>c[k]===false)){m.load_cases=[];m.load_combinations=[];}
 return m;
}
function dynamicViews(ref,jobs){
 assert(jobs.length===1,'One protected dynamic execution required');const job=jobs[0];
 assert(job.verified&&job.engine===ref.engine&&job.state.dynamicResult?.meta?.engineId==='builtin-opensees','Verified designated-engine dynamic job required');
 const result=physical(dynamicPhysicalView(job.state.model),dynamicPhysicalView(ref.model),'dynamic');assert(result.pass,'Dynamic physical model differs: '+result.failures.join('; '));
 const inverse=Object.fromEntries(Object.entries(result.diagnostics.nodeMapping).map(([publicId,actualId])=>[actualId,publicId]));
 const data=clone(job.state.dynamicResult.data),rename=rows=>Object.fromEntries(Object.entries(rows||{}).map(([id,row])=>[inverse[id]||id,row]));
 for(const mode of data.modes||[])if(mode.modeShape)mode.modeShape=rename(mode.modeShape);
 for(const row of data.timeHistory||[])if(row.nodes)row.nodes=rename(row.nodes);
 return [{...job,state:{...job.state,model:ref.model,dynamicResult:{...job.state.dynamicResult,data}}}];
}
function provider(model,selection,jobs){
 const expected=activeView(model,selection);let last='No jobs';
 for(const job of jobs){
  try{
   assert(job.verified&&job.engine==='OpenSees'&&job.state.analysisResult?.meta?.engineId==='builtin-opensees','Verified native OpenSees static job required');
   for(const key of Object.keys(job.state.analysisResult.results||{})){
    const [kind,...tail]=key.split(':'),actualSelection={kind,id:tail.join(':')};if(!['case','combination'].includes(kind))continue;
    const result=physical(activeView(job.state.model,actualSelection),expected);if(!result.pass){last=result.failures.join('; ');continue;}
    selectAnalysisResult(job.state.analysisResult,actualSelection);
    const mapping={...result.diagnostics,model:job.state.model,selectionMapping:{[selectionKey(selection)]:actualSelection}};
    const cache=new Map();return {job,mapping,selection,read(loc,component){
     const key=JSON.stringify([loc,component]);if(!cache.has(key))cache.set(key,readMapped(job,{selection,location:loc,component,unit:UNITS[component]},mapping));return cache.get(key);
    }};
   }
  }catch(error){last=error.message;}
 }
 throw Error('No physically correct executed '+selectionKey(selection)+': '+last);
}
function length(model,e){const [a,b]=e.nodes.map(id=>model.nodes.find(n=>n.id===id));return Math.hypot(a.x-b.x,a.y-b.y,a.z-b.z);}
function envelope(model,providers,type,ids){
 const rows=[];
 for(const p of providers){
  if(type==='force'){
   const bending=model.elements.some(e=>(!ids||ids.has(e.id))&&!['truss','brace'].includes(e.type));
   for(const e of model.elements){
    if(ids&&!ids.has(e.id)||bending&&['truss','brace'].includes(e.type))continue;
    for(const component of bending?(model.coordinate_system.dimension==='2d'?['M2']:['M2','M3']):['N'])for(const [positionM,side]of [[0,'right'],[length(model,e),'left']]){
     const value=p.read({kind:'member',id:e.id,positionM,side},component);
     rows.push({value,unit:bending?'kN.m':'kN',governingMember:e.id,positionM,side,component,selection:p.selection});
    }
   }
  }else for(const n of model.nodes){
   if(ids&&!ids.has(n.id))continue;const loc={kind:'node',id:n.id};
   const value=type==='lateral'?Math.hypot(p.read(loc,'ux'),model.coordinate_system.dimension==='3d'?p.read(loc,'uy'):0):p.read(loc,'uz');
   rows.push({value,unit:'m',governingJoint:n.id,selection:p.selection});
  }
 }
 assert(rows.length&&rows.every(r=>finite(r.value)),'Complete finite global envelope required');return rows.reduce((a,b)=>Math.abs(b.value)>Math.abs(a.value)?b:a);
}
function modelGroup(jobs,ids){
 assert(Array.isArray(ids)&&ids.length&&new Set(ids).size===ids.length,'Nonempty unique job group required');
 return ids.map(id=>{const j=jobs.find(j=>j.jobId===id);assert(j,'Untrusted job in group');return j;});
}
function selectedModels(ref,truth){
 if(ref.integration==='rigid')return {combined:{...clone(ref.combinedTemplate),sections:clone(truth.combinedSections),load_cases:clone(truth.combinedLoadCases)}};
 return Object.fromEntries(['upper','primary'].map(k=>[k,{...clone(ref[k+'Template']),sections:clone(truth[k+'Sections']),load_cases:clone(truth[k+'LoadCases'])}]));
}
function metricReport(report,actual,truth,readAt){
 const absolute=actual.unit==='m'?1e-8:1e-6;
 assert(close(readAt(truth),truth.value,absolute),'Signed native response at independent governing location differs from independent mechanics');
 assert(close(Math.abs(actual.value),Math.abs(truth.value),absolute),'Native global envelope differs from independent mechanics');
 assert(report&&report.selection?.kind&&typeof report.selection.id==='string','Explicit governing selection required');
 const observed=readAt(report);
 assert(close(Math.abs(observed),Math.abs(actual.value),absolute),'Reported location/selection is not globally governing');
 assert(close(convert(report,actual.unit),observed,absolute),'Reported signed response differs from native governing location');
}
function fromReport(model,providers,type,row,ids,idMap){
 const p=providers.find(p=>selectionKey(p.selection)===selectionKey(row.selection));assert(p,'Unissued governing selection');
 if(type==='force'){
  const id=idMap?.[row.governingMember]||row.governingMember,e=model.elements.find(e=>e.id===id);assert(e&&(!ids||ids.has(id)),'Governing member outside issued scope');
  const bending=model.elements.some(e=>(!ids||ids.has(e.id))&&!['truss','brace'].includes(e.type));assert(bending?['beam','column'].includes(e.type)&&(model.coordinate_system.dimension==='2d'?row.component==='M2':['M2','M3'].includes(row.component)):row.component==='N','Wrong end-action component');
  const L=length(model,e);assert(close(row.positionM,0,1e-9,0)&&row.side==='right'||close(row.positionM,L,1e-9,0)&&row.side==='left','Issued end cut and face required');
  return p.read({kind:'member',id,positionM:row.positionM,side:row.side},row.component);
 }
 const id=idMap?.[row.governingJoint]||row.governingJoint;assert(model.nodes.some(n=>n.id===id)&&(!ids||ids.has(id)),'Governing joint outside issued scope');
 const loc={kind:'node',id};return type==='lateral'?Math.hypot(p.read(loc,'ux'),model.coordinate_system.dimension==='3d'?p.read(loc,'uy'):0):p.read(loc,'uz');
}
function observe(ref,answer,jobs){
 const metrics={},transfers=[];
 if(ref.kind==='analysis'){
  assert(Object.keys(answer.jobIdsByScenario||{}).sort().join(',')===ref.scenarios.map(s=>s.id).sort().join(','),'Exact issued scenario groups required');
  for(const scenario of ref.scenarios){
   const group=modelGroup(jobs,answer.jobIdsByScenario?.[scenario.id]),ps=scenario.selections.map(s=>provider(scenario.model,s,group));
   assert(new Set(ps.map(p=>p.job.jobId)).size===group.length,'Extraneous or duplicate scenario evidence');
   metrics[scenario.id]={};for(const type of ['uz','lateral','force']){
    const actual=envelope(scenario.model,ps,type);metrics[scenario.id][type]=actual;
    metricReport(answer.metrics?.[scenario.id]?.[type],actual,scenario.metrics[type],row=>fromReport(scenario.model,ps,type,row));
   }
  }
  if(ref.scenarios.length===2)for(const type of ['uz','lateral','force']){
   const [a,b]=ref.scenarios.map(s=>Math.abs(metrics[s.id][type].value)),delta=(b-a)/a;
   assert(close(answer.relativeChangeWhenRequested?.[type],delta,1e-7),'Relative scenario change differs');
  }
 }else{
  assert(answer.design&&Object.keys(answer.design).sort().join(',')==='G0,G1,G2','Exactly three design groups required');
  const id=['G0','G1','G2'].map(g=>answer.design[g]).join('-'),truth=ref.truths.find(t=>t.id===id);assert(truth,'Unissued design choice');
  const models=selectedModels(ref,truth),roles=Object.keys(models),ps={};
  assert(Object.keys(answer.jobIdsByModel||{}).sort().join(',')===roles.sort().join(','),'Executed structural roles differ');
  for(const role of roles)ps[role]=(ref.requirements[role+'Selections']||[]).map(s=>provider(models[role],s,modelGroup(jobs,answer.jobIdsByModel?.[role])));
  for(const role of roles)assert(new Set(ps[role].map(p=>p.job.jobId)).size===answer.jobIdsByModel[role].length,'Extraneous or duplicate structural evidence');
  const rigid=ref.integration==='rigid',combined=ps.combined;
  const upperP=rigid?combined:ref.primaryTemplate.load_combinations.map(c=>{
   const selection={kind:'combination',id:c.id};return {selection,read(loc,comp){return Object.entries(c.factors).reduce((sum,[id,f])=>sum+f*ps.upper.find(p=>p.selection.id===id).read(loc,comp),0);}};
  });
  const model=rigid?models.combined:null,map=ref.combinedMapping;
  for(const [name,role,type]of [['upperVertical','upper','uz'],['primaryVertical','primary','uz'],['primaryLateral','primary','lateral'],['primaryEndAction','primary','force']]){
   const active=rigid?combined:role==='upper'?upperP:ps.primary,m=rigid?model:models[role],label=role==='upper'?'U':'P';
   const ids=rigid?new Set(Object.values(map[label][type==='force'?'elements':'nodes'])):undefined;
   const actual=envelope(m,active,type,ids);metrics[name]=actual;
   metricReport(answer.metrics?.[name],actual,truth.metrics[name],row=>fromReport(m,active,type,row,ids,rigid?map[label][type==='force'?'elements':'nodes']:undefined));
  }
  const required=rigid?combined:ps.upper;assert(Array.isArray(answer.transfers)&&answer.transfers.length===required.length,'Complete interface report required');
  for(const p of required){
   const block=answer.transfers.find(t=>selectionKey(t.selection)===selectionKey(p.selection));assert(block&&Array.isArray(block.values)&&block.values.length===4,'Four unique issued interfaces required per selection');
   const values=[];for(const link of ref.interface){
    const rows=block.values.filter(v=>v.upperSupport===link.upperSupport&&v.primaryJoint===link.primaryJoint);assert(rows.length===1,'Duplicate/missing interface identity');const row=rows[0];
    const loc={kind:'node',id:rigid?map.P.nodes[link.primaryJoint]:link.upperSupport},value={...link};
    const expectedBlock=truth.transfer.find(t=>selectionKey(t.selection)===selectionKey(p.selection));
    const expected=expectedBlock?.values.find(v=>v.upperSupport===link.upperSupport&&v.primaryJoint===link.primaryJoint);assert(expected,'Independent interface reference missing');
    for(const c of rigid?['ux','uz']:['fx','fz']){const native=p.read(loc,rigid?c:c==='fx'?'Fx':'Fz');assert(close(native,expected[c],rigid?1e-8:1e-6),'Signed native interface value differs from independent mechanics');assert(close(row[c],native,rigid?1e-8:1e-6),'Interface signed value differs from native result');value[c]=native;}
    values.push(value);
   }
   transfers.push({selection:p.selection,values});
  }
  assert(answer.feasible===truth.feasible,'Incorrect constraint feasibility');
  assert(close(convert(answer.volume,'m^3'),truth.volume,1e-10,1e-7),'Material volume differs from selected physical sections');
  const valid=ref.optimalDesigns.length?ref.optimalDesigns:ref.leastViolationDesigns;assert(valid.includes(id),'Not a globally optimal feasible design or minimum-violation witness');
 }
 return {metrics,transfers};
}
function evaluateCore(ref,answer,jobs,currentJobIds=[]){
 try{jobs=evidenceViews(jobs);}catch(error){return {passed:false,metrics:[{name:'complete_valid_evidence',pass:false,detail:error.message}]};}
 if(!['analysis','project'].includes(ref.kind)){
  let result;try{
   if(['static','query'].includes(ref.kind)){
    result=pilot.evaluate(ref,answer,staticViews(ref,jobs),currentJobIds);
    if(ref.derived?.length){const rows=answer?.derived;result.metrics.push({name:'required_derived_report',pass:Array.isArray(rows)&&rows.length===ref.derived.length&&new Set(rows.map(r=>r?.id)).size===rows.length&&ref.derived.every(d=>rows.some(r=>r?.id===d.id))});}
    if(ref.requireFreshExecution){const current=new Set(currentJobIds);result.metrics.push({name:'required_fresh_execution',pass:jobs.length>0&&jobs.every(j=>current.has(j.jobId))});}
    assert(ref.expectedIssuePaths===undefined,'V3 low-level inputs do not contain review/audit drafts');
   }else if(['modal','transient'].includes(ref.kind))result=v2.evaluate(ref,answer,dynamicViews(ref,jobs),currentJobIds);
   else result=v2.evaluate(ref,answer,jobs,currentJobIds);
  }catch(error){result={passed:false,metrics:[{name:'complete_valid_evidence',pass:false,detail:error.message}]};}
  if(ref.massRule){const total=ref.model.nodes.reduce((s,n)=>s+(n.mass||0),0);let pass=false;try{pass=close(convert(answer.massTotal,'tonne'),total,1e-8);}catch{}result.metrics.push({name:'derived_participating_mass',pass});result.passed=result.metrics.every(m=>m.pass);}
  result.passed=result.metrics.every(m=>m.pass);result.diagnostics||={};delete result.diagnostics.fullInputReconstruction;result.diagnostics.originalInputPolicy='Every original protected job is physically checked by the same v3 comparison policy before observed values/IDs are normalized; original state is unchanged.';
  return result;
 }
 const metrics=[];try{
  assert(jobs.length&&jobs.every(j=>j.verified&&j.engine===ref.engine),'Actual protected broker jobs required');
  const groups=Object.values(answer[ref.kind==='project'?'jobIdsByModel':'jobIdsByScenario']||{}).flat();
  assert(groups.length&&new Set(groups).size===groups.length&&groups.length===jobs.length&&jobs.every(j=>groups.includes(j.jobId)),'Exact unique reported job binding required');
  observe(ref,answer,jobs);metrics.push({name:'physical_input_native_global_metrics_governors_and_decision',pass:true});
 }catch(error){metrics.push({name:'complete_valid_evidence',pass:false,detail:error.message});}
 return {passed:metrics.every(m=>m.pass),metrics};
}
function evaluate(ref,answer,jobs,currentJobIds=[]){
 const result=evaluateCore(ref,answer,jobs,currentJobIds);
 const audit=require('./audit-metadata-v32.cjs');
 let unhandled=[],reviewOnlyJobs;
 try{
  reviewOnlyJobs=jobs.map(job=>{
   const view=audit.reviewOnlyView(job.state.model);unhandled.push(...view.unhandled);
   return {...job,state:{...job.state,model:view.model}};
  });
 }catch{
  // Invalid original model evidence has already failed evaluateCore. Do not
  // let optional metadata diagnostics throw and reclassify it as integration loss.
  unhandled=[];
 }
 let metadataOnly=false,auditAttribution;
 if(!result.passed&&unhandled.length&&reviewOnlyJobs){
  const diagnostic=evaluateCore(ref,answer,reviewOnlyJobs,currentJobIds);
  metadataOnly=diagnostic.passed;
  const independentFailures=diagnostic.metrics.filter(m=>!m.pass);
  auditAttribution={diagnosticOnly:true,passesWithoutMalformedLabels:metadataOnly,independentFailures};
  // Preserve the original rejection and its evidence. This counterfactual can
  // establish an independent failure, but can never award a pass.
  result.metrics.push(...independentFailures.map(m=>({...m,name:'audit_independent:'+m.name,diagnosticOnly:true})));
 }
 return {...result,evaluationRevision:'v3.2',runtimeQualification:'not-run',
  outcome:result.passed?'passed':metadataOnly?'needs_review':'candidate_failure',
  reviewReasons:metadataOnly?['Unsupported audit metadata requires an explicit equivalence decision']:[],
  unhandledAuditFields:unhandled,auditAttribution,numericalTolerancesChanged:false};
}
function oracleAnswer(ref,jobs,groups={}){
 jobs=evidenceViews(jobs);
 if(!['analysis','project'].includes(ref.kind)){
  const a=['static','query'].includes(ref.kind)?pilot.oracleAnswer(ref,staticViews(ref,jobs)):['modal','transient'].includes(ref.kind)?v2.oracleAnswer(ref,dynamicViews(ref,jobs)):v2.oracleAnswer(ref,jobs);if(ref.massRule)a.massTotal={value:ref.model.nodes.reduce((s,n)=>s+(n.mass||0),0),unit:'tonne'};return a;
 }
 // Bootstrap only labels/independent expectations. Replace values with actual
 // native observations below; positives must still pass independent checks.
 if(ref.kind==='analysis'){
  const a={jobIdsByScenario:groups,metrics:{},relativeChangeWhenRequested:{}};
  for(const s of ref.scenarios){const ps=s.selections.map(sel=>provider(s.model,sel,modelGroup(jobs,groups[s.id])));a.metrics[s.id]=Object.fromEntries(['uz','lateral','force'].map(t=>[t,envelope(s.model,ps,t)]));}
  if(ref.scenarios.length===2)for(const t of ['uz','lateral','force']){const [a0,b]=ref.scenarios.map(s=>Math.abs(a.metrics[s.id][t].value));a.relativeChangeWhenRequested[t]=(b-a0)/a0;}return a;
 }
 const truth=ref.truths.find(t=>t.id===(ref.optimalDesigns[0]||ref.leastViolationDesigns[0])),models=selectedModels(ref,truth),ps={};
 for(const role of Object.keys(models))ps[role]=(ref.requirements[role+'Selections']||[]).map(s=>provider(models[role],s,modelGroup(jobs,groups[role])));
 const a={design:truth.choice,feasible:truth.feasible,volume:{value:truth.volume,unit:'m^3'},jobIdsByModel:groups,metrics:{},transfers:[]},rigid=ref.integration==='rigid',map=ref.combinedMapping;
 const upperP=rigid?ps.combined:ref.primaryTemplate.load_combinations.map(c=>({selection:{kind:'combination',id:c.id},read(loc,comp){return Object.entries(c.factors).reduce((sum,[id,f])=>sum+f*ps.upper.find(p=>p.selection.id===id).read(loc,comp),0);}}));
 for(const [name,role,type]of [['upperVertical','upper','uz'],['primaryVertical','primary','uz'],['primaryLateral','primary','lateral'],['primaryEndAction','primary','force']]){
  const m=rigid?models.combined:models[role],label=role==='upper'?'U':'P',identities=rigid?map[label][type==='force'?'elements':'nodes']:null;
  const value=envelope(m,rigid?ps.combined:role==='upper'?upperP:ps.primary,type,identities?new Set(Object.values(identities)):undefined);
  if(identities){const key=type==='force'?'governingMember':'governingJoint';value[key]=Object.keys(identities).find(k=>identities[k]===value[key]);}a.metrics[name]=value;
 }
 for(const p of rigid?ps.combined:ps.upper)a.transfers.push({selection:p.selection,values:ref.interface.map(link=>{
  const loc={kind:'node',id:rigid?map.P.nodes[link.primaryJoint]:link.upperSupport};return {...link,...Object.fromEntries((rigid?['ux','uz']:['fx','fz']).map(c=>[c,p.read(loc,rigid?c:c==='fx'?'Fx':'Fz')]))};
 })});return a;
}
function numericJSON(value){
 if(typeof value==='number')return value===0?0:value;
 if(Array.isArray(value))return value.map(numericJSON);
 if(value&&typeof value==='object')return Object.fromEntries(Object.entries(value).map(([k,v])=>[k,numericJSON(v)]));return value;
}
function loadJobs(work,caseId,ids){
 assert(Array.isArray(ids)&&new Set(ids).size===ids.length,'Unique evidence IDs required');
 return ids.map(id=>{
  assert(/^[a-f0-9]{32}$/.test(id),'Unsafe job ID');const dir=path.join(work,'solver-jobs',caseId,id),read=name=>JSON.parse(fs.readFileSync(path.join(dir,name)));
  const receipt=read('broker-receipt.json');assert(receipt.ok&&receipt.caseId===caseId&&['oracle','candidate'].includes(receipt.role)&&receipt.stateSha256,'Sealed successful same-case broker receipt required');
  const raw=fs.readFileSync(path.join(dir,'state.json'));assert(crypto.createHash('sha256').update(raw).digest('hex')===receipt.stateSha256,'Broker state changed');
  const state=JSON.parse(raw),model=read('model.json');
  // Python preserves -0.0; JavaScript JSON.stringify emits 0. This sole IEEE
  // representation equivalence is exact, never a numerical tolerance bypass.
  assert(util.isDeepStrictEqual(numericJSON(state.model),numericJSON(model)),'State/model identity differs');
  return {jobId:id,engine:receipt.engine,verified:true,state};
 });
}
module.exports={...v2,evaluate,oracleAnswer,loadJobs,dynamicPhysicalView,numericJSON,activeView,provider,envelope,selectedModels,observe,physical,evidenceViews,emptyDefaults};
