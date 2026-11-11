'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const e=require('./evaluate-v31.cjs'),{physical}=require('./physical-v31.cjs');
const {axesFor}=require('../../lib/physical-model-fidelity.cjs');
function model(){
 const m=JSON.parse(fs.readFileSync(path.join(__dirname,'../../corpora/research300-v2-v1/cases/V2-STD-001/private/t1.json'))).model;
 m.stories=[];for(const row of [...m.nodes,...m.elements])delete row.story;
 return m;
}
test('empty optional element extras are equivalent, nonempty extensions remain bound',()=>{
 const b=model(),a=structuredClone(b);for(const el of a.elements)el.extra={};
 assert.equal(physical(a,b).pass,true);a.elements[0].extra={eccentricity:0};assert.equal(physical(a,b).pass,false);
});
test('exact SDK gravity defaults are equivalent with self-weight active or inactive',()=>{
 const b=model(),a=structuredClone(b);a.analysis_control.gravity_m_s2=9.80665;a.analysis_control.gravity_direction='-z';
 assert.equal(physical(a,b).pass,true);a.analysis_control.gravity_m_s2=9.7;assert.equal(physical(a,b).pass,false);
 a.analysis_control.gravity_m_s2=9.80665;a.analysis_control.self_weight=true;assert.equal(physical(a,b).pass,false);
 b.analysis_control.self_weight=true;assert.equal(physical(a,b).pass,true);
 a.analysis_control.gravity_m_s2=9.7;assert.equal(physical(a,b).pass,false);
});
test('inactive natural-story grouping cannot replace physical geometry or active floor controls',()=>{
 const b=model(),a=structuredClone(b);a.stories=[{id:'group',elevation:0,height:8,rigid_diaphragm:false,floor_loads:[]}];
 for(const row of [...a.nodes,...a.elements])row.story='group';
 assert.equal(physical(a,b).pass,true);
 for(const change of [m=>m.nodes.at(-1).z+=.1,m=>m.stories[0].rigid_diaphragm=true,
  m=>m.stories[0].floor_loads=[{pressure:1}],m=>m.analysis_control.rigid_floor=true,
  m=>m.stories[0].extra={seismic_mass:1}]){
  const wrong=structuredClone(a);change(wrong);assert.equal(physical(wrong,b).pass,false);
 }
});
test('explicit-nodal dynamics compares every mass and stiffness, without unused static bookkeeping',()=>{
 const b=model();Object.assign(b.analysis_control,{mass_source:'nodal',mass_directions:['x']});b.nodes.at(-1).mass=2;
 const a=structuredClone(b);a.load_cases=[];a.load_combinations=[];
 assert.equal(physical(e.dynamicPhysicalView(a),e.dynamicPhysicalView(b)).pass,true);
 const wrongMass=structuredClone(a);wrongMass.nodes.at(-1).mass=3;
 assert.equal(physical(e.dynamicPhysicalView(wrongMass),e.dynamicPhysicalView(b)).pass,false);
 const wrongE=structuredClone(a);wrongE.materials[0].E*=.8;
 assert.equal(physical(e.dynamicPhysicalView(wrongE),e.dynamicPhysicalView(b)).pass,false);
 assert.equal(physical(a,b).pass,false);
 const active=structuredClone(b);active.analysis_control.self_weight=true;
 assert.deepEqual(e.dynamicPhysicalView(active).load_cases,active.load_cases);
});
test('mass is inactive only for explicitly uncoupled static comparison',()=>{
 const {staticPhysical}=require('./physical-v31.cjs'),b=model(),a=structuredClone(b);for(const n of a.nodes)n.mass=2;
 assert.equal(staticPhysical(a,b).pass,true);assert.equal(physical(a,b).pass,false);
 a.analysis_control.p_delta=true;assert.equal(staticPhysical(a,b).pass,false);
});
test('mixed truss and bending results do not require fictional truss cut axes',()=>{
 const m=model(),el=m.elements[0];el.offsets={};const basis=axesFor(m,el);
 m.elements.push({id:'axial',type:'truss',nodes:el.nodes,material:el.material,section:el.section,offsets:{}});
 const vector={N:2,V2:3,V3:4,T:5,M2:6,M3:7};
 const data={meta:{forceConvention:'element-end-resisting-actions',solverVersion:'fixture',execution:{executed:true,analysisReturnCode:0,constitutiveModel:'linear-elastic',solverConfiguration:{algorithm:'Linear'}}},
  memberResponses:[{id:el.id,state:'interpolated',reason:'consistency',axes:basis},{id:'axial',state:'truss',reason:'checked',samples:[{x:0,N:2}]}],
  forces:{[el.id]:{responseCoordinateConvention:'global-xyz',referenceFrame:'element-local',source:{kind:'solver-direct'},n1:vector,n2:vector}}};
 const job={state:{model:m,analysisResult:{results:{'case:D':{data,meta:{modelHash:'fixture',settingsHash:'fixture'}}}}}};
 const before=structuredClone(job),view=e.evidenceViews([job])[0].state.analysisResult.results['case:D'].data;
 assert.equal(view.memberStations[el.id][0].components.My,-6);assert.equal(view.memberStations.axial,undefined);assert.deepEqual(job,before);
 const explicit=structuredClone(job);explicit.state.model.elements[0].offsets={i_x:0,i_y:0,i_z:0,j_x:0,j_y:0,j_z:0};
 assert.equal(e.evidenceViews([explicit])[0].state.analysisResult.results['case:D'].data.memberStations[el.id][0].components.My,-6);
 for(const offsets of [{i_x:.001},{unknown:0}]){
  const offset=structuredClone(job);offset.state.model.elements[0].offsets=offsets;
  assert.equal(e.evidenceViews([offset])[0].state.analysisResult.results['case:D'].data.memberStations,undefined);
 }
 const wrong=structuredClone(job);wrong.state.analysisResult.results['case:D'].data.memberResponses[0].axes=[[1,0,0],[0,0,0],[0,0,1]];
 assert.throws(()=>e.evidenceViews([wrong]),/axes/);
});
