'use strict';
// Port of the frozen v3.1 mutation controls, applied to v3.2 only.
// The historical qualifier stays byte-identical. These are synthetic evaluator
// controls over saved native observations, never new executions or agent trials.
const e=require('./evaluate-v32.cjs'),clone=structuredClone;
function controls(ref,a,jobs,current){
 const rows=[],run=(name,b,js=jobs,expected=false)=>{const r=e.evaluate(ref,b,js,current);rows.push({name,scope:'full-evaluator',expected,actual:r.passed,passed:r.passed===expected,failures:r.metrics.filter(m=>!m.pass)});};
 run('missing-native-evidence',a,[]);
 const groupKey=ref.kind==='project'?'jobIdsByModel':'jobIdsByScenario';
 if(['project','analysis'].includes(ref.kind)){
  let b=clone(a);delete b[groupKey];run('missing-job-groups',b);
  b=clone(a);const metric=ref.kind==='project'?Object.values(b.metrics)[0]:Object.values(Object.values(b.metrics)[0])[0];metric.value+=Math.max(Math.abs(metric.value),1e-4);run('wrong-signed-global-value',b);
  b=clone(a);const metric2=ref.kind==='project'?Object.values(b.metrics)[0]:Object.values(Object.values(b.metrics)[0])[0];delete metric2.governingJoint;delete metric2.governingMember;run('missing-governing-location',b);
  b=clone(a);const metric3=ref.kind==='project'?Object.values(b.metrics)[0]:Object.values(Object.values(b.metrics)[0])[0];metric3.selection.id='UNISSUED';run('wrong-governing-selection',b);
  b=clone(a);const metric4=ref.kind==='project'?Object.values(b.metrics)[0]:Object.values(Object.values(b.metrics)[0])[0];metric4.value*=1000;metric4.unit='mm';run('legal-unit-conversion',b,jobs,true);
  b=clone(a);const metric5=ref.kind==='project'?Object.values(b.metrics)[0]:Object.values(Object.values(b.metrics)[0])[0];metric5.unit='kN';run('dimensionally-wrong-unit',b);
  // A coordinated native/report sign error used to preserve the absolute
  // envelope. Independent signed checks must reject it even when they agree.
  const nativeSign=clone(jobs),signAnswer=clone(a);
  for(const j of nativeSign)for(const entry of Object.values(j.state.analysisResult.results||{}))for(const d of Object.values(entry.data.displacements||{}))for(const key of ['ux','uy','uz'])if(typeof d[key]==='number')d[key]*=-1;
  if(ref.kind==='analysis')for(const scenario of Object.values(signAnswer.metrics))scenario.uz.value*=-1;
  else{signAnswer.metrics.upperVertical.value*=-1;signAnswer.metrics.primaryVertical.value*=-1;
   if(ref.integration==='rigid')for(const block of signAnswer.transfers)for(const v of block.values){v.ux*=-1;v.uz*=-1;}}
  run('correlated-native-and-reported-displacement-sign',signAnswer,nativeSign);
  if(ref.kind==='project'){
   b=clone(a);b.feasible=!b.feasible;run('wrong-feasibility',b);
   b=clone(a);b.volume.value*=1.2;run('wrong-geometric-objective',b);
   b=clone(a);b.transfers[0].values[0][ref.integration==='rigid'?'uz':'fz']+=10;run('wrong-interface-value',b);
   b=clone(a);b.design.G0='UNISSUED';run('illegal-design',b);
   if(ref.integration==='one-way'){
    const nativeReaction=clone(jobs),reactionAnswer=clone(a),ids=new Set(a.jobIdsByModel.upper);
    for(const j of nativeReaction)if(ids.has(j.jobId))for(const entry of Object.values(j.state.analysisResult.results||{}))for(const r of Object.values(entry.data.reactions||{}))for(const key of ['fx','fz'])if(typeof r[key]==='number')r[key]*=-1;
    for(const block of reactionAnswer.transfers)for(const v of block.values){v.fx*=-1;v.fz*=-1;}
    run('correlated-native-and-reported-transfer-sign',reactionAnswer,nativeReaction);
   }
  }
 }else if(a.quantities?.length){
  let b=clone(a);b.quantities[0].value+=Math.max(Math.abs(b.quantities[0].value),1);run('wrong-reported-quantity',b);
  b=clone(a);delete b.quantities;run('missing-quantity-report',b);
  if(ref.massRule){b=clone(a);delete b.massTotal;run('missing-derived-mass',b);}
 }
 // These mutations are evaluator controls, never new native executions.
 if(jobs.length){
  const corrupted=clone(jobs);for(const j of corrupted)j.state.model.materials[0].E*=.8;run('wrong-executed-stiffness',a,corrupted);
  const support=clone(jobs);for(const j of support)j.state.model.nodes[0].restraints[0]=!j.state.model.nodes[0].restraints[0];run('wrong-executed-support',a,support);
  const loads=clone(jobs);let changed=false;for(const j of loads)for(const c of j.state.model.load_cases)if(c.id==='D')for(const l of c.loads)for(const k of ['fx','fy','fz','mx','my','mz','wx','wy','wz'])if(l[k]){l[k]*=1.3;changed=true;}
  if(changed&&['analysis','project','static','query'].includes(ref.kind))run('wrong-active-dead-load',a,loads);
  const gravity=clone(jobs);for(const j of gravity)j.state.model.analysis_control.self_weight=!j.state.model.analysis_control.self_weight;run('duplicate-or-missing-automatic-gravity',a,gravity);
 }
 return rows;
}
module.exports={controls};
