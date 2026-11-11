'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const review = require('./public-input-review.cjs');

const model = () => ({
  coordinate_system: { dimension: '2d', plane: 'xz', semantics: 'global-z-up', dof_order: ['ux','uy','uz','rx','ry','rz'] },
  nodes: [{id:'a',x:0,y:0,z:0,restraints:[true,true,true,true,true,true]}, {id:'b',x:2,y:0,z:0,restraints:[false,true,false,true,false,true]}],
  elements: [{id:'e',type:'beam',nodes:['a','b'],material:'M',section:'S'}],
  materials: [{id:'M',E:200000,G:80000,nu:0.25,rho:7800}],
  sections: [{id:'S',properties:{A:0.1,Iy:0.01,Iz:0.001,J:0.002}}],
  load_cases: [{id:'D',loads:[{id:'one',type:'nodal',node:'b',reference_frame:'global',fz:-12}]}],
  load_combinations: [], analysis_control:{self_weight:false,rigid_floor:false,p_delta:false,rigid_offsets:false,construction_stage:false},
  metadata: {},
});
const submission = () => ({ schemaVersion:1,caseId:'MM-001',turnId:'t1',packetSha256:'a'.repeat(64),
  reviewer:{id:'fresh-reviewer',kind:'agent',independent:true}, method:'public-only-reconstruction',
  model:{...model(),axes:{mode:'xz',elementDirection:'listed-node-order',rotationDefaultDegrees:0}}, unresolved:[],
  observations:review.CATEGORIES.map(category=>({category,files:['t1/input.png'],observation:'Read the labelled drawing and public appendix.'})) });
const packet = () => ({files:[{path:'t1/input.png',sha256:'b'.repeat(64),bytes:1}]});

test('complete physical readback passes, while plausible geometry alone remains partial', () => {
  assert.equal(review.compareReconstruction(submission(),model(),{id:'MM-001',turn:{id:'t1',expectation:'analyze'}},packet()).status,'passed');
  const partial=submission(); partial.model={nodes:partial.model.nodes,elements:partial.model.elements};
  const result=review.compareReconstruction(partial,model(),{id:'MM-001',turn:{id:'t1',expectation:'analyze'}},packet());
  assert.equal(result.status,'partial'); assert.ok(result.coverage.loads.missing>0);
});

test('wrong load direction, restraint, connectivity, material, section and local-axis roll each fail', () => {
  const mutations=[s=>s.model.load_cases[0].loads[0].fz=12,s=>s.model.nodes[0].restraints[0]=false,
    s=>s.model.elements[0].nodes.reverse(),s=>s.model.materials[0].E=100000,s=>s.model.sections[0].properties.Iy=0.001,
    s=>s.model.elements[0].rotation_angle=90];
  for(const mutate of mutations){const s=submission();mutate(s);assert.equal(review.compareReconstruction(s,model(),{id:'MM-001',turn:{id:'t1',expectation:'analyze'}},packet()).status,'failed');}
});

test('missing visual observations or independent identity cannot earn complete pass', () => {
  const s=submission();s.observations=[];
  assert.equal(review.compareReconstruction(s,model(),{id:'MM-001',turn:{id:'t1',expectation:'analyze'}},packet()).status,'partial');
  s.reviewer.independent=false;
  assert.throws(()=>review.validateSubmission(s),/independent/);
});

test('observed regular stations and member chains expand without consulting a gold model', () => {
  const expanded=review.expandReconstruction({grids:[{stations:{x:[0,3,7],y:[0],z:[0,4]},idTemplate:'n{i}-{j}-{k}',restraints:[false,true,false,true,false,true],
    members:[{axis:'x',starts:[[0,0,1],[1,0,1]],idTemplate:'b{i}',type:'beam',material:'M',section:'S'}]}],
    memberChains:[{nodes:['a','b','c'],ids:['u','v'],type:'truss',material:'M',section:'S'}]});
  assert.deepEqual(expanded.nodes.find(n=>n.id==='n2-0-1'),{id:'n2-0-1',x:7,y:0,z:4,restraints:[false,true,false,true,false,true]});
  assert.deepEqual(expanded.elements.find(e=>e.id==='b1').nodes,['n1-0-1','n2-0-1']);
  assert.deepEqual(expanded.elements.find(e=>e.id==='v').nodes,['b','c']);
  assert.throws(()=>review.expandReconstruction({nodes:[{id:'a'},{id:'a'}]}),/duplicate/);
});

