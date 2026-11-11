'use strict';
// Preserve the frozen pilot's planar/active-property policy. Only v3 uses the
// distributed-position fix; historical evaluators and their source stay intact.
const core=require('./fidelity.cjs');
const {axesFor}=require('../../lib/physical-model-fidelity.cjs');
const {comparisonView}=require('../challenge/physical-view-v2.cjs');
const {closedPlanarDomain,liftPlanar}=require('../challenge/physical-view-v3.cjs');
const clone=structuredClone;
function comparePhysicalModels(actual,expected,options){
 if(actual.coordinate_system?.dimension!==expected.coordinate_system?.dimension&&closedPlanarDomain(actual)&&closedPlanarDomain(expected)){actual=liftPlanar(actual);expected=liftPlanar(expected);}
 const inactive=[actual,expected].every(m=>['self_weight','rigid_floor','p_delta','rigid_offsets','construction_stage'].every(k=>m.analysis_control?.[k]===false));
 return core.comparePhysicalModels(comparisonView(actual,inactive),comparisonView(expected,inactive),options);
}
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

module.exports={physical};
