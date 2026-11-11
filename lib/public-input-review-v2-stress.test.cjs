'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const review=require('./public-input-review-v2.cjs');
const {validate}=require('./input-review-schema.cjs');
const {compareLoads}=require('./input-review-loads.cjs');
const fixture=()=>({
  coordinate_system:{dimension:'2d',plane:'xz',semantics:'global-z-up',dof_order:['ux','uy','uz','rx','ry','rz']},
  nodes:[{id:'n0',x:0,y:0,z:0,restraints:[true,true,true,true,true,true]},{id:'n1',x:5,y:0,z:0,restraints:[false,true,false,true,false,true]}],
  elements:[{id:'e0',type:'beam',nodes:['n0','n1'],material:'M',section:'S',rotation_angle:0}],
  materials:[{id:'M',E:200000,G:80000,nu:0.25,rho:7800}],sections:[{id:'S',properties:{A:0.1,Iy:0.01,Iz:0.001,J:0.002}}],
  load_cases:[{id:'D',loads:[{id:'w',type:'distributed',element:'e0',reference_frame:'global',wz:-10}]}],load_combinations:[{id:'U',factors:{D:1}}],
  analysis_control:{self_weight:false,rigid_floor:false,p_delta:false,rigid_offsets:false,construction_stage:false},
});
const submission=m=>({schemaVersion:1,caseId:'MM-001',turnId:'t1',packetSha256:'a'.repeat(64),reviewer:{id:'synthetic-stress-fixture',kind:'agent',independent:true},method:review.METHOD,
  model:{...structuredClone(m),axes:{mode:'xz',elementDirection:'listed-node-order',rotationDefaultDegrees:0}},unresolved:[],
  observations:review.CATEGORIES.map(category=>({category,files:['t1/input.png'],observation:'Synthetic robustness test, never independent review evidence.'}))});
const packet=()=>({protocolVersion:review.PROTOCOL_VERSION||review.VERSION,files:[{path:'t1/input.png',sha256:'b'.repeat(64),bytes:1}]});
const context=()=>({id:'MM-001',turn:{id:'t1',expectation:'analyze'},conventions:{controls:{},constraints:[]}});
const grade=(s,m,c=context())=>review.compareReconstruction(s,m,c,packet());