test('clarification masks unresolved force without asking for the hidden answer', () => {
  const m=model();m.nodes[1].id='n1';m.elements[0].nodes[1]='n1';m.load_cases[0].loads[0].node='n1';
  const s=submission();s.caseId='MM-007';s.model={...structuredClone(m),axes:s.model.axes};delete s.model.load_cases[0].loads[0].fz;
  s.unresolved=[{kind:'load-component',ids:['n1'],component:'fz',reason:'Value is unreadable.',question:'What is the force magnitude?'}];
  const context={id:'MM-007',turn:{id:'t1',expectation:'clarify',unresolvedFields:['/load_cases/0/loads/0/fz']}};
  assert.equal(review.compareReconstruction(s,m,context,packet()).status,'passed');
  s.model.load_cases[0].loads[0].fz=-12;
  assert.equal(review.compareReconstruction(s,m,context,packet()).status,'failed');
});

test('absent review stays pending and a fabricated passed report is invalid', t => {
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'public-review-'));t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
  const record={root,id:'MM-001'},binding={schemaVersion:1,caseId:'MM-001',inputEdition:'current',publicInputSha256:'a'.repeat(64)};
  assert.equal(review.getPublicInputReview(record,binding).status,'pending');
  const file=review.reviewPath(record,binding);fs.mkdirSync(path.dirname(file),{recursive:true});fs.writeFileSync(file,JSON.stringify({status:'passed',inputBinding:binding}));
  assert.equal(review.getPublicInputReview(record,binding).status,'invalid');
});

test('historical review files never accept current inputs and non-MM review remains pending', t => {
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'current-review-'));t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
  const binding={schemaVersion:1,caseId:'MM-001',inputEdition:'current',publicInputSha256:'a'.repeat(64)};
  const archived=path.join(root,'docs/implementation/reviews/mm-visual-v2-20261016/records/MM-001/review.json');
  fs.mkdirSync(path.dirname(archived),{recursive:true});fs.writeFileSync(archived,JSON.stringify({status:'passed',inputBinding:binding}));
  assert.equal(review.getPublicInputReview({root,id:'MM-001'},binding).status,'pending');
  assert.equal(review.reviewPath({root,id:'STD-001'},{...binding,caseId:'STD-001'}),null);
  assert.equal(review.getPublicInputReview({root,id:'STD-001'},{...binding,caseId:'STD-001'}).status,'pending');
  assert.throws(()=>review.buildPacketFiles([{id:'STD-001',inputBinding:binding}],0),/MM cases only/);
});

test('unsupported physical mechanisms cannot be silently ignored by a complete review',()=>{
  const s=submission();s.model.elements[0].releases={ry:true};assert.throws(()=>review.validateSubmission(s),/unsupported.*element/);
});
test('3D default reference convention is checked and a missing convention remains partial',()=>{
  const m=model();m.coordinate_system.dimension='3d';m.coordinate_system.plane=null;
  const s=submission();s.model=structuredClone(m);s.model.axes={mode:'reference-vectors',elementDirection:'listed-node-order',rotationDefaultDegrees:0,referenceVectorRule:{vertical:[1,0,0],other:[0,0,1],verticalThreshold:0.9}};
  assert.equal(review.compareReconstruction(s,m,{id:'MM-001',turn:{expectation:'analyze'}},packet()).status,'passed');
  delete s.model.axes.referenceVectorRule;
  assert.equal(review.compareReconstruction(s,m,{id:'MM-001',turn:{expectation:'analyze'}},packet()).status,'partial');
});
test('roof ambiguity masks dependent coordinates but preserves measurable horizontal dimensions',()=>{
  const m=model();m.nodes=[{id:'U1',x:3,y:0,z:1.25,restraints:[false,true,false,true,true,true]},{id:'U2',x:6,y:0,z:2.5,restraints:[false,true,false,true,true,true]}];m.elements[0].nodes=['U1','U2'];m.load_cases[0].loads[0].node='U2';
  const s=submission();s.caseId='MM-032';s.model={...structuredClone(m),axes:s.model.axes};s.model.nodes.forEach(n=>delete n.z);
  s.unresolved=[{kind:'node-coordinate',ids:['U1','U2'],component:'z',reason:'Roof height missing.',question:'What is the roof height?'}];
  const context={id:'MM-032',turn:{expectation:'clarify'}};
  assert.equal(review.compareReconstruction(s,m,context,packet()).status,'passed');
  s.model.nodes[0].x=5;assert.equal(review.compareReconstruction(s,m,context,packet()).status,'failed');
});

