'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const review=require('./public-input-review-v2.cjs');
const legacy=require('./public-input-review.cjs');
const {validate,schema}=require('./input-review-schema.cjs');
const {memberLength,compareLoads}=require('./input-review-loads.cjs');
const {releasedConventions}=require('./input-review-conventions.cjs');
function model(){return {
  coordinate_system:{dimension:'2d',plane:'xz',semantics:'global-z-up',dof_order:['ux','uy','uz','rx','ry','rz']},
  nodes:[{id:'a',x:0,y:0,z:0,restraints:[true,true,true,true,true,true]},{id:'b',x:5,y:0,z:0,restraints:[false,true,false,true,false,true]}],
  elements:[{id:'e',type:'beam',nodes:['a','b'],material:'M',section:'S'}],materials:[{id:'M',E:200000,G:80000,nu:0.25,rho:7800}],
  sections:[{id:'S',properties:{A:0.1,Iy:0.01,Iz:0.001,J:0.002}}],
  load_cases:[{id:'D',loads:[{id:'w',type:'distributed',element:'e',reference_frame:'global',wz:-10}]}],load_combinations:[],
  analysis_control:{self_weight:false,rigid_floor:false,p_delta:false,rigid_offsets:false,construction_stage:false}};}
function submission(m=model()){return {schemaVersion:1,caseId:'MM-001',turnId:'t1',packetSha256:'a'.repeat(64),reviewer:{id:'test-only',kind:'agent',independent:true},method:legacy.METHOD,
  model:{...structuredClone(m),axes:{mode:'xz',elementDirection:'listed-node-order',rotationDefaultDegrees:0}},unresolved:[],
  observations:legacy.CATEGORIES.map(category=>({category,files:['t1/input.png'],observation:'Synthetic test fixture, not independent review evidence.'}))};}
const packet=()=>({protocolVersion:review.PROTOCOL_VERSION,files:[{path:'t1/input.png',sha256:'b'.repeat(64),bytes:1}]});
const context=()=>({id:'MM-001',turn:{expectation:'analyze'},conventions:{controls:{first_order:true,linear_elastic:true,stiffness_reductions:false,automatic_combinations:false,full_explicit_stiffness:true},constraints:[]}});
const grade=(s=submission(),m=model(),c=context(),p=packet())=>review.compareReconstruction(s,m,c,p);

