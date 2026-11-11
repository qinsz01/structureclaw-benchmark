'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const {createHash} = require('node:crypto');
const {verifyStructureClawPayloadBinding: verify} = require('./structureclaw-payload-binding.cjs');

// Independent, closed-form simply supported uniform-load beam. These synthetic
// receipts test the verifier contract; they are never reported as solver runs.
function example() {
  const model = {schema_version:'2.2.0',unit_system:'SI',coordinate_system:{dimension:'2d',vertical_axis:'z'},
    nodes:[{id:'A',x:0,y:0,z:0},{id:'B',x:6,y:0,z:0}],
    elements:[{id:'E',type:'beam',nodes:['A','B'],material:'M',section:'S'}],
    materials:[{id:'M',type:'steel',E:206000}],sections:[{id:'S',properties:{A:.18,Iy:.0054,Iz:.00135}}],
    load_cases:[{id:'D',loads:[{type:'distributed',element:'E',wz:-20}]}]};
  const localAxes={x:[1,0,0],y:[0,1,0],z:[0,0,1]};
  const zero={ux:0,uy:0,uz:0,rx:0,ry:0,rz:0};
  const force={n1:{N:0,V2:0,V3:60,T:0,M2:0,M3:0},n2:{N:0,V2:0,V3:60,T:0,M2:0,M3:0},localAxes};
  const native={displacements:{A:{...zero},B:{...zero}},reactions:{A:{fz:60},B:{fz:60}},forces:{E:force},
    solverMesh:{schemaVersion:1,positionUnit:'m',nodes:model.nodes,elements:[{id:'E',physicalElementId:'E',nodes:['A','B'],start:0,end:6,localAxes}]},
    effectiveLoads:model.load_cases[0].loads,segmentResults:{displacements:{A:{...zero},B:{...zero}},forces:{E:force}}};
  const settings={parameters:{loadCaseIds:['D']}};
  const normalizedInput=structuredClone(model); normalizedInput.materials[0].category='steel';delete normalizedInput.materials[0].type;
  normalizedInput.sections[0].extra={}; normalizedInput.metadata={coordinateContractVersion:1,coordinateSemantics:'global-z-up',frameDimension:'2d'};
  const artifactBytes=Object.fromEntries(Object.entries({normalizedInput,settings,solverResponse:native}).map(([key,value])=>[key,Buffer.from(JSON.stringify(value))]));
  const execution={solver:'OpenSees',artifacts:{hashFormat:'sha256:python-json-sort-keys-utf8-compact-v1',solverResponseKeys:Object.keys(native),
    ...Object.fromEntries(Object.entries(artifactBytes).map(([key,value])=>[key+'Sha256',createHash('sha256').update(value).digest('hex')]))}};
  const data=structuredClone(native);
  const deflection=-5*20*6**4/(384*206000*1000*.0054);
  data.memberResponses=[{id:'E',length:6,state:'recovered',samples:[{x:0,side:'right',N:0,V2:0,V3:60,T:0,M2:0,M3:0,position:[0,0,0],displacement:[0,0,0]},
    {x:3,side:'left',N:0,V2:0,V3:0,T:0,M2:-90,M3:0,position:[3,0,0],displacement:[0,0,deflection]},
    {x:6,side:'left',N:0,V2:0,V3:-60,T:0,M2:0,M3:0,position:[6,0,0],displacement:[0,0,0]}]}];
  return {model,selection:{kind:'case',id:'D'},data,meta:{units:{length:'m',displacement:'m',force:'kN',moment:'kN.m',rotation:'rad'}},execution,artifactBytes};
}
function rejects(change, pattern) {const input=example();change(input);const result=verify(input);assert.equal(result.pass,false,JSON.stringify(result));assert.match(result.failures.join(';'),pattern);}

test('verified native payload and independently recovered uniform-load beam agree',()=>{
  assert.deepEqual(verify(example()),{pass:true,failures:[],verifiedMemberSamples:3});
});

test('old native receipt cannot validate modified candidate reactions, end forces, mesh or distributed loads',()=>{
  for(const [field,change] of [
    ['reactions',x=>x.data.reactions.A.fz=60000],
    ['forces',x=>x.data.forces.E.n1.V3=999],
    ['solverMesh',x=>x.data.solverMesh.elements[0].end=7],
    ['effectiveLoads',x=>x.data.effectiveLoads[0].wz=-200],
    ['segmentResults',x=>x.data.segmentResults.displacements.A.uz=1],
  ]) rejects(change,new RegExp(field+': candidate differs'));
});

test('host model stiffness, geometry and load cannot be rebound to an old native input receipt',()=>{
  for(const change of [x=>x.model.materials[0].E*=2,x=>x.model.nodes[1].x=7,x=>x.model.load_cases[0].loads[0].wz=-200])
    rejects(change,/native normalized input differs/);
  rejects(x=>x.model.materials[0].category='concrete',/category\/type conflict/);
});

test('settings selection must match the exact case or combination',()=>{
  rejects(x=>x.selection.id='L',/settings differ/);
  rejects(x=>x.selection={kind:'combination',id:'D'},/settings differ/);
});

test('SHA, field manifest and hash format fail closed when removed or changed',()=>{
  rejects(x=>x.artifactBytes.solverResponse=Buffer.from('{}'),/SHA256 mismatch/);
  rejects(x=>delete x.execution.artifacts.hashFormat,/unsupported native payload receipt/);
  rejects(x=>delete x.execution.artifacts.solverResponseKeys,/field manifest mismatch/);
  rejects(x=>x.execution.solver='another-solver',/unsupported native payload receipt/);
});

test('host-derived member actions, displacements, sample position and frame are independently verified',()=>{
  rejects(x=>x.data.memberResponses[0].samples[1].M2=90,/M2 differs/);
  rejects(x=>x.data.memberResponses[0].samples[1].displacement[2]*=-1,/displacement differs/);
  rejects(x=>x.data.memberResponses[0].samples[1].position[0]=99,/position differs/);
  rejects(x=>x.data.memberResponses[0].length=7,/length\/position mismatch/);
  rejects(x=>x.data.memberResponses.push(structuredClone(x.data.memberResponses[0])),/duplicate/);
});

test('unit overrides at every readQuantity precedence and commercial-data injection are rejected',()=>{
  rejects(x=>x.data.units={force:'N'},/unit differs/);
  rejects(x=>x.data.meta={units:{displacement:'mm'}},/unit differs/);
  rejects(x=>x.meta.units.moment='N.m',/unit differs/);
  rejects(x=>x.data.memberStations=[],/unbound commercial/);
  rejects(x=>x.data.nativeContext={},/unbound commercial/);
});

test('native negative zero survives comparison with host zero while original bytes retain their hash',()=>{
  const input=example();input.data.forces.E.n1.N=-0;
  assert.equal(verify(input).pass,true);
});
