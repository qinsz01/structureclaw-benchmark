'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const e=require('./evaluate-v32.cjs'),{comparisonView}=require('./audit-metadata-v32.cjs');
const {example}=require('./test-support-v32.cjs');
const {physical,staticPhysical}=require('./physical-v32.cjs');

test('v3.2 accepts independently specified cantilever observations without changing originals',()=>{
 const x=example(),before=structuredClone(x),result=e.evaluate(x.ref,x.answer,x.jobs);
 assert.equal(result.outcome,'passed',JSON.stringify(result));assert.deepEqual(x,before);
});
for(const [name,extra] of Object.entries({
 source:{source:'attachment:sections.csv'},provenance:{provenance:{properties:'user',propertyFields:{A:'attachment'}}},
 evidence:{evidence:{'properties.A':{evidenceId:'input-1',path:'/sections/0/A',unit:'m^2'}}},
 rule:{rules:{'properties.A':{sourceSectionId:'S',sourceField:'properties.A',factor:1,statement:'Use the issued area'}}},
 confirmation:{confirmation:{clarificationId:'q1',candidateIds:['choice-1']}},
 discarded:{discarded_nonuser_properties:{A:.02},discarded_table_properties:{Iy:.001},property_geometry_delta:{Iy:.0001}},
 diagnostic:{section_diagnostics:[{code:'SECTION_CATALOG_LABEL',severity:'info',message:{en:'Label only',zh:'仅标签'}}]},
}))test('recognized audit label is equivalent: '+name,()=>{
 const x=example(),m=x.jobs[0].state.model;m.sections[0].extra=extra;const before=structuredClone(m);
 assert.equal(physical(m,x.ref.model).pass,true);assert.equal(e.evaluate(x.ref,x.answer,x.jobs).outcome,'passed');
 assert.deepEqual(m,before);assert.ok(comparisonView(m).removed.length);
});

test('geometric cache annotations cannot change the executed section stiffness',()=>{
 const a=example().ref.model,b=structuredClone(a);a.sections[0].shape=b.sections[0].shape={kind:'rectangular',B:100,H:100};
 a.sections[0].extra={provenance:{properties:'geometry'},derived_properties:{method:'section-geometry-v1',fields:['A','Iy','Iz'],shape:structuredClone(a.sections[0].shape)}};
 assert.equal(physical(a,b).pass,true);a.sections[0].properties.Iy*=2;assert.equal(physical(a,b).pass,false);
});
for(const [name,change] of Object.entries({
 geometry:m=>m.nodes[1].x+=.01,stiffness:m=>m.materials[0].E*=.8,area:m=>m.sections[0].properties.A*=1.2,
 inertia:m=>m.sections[0].properties.Iy*=1.2,torsion:m=>m.sections[0].properties.J*=1.2,
 load:m=>m.load_cases[0].loads[0].fz*=1.2,support:m=>m.nodes[1].restraints[2]=true,
 gravity:m=>m.analysis_control.self_weight=true,unknownExtension:m=>m.sections[0].extra={newPhysicalOption:1},
}))test('audit labels do not waive wrong physics: '+name,()=>{
 const x=example();x.jobs[0].state.model.sections[0].extra={source:'issued source'};change(x.jobs[0].state.model);
 assert.equal(e.evaluate(x.ref,x.answer,x.jobs).outcome,'candidate_failure');
});

test('malformed audit label alone is reviewable and never counted as a pass',()=>{
 const x=example();x.jobs[0].state.model.sections[0].extra={provenance:{properties:'unrecognized-source'}};
 const result=e.evaluate(x.ref,x.answer,x.jobs);assert.equal(result.outcome,'needs_review');assert.equal(result.passed,false);
});
for(const [name,change] of Object.entries({
 stiffness:x=>x.jobs[0].state.model.materials[0].E*=.8,
 reportedValue:x=>x.answer.quantities[0].value*=2,
 nativeValue:x=>x.jobs[0].state.analysisResult.results['case:D'].data.displacements.B.uz*=2,
 missingEvidence:x=>x.jobs[0].verified=false,
}))test('unsupported audit labels cannot hide an independent candidate error: '+name,()=>{
 const x=example();x.jobs[0].state.model.sections[0].extra={provenance:{properties:'unrecognized-source'}};
 change(x);assert.equal(e.evaluate(x.ref,x.answer,x.jobs).outcome,'candidate_failure');
});

test('pure audit uncertainty does not throw on malformed model evidence',()=>{
 const x=example();delete x.jobs[0].state.model;
 assert.doesNotThrow(()=>e.evaluate(x.ref,x.answer,x.jobs));
 assert.equal(e.evaluate(x.ref,x.answer,x.jobs).outcome,'candidate_failure');
});
test('legal serial member refinement preserves the same physical problem',()=>{
 const b=example().ref.model,a=structuredClone(b),el=a.elements[0];
 a.nodes.push({id:'MID',x:1,y:0,z:0,restraints:[false,false,false,false,false,false]});
 a.elements=[{...el,id:'E1',nodes:['A','MID']},{...el,id:'E2',nodes:['MID','B']}];
 assert.equal(physical(a,b).pass,true);
 for(const change of [m=>m.nodes[2].restraints[2]=true,m=>m.nodes[2].mass=1,m=>m.nodes[2].z=.01,
  m=>m.elements[1].nodes=['A','B']]){const wrong=structuredClone(a);change(wrong);assert.equal(physical(wrong,b).pass,false);}
});
test('split uniform loads preserve force, first moment and spatial density, not only the resultant',()=>{
 const b=example().ref.model;b.load_cases[0].loads=[{type:'distributed',element:'E',wz:-1,start:0,end:2}];
 const a=structuredClone(b);a.load_cases[0].loads=[{type:'distributed',element:'E',wz:-1,start:0,end:1},{type:'distributed',element:'E',wz:-1,start:1,end:2}];
 assert.equal(physical(a,b).pass,true);
 a.load_cases[0].loads[0].wz=-.5;a.load_cases[0].loads[1].wz=-1.5;assert.equal(physical(a,b).pass,false);
});
test('nodal mass equivalence is restricted to uncoupled static analysis',()=>{
 const b=example().ref.model,a=structuredClone(b);a.nodes[1].mass=10;
 assert.equal(staticPhysical(a,b).pass,true);assert.equal(physical(a,b).pass,false);
});