test('both cropped column bases must be identified as unknown, not just one',()=>{
  const m=model();m.nodes[0].id='A0';m.nodes[1].id='B0';m.elements[0].nodes=['A0','B0'];m.load_cases[0].loads[0].node='B0';
  const s=submission();s.caseId='MM-058';s.model={...structuredClone(m),axes:s.model.axes};for(const node of s.model.nodes)for(const i of [0,2,4])node.restraints[i]=null;
  s.unresolved=[{kind:'node-restraints',ids:['A0'],reason:'Support cropped.',question:'What is the base support?'}];
  const context={id:'MM-058',turn:{expectation:'clarify'}};
  assert.equal(review.compareReconstruction(s,m,context,packet()).status,'partial');s.unresolved[0].ids.push('B0');assert.equal(review.compareReconstruction(s,m,context,packet()).status,'passed');
});

test('a complete reconstruction rejects contradictory or unknown model units',()=>{
  const context={id:'MM-001',turn:{expectation:'analyze'}};
  for(const declaration of ['mm-N',{length:'mm',force:'N'},'US','si',null]){
    const s=submission();s.model.unit_system=declaration;
    assert.throws(()=>review.compareReconstruction(s,model(),context,packet()),/unit/i);
  }
  const s=submission();s.model.unit_system='SI';
  assert.equal(review.compareReconstruction(s,model(),context,packet()).status,'passed');
});

test('unit overrides in otherwise ungraded model fields cannot retain a complete pass',()=>{
  const overrides=[
    s=>s.model.coordinate_system.units={length:'mm'},
    s=>s.model.coordinate_system.lengthUnit='mm',
    s=>s.model.load_cases[0].force_unit='N',
    s=>s.model.sections[0].shape={kind:'rectangular',units:'mm'},
    s=>s.model.axes.referenceVectorRule={vertical:[1,0,0],other:[0,0,1],verticalThreshold:0.9,angleUnits:'rad'},
    s=>s.model.grids=[{stations:{x:[1],y:[0],z:[0]},idTemplate:'extra',units:'mm'}],
  ];
  for(const override of overrides){
    const s=submission();override(s);
    assert.throws(()=>review.compareReconstruction(s,model(),{id:'MM-001',turn:{expectation:'analyze'}},packet()),/unit/i);
  }
});

test('distributed-load omission means the complete member interval on each reconstruction',()=>{
  const m=model();m.nodes[1].x=3;m.nodes[1].z=4;
  m.load_cases[0].loads=[{id:'w',type:'distributed',element:'e',reference_frame:'global',wz:-10,start:0,end:5}];
  const s=submission();s.model={...structuredClone(m),axes:s.model.axes};delete s.model.load_cases[0].loads[0].start;delete s.model.load_cases[0].loads[0].end;
  const context={id:'MM-001',turn:{expectation:'analyze'}};
  assert.equal(review.compareReconstruction(s,m,context,packet()).status,'passed');
  for(const mutate of [load=>load.start=1,load=>load.end=4]){const bad=structuredClone(s);mutate(bad.model.load_cases[0].loads[0]);assert.equal(review.compareReconstruction(bad,m,context,packet()).status,'failed');}
  const badGeometry=structuredClone(s);badGeometry.model.nodes[1].z=0;
  const result=review.compareReconstruction(badGeometry,m,context,packet());assert.equal(result.status,'failed');assert.ok(result.coverage.geometry.mismatched>0);assert.ok(result.coverage.loads.mismatched>0);
  const expectedImplicit=structuredClone(m);delete expectedImplicit.load_cases[0].loads[0].start;delete expectedImplicit.load_cases[0].loads[0].end;
  s.model.load_cases[0].loads[0].start=0;s.model.load_cases[0].loads[0].end=5;
  assert.equal(review.compareReconstruction(s,expectedImplicit,context,packet()).status,'passed');
  for(const key of ['start','end']){const unknown=structuredClone(s);unknown.model.load_cases[0].loads[0][key]=null;assert.equal(review.compareReconstruction(unknown,m,context,packet()).status,'partial');}
  expectedImplicit.load_cases[0].loads[0].start=1;delete s.model.load_cases[0].loads[0].start;
  assert.equal(review.compareReconstruction(s,expectedImplicit,context,packet()).status,'failed');
});