test('v2 reports independent mandatory dimensions without altering original input',()=>{
  const s=submission(),before=structuredClone(s),g=grade(s);assert.equal(g.status,'passed');assert.deepEqual(s,before);
  assert.deepEqual(Object.values(g.dimensions).map(d=>d.status),['passed','passed','passed','passed']);
  s.observations=[];const partial=grade(s);assert.equal(partial.dimensions.physical.status,'passed');assert.equal(partial.dimensions.observations.status,'partial');assert.equal(partial.status,'partial');
  s.observations=[{category:'bad',files:['t1/input.png'],observation:'Invalid source category.'}];const bad=grade(s);assert.equal(bad.dimensions.physical.status,'passed');assert.equal(bad.dimensions.protocol.status,'failed');assert.equal(bad.dimensions.observations.status,'failed');
});
test('published optional analysis settings accept equivalence and reject each opposite value',()=>{
  for(const [key,value]of Object.entries(context().conventions.controls)){
    const s=submission();s.model.analysis_control[key]=value;assert.equal(grade(s).status,'passed',key);
    s.model.analysis_control[key]=!value;assert.equal(grade(s).dimensions.physical.status,'failed',key);
    s.model.analysis_control[key]=value;const c=context();delete c.conventions.controls[key];assert.equal(grade(s,model(),c).dimensions.protocol.status,'failed',key);assert.equal(grade(s,model(),c).dimensions.physical.status,'ungradable',key);
  }
});
test('known analysis aliases are checked and contradictory aliases cannot override settings',()=>{
  const s=submission();s.model.analysis={type:'first-order linear elastic static',full_explicit_stiffness:true,automatic_reduction:false};assert.equal(grade(s).status,'passed');
  s.model.analysis_control.stiffness_reductions=true;assert.equal(grade(s).status,'failed');assert.ok(grade(s).findings.some(f=>f.code==='conflicting-alias'));
});
test('shape-unit metadata stays separate from physical units and true stiffness errors',()=>{
  const s=submission();s.model.sections[0].shape={B:300,H:600};s.model.sections[0].shape_units='mm';assert.equal(grade(s).status,'passed');
  const old=packet();delete old.protocolVersion;const g=grade(s,model(),context(),old);assert.equal(g.dimensions.physical.status,'passed');assert.equal(g.dimensions.protocol.status,'failed');
  s.model.sections[0].properties.A*=1e6;assert.equal(grade(s).dimensions.physical.status,'failed');
  for(const mutate of [s=>s.model.unit_system='mm-N',s=>s.model.sections[0].properties.units='mm',s=>s.model.nodes[0].length_unit='mm',s=>s.model.load_cases[0].force_unit='N']){
    const bad=submission();mutate(bad);assert.equal(grade(bad).dimensions.protocol.status,'failed');assert.notEqual(grade(bad).status,'passed');
  }
});
test('unsupported mechanisms and malformed numeric values remain visible, not silently dropped',()=>{
  for(const mutate of [s=>s.model.elements[0].releases={ry:true},s=>s.model.analysis_control.hiddenFeature=false,s=>s.model.materials[0].E='200000',s=>s.model.nodes[0].x=Infinity,s=>s.model.nodes[0].restraints[0]=1]){
    const s=submission();mutate(s);const g=grade(s);assert.equal(g.dimensions.protocol.status,'failed');assert.equal(g.dimensions.physical.status,'ungradable');
  }
});
test('machine-readable schema and runtime share the same contract, including expansions',()=>{
  assert.equal(schema.$schema,'https://json-schema.org/draft/2020-12/schema');assert.deepEqual(validate(submission()),[]);
  const s=submission();s.model.grids=[{stations:{x:[8],y:[0],z:[0]},idTemplate:'n{i}{j}{k}',members:[]}];assert.deepEqual(validate(s),[]);
  s.model.grids[0].units='mm';assert.ok(validate(s).some(f=>f.code==='unsupported-field'));
});
test('metre intervals and explicit full-member syntax are equivalent; fractions and mixed declarations fail',()=>{
  for(const extent of [{},{start:0,end:5},{extent:'full-member'}]){
    const s=submission();Object.assign(s.model.load_cases[0].loads[0],extent);assert.equal(grade(s).status,'passed');
  }
  for(const extent of [{start:0,end:1},{start:1,end:5},{start:0,end:4}]){
    const s=submission();Object.assign(s.model.load_cases[0].loads[0],extent);const g=grade(s);assert.equal(g.dimensions.physical.status,'failed');assert.ok(g.findings.some(f=>f.code==='mismatch'&&Number.isFinite(f.tolerance)));
  }
  const s=submission();Object.assign(s.model.load_cases[0].loads[0],{extent:'full-member',end:1});assert.equal(grade(s).dimensions.protocol.status,'failed');
});
test('wrong geometry cannot borrow expected member length and null never means default',()=>{
  const s=submission();s.model.nodes[1].z=4;const g=grade(s);assert.equal(g.status,'failed');assert.ok(g.findings.some(f=>f.category==='loads'&&f.code==='mismatch'));
  for(const key of ['start','end']){const s=submission();s.model.load_cases[0].loads[0][key]=null;const g=grade(s);assert.equal(g.dimensions.physical.status,'partial');}
});
test('load comparison is a tolerance-aware multiset, independent of IDs and record order',()=>{
  const m=model();m.load_cases[0].loads=[{type:'nodal',node:'a',reference_frame:'global',fx:1,fz:10},{type:'nodal',node:'a',reference_frame:'global',fx:1.00000005,fz:20}];
  const s=submission(m);s.model.load_cases[0].loads.reverse();s.model.load_cases[0].loads[0].fx=0.99999999;s.model.load_cases[0].loads[1].fx=1.00000001;
  assert.equal(grade(s,m).status,'passed');s.model.load_cases[0].loads.push(structuredClone(s.model.load_cases[0].loads[0]));assert.equal(grade(s,m).status,'failed');
  s.model.load_cases[0].loads.pop();s.model.load_cases[0].loads[0].fz=-20;assert.equal(grade(s,m).status,'failed');
});
test('multiset matching finds an augmenting path instead of greedily rejecting a valid permutation',()=>{
  const base={type:'nodal',node:'a',reference_frame:'global'},m=model();m.load_cases[0].loads=[{...base,fx:1},{...base,fx:1.00000015}];
  const s=submission(m);s.model.load_cases[0].loads=[{...base,fx:1.00000007},{...base,fx:0.99999995}];assert.equal(grade(s,m).status,'passed');
});
test('case and combination identities, load multiplicity and empty declarations remain required',()=>{
  const s=submission();s.model.load_cases[0].id='other';assert.equal(grade(s).status,'failed');
  const missing=submission();delete missing.model.load_combinations;assert.equal(grade(missing).status,'partial');
  const m=model();m.load_combinations=[{id:'U',factors:{D:1}}];const combo=submission(m);combo.model.load_combinations[0].factors.D=-1;assert.equal(grade(combo,m).status,'failed');
  const duplicate=submission();duplicate.model.load_cases[0].loads.push(structuredClone(duplicate.model.load_cases[0].loads[0]));assert.equal(grade(duplicate).status,'failed');
  const emptyExtra=submission();emptyExtra.model.load_combinations.push({id:'invented',factors:{}});assert.equal(grade(emptyExtra).status,'failed');
});
test('section clarification normalizes only the exact section alias, not wrong IDs or components',()=>{
  const m=model();m.elements=[...m.elements,{...m.elements[0],id:'second'},{...m.elements[0],id:'b3'}];
  const s=submission(m);s.caseId='MM-021';s.model.elements[2].section=null;s.unresolved=[{kind:'element-section',ids:['b3'],component:'section',reason:'Conflicting section labels.',question:'Which section belongs to b3?'}];
  const c={...context(),id:'MM-021',turn:{expectation:'clarify'}};assert.equal(grade(s,m,c).status,'passed');
  s.unresolved[0].component='fz';assert.equal(grade(s,m,c).dimensions.clarification.status,'failed');s.unresolved[0].component='section';s.unresolved[0].ids=['second'];assert.notEqual(grade(s,m,c).status,'passed');
});
test('relative geometry survives unknown absolute elevations only with source-bound constraints',()=>{
  const m=model();m.nodes[0].id='C2';m.nodes[1].id='R1';m.nodes.forEach(n=>n.z=3.8);m.elements[0].nodes=['C2','R1'];
  const s=submission(m);s.caseId='MM-072';s.model.nodes.forEach(n=>n.z=null);s.model.load_cases[0].loads[0].end=5;
  s.unresolved=[{kind:'node-coordinate',ids:['C2','R1'],component:'z',reason:'Offset omitted.',question:'What is the right-bay elevation offset?'}];
  const c={...context(),id:'MM-072',turn:{expectation:'clarify'},conventions:{controls:{},constraints:[{axis:'z',nodes:['C2','R1']}]}};
  assert.equal(grade(s,m,c).status,'passed');const no=structuredClone(c);no.conventions.constraints=[];assert.notEqual(grade(s,m,no).status,'passed');
  assert.equal(grade(s,m,no).dimensions.physical.status,'partial');assert.ok(grade(s,m,no).findings.some(f=>f.code==='unverifiable-extent'));
  s.model.load_cases[0].loads[0].end=4;assert.equal(grade(s,m,c).status,'failed');
  s.model.load_cases[0].loads[0].end=5;s.model.nodes[1].x=6;assert.equal(grade(s,m,c).status,'failed');
  assert.equal(memberLength({nodes:[{id:'a',x:0,y:0},{id:'b',x:5,y:0}],elements:[{id:'e',nodes:['a','b']}]},'e'),undefined);
});
test('symbolic full-member extents preserve disclosed intent without inventing an unknown length',()=>{
  const unknown={nodes:[{id:'a',x:0,y:0},{id:'b',x:5,y:0}],elements:[{id:'e',nodes:['a','b']}],load_cases:[{id:'D',loads:[{type:'distributed',element:'e',reference_frame:'global',wz:-10}]}],load_combinations:[]};
  assert.deepEqual(compareLoads(unknown,unknown).findings,[]);
  const numeric=structuredClone(unknown);numeric.load_cases[0].loads[0].end=5;
  const g=compareLoads(numeric,unknown);assert.equal(g.coverage.deferred,1);assert.equal(g.coverage.mismatched,0);
});
test('relative-coordinate declarations cannot be inherited by changed or future image bytes',()=>{
  const facts=require('./input-review-public-facts.json').records[0];
  const p={files:[{path:facts.sourcePath,sha256:facts.sourceSha256}]};assert.equal(releasedConventions([{attachments:[]}],0,p).constraints.length,3);
  p.files[0].sha256='a'.repeat(64);assert.deepEqual(releasedConventions([{attachments:[]}],0,p).constraints,[]);
  p.files[0].sha256=facts.sourceSha256;p.files[0].path='t2/drawing.png';assert.deepEqual(releasedConventions([{attachments:[]}],0,p).constraints,[]);
});
test('public convention extraction uses released source bytes and rejects tampering',()=>{
  const provider=require('./corpus-provider.cjs'),record=provider.loadCase(provider.loadCorpus({corpus:'research-300'}),'MM-010');
  const source=provider.getFrozenPublicTurnInput(record,0),c=releasedConventions([source],0,packet());assert.equal(c.controls.stiffness_reductions,false);assert.equal(c.controls.first_order,true);assert.ok(c.sources.length);
  assert.deepEqual(releasedConventions([{attachments:[]},source],0,packet()).controls,{});
  const bad=structuredClone(source);bad.attachments.find(a=>a.name==='properties.txt').sha256='0'.repeat(64);assert.throws(()=>releasedConventions([bad],0,packet()),/hash mismatch/);
});
test('all MM states retain baseline physical agreement; synthetic self-check is not corpus review',()=>{
  for(let n=1;n<=100;n++){
    const id=`MM-${String(n).padStart(3,'0')}`,dir=path.resolve(__dirname,'../corpora/research-300/cases',id);
    for(const file of fs.readdirSync(dir).filter(f=>/^model-state-\d+\.json$/.test(f))){
      const m=JSON.parse(fs.readFileSync(path.join(dir,file))),s=submission(m);s.caseId=id;delete s.model.stories;
      s.model.metadata=m.metadata?.elementReferenceVectors?{elementReferenceVectors:m.metadata.elementReferenceVectors}:{};
      if(m.coordinate_system.dimension==='3d')Object.assign(s.model.axes,{mode:'reference-vectors',referenceVectorRule:{vertical:[1,0,0],other:[0,0,1],verticalThreshold:0.9}});
      const result=grade(s,m,{...context(),id});assert.equal(result.status,'passed',`${id}/${file}: ${JSON.stringify(result.findings.slice(0,4))}`);
    }
  }
});
