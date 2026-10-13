const test=require('node:test');
const assert=require('node:assert/strict');
const {comparePhysicalModels}=require('./physical-model-fidelity.cjs');
const clone=v=>JSON.parse(JSON.stringify(v));
function model() {
  return {schema_version:'2.0.0',unit_system:'SI',coordinate_system:{semantics:'global-z-up',version:1,dimension:'2d',plane:'xz',dof_order:['ux','uy','uz','rx','ry','rz']},
    nodes:[{id:'a',x:0,y:0,z:0,restraints:[true,true,true,true,false,true]},{id:'b',x:6,y:0,z:0,restraints:[false,true,true,true,false,true]}],
    elements:[{id:'beam',type:'beam',nodes:['a','b'],material:'steel',section:'s'}],
    materials:[{id:'steel',E:200000,nu:.3,rho:7850}],sections:[{id:'s',type:'beam',properties:{A:.02,Iy:.0001,Iz:.0002,J:.00005}}],
    load_cases:[{id:'D',type:'dead',loads:[{type:'distributed',element:'beam',wz:-10,start:1,end:5}]}],
    load_combinations:[{id:'ULS',factors:{D:1.3}}],stories:[],analysis_control:{self_weight:false,rigid_floor:false}};
}
function refined(reference) {
  const actual=clone(reference);actual.nodes.push({id:'mid',x:3,y:0,z:0});
  actual.elements=[{...actual.elements[0],id:'left',nodes:['a','mid']},{...actual.elements[0],id:'right',nodes:['mid','b']}];
  actual.load_cases[0].loads=[{type:'distributed',element:'left',wz:-10,start:1,end:3},{type:'distributed',element:'right',wz:-10,start:0,end:2}];
  return actual;
}
test('approved refinement compares physical load intervals and all assigned sections',()=>{
  const reference=model(),actual=refined(reference),result=comparePhysicalModels(actual,reference);
  assert.equal(result.pass,true,result.summary+' '+result.failures.join(','));
  assert.equal(result.diagnostics.elementSegments.beam.length,2);
  actual.sections.push({id:'wrong',type:'beam',properties:{A:.02,Iy:.00001,Iz:.0002,J:.00005}});
  actual.elements[1].section='wrong';assert.equal(comparePhysicalModels(actual,reference).pass,false);
});
test('node and element renumbering and reversed member orientation are allowed',()=>{
  const reference=model(),actual=model();
  actual.nodes[0].id='100';actual.nodes[1].id='200';actual.elements[0].id='99';actual.elements[0].nodes=['200','100'];
  actual.load_cases[0].id='dead';actual.load_cases[0].loads[0].element='99';actual.load_combinations[0].factors={dead:1.3};
  const result=comparePhysicalModels(actual,reference);assert.equal(result.pass,true,result.summary+' '+result.failures.join(','));
  assert.equal(result.diagnostics.elementOrientation.beam,'reversed');assert.equal(result.diagnostics.caseMapping.D,'dead');
});
test('point load on a solver refinement node equals a physical interior point load',()=>{
  const reference=model(),actual=refined(reference);
  reference.load_cases[0].loads=[{type:'point',element:'beam',position:3,fz:-20}];
  actual.load_cases[0].loads=[{node:'mid',fz:-20}];
  const result=comparePhysicalModels(actual,reference);assert.equal(result.pass,true,result.summary+' '+result.failures.join(','));
});
for(const [name,mutate] of [
  ['support',m=>m.nodes[2].restraints=[false,false,true,false,false,false]],
  ['connectivity',m=>m.elements[1].nodes=['a','b']],
  ['load position',m=>m.load_cases[0].loads[1].end=1.5],
  ['load sign',m=>m.load_cases[0].loads[1].wz=10],
  ['missing case',m=>{m.load_cases=[];m.load_combinations=[];}],
  ['combination',m=>m.load_combinations[0].factors.D=1.5],
  ['self weight',m=>m.analysis_control.self_weight=true],
]) test(`wrong ${name} fails rather than using visual similarity`,()=>{
  const reference=model(),actual=refined(reference);mutate(actual);assert.equal(comparePhysicalModels(actual,reference).pass,false);
});
test('redistributing loads between distinct cases cannot pass on equal aggregate loads',()=>{
  const reference=model();reference.load_cases.push({id:'L',type:'live',loads:[{node:'b',fx:5}]});
  const actual=clone(reference);[actual.load_cases[0].loads,actual.load_cases[1].loads]=[actual.load_cases[1].loads,actual.load_cases[0].loads];
  assert.equal(comparePhysicalModels(actual,reference).pass,false);
});
test('compatible minor version and optional null material strengths preserve physics',()=>{
  const reference=model(),actual=model();actual.schema_version='2.1.0';actual.materials[0].fy=null;actual.materials[0].fc=null;
  const result=comparePhysicalModels(actual,reference);assert.equal(result.pass,true,result.failures.join(';'));
});
module.exports={model,refined};