test('cropped support clarification accepts exact active-DOF lists and rejects wrong DOFs or asserted support truth',()=>{
  const m=model();m.nodes[0].id='A0';m.nodes[1].id='B0';m.elements[0].nodes=['A0','B0'];m.load_cases[0].loads[0].node='B0';
  const s=submission();s.caseId='MM-058';s.model={...structuredClone(m),axes:s.model.axes};for(const node of s.model.nodes)for(const i of [0,2,4])node.restraints[i]=null;
  s.unresolved=[{kind:'node-restraints',ids:['A0','B0'],component:'ux,uz,ry',reason:'Both support symbols are cropped.',question:'What are the in-plane restraints at both bases?'}];
  const context={id:'MM-058',turn:{expectation:'clarify'}};
  for(const component of ['ux,uz,ry','ry / ux / uz',['uz','ry','ux']]){s.unresolved[0].component=component;assert.equal(review.compareReconstruction(s,m,context,packet()).status,'passed');}
  for(const component of ['ux,uy,uz','ux,uz','ux,uz,ry,rx']){s.unresolved[0].component=component;assert.equal(review.compareReconstruction(s,m,context,packet()).status,'failed');}
  s.unresolved[0].component='ux,uz,ry';s.unresolved[0].ids=['A0'];assert.equal(review.compareReconstruction(s,m,context,packet()).status,'partial');
  s.unresolved[0].ids=['A0','B0','extra'];assert.equal(review.compareReconstruction(s,m,context,packet()).status,'failed');
  s.unresolved[0].ids=['A0','B0'];s.model.nodes[1].restraints[4]=true;assert.equal(review.compareReconstruction(s,m,context,packet()).status,'failed');
});

function actualModel(id){return JSON.parse(fs.readFileSync(path.resolve(__dirname,'../corpora/research-300/cases',id,'model-state-1.json'),'utf8'));}
function actualPublicTurns(id){
  const provider=require('./corpus-provider.cjs'),record=provider.loadCase(provider.loadCorpus({corpus:'research-300'}),id);
  return record.contract.turns.map((_,i)=>provider.getFrozenPublicTurnInput(record,i));
}

function syntheticReadback(id,expected){
  const s=submission();s.caseId=id;s.model=structuredClone(expected);s.model.metadata=expected.metadata?.elementReferenceVectors?{elementReferenceVectors:structuredClone(expected.metadata.elementReferenceVectors)}:{};
  delete s.model.stories;
  s.model.axes={mode:expected.coordinate_system.dimension==='2d'?'xz':'reference-vectors',elementDirection:'listed-node-order',rotationDefaultDegrees:0};return s;
}

test('MM-043 through MM-050 full-member load extents accept the solver defaults',()=>{
  for(let number=43;number<=50;number++){
    const id=`MM-${String(number).padStart(3,'0')}`,m=actualModel(id),s=syntheticReadback(id,m);
    for(const lc of s.model.load_cases)for(const load of lc.loads)if(load.type==='distributed'){delete load.start;delete load.end;}
    const result=review.compareReconstruction(s,m,{id,turn:{expectation:'analyze'}},packet());assert.equal(result.status,'passed',`${id}: ${JSON.stringify(result.findings.slice(0,3))}`);
  }
});

