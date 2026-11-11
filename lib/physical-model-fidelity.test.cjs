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
test('StructureModelV2 material migration and empty default dictionaries preserve model identity',()=>{
  const reference=model();reference.materials[0].type='steel';
  const actual=clone(reference);delete actual.materials[0].type;actual.materials[0].category='steel';
  actual.materials[0].extra={};actual.sections[0].extra={};
  const before=clone(actual);
  for(const [a,e] of [[actual,reference],[reference,actual]]) {
    const result=comparePhysicalModels(a,e);assert.equal(result.pass,true,result.failures.join(';'));
  }
  assert.deepEqual(actual,before,'native evidence is not modified');
});
test('material aliases cannot hide conflicts, category changes or nonempty extra fields',()=>{
  const reference=model();reference.materials[0].type='steel';
  for(const mutate of [
    m=>m.materials[0].category='concrete',
    m=>{delete m.materials[0].type;m.materials[0].category='concrete';},
    m=>m.materials[0].type='elastic',
    m=>m.materials[0].extra={stiffness_factor:.5},
    m=>m.sections[0].extra={stiffness_factor:.5},
    m=>m.sections[0].extra=[],
  ]) {
    const actual=clone(reference);mutate(actual);
    assert.equal(comparePhysicalModels(actual,reference).pass,false);
    assert.equal(comparePhysicalModels(reference,actual).pass,false);
  }
});
test('explicit elastic properties can represent a section without unavailable shape/category metadata',()=>{
  const reference=model();reference.materials[0].G=76923;reference.materials[0].category='steel';
  reference.sections[0].shape={kind:'rectangular',B:100,H:200};
  const actual=clone(reference);delete actual.sections[0].shape;delete actual.materials[0].category;
  assert.equal(comparePhysicalModels(actual,reference).pass,false,'strict archival comparison stays strict');
  for(const [a,e] of [[actual,reference],[reference,actual]]) {
    const r=comparePhysicalModels(a,e,{explicitElasticProperties:true});assert.equal(r.pass,true,r.failures.join(';'));
  }
  const generic=clone(actual);generic.sections[0].type='custom';
  assert.equal(comparePhysicalModels(generic,reference,{explicitElasticProperties:true}).pass,true);
  for(const mutate of [
    m=>delete m.sections[0].properties.J,
    m=>m.sections[0].properties.Iy*=.9,
    m=>delete m.materials[0].G,
    m=>m.materials[0].E*=.9,
    m=>m.materials[0].category='concrete',
    m=>m.sections[0].shape={kind:'rectangular',B:999,H:200},
    m=>m.sections[0].type='circular',
    m=>m.sections[0].extra={stiffness_factor:.5},
  ]) {
    const bad=clone(actual);mutate(bad);
    assert.equal(comparePhysicalModels(bad,reference,{explicitElasticProperties:true}).pass,false);
  }
});
test('complete elasticity permits an omitted unsupported legacy material description without accepting a contradictory class',()=>{
  const reference=model();reference.materials[0].G=76923;reference.materials[0].type='aluminium';
  const actual=clone(reference);delete actual.materials[0].type;
  assert.equal(comparePhysicalModels(actual,reference).pass,false,'strict historical comparison stays strict');
  for(const category of [undefined,'other']) {
    const candidate=clone(actual);if(category)candidate.materials[0].category=category;
    for(const [a,e] of [[candidate,reference],[reference,candidate]])assert.equal(comparePhysicalModels(a,e,{explicitElasticProperties:true}).pass,true);
  }
  for(const mutate of [m=>m.materials[0].category='steel',m=>m.materials[0].type='wood',m=>m.materials[0].E*=.9,m=>delete m.materials[0].G]) {
    const bad=clone(actual);mutate(bad);assert.equal(comparePhysicalModels(bad,reference,{explicitElasticProperties:true}).pass,false);
  }
});
test('project labels and a redundant explicit-frame classification do not add physics or hide design parameters',()=>{
  const reference=model();reference.elements[0].type='beam';
  reference.nodes.push({id:'c',x:6,y:0,z:3,restraints:[false,true,false,true,false,true]});
  reference.elements.push({...reference.elements[0],id:'column',type:'column',nodes:['b','c']});
  const actual=clone(reference);actual.project={name:'candidate project'};actual.structure_system={type:'frame'};
  const before=clone(actual),options={explicitElasticProperties:true};
  assert.equal(comparePhysicalModels(actual,reference).pass,false,'strict archival comparison unchanged');
  for(const [a,e] of [[actual,reference],[reference,actual]])assert.equal(comparePhysicalModels(a,e,options).pass,true);
  assert.deepEqual(actual,before,'actual submitted evidence is preserved');
  for(const change of [m=>m.project.code_standard='different',m=>m.project.extra={stiffness:.9},
    m=>m.structure_system.seismic_grade='first',m=>m.structure_system.type='braced-frame',
    m=>m.structure_system.extra={rigid_floor:true},m=>m.elements[1].type='truss']) {
    const bad=clone(actual);change(bad);assert.equal(comparePhysicalModels(bad,reference,options).pass,false);
  }
});
test('rectangular default shear areas and correct purpose are equivalent only with their actual assigned properties',()=>{
  const reference=model();reference.materials[0].G=76923;
  reference.sections[0].shape={kind:'rectangular',B:100,H:200};
  const actual=clone(reference),s=actual.sections[0];s.purpose='beam';s.properties.Asy=s.properties.Asz=5*s.properties.A/6;
  const before=clone(actual),options={explicitElasticProperties:true};
  assert.equal(comparePhysicalModels(actual,reference).pass,false);
  for(const [a,e] of [[actual,reference],[reference,actual]])assert.equal(comparePhysicalModels(a,e,options).pass,true);
  assert.deepEqual(actual,before);
  for(const change of [m=>m.sections[0].properties.Asy*=.9,m=>m.sections[0].properties.Asz*=.9,m=>m.sections[0].purpose='column',m=>m.sections[0].shape.kind='circular']) {
    const bad=clone(actual);change(bad);assert.equal(comparePhysicalModels(bad,reference,options).pass,false);
  }
});
test('a material grade matching the opposite explicit material name cannot invent a new grade',()=>{
  const reference=model();reference.materials[0].G=76923;reference.materials[0].name='C30';
  const actual=clone(reference);actual.materials[0].grade='C30';const options={explicitElasticProperties:true},before=clone(reference);
  for(const [a,e] of [[actual,reference],[reference,actual]])assert.equal(comparePhysicalModels(a,e,options).pass,true);
  assert.deepEqual(reference,before);
  for(const mutate of [m=>m.materials[0].grade='C40',m=>m.materials[0].E*=.9,m=>m.materials[0].grade='arbitrary']) {
    const bad=clone(actual);mutate(bad);assert.equal(comparePhysicalModels(bad,reference,options).pass,false);
  }
});
test('redundant story assignments require matching inactive floors and geometrically correct member membership',()=>{
  const reference=model();reference.nodes[0].z=reference.nodes[1].z=3;reference.materials[0].G=76923;
  Object.assign(reference.analysis_control,{p_delta:false,rigid_offsets:false,construction_stage:false});
  reference.stories=[{id:'s1',elevation:0,height:3,rigid_diaphragm:false},{id:'s2',elevation:3,height:3,rigid_diaphragm:false}];
  const actual=clone(reference);actual.elements[0].story='s1';actual.nodes[0].story='s1';const before=clone(actual),options={explicitElasticProperties:true};
  assert.equal(comparePhysicalModels(actual,reference).pass,false);
  for(const [a,e] of [[actual,reference],[reference,actual]])assert.equal(comparePhysicalModels(a,e,options).pass,true);
  assert.deepEqual(actual,before);
  for(const mutate of [m=>m.elements[0].story='s2',m=>m.nodes[0].story='s2',m=>m.stories[0].rigid_diaphragm=true,m=>m.stories[0].dead_load=1,m=>m.analysis_control.rigid_floor=true]) {
    const bad=clone(actual);mutate(bad);assert.equal(comparePhysicalModels(bad,reference,options).pass,false);
  }
});
test('an omitted inactive story table must be completely redundant with explicit node levels',()=>{
  const reference=model();reference.nodes.push({id:'top',x:6,y:0,z:3,restraints:[false,true,false,true,false,true]});
  reference.elements.push({...reference.elements[0],id:'column',type:'column',nodes:['b','top']});
  reference.stories=[{id:'s1',elevation:0,height:3,rigid_diaphragm:false}];
  Object.assign(reference.analysis_control,{p_delta:false,rigid_offsets:false,construction_stage:false});
  const actual=clone(reference);delete actual.stories;const before=clone(reference),options={explicitElasticProperties:true};
  for(const [a,e] of [[actual,reference],[reference,actual]])assert.equal(comparePhysicalModels(a,e,options).pass,true);
  assert.deepEqual(reference,before);
  for(const change of [m=>m.stories[0].dead_load=1,m=>m.stories[0].rigid_diaphragm=true,m=>m.stories[0].height=4,
    m=>m.elements[1].story='undefined-story',m=>m.stories[0].extra={rigid:true},m=>m.analysis_control.construction_stage=true]) {
    const declared=clone(reference);change(declared);assert.equal(comparePhysicalModels(actual,declared,options).pass,false);
  }
  const grouped=clone(reference);grouped.elements[1].story='s1';grouped.nodes[2].story='s1';
  assert.equal(comparePhysicalModels(actual,grouped,options).pass,true,'inactive native floor grouping preserves complete explicit geometry');
  grouped.nodes[2].z=4;
  assert.equal(comparePhysicalModels(actual,grouped,options).pass,false,'membership outside its declared interval is not a redundant grouping');
});
test('I section spelling aliases preserve every declared dimension and elastic property',()=>{
  const reference=model();reference.sections[0].type='i_section';reference.sections[0].shape={kind:'i_section',B:300,H:300,tw:10,tf:15};
  const actual=clone(reference);actual.sections[0].type='I';actual.sections[0].shape.kind='I';const before=clone(actual),options={explicitElasticProperties:true};
  for(const [a,e] of [[actual,reference],[reference,actual]])assert.equal(comparePhysicalModels(a,e,options).pass,true);
  assert.deepEqual(actual,before);
  for(const alias of ['H','h-section','h_section']) {
    const equivalent=clone(actual);equivalent.sections[0].type=alias;equivalent.sections[0].shape.kind=alias;
    assert.equal(comparePhysicalModels(equivalent,reference,options).pass,true,alias);
    equivalent.sections[0].shape.tw=12;
    assert.equal(comparePhysicalModels(equivalent,reference,options).pass,false,'H aliases cannot hide a changed web');
    delete equivalent.sections[0].shape.tw;
    assert.equal(comparePhysicalModels(equivalent,reference,options).pass,false,'H aliases cannot hide a missing web');
  }
  for(const change of [m=>m.sections[0].shape.tw=12,m=>m.sections[0].properties.J*=.9,m=>m.sections[0].shape.kind='box']) {
    const bad=clone(actual);change(bad);assert.equal(comparePhysicalModels(bad,reference,options).pass,false);
  }
});
test('explicitly disabled live-load reduction preserves unchanged authored loads without allowing activation',()=>{
  const reference=model(),actual=clone(reference);actual.analysis_control.live_load_reduction=false;
  assert.equal(comparePhysicalModels(actual,reference).pass,false,'strict archival comparison stays unchanged');
  assert.equal(comparePhysicalModels(actual,reference,{explicitElasticProperties:true}).pass,true);
  actual.analysis_control.live_load_reduction=true;
  assert.equal(comparePhysicalModels(actual,reference,{explicitElasticProperties:true}).pass,false);
  reference.analysis_control.live_load_reduction=true;actual.analysis_control.live_load_reduction=false;
  assert.equal(comparePhysicalModels(actual,reference,{explicitElasticProperties:true}).pass,false);
});
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
test('changed distributed endpoint intensities cannot disappear during canonicalization',()=>{
  const reference=model();reference.load_cases[0].loads=[{type:'distributed',element:'beam',wz_start:0,wz_end:-18}];
  const actual=clone(reference);actual.load_cases[0].loads[0].wz_end=-36;
  assert.equal(comparePhysicalModels(actual,reference).pass,false);
});
test('endpoint-linear loads agree across refinement, local axes and reversed orientation',()=>{
  const reference=model();reference.elements[0].rotation_angle=90;
  reference.load_cases[0].loads=[{type:'distributed',element:'beam',start:1,end:5,wx_start:2,wx_end:6,wz_start:-2,wz_end:-10}];
  const actual=refined(reference);actual.elements[1].nodes=['b','mid'];
  actual.load_cases[0].loads=[
    {type:'distributed',element:'left',variation:'linear',reference_frame:'element-local',start:1,end:3,wx_start:2,wx_end:4,wy_start:-2,wy_end:-6},
    {type:'distributed',element:'right',distribution:'linear',reference_frame:'element-local',start:1,end:3,wx_start:-6,wx_end:-4,wy_start:10,wy_end:6},
  ];
  const result=comparePhysicalModels(actual,reference);assert.equal(result.pass,true,result.failures.join(';'));
});
for(const [name,fields] of [
  ['missing endpoint',{wz_start:-10}],
  ['mixed endpoint and uniform component',{wz:-10,wz_start:-10,wz_end:-10}],
  ['non-finite endpoint',{wz_start:-10,wz_end:Infinity}],
  ['unequal uniform endpoints',{distribution:'uniform',wz_start:0,wz_end:-20}],
  ['conflicting variation',{variation:'linear',distribution:'uniform',wz_start:-10,wz_end:-10}],
]) test(`ambiguous distributed load fails closed: ${name}`,()=>{
  const reference=model(),actual=clone(reference);
  reference.load_cases[0].loads[0].wz=fields.wz??0;
  actual.load_cases[0].loads=[{type:'distributed',element:'beam',start:1,end:5,...fields}];
  assert.equal(comparePhysicalModels(actual,reference).pass,false);
});
test('load-case physical attributes survive renaming and reject changes or omission',()=>{
  const reference=model();reference.load_cases[0].self_weight_factor=1;
  const actual=refined(reference);actual.load_cases[0].id='dead';actual.load_cases[0].name='Renamed dead case';
  actual.load_combinations[0].factors={dead:1.3};
  const result=comparePhysicalModels(actual,reference);assert.equal(result.pass,true,result.failures.join(';'));
  actual.load_cases[0].self_weight_factor=0;
  assert.equal(comparePhysicalModels(actual,reference).pass,false,'changed factor');
  delete actual.load_cases[0].self_weight_factor;
  assert.equal(comparePhysicalModels(actual,reference).pass,false,'omitted factor');
  delete reference.load_cases[0].self_weight_factor;actual.load_cases[0].self_weight_factor=1;
  assert.equal(comparePhysicalModels(actual,reference).pass,false,'injected factor');
});
test('case identity mismatches are distinguished from changed signed loads',()=>{
  const reference=model(),actual=clone(reference);actual.load_cases[0].type='other';
  const result=comparePhysicalModels(actual,reference);assert.equal(result.pass,false);
  assert.match(result.failures.join(';'),/case type or attributes differ/);
  assert.doesNotMatch(result.failures.join(';'),/signed loads or physical positions differ/);
  actual.load_cases[0].loads[0].wz=-99;
  assert.match(comparePhysicalModels(actual,reference).failures.join(';'),/signed loads or physical positions differ/);
});
test('subdivision cannot inject mass on an interior solver node',()=>{
  const reference=model(),actual=refined(reference);
  actual.nodes[2].mass=100;
  const result=comparePhysicalModels(actual,reference);
  assert.equal(result.pass,false,'adding 100 units of nodal mass changes the physical model');
  assert.match(result.failures.join(';'),/mass/);
});
test('unrestrained refinement nodes may explicitly declare zero mass',()=>{
  const reference=model(),actual=refined(reference);actual.nodes[2].mass=0;
  const result=comparePhysicalModels(actual,reference);assert.equal(result.pass,true,result.failures.join(';'));
});
for(const [name,setup,mutate] of [
  ['material shear modulus',m=>m.materials[0].G=76923,m=>m.materials[0].G=1000],
  ['additional section stiffness',m=>m.sections[0].properties.Asy=.01,m=>m.sections[0].properties.Asy=.00001],
  ['injected section stiffness',()=>{},m=>m.sections[0].properties.Asy=.00001],
  ['support spring',m=>m.nodes[0].springs={ux:100},m=>m.nodes[0].springs.ux=10],
  ['refinement spring',()=>{},m=>m.nodes[2].springs={uz:100}],
  ['refinement member modifier',()=>{},m=>m.elements[1].stiffness_modifiers={bending:.1}],
  ['mass source',()=>{},m=>m.analysis_control.mass_source={D:1}],
  ['analysis setting',()=>{},m=>m.analysis_control.geometric_transformation='PDelta'],
]) test(`changed ${name} cannot escape physical comparison`,()=>{
  const reference=model();setup(reference);const actual=refined(reference);mutate(actual);
  assert.equal(comparePhysicalModels(actual,reference).pass,false,`${name} changes the declared physics`);
});
test('equal structured analysis settings are compared by value',()=>{
  const reference=model();reference.analysis_control.mass_source={cases:{D:1},include_element_mass:true};
  const actual=refined(reference),result=comparePhysicalModels(actual,reference);
  assert.equal(result.pass,true,result.failures.join(';'));
  actual.analysis_control.mass_source.cases.D=.5;
  assert.equal(comparePhysicalModels(actual,reference).pass,false);
});
test('2D section rotation changes anisotropic bending stiffness',()=>{
  const reference=model();reference.elements[0].rotation_angle=90;
  const actual=refined(reference),same=comparePhysicalModels(actual,reference);
  assert.equal(same.pass,true,same.failures.join(';'));
  actual.elements[1].rotation_angle=0;
  const result=comparePhysicalModels(actual,reference);
  assert.equal(result.pass,false,'one subdivision segment has the wrong bending axis');
  assert.match(result.failures.join(';'),/section axes/);
});
test('rotated 2D local loads are compared in global axes',()=>{
  const reference=model();reference.elements[0].rotation_angle=90;
  const actual=refined(reference);
  for(const load of actual.load_cases[0].loads) {load.wy=load.wz;delete load.wz;load.reference_frame='element-local';}
  const result=comparePhysicalModels(actual,reference);
  assert.equal(result.pass,true,result.failures.join(';'));
});
test('physically identical rotation of an isotropic section is allowed',()=>{
  const reference=model();reference.sections[0].properties.Iz=reference.sections[0].properties.Iy;
  const actual=refined(reference);actual.elements[1].rotation_angle=90;
  const result=comparePhysicalModels(actual,reference);assert.equal(result.pass,true,result.failures.join(';'));
});
test('story renaming preserves refinement but diaphragm changes fail',()=>{
  const reference=model();reference.stories=[{id:'roof',height:3,elevation:0,rigid_diaphragm:false}];
  for(const entity of [...reference.nodes,...reference.elements]) entity.story='roof';
  const actual=refined(reference);actual.stories[0].id='level1';
  for(const entity of [...actual.nodes,...actual.elements]) entity.story='level1';
  const result=comparePhysicalModels(actual,reference);
  assert.equal(result.pass,true,result.failures.join(';'));
  actual.stories[0].rigid_diaphragm=true;
  assert.equal(comparePhysicalModels(actual,reference).pass,false,'a diaphragm alters the kinematic constraints');
});
function unassignedStoryModel() {
  const reference=model();
  reference.stories=[{id:'roof',name:'Roof',height:3,elevation:3,rigid_diaphragm:false,dead_load:2,live_load:1},
    {id:'penthouse',height:2,elevation:5,rigid_diaphragm:true,floor_loads:[{type:'dead',value:1.5}]}];
  return reference;
}
test('unassigned story metadata permits identity, renaming and refinement',()=>{
  const reference=unassignedStoryModel();
  const identity=comparePhysicalModels(clone(reference),reference);
  assert.equal(identity.pass,true,identity.failures.join(';'));
  const actual=refined(reference);actual.stories.reverse();actual.stories[0].id='upper';actual.stories[1].id='lower';
  actual.stories[1].name='Renamed floor';
  const result=comparePhysicalModels(actual,reference);assert.equal(result.pass,true,result.failures.join(';'));
});
test('unassigned story geometry, loads, diaphragms and assignments remain bound',()=>{
  const reference=unassignedStoryModel();
  assert.equal(comparePhysicalModels(clone(reference),reference).pass,true,'unchanged metadata must be a valid control');
  for(const [name,mutate] of [
    ['height',m=>m.stories[0].height=4],
    ['elevation',m=>m.stories[0].elevation=4],
    ['floor load',m=>m.stories[0].dead_load=3],
    ['load omission',m=>delete m.stories[0].live_load],
    ['diaphragm',m=>m.stories[0].rigid_diaphragm=true],
    ['diaphragm omission',m=>delete m.stories[1].rigid_diaphragm],
    ['missing story',m=>m.stories.pop()],
    ['extra story',m=>m.stories.push({id:'extra',height:2,elevation:7})],
    ['node assignment',m=>m.nodes[0].story='roof'],
    ['element assignment',m=>m.elements[0].story='roof'],
  ]) {
    const actual=clone(reference);mutate(actual);
    assert.equal(comparePhysicalModels(actual,reference).pass,false,name);
  }
});
test('assigned and unassigned stories coexist without losing entity assignment checks',()=>{
  const reference=unassignedStoryModel();
  for(const entity of [...reference.nodes,...reference.elements]) entity.story='roof';
  const actual=refined(reference),result=comparePhysicalModels(actual,reference);
  assert.equal(result.pass,true,result.failures.join(';'));
  actual.nodes[0].story='penthouse';
  assert.equal(comparePhysicalModels(actual,reference).pass,false,'changed assignment');
  delete actual.nodes[0].story;
  assert.equal(comparePhysicalModels(actual,reference).pass,false,'missing assignment');
});
test('injected top-level constraints cannot bypass the line-model comparison',()=>{
  const reference=model(),actual=refined(reference);
  actual.constraints=[{type:'equalDOF',retained_node:'a',constrained_node:'mid',dofs:['ux']}];
  assert.equal(comparePhysicalModels(actual,reference).pass,false);
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

test('inactive default load category is equivalent only under an explicit caller policy and five disabled effects',()=>{
  const reference=model();Object.assign(reference.analysis_control,{p_delta:false,rigid_offsets:false,construction_stage:false});
  const actual=clone(reference);actual.load_cases[0].type='other';const options={inactiveLoadCaseClassification:true};
  assert.equal(comparePhysicalModels(actual,reference).pass,false);
  assert.equal(comparePhysicalModels(actual,reference,options).pass,true);
  delete actual.load_cases[0].type;assert.equal(comparePhysicalModels(actual,reference,options).pass,true);
  for(const mutate of [m=>m.load_cases[0].type='live',m=>m.analysis_control.self_weight=true,m=>delete m.analysis_control.p_delta,m=>m.load_cases[0].self_weight_factor=1,m=>m.load_cases[0].loads[0].wz=-99,m=>m.load_combinations[0].factors.D=1.4]) {
    const changed=clone(actual);mutate(changed);assert.equal(comparePhysicalModels(changed,reference,options).pass,false,String(mutate));
  }
});

test('documented drawing geometry in section extras must exactly match the counterpart shape',()=>{
  const reference=model();reference.materials[0].G=76923.076923;reference.sections[0].shape={kind:'rectangular',H:600,B:300};
  const actual=clone(reference);delete actual.sections[0].shape;actual.sections[0].extra={drawing_geometry_mm:clone(reference.sections[0].shape),source:'Original drawing dimensions retained for unsupported native shape'};
  const options={explicitElasticProperties:true};assert.equal(comparePhysicalModels(actual,reference,options).pass,true);
  for(const mutate of [m=>m.sections[0].extra.drawing_geometry_mm.H=700,m=>m.sections[0].extra.unknownStiffness=2,m=>m.sections[0].extra.source={factor:2},m=>m.sections[0].properties.Iy*=2]) {
    const changed=clone(actual);mutate(changed);assert.equal(comparePhysicalModels(changed,reference,options).pass,false,String(mutate));
  }
});

test('empty floor loads and verified inactive plan area do not change explicit 3D floor geometry',()=>{
  const reference=model();reference.coordinate_system.dimension='3d';reference.coordinate_system.plane=null;
  reference.nodes.push(...[[0,0],[6,0],[0,4],[6,4]].map(([x,y],i)=>({id:'p'+i,x,y,z:3,restraints:[false,false,false,false,false,false]})));
  reference.stories=[{id:'s1',elevation:0,height:3,rigid_diaphragm:false}];Object.assign(reference.analysis_control,{p_delta:false,rigid_offsets:false,construction_stage:false});
  const actual=clone(reference);Object.assign(actual.stories[0],{floor_loads:[],load_area_m2:24});const options={explicitElasticProperties:true};
  assert.equal(comparePhysicalModels(actual,reference,options).pass,true);
  for(const mutate of [m=>m.stories[0].load_area_m2=25,m=>m.stories[0].floor_loads=[{case:'D',value:1}],m=>m.stories[0].rigid_diaphragm=true,m=>m.analysis_control.rigid_floor=true]) {
    const changed=clone(actual);mutate(changed);assert.equal(comparePhysicalModels(changed,reference,options).pass,false,String(mutate));
  }
});

test('explicit zero floor pressures are inactive only with disabled automatic effects and no floor loads',()=>{
  const reference=model();reference.nodes.push({id:'top',x:6,y:0,z:3});reference.elements.push({...reference.elements[0],id:'column',type:'column',nodes:['b','top']});
  reference.stories=[{id:'s1',elevation:0,height:3,rigid_diaphragm:false}];Object.assign(reference.analysis_control,{p_delta:false,rigid_offsets:false,construction_stage:false});
  const actual=clone(reference);Object.assign(actual.stories[0],{dead_load:0,live_load:0,floor_loads:[]});const options={explicitElasticProperties:true};
  assert.equal(comparePhysicalModels(actual,reference,options).pass,true);
  for(const mutate of [m=>m.stories[0].dead_load=1,m=>m.stories[0].live_load=1,m=>m.analysis_control.rigid_floor=true]) {
    const changed=clone(actual);mutate(changed);assert.equal(comparePhysicalModels(changed,reference,options).pass,false,String(mutate));
  }
});

test('pinned OpenSees defaults and verified 2D axis notes require an explicit engine policy',()=>{
  const reference=model();Object.assign(reference.analysis_control,{p_delta:false,rigid_offsets:false,construction_stage:false});
  const actual=clone(reference);delete actual.analysis_control.rigid_offsets;delete actual.analysis_control.construction_stage;
  actual.analysis_control.consideration_torsion=true;actual.load_cases[0].type='other';actual.elements[0].extra={axis_reference_vector:[0,1,0]};
  const options={openSeesStaticDefaults:true,inactiveLoadCaseClassification:true};
  assert.equal(comparePhysicalModels(actual,reference).pass,false);
  assert.equal(comparePhysicalModels(actual,reference,options).pass,true);
  for(const mutate of [m=>m.analysis_control.rigid_offsets=true,m=>m.analysis_control.construction_stage=true,m=>m.analysis_control.self_weight=true,m=>m.analysis_control.consideration_torsion=false,m=>m.elements[0].extra.axis_reference_vector=[1,0,0],m=>m.elements[0].extra.unknown=1]) {
    const changed=clone(actual);mutate(changed);assert.equal(comparePhysicalModels(changed,reference,options).pass,false);
  }
  assert.equal(actual.analysis_control.rigid_offsets,undefined);
});
test('custom section geometry moved to schema extras must retain every numeric dimension',()=>{
  const reference=model();reference.materials[0].G=76923.076923;reference.sections[0].type='custom';
  reference.sections[0].shape={kind:'custom',description:'Unequal welded flanges',depth:400,width:300};
  const actual=clone(reference);actual.sections[0].shape={kind:'custom'};actual.sections[0].extra={description:'Same centroidal section',depth:400,width:300,section_diagnostics:[{code:'SECTION_GEOMETRY_UNVERIFIED',severity:'warning',message:{en:'Explicit geometry',zh:'显式几何'}}]};
  const options={explicitElasticProperties:true,property:1e-6};assert.equal(comparePhysicalModels(actual,reference,options).pass,true);
  for(const mutate of [m=>m.sections[0].extra.width=301,m=>delete m.sections[0].extra.depth,m=>m.sections[0].extra.unknown=1,m=>m.sections[0].properties.J*=2]) {
    const changed=clone(actual);mutate(changed);assert.equal(comparePhysicalModels(changed,reference,options).pass,false,String(mutate));
  }
});

test('approved roof refinement nodes preserve only verified inactive story grouping',()=>{
  const reference=model();reference.nodes.forEach(n=>n.z=3);reference.stories=[{id:'s',elevation:0,height:3,rigid_diaphragm:false}];
  Object.assign(reference.analysis_control,{p_delta:false,rigid_offsets:false,construction_stage:false});
  const actual=refined(reference);actual.nodes.find(n=>n.id==='mid').z=3;
  for(const e of [...actual.nodes,...actual.elements])e.story='s';const options={explicitElasticProperties:true};
  assert.equal(comparePhysicalModels(actual,reference,options).pass,true);
  const changed=clone(actual);changed.nodes.find(n=>n.id==='mid').story='unknown';
  assert.equal(comparePhysicalModels(changed,reference,options).pass,false);
});

test('numeric rectangular section source notes must prove geometry and default shear area',()=>{
  const reference=model();reference.materials[0].G=76923;reference.sections[0].type='rectangular';reference.sections[0].shape={kind:'rectangular',B:300,H:600};
  const actual=clone(reference);actual.sections[0].type='custom';delete actual.sections[0].shape;
  actual.sections[0].extra={sourceShape:{kind:'rectangular',B_mm:300,H_mm:600},representation:'Explicit numerical section, original geometry retained'};
  actual.sections[0].properties.Asy=actual.sections[0].properties.Asz=5*actual.sections[0].properties.A/6;
  const options={explicitElasticProperties:true,property:1e-6};assert.equal(comparePhysicalModels(actual,reference,options).pass,true);
  for(const mutate of [m=>m.sections[0].extra.sourceShape.B_mm=301,m=>m.sections[0].extra.sourceShape.unknown=1,m=>m.sections[0].properties.Asy*=.9,m=>m.sections[0].properties.J*=2]) {
    const changed=clone(actual);mutate(changed);assert.equal(comparePhysicalModels(changed,reference,options).pass,false);
  }
});

test('static analysis notes must match the designated theory and inactive explicit loading',()=>{
  const reference=model();Object.assign(reference.analysis_control,{p_delta:false,rigid_offsets:false,construction_stage:false});
  const actual=clone(reference);actual.analysis_control.extra={analysis_type:'linear_static',beam_theory:'Timoshenko',automatic_load_transfer:false,automatic_code_combinations:false};
  const options={explicitElasticProperties:true,staticTheory:'Timoshenko'};assert.equal(comparePhysicalModels(actual,reference,options).pass,true);
  assert.equal(comparePhysicalModels(actual,reference,{...options,staticTheory:'Euler-Bernoulli'}).pass,false);
  for(const mutate of [m=>m.analysis_control.extra.analysis_type='nonlinear',m=>m.analysis_control.extra.automatic_load_transfer=true,m=>m.analysis_control.extra.automatic_code_combinations=true,m=>m.analysis_control.extra.unknown=1]) {
    const changed=clone(actual);mutate(changed);assert.equal(comparePhysicalModels(changed,reference,options).pass,false);
  }
});

test('pre-roll 2D reference axes do not replace section roll',()=>{
  const reference=model();reference.elements[0].rotation_angle=90;
  const actual=clone(reference);actual.elements[0].extra={axis_reference_vector:[0,1,0]};
  const options={openSeesStaticDefaults:true};assert.equal(comparePhysicalModels(actual,reference,options).pass,true);
  for(const mutate of [m=>m.elements[0].rotation_angle=0,m=>m.elements[0].extra.axis_reference_vector=[0,0,1],m=>m.elements[0].extra.stiffness_factor=.5]) {
    const changed=clone(actual);mutate(changed);assert.equal(comparePhysicalModels(changed,reference,options).pass,false);
  }
});

test('3D reference-vector annotations must match the active metadata or default reference',()=>{
  const reference=model();reference.coordinate_system.dimension='3d';reference.coordinate_system.plane=null;
  const actual=clone(reference);actual.elements[0].extra={axis_reference_vector:[0,0,1]};
  const options={explicitElasticProperties:true};assert.equal(comparePhysicalModels(actual,reference,options).pass,true);
  for(const mutate of [m=>m.elements[0].extra.axis_reference_vector=[0,1,0],m=>m.elements[0].rotation_angle=90,m=>m.elements[0].extra.offset=1]) {
    const changed=clone(actual);mutate(changed);assert.equal(comparePhysicalModels(changed,reference,options).pass,false);
  }
  actual.metadata=reference.metadata={elementReferenceVectors:{beam:[0,1,0]}};
  assert.equal(comparePhysicalModels(actual,reference,options).pass,false);
  actual.elements[0].extra.axis_reference_vector=[0,1,0];
  assert.equal(comparePhysicalModels(actual,reference,options).pass,true);
});

test('numeric unequal-flange drawing notes retain all dimensions and the declared elastic theory',()=>{
  const reference=model();reference.materials[0].G=76923;reference.sections[0].type='H';
  reference.sections[0].shape={kind:'unequal-flange-I',H:500,Bpositive3:300,Bnegative3:200,tw:12,tf:20,centroidFromNegative3Edge:280.927835};
  const actual=clone(reference);actual.sections[0].type='custom';delete actual.sections[0].shape;
  actual.sections[0].extra={drawingType:'H',geometry_mm:Object.fromEntries(Object.entries(reference.sections[0].shape).filter(([k])=>k!=='kind')),formulation:'Supplied centroidal uncoupled Euler-Bernoulli A/Iy/Iz/J; no offsets'};
  const options={explicitElasticProperties:true,staticTheory:'Euler-Bernoulli'};
  assert.equal(comparePhysicalModels(actual,reference,options).pass,true);
  for(const mutate of [m=>m.sections[0].extra.geometry_mm.Bnegative3=300,m=>delete m.sections[0].extra.geometry_mm.tw,m=>m.sections[0].extra.geometry_mm.centroidFromNegative3Edge=250,m=>m.sections[0].extra.offset=1,m=>m.sections[0].extra.formulation='Use shear-center offsets',m=>m.sections[0].properties.J*=2]) {
    const changed=clone(actual);mutate(changed);assert.equal(comparePhysicalModels(changed,reference,options).pass,false);
  }
  assert.equal(comparePhysicalModels(actual,reference,{...options,staticTheory:'Timoshenko'}).pass,false);
});

test('shear-area rule annotation requires the public rule and actual section areas',()=>{
  const reference=model();Object.assign(reference.analysis_control,{p_delta:false,rigid_offsets:false,construction_stage:false});
  const actual=clone(reference);actual.analysis_control.extra={shear_area_rule:'Asy=Asz=5*A/6'};
  const options={explicitElasticProperties:true,staticTheory:'Timoshenko',prescribedShearAreaRatio:5/6};
  assert.equal(comparePhysicalModels(actual,reference,options).pass,true);
  assert.equal(comparePhysicalModels(actual,reference,{...options,prescribedShearAreaRatio:undefined}).pass,false);
  for(const mutate of [m=>m.sections[0].properties.Asy=m.sections[0].properties.A*.5,m=>m.analysis_control.extra.shear_area_rule='Asy=Asz=A',m=>m.analysis_control.extra.unknown=1]) {
    const changed=clone(actual);mutate(changed);assert.equal(comparePhysicalModels(changed,reference,options).pass,false);
  }
});

test('an explicit authored shear convention equates omitted and stated default areas for general sections',()=>{
  const reference=model();reference.sections[0].type='general';delete reference.sections[0].shape;
  const actual=clone(reference);for(const k of ['Asy','Asz'])actual.sections[0].properties[k]=5*actual.sections[0].properties.A/6;
  const options={explicitElasticProperties:true,staticTheory:'Timoshenko',prescribedShearAreaRatio:5/6};
  assert.equal(comparePhysicalModels(actual,reference,options).pass,true);
  assert.equal(comparePhysicalModels(actual,reference,{...options,prescribedShearAreaRatio:undefined}).pass,false);
  assert.equal(comparePhysicalModels(actual,reference,{...options,staticTheory:'Euler-Bernoulli'}).pass,false);
  actual.sections[0].properties.Asy*=.99;assert.equal(comparePhysicalModels(actual,reference,options).pass,false);
});
test('descriptive element groups do not mask numerical extras or active floor behavior',()=>{
  const reference=model();Object.assign(reference.analysis_control,{p_delta:false,rigid_offsets:false,construction_stage:false});
  const actual=clone(reference);actual.elements[0].extra={group:'main beam'};const options={explicitElasticProperties:true};
  assert.equal(comparePhysicalModels(actual,reference,options).pass,true);
  assert.equal(comparePhysicalModels(actual,reference).pass,false);
  const override=clone(actual);override.elements[0].extra.stiffness_factor=2;assert.equal(comparePhysicalModels(override,reference,options).pass,false);
  const nonlinear=clone(actual);nonlinear.analysis_control.p_delta=true;assert.equal(comparePhysicalModels(nonlinear,reference,options).pass,false);
});
test('inactive concave floor outlines need covered edges and contained physical nodes',()=>{
  const reference=JSON.parse(require('node:fs').readFileSync(require('node:path').join(__dirname,'../corpora/research-300/cases/INT-086/model-state-1.json')));
  const actual=clone(reference),outline=[[0,0],[12,0],[12,5],[6,5],[6,10],[0,10]];
  for(const s of actual.stories)s.extra={polygonXY:clone(outline)};
  for(const e of actual.elements)e.story=actual.stories.find(s=>Math.abs(Math.max(...e.nodes.map(id=>actual.nodes.find(n=>n.id===id).z))-s.elevation-s.height)<1e-9).id;
  const options={explicitElasticProperties:true};const before=clone(actual);
  assert.equal(comparePhysicalModels(actual,reference,options).pass,true);assert.deepEqual(actual,before);
  for(const change of [m=>m.stories[0].extra.polygonXY=[[0,0],[12,0],[12,10],[0,10]],
    m=>m.stories[0].extra.polygonXY=[[0,0],[6,0],[6,5],[0,5]],m=>m.stories[0].extra.rigid=true,
    m=>m.stories[0].dead_load=1,m=>m.stories[0].rigid_diaphragm=true,m=>m.elements[0].story='s2']) {
    const bad=clone(actual);change(bad);assert.equal(comparePhysicalModels(bad,reference,options).pass,false);
  }
});


test('a fully fixed base may carry the matching inactive story label',()=>{
  const reference=model();reference.nodes[0].restraints=Array(6).fill(true);
  reference.stories=[{id:'s1',elevation:0,height:3,rigid_diaphragm:false}];
  Object.assign(reference.analysis_control,{p_delta:false,rigid_offsets:false,construction_stage:false});
  const actual=clone(reference);actual.nodes[0].story='s1';const options={explicitElasticProperties:true};
  for(const [a,e] of [[actual,reference],[reference,actual]])assert.equal(comparePhysicalModels(a,e,options).pass,true);
  for(const mutate of [m=>m.nodes[0].restraints[4]=false,m=>m.stories[0].elevation=-1,m=>m.stories[0].rigid_diaphragm=true,m=>m.stories[0].dead_load=1]){
    const bad=clone(actual);mutate(bad);assert.equal(comparePhysicalModels(bad,reference,options).pass,false);
  }
});

test('centered custom section geometry may be supplied in extras with a proved zero product of inertia',()=>{
  const reference=JSON.parse(require('node:fs').readFileSync(require('node:path').join(__dirname,'../corpora/research-300/cases/STD-098/model-state-1.json')));
  const actual=clone(reference);actual.sections[0].extra={...actual.sections[0].shape,Iyz_m4:0};delete actual.sections[0].extra.kind;delete actual.sections[0].shape;
  const options={explicitElasticProperties:true};
  assert.equal(comparePhysicalModels(actual,reference,options).pass,true);
  for(const change of [m=>m.sections[0].extra.Iyz_m4=1e-9,m=>m.sections[0].extra.web_thickness_mm=14,m=>m.sections[0].extra.unknown=0]) {
    const bad=clone(actual);change(bad);assert.equal(comparePhysicalModels(bad,reference,options).pass,false);
  }
  assert.equal(comparePhysicalModels(actual,reference).pass,false);
});

test('element concrete grade may repeat its explicitly assigned material grade',()=>{
  const reference=model();Object.assign(reference.materials[0],{type:'concrete',name:'C30',E:30000});
  const actual=clone(reference);actual.elements[0].concrete_grade='C30';const options={explicitElasticProperties:true};
  assert.equal(comparePhysicalModels(actual,reference,options).pass,true);
  const bad=clone(actual);bad.elements[0].concrete_grade='C40';assert.equal(comparePhysicalModels(bad,reference,options).pass,false);
  bad.elements[0].concrete_grade='C30';bad.materials[0].E=32500;assert.equal(comparePhysicalModels(bad,reference,options).pass,false);
  assert.equal(comparePhysicalModels(actual,reference).pass,false);
});
