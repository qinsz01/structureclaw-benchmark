'use strict';
// Continuous observations from sealed candidate executions. This is a read-only
// diagnostic, not an alternative score or a repaired candidate answer.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {context}=require('./audit_codex_full_controls_v32.cjs');
const e=require('./evaluate-v32.cjs');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const finite=x=>typeof x==='number'&&Number.isFinite(x);
const assert=(ok,message)=>{if(!ok)throw Error(message);};
const units={m:['length',1],mm:['length',.001],rad:['angle',1],mrad:['angle',.001],
 kN:['force',1],N:['force',.001],'kN.m':['moment',1],'kN*m':['moment',1],'kN·m':['moment',1],
 'N.m':['moment',.001],'N*m':['moment',.001],'kN.mm':['moment',.001],'N.mm':['moment',1e-6],
 s:['time',1],Hz:['frequency',1],tonne:['mass',1],kg:['mass',.001],'m^3':['volume',1],m3:['volume',1]};
function value(row,to){assert(row&&finite(row.value)&&units[row.unit]?.[0]===units[to]?.[0]&&units[to],'Invalid finite value or unit');return row.value*units[row.unit][1]/units[to][1];}
const key=s=>s.kind+':'+s.id;
function measureTurn(x,c,t){
 const score=x.diagnostic.rows.find(r=>r.caseId===c.id&&r.turnId===t.id),ref=JSON.parse(fs.readFileSync(path.join(x.edition,t.private))),
  result={caseId:c.id,turnId:t.id,engine:c.engine,level:c.level,family:c.family,kind:ref.kind,outcome:score.outcome,
   originalAnswerSha256:score.originalAnswerSha256,observations:[],unavailable:[]};
 const absent=(metric,comparison,reason)=>result.unavailable.push({metric,comparison,status:'unavailable',reason});
 const compare=(metric,comparison,actual,expected,unit,tolerance,extra={})=>{
  assert(finite(actual)&&finite(expected)&&finite(tolerance.absolute)&&finite(tolerance.relative),'Nonfinite observation');
  const absoluteError=Math.abs(actual-expected),limit=tolerance.absolute+tolerance.relative*Math.abs(expected);
  result.observations.push({metric,comparison,actual,expected,unit,absoluteError,
   relativeError:expected===0?null:absoluteError/Math.abs(expected),tolerance,allowedError:limit,
   errorOverTolerance:limit===0?(absoluteError===0?0:null):absoluteError/limit,withinTolerance:absoluteError<=limit,...extra});
 };
 let captured,jobs;
 try{captured=x.reader.readAnswer(c.id,t.id);jobs=e.evidenceViews(captured.jobs);result.captureResolved=true;}
 catch(error){result.captureResolved=false;absent('all','native/reference/report',error.code||error.message);return result;}
 const a=captured.answer;
 function providers(model,selections,ids){
  assert(Array.isArray(ids)&&ids.length,'No bound execution group');
  const group=ids.map(id=>{const j=jobs.find(j=>j.jobId===id);assert(j,'Unbound execution');return j;});
  return selections.map(selection=>e.provider(model,selection,group));
 }
 function at(model,ps,type,row,ids,idMap){
  assert(row&&row.selection,'Missing governing selection');
  const p=ps.find(p=>key(p.selection)===key(row.selection));assert(p,'Unissued governing selection');
  if(type==='force'){
   const id=idMap?.[row.governingMember]||row.governingMember,member=model.elements.find(m=>m.id===id);
   assert(member&&(!ids||ids.has(id)),'Governing member outside requested scope');
   assert(finite(row.positionM)&&['left','right'].includes(row.side),'Missing cut position/side');
   return p.read({kind:'member',id,positionM:row.positionM,side:row.side},row.component);
  }
  const id=idMap?.[row.governingJoint]||row.governingJoint;
  assert(model.nodes.some(n=>n.id===id)&&(!ids||ids.has(id)),'Governing joint outside requested scope');
  const loc={kind:'node',id};return type==='lateral'?Math.hypot(p.read(loc,'ux'),model.coordinate_system.dimension==='3d'?p.read(loc,'uy'):0):p.read(loc,'uz');
 }
 function globalMetric(name,model,ps,type,truth,report,ids,idMap){
  const native=e.envelope(model,ps,type,ids),unit=native.unit,tol={absolute:unit==='m'?1e-8:1e-6,relative:1e-6};
  compare(name,'native-global-magnitude/reference',Math.abs(native.value),Math.abs(truth.value),unit,tol,{nativeLocation:native,referenceLocation:truth});
  try{compare(name,'native-signed-at-reference/reference',at(model,ps,type,truth,ids,idMap),truth.value,unit,tol);}
  catch(error){absent(name,'native-signed-at-reference/reference',error.message);}
  try{
   const observed=at(model,ps,type,report,ids,idMap);
   compare(name,'report/native-at-reported-location',value(report,unit),observed,unit,tol,{reportedLocation:report});
   compare(name,'reported-location-magnitude/native-global',Math.abs(observed),Math.abs(native.value),unit,tol);
  }catch(error){absent(name,'report/native-at-reported-location',error.message);}
 }
 if(['static','query','modal','transient'].includes(ref.kind)){
  let observed;
  try{
   // This existing projection reads protected native values after the same
   // physical checks. Only quantities are consumed; no generated answer is
   // saved, scored, sent to a candidate or substituted for the original.
   observed=e.oracleAnswer(ref,jobs).quantities;
   result.nativeProjectionAvailable=true;
  }catch(error){result.nativeProjectionAvailable=false;absent('all-required-quantities','native/reference/report',error.message);return result;}
  for(const q of ref.requests){
   const native=observed.find(r=>r.id===q.id),reported=a.quantities?.find(r=>r.id===q.id);
   if(!native){absent(q.id,'native/reference','Quantity is not included in the native report projection');continue;}
   compare(q.id,'native/reference',value(native,q.unit),q.value,q.unit,q.tolerance);
   try{compare(q.id,'report/native',value(reported,q.unit),value(native,q.unit),q.unit,q.tolerance);}
   catch(error){absent(q.id,'report/native',error.message);}
   if(q.time!==undefined){
    if(finite(native.time))compare(q.id+'.peakTime','native/reference',native.time,q.time,'s',{absolute:1e-9,relative:0});
    else absent(q.id+'.peakTime','native/reference','Native peak time unavailable');
    if(finite(native.time)&&finite(reported?.time))compare(q.id+'.peakTime','report/native',reported.time,native.time,'s',{absolute:1e-9,relative:0});
    else absent(q.id+'.peakTime','report/native','Reported or native peak time unavailable');
   }
  }
 }else if(ref.kind==='analysis'){
  for(const scenario of ref.scenarios){
   let ps;
   try{ps=providers(scenario.model,scenario.selections,a.jobIdsByScenario?.[scenario.id]);}
   catch(error){for(const type of ['uz','lateral','force'])absent(scenario.id+'.'+type,'native/reference/report',error.message);continue;}
   for(const type of ['uz','lateral','force'])try{globalMetric(scenario.id+'.'+type,scenario.model,ps,type,scenario.metrics[type],a.metrics?.[scenario.id]?.[type]);}
   catch(error){absent(scenario.id+'.'+type,'native/reference/report',error.message);}
  }
 }else if(ref.kind==='project'){
  try{
   const id=['G0','G1','G2'].map(g=>a.design?.[g]).join('-'),truth=ref.truths.find(t=>t.id===id);assert(truth,'Candidate selected an unissued design');
   const models=e.selectedModels(ref,truth),ps={};
   for(const role of Object.keys(models))ps[role]=providers(models[role],ref.requirements[role+'Selections']||[],a.jobIdsByModel?.[role]);
   const rigid=ref.integration==='rigid',map=ref.combinedMapping,upper=rigid?ps.combined:ref.primaryTemplate.load_combinations.map(c=>({
    selection:{kind:'combination',id:c.id},read(loc,component){return Object.entries(c.factors).reduce((sum,[id,f])=>sum+f*ps.upper.find(p=>p.selection.id===id).read(loc,component),0);}}));
   result.selectedDesign=id;
   result.referenceDesignStatus={feasible:truth.feasible,globallyAccepted:(ref.optimalDesigns.length?ref.optimalDesigns:ref.leastViolationDesigns).includes(id)};
   for(const [name,role,type]of [['upperVertical','upper','uz'],['primaryVertical','primary','uz'],['primaryLateral','primary','lateral'],['primaryEndAction','primary','force']]){
    const label=role==='upper'?'U':'P',identity=rigid?map[label][type==='force'?'elements':'nodes']:undefined;
    try{globalMetric(name,rigid?models.combined:models[role],rigid?ps.combined:role==='upper'?upper:ps.primary,type,
     truth.metrics[name],a.metrics?.[name],identity?new Set(Object.values(identity)):undefined,identity);}
    catch(error){absent(name,'native/reference/report',error.message);}
   }
   for(const p of rigid?ps.combined:ps.upper)for(const link of ref.interface){
    const expected=truth.transfer.find(b=>key(b.selection)===key(p.selection))?.values.find(v=>v.upperSupport===link.upperSupport&&v.primaryJoint===link.primaryJoint),
     report=a.transfers?.find(b=>key(b.selection)===key(p.selection))?.values?.find(v=>v.upperSupport===link.upperSupport&&v.primaryJoint===link.primaryJoint);
    for(const component of rigid?['ux','uz']:['fx','fz']){
     const name='interface.'+key(p.selection)+'.'+link.upperSupport+'.'+component,unit=rigid?'m':'kN',tol={absolute:rigid?1e-8:1e-6,relative:1e-6};
     try{
      const native=p.read({kind:'node',id:rigid?map.P.nodes[link.primaryJoint]:link.upperSupport},rigid?component:component==='fx'?'Fx':'Fz');
      compare(name,'native/reference',native,expected?.[component],unit,tol);
      if(finite(report?.[component]))compare(name,'report/native',report[component],native,unit,tol);
      else absent(name,'report/native','Missing finite interface report');
     }catch(error){absent(name,'native/reference/report',error.message);}
    }
   }
   try{compare('material-volume','report/reference-geometry',value(a.volume,'m^3'),truth.volume,'m^3',{absolute:1e-10,relative:1e-7});}
   catch(error){absent('material-volume','report/reference-geometry',error.message);}
  }catch(error){absent('all-project-observations','native/reference/report',error.message);}
 }else absent('all','native/reference/report','Unsupported measurement projection');
 return result;
}
function main(){
 const [edition,work,pinPath,pinSha256,diagnosticPath,output]=process.argv.slice(2),x=context({edition,work,pinPath,pinSha256,diagnosticPath}),rows=[];
 for(const c of x.manifest.cases)for(const t of c.turns)rows.push(measureTurn(x,c,t));
 assert(rows.length===560,'Full measurement denominator required');
 const observed=rows.flatMap(r=>r.observations),groups={};
 for(const row of observed){const k=row.comparison+' / '+row.unit,g=groups[k]||={observations:0,withinTolerance:0,maxAbsoluteError:0,maxErrorOverTolerance:0};
  g.observations++;g.withinTolerance+=row.withinTolerance;g.maxAbsoluteError=Math.max(g.maxAbsoluteError,row.absoluteError);g.maxErrorOverTolerance=Math.max(g.maxErrorOverTolerance,row.errorOverTolerance||0);}
 const result={kind:'research300-v32-full-continuous-observations',formalComparisonScore:false,candidateInvocations:0,nativeSolverInvocations:0,
  originalAnswersModified:false,originalGradesModified:false,cases:300,turns:560,
  turnsWithObservations:rows.filter(r=>r.observations.length).length,turnsWithUnavailableItems:rows.filter(r=>r.unavailable.length).length,
  observations:observed.length,withinTolerance:observed.filter(r=>r.withinTolerance).length,groups,rows,
  operatorPinSha256:pinSha256,diagnosticSha256:sha(fs.readFileSync(diagnosticPath)),measurementSourceSha256:sha(fs.readFileSync(__filename)),
  scope:'Required reported scalar native quantities, signed global-governing checks and project interfaces. Unavailable or physically unmatched observations are not assigned zero error. Aggregates describe available observations only; all 560 turn rows remain. Modal MAC, complete histories and all decision fields remain in the frozen evaluator, not these scalar summaries.'};
 fs.writeFileSync(output,JSON.stringify(result,null,2)+'\n',{flag:'wx'});
 process.stdout.write(JSON.stringify({turns:560,observations:result.observations,withinTolerance:result.withinTolerance,turnsWithUnavailableItems:result.turnsWithUnavailableItems})+'\n');
}
if(require.main===module)try{main();}catch(error){process.stderr.write(error.stack+'\n');process.exitCode=2;}
module.exports={measureTurn};