test('the released commercial appendix alone enables effective beam shear-area grading',()=>{
  const inputs=actualPublicTurns('MM-084'),conventions=review.getReleasedAnalysisConventions(inputs,0);
  assert.deepEqual(conventions,{effectiveShearAreas:'5*A/6'});
  const noConvention=inputs.map(t=>({...t,attachments:t.attachments.filter(a=>a.name!=='analysis-conventions-v2.txt')}));
  assert.deepEqual(review.getReleasedAnalysisConventions(noConvention,0),{});
  assert.deepEqual(review.getReleasedAnalysisConventions([noConvention[0],inputs[0]],0),{});
  assert.deepEqual(review.getReleasedAnalysisConventions([noConvention[0],inputs[0]],1),{effectiveShearAreas:'5*A/6'});
  const m=model(),s=submission();s.model.sections[0].properties.Asy=1/12;s.model.sections[0].properties.Asz=1/12;
  const context={id:'MM-001',turn:{expectation:'analyze'},analysisConventions:conventions};
  assert.equal(review.compareReconstruction(s,m,context,packet()).status,'passed');
  assert.equal(review.compareReconstruction(s,m,{...context,analysisConventions:{}},packet()).status,'failed');
  s.model.sections[0].properties.Asy=0.01;assert.equal(review.compareReconstruction(s,m,context,packet()).status,'failed');
  delete s.model.sections[0].properties.Asy;const missing=review.compareReconstruction(s,m,context,packet());assert.equal(missing.status,'partial');assert.ok(missing.findings.some(f=>f.code==='missing'&&f.path.endsWith('/Asy')));
  s.model.sections[0].properties.Asy=1/12;s.model.sections[0].properties.inventedShearArea=1/12;assert.equal(review.compareReconstruction(s,m,context,packet()).status,'failed');
  delete s.model.sections[0].properties.inventedShearArea;m.elements[0].type='truss';s.model.elements[0].type='truss';assert.equal(review.compareReconstruction(s,m,context,packet()).status,'failed');
});

test('all eleven actual MM commercial declarations require their effective shear areas, including MM-084 and MM-085',()=>{
  const applicable=[];
  for(let number=1;number<=100;number++){
    const id=`MM-${String(number).padStart(3,'0')}`,conventions=review.getReleasedAnalysisConventions(actualPublicTurns(id),0);if(!conventions.effectiveShearAreas)continue;applicable.push(id);
    const m=actualModel(id),s=syntheticReadback(id,m),context={id,turn:{expectation:'analyze'},analysisConventions:conventions};
    const missing=review.compareReconstruction(s,m,context,packet());assert.equal(missing.status,'partial',id);assert.ok(missing.findings.some(f=>f.path?.endsWith('/Asy')),id);
    for(const section of s.model.sections)if(m.elements.some(e=>!['truss','brace'].includes(e.type)&&e.section===section.id)){section.properties.Asy=5*section.properties.A/6;section.properties.Asz=5*section.properties.A/6;}
    assert.equal(review.compareReconstruction(s,m,context,packet()).status,'passed',id);
    if(['MM-084','MM-085'].includes(id)){assert.ok(Math.abs(s.model.sections.find(section=>section.id==='C1').properties.Asy-0.20833333333333333)<1e-12);s.model.sections[0].properties.Asz=0.01;assert.equal(review.compareReconstruction(s,m,context,packet()).status,'failed');}
  }
  assert.deepEqual(applicable,['MM-079','MM-080','MM-081','MM-082','MM-083','MM-084','MM-085','MM-086','MM-087','MM-089','MM-091']);
});

test('MM-041 axial-member transverse references do not affect physics but endpoint orientation still does',()=>{
  const m=actualModel('MM-041'),s=syntheticReadback('MM-041',m),context={id:'MM-041',turn:{expectation:'analyze'}};
  s.model.metadata.elementReferenceVectors.apex_link=[1,0,0];assert.equal(review.compareReconstruction(s,m,context,packet()).status,'passed');
  s.model.elements.find(e=>e.id==='apex_link').nodes.reverse();assert.equal(review.compareReconstruction(s,m,context,packet()).status,'failed');
  const beam=model();beam.coordinate_system.dimension='3d';beam.coordinate_system.plane=null;beam.metadata.elementReferenceVectors={e:[0,0,1]};const b=syntheticReadback('MM-001',beam);
  b.model.metadata.elementReferenceVectors.e=[0,1,0];assert.equal(review.compareReconstruction(b,beam,{id:'MM-001',turn:{expectation:'analyze'}},packet()).status,'failed');
  b.model.metadata.elementReferenceVectors.e=[0,0,1];b.model.elements[0].rotation_angle=90;assert.equal(review.compareReconstruction(b,beam,{id:'MM-001',turn:{expectation:'analyze'}},packet()).status,'failed');
});
