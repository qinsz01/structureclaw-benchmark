'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),e=require('./evaluate.cjs');
test('zero sign is equivalent, nonzero input and omitted keys remain distinct',()=>{
 assert.deepEqual(e.numericJSON({x:-0,loads:[{f:-0.0}]}),{x:0,loads:[{f:0}]});
 assert.notDeepEqual(e.numericJSON({x:1e-30}),{x:0});assert.notDeepEqual(e.numericJSON({x:0}),{});
});
test('active combinations scale force components once and preserve load intervals',()=>{
 const m={load_cases:[{id:'D',loads:[{type:'distributed',element:'e',wz:-3,start:1,end:2}]},{id:'W',loads:[{type:'nodal',node:'n',fx:4}]}],load_combinations:[{id:'R',factors:{D:1.2,W:-.5}}]};
 const a=e.activeView(m,{kind:'combination',id:'R'});assert.equal(a.load_cases[0].loads[0].wz,-3.5999999999999996);assert.equal(a.load_cases[0].loads[0].start,1);assert.equal(a.load_cases[0].loads[1].fx,-2);assert.equal(m.load_cases[0].loads[0].wz,-3);
});
test('unissued, incomplete and unsupported selected loads are rejected',()=>{
 const m={load_cases:[],load_combinations:[]};assert.throws(()=>e.activeView(m,{kind:'case',id:'missing'}));
 assert.throws(()=>e.activeView({load_cases:[{id:'D',loads:[{type:'displacement'}]}],load_combinations:[]},{kind:'case',id:'D'}));
});
test('only explicitly empty inert collections are equivalent to omitted defaults',()=>{
 assert.deepEqual(e.emptyDefaults({wall_openings:[],slab_openings:[],extensions:{},nodes:[]}),{nodes:[]});
 assert.deepEqual(e.emptyDefaults({wall_openings:[{id:'wall-cut'}],extensions:{factor:0}}),{wall_openings:[{id:'wall-cut'}],extensions:{factor:0}});
 assert.deepEqual(e.emptyDefaults({extensions:[],load_cases:[]}),{extensions:[],load_cases:[]});
});
test('invalid empty-offset evidence fails as a grading result without throwing',()=>{
 const model={elements:[{id:'e',offsets:{}}],nodes:[]};const data={memberResponses:[{id:'e',state:'interpolated',reason:'consistency'}]};
 const result=e.evaluate({kind:'analysis'}, {},[{state:{model,analysisResult:{results:{'case:D':{data}}}}}]);assert.equal(result.passed,false);assert.match(result.metrics[0].detail,/end-action convention/);
});
test('equivalent full-span intervals cannot create an IEEE roundoff sliver',()=>{
 const fs=require('node:fs'),path=require('node:path');
 const ref=JSON.parse(fs.readFileSync(path.resolve(__dirname,'../../corpora/research300-v2-v1/cases/V2-STD-001/private/t1.json'))),m=structuredClone(ref.model);
 const element=m.elements[0],[a,b]=element.nodes.map(id=>m.nodes.find(n=>n.id===id));
 // Rotate a test member into a nontrivial slope while retaining its supports.
 b.z+=.12345;
 const L=Math.hypot(b.x-a.x,b.y-a.y,b.z-a.z);
 m.load_cases=[{id:'D',type:'dead',loads:[{type:'distributed',element:element.id,wz:-3},{type:'distributed',element:element.id,wz:-2,start:0,end:L}]}];m.load_combinations=[];
 const candidate=structuredClone(m);candidate.load_cases[0].loads[0].start=0;candidate.load_cases[0].loads[0].end=L+Number.EPSILON*Math.max(1,L);
 assert.equal(e.physical(candidate,m).pass,true);
 candidate.load_cases[0].loads[0].end=L-1e-5;assert.equal(e.physical(candidate,m).pass,false);
 const spike=structuredClone(m);spike.load_cases[0].loads.push({type:'distributed',element:element.id,wz:1e12,start:0,end:1e-10});assert.equal(e.physical(spike,m).pass,false);
});
test('empty-offset bridge reads only exact native end cuts and retains protected state',()=>{
 const fs=require('node:fs'),path=require('node:path'),{axesFor}=require('../../lib/physical-model-fidelity.cjs'),{readNativeStation}=require('../../lib/commercial-stations.cjs');
 const model=JSON.parse(fs.readFileSync(path.resolve(__dirname,'../../corpora/research300-v2-v1/cases/V2-STD-001/private/t1.json'))).model,element=model.elements[0];element.offsets={};
 const nativeAxes=axesFor(model,element),n1={N:2,V2:3,V3:4,T:5,M2:6,M3:7},n2={N:-2,V2:-3,V3:-4,T:-5,M2:-6,M3:-7};
 const data={meta:{forceConvention:'element-end-resisting-actions',solverVersion:'fixture',execution:{executed:true,analysisReturnCode:0,constitutiveModel:'linear-elastic',solverConfiguration:{algorithm:'Linear'}}},memberResponses:[{id:element.id,state:'interpolated',reason:'consistency',axes:nativeAxes}],forces:{[element.id]:{responseCoordinateConvention:'global-xyz',referenceFrame:'element-local',source:{kind:'solver-direct'},n1,n2}}};
 const job={state:{model,analysisResult:{results:{'case:D':{data,meta:{modelHash:'protected-fixture',settingsHash:'protected-settings'}}}}}};
 const view=e.evidenceViews([job])[0].state.analysisResult.results['case:D'].data;
 assert.equal(view.memberStations[element.id][0].components.My,-6);assert.equal(view.memberStations[element.id][1].components.My,-6);
 assert.equal(job.state.analysisResult.results['case:D'].data.memberStations,undefined);
 assert.throws(()=>readNativeStation(view,element.id,view.memberLengths[element.id]/2,'right'),/unavailable/);
 const bad=structuredClone(job);bad.state.analysisResult.results['case:D'].data.forces[element.id].source.kind='invented';assert.throws(()=>e.evidenceViews([bad]),/solver end actions/);
});