test('conflicting duplicate combination IDs cannot hide an incorrect earlier definition',()=>{
  for(const factors of [[100,1],[1,100],[1,1]]){
    const m=fixture(),s=submission(m);s.model.load_combinations=factors.map(value=>({id:'U',factors:{D:value}}));
    const g=grade(s,m);assert.equal(g.dimensions.protocol.status,'failed');assert.notEqual(g.status,'passed');
  }
});
test('prototype property names cannot bypass the closed public schema',()=>{
  for(const key of ['toString','valueOf','hasOwnProperty','isPrototypeOf','propertyIsEnumerable','toLocaleString']){
    const m=fixture(),s=submission(m);s[key]={unexpected:true};assert.ok(validate(s).some(f=>f.code==='unsupported-field'),key);assert.notEqual(grade(s,m).status,'passed',key);
  }
});
test('a valid string ID matching a prototype property is graded without crashing',()=>{
  for(const id of ['toString','valueOf','hasOwnProperty','isPrototypeOf']){
    const m=fixture(),s=submission(m);s.model.load_cases[0].id=id;let g;
    assert.doesNotThrow(()=>g=grade(s,m),id);assert.notEqual(g.status,'passed',id);
    const renamed=structuredClone(m);renamed.load_cases[0].id=id;renamed.load_combinations[0].factors={[id]:1};assert.equal(grade(submission(renamed),renamed).status,'passed',id);
  }
});
test('observed grids and node overrides retain the same load intervals as explicit nodes',()=>{
  const m=fixture(),s=submission(m);delete s.model.nodes;delete s.model.elements;
  s.model.grids=[{stations:{x:[0,5],y:[0],z:[0]},idTemplate:'n{i}',restraints:[false,true,false,true,false,true],members:[{axis:'x',starts:[[0,0,0]],idTemplate:'e{i}',type:'beam',material:'M',section:'S',rotation_angle:0}]}];
  s.model.nodeOverrides=[{id:'n0',restraints:[true,true,true,true,true,true]}];
  assert.equal(grade(s,m).status,'passed');
  s.model.grids[0].stations.x[1]=6;assert.notEqual(grade(s,m).status,'passed');
});
test('member-chain expansion and coordinate overrides participate in load geometry',()=>{
  const m=fixture(),s=submission(m);delete s.model.elements;s.model.memberChains=[{nodes:['n0','n1'],ids:['e0'],type:'beam',material:'M',section:'S',rotation_angle:0}];
  assert.equal(grade(s,m).status,'passed');s.model.nodeOverrides=[{id:'n1',x:6}];const g=grade(s,m);assert.equal(g.status,'failed');assert.ok(g.findings.some(f=>f.category==='loads'&&f.code==='mismatch'));
  s.model.nodeOverrides.push({id:'n1',x:5});assert.equal(grade(s,m).dimensions.protocol.status,'failed');
});
test('load multiset matching agrees with independent exhaustive permutation search',t=>{
  let seed=20261026,checked=0;const random=()=>((seed=(Math.imul(seed,1664525)+1013904223)>>>0)/4294967296);
  const close=(a,b)=>Math.abs(a-b)<=Math.max(1e-10,Math.abs(b)*1e-7);
  function oracle(actual,expected){
    if(actual.length!==expected.length)return false;
    function assign(j,used){if(j===expected.length)return true;for(let i=0;i<actual.length;i++)if(!used.has(i)&&close(actual[i].fx,expected[j].fx)&&close(actual[i].fz,expected[j].fz)){
      used.add(i);if(assign(j+1,used))return true;used.delete(i);
    }return false;}
    return assign(0,new Set());
  }
  for(let run=0;run<1200;run++){
    const n=1+Math.floor(random()*5),base={type:'nodal',node:'n1',reference_frame:'global'};
    const expected=Array.from({length:n},()=>({...base,fx:1+Math.floor(random()*8)*3e-8,fz:10*(1+Math.floor(random()*2))}));
    const actual=structuredClone(expected);for(let i=actual.length-1;i>0;i--){const j=Math.floor(random()*(i+1));[actual[i],actual[j]]=[actual[j],actual[i]];}
    for(const l of actual)l.fx+=(random()-0.5)*3e-7;
    if(run%4===0)actual[0].fz*=-1;if(run%11===0)actual.push(structuredClone(actual[0]));if(run%13===0)actual.pop();
    const m=fixture(),a=fixture();m.load_cases[0].loads=expected;a.load_cases[0].loads=actual;
    const accepted=compareLoads(a,m).findings.length===0;assert.equal(accepted,oracle(actual,expected),`seed=20261026 run=${run}`);checked++;
  }
  t.diagnostic(JSON.stringify({exhaustiveOracleComparisons:checked,seed:20261026}));
});
test('all 100 MM states reject injected physical faults while retaining order invariance',t=>{
  let cases=0,mutations=0,equivalent=0;
  for(let number=1;number<=100;number++){
    const id=`MM-${String(number).padStart(3,'0')}`,m=JSON.parse(fs.readFileSync(path.resolve(__dirname,'../corpora/research-300/cases',id,'model-state-1.json')));
    const original=submission(m);original.caseId=id;delete original.model.stories;
    original.model.metadata=m.metadata?.elementReferenceVectors?{elementReferenceVectors:structuredClone(m.metadata.elementReferenceVectors)}:{};
    if(m.coordinate_system.dimension==='3d')Object.assign(original.model.axes,{mode:'reference-vectors',referenceVectorRule:{vertical:[1,0,0],other:[0,0,1],verticalThreshold:0.9}});
    const c={...context(),id};assert.equal(grade(original,m,c).status,'passed',id);cases++;
    const reordered=structuredClone(original);
    for(const key of ['nodes','elements','materials','sections','load_cases','load_combinations'])reordered.model[key]?.reverse();
    for(const lc of reordered.model.load_cases||[])lc.loads.reverse();assert.equal(grade(reordered,m,c).status,'passed',id);equivalent++;
    const inject=[s=>s.model.nodes[0].x+=0.125,s=>s.model.nodes[0].restraints[0]=!s.model.nodes[0].restraints[0],s=>s.model.elements[0].nodes.reverse(),
      s=>s.model.materials[0].E*=0.9,s=>s.model.sections[0].properties.A*=1.1,s=>s.model.elements[0].section='unpublished-section',s=>s.model.analysis_control.self_weight=!s.model.analysis_control.self_weight,
      s=>{const load=s.model.load_cases.flatMap(l=>l.loads).find(l=>['fx','fy','fz','mx','my','mz','wx','wy','wz'].some(k=>typeof l[k]==='number'&&l[k]!==0));assert.ok(load,id);const key=['fx','fy','fz','mx','my','mz','wx','wy','wz'].find(k=>typeof load[k]==='number'&&load[k]!==0);load[key]*=-1;}];
    for(const [index,mutate]of inject.entries()){const bad=structuredClone(original);mutate(bad);const g=grade(bad,m,c);assert.equal(g.dimensions.physical.status,'failed',`${id} mutation=${index}`);assert.notEqual(g.status,'passed');mutations++;}
  }
  t.diagnostic(JSON.stringify({syntheticCases:cases,knownPhysicalFaultsRejected:mutations,equivalentPermutationsAccepted:equivalent,baselineChecks:cases,independentInputReview:false}));
});
test('malformed nonidentity fields produce diagnostic results without uncaught exceptions',t=>{
  const paths=[['model'],['model','nodes'],['model','nodes',0],['model','nodes',0,'x'],['model','nodes',0,'restraints'],['model','nodes',0,'restraints',0],['model','elements'],['model','elements',0,'nodes'],
    ['model','materials',0,'E'],['model','sections',0,'properties'],['model','load_cases'],['model','load_cases',0,'loads'],['model','load_cases',0,'loads',0,'end'],['model','load_combinations'],['model','analysis_control'],['model','axes'],
    ['unresolved'],['observations'],['observations',0],['observations',0,'files']];
  const values=[null,0,true,false,'','invalid',[],{},[null]];let checks=0;
  for(const keys of paths)for(const v of values){
    const m=fixture(),s=submission(m);let cursor=s;for(const k of keys.slice(0,-1))cursor=cursor[k];cursor[keys.at(-1)]=structuredClone(v);
    let g;assert.doesNotThrow(()=>g=grade(s,m),keys.join('/'));assert.ok(['passed','partial','failed'].includes(g.status));assert.doesNotThrow(()=>JSON.stringify(g));checks++;
  }
  t.diagnostic(JSON.stringify({malformedFieldAssessments:checks}));
});
