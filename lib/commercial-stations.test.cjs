const test=require('node:test');
const assert=require('node:assert/strict');
const {normalizeCommercialEngineResponse,compareCommercialEngineResponses}=require('./cross-engine-ground-truth.cjs');
const {compareRequestedQuantities}=require('./requested-quantities.cjs');
const {readNativeStation}=require('./commercial-stations.cjs');
const {yjk,pkpm}=require('./fixtures/commercial-native-stations.json');
const clone=value=>JSON.parse(JSON.stringify(value));
const fullAxes=[[1,0,0],[0,1,0],[0,0,1]],reverseAxes=[[-1,0,0],[0,-1,0],[0,0,1]];
const components={N:10,Vy:2,Vz:3,T:4,My:5,Mz:6};
const row=(positionM,side,c=components,localAxes=fullAxes)=>({positionM,side,components:c,localAxes,referenceFrame:'element-local'});

test('both actual native engines keep six DOFs, real support reactions and signed stations',()=>{
  for(const [engine,fixture,data] of [['yjk',yjk,yjk.cases.D],['pkpm',pkpm,pkpm.case]]) {
    // The PKPM fixture deliberately excerpts three physical members only.
    const model={...fixture.model,elements:fixture.model.elements.filter(e=>data.memberStations[e.id])};
    const normalized=normalizeCommercialEngineResponse(engine,model,{status:'success',caseResults:{D:data}},{caseKey:'D'});
    assert.equal(normalized.format,'signed-stations-v1');
    assert.equal(Object.keys(normalized.displacements).length,model.nodes.length);
    assert.equal(Object.keys(normalized.reactions).length,model.nodes.filter(n=>n.restraints.some(Boolean)).length);
    assert.equal(compareCommercialEngineResponses(normalized,normalized,{}).pass,true);
    const wrong=clone(normalized),member=Object.keys(wrong.memberStations)[0];
    wrong.memberStations[member][0].components.Vy+=1;
    assert.equal(compareCommercialEngineResponses(wrong,normalized,{}).pass,false);
    const missing=clone(data);delete missing.reactions[Object.keys(normalized.reactions)[0]].mx;
    assert.throws(()=>normalizeCommercialEngineResponse(engine,model,{status:'success',caseResults:{D:missing}},{caseKey:'D'}),/complete reactions/);
  }
});

test('native combinations cannot be confused with a case with the same ID',()=>{
  const raw={status:'success',caseResults:yjk.cases,combinationResults:{CX:yjk.combination},selectedResult:yjk.selection};
  const result=normalizeCommercialEngineResponse('yjk',yjk.model,raw,{selection:{kind:'combination',id:'CX'}});
  assert.equal(result.selection.kind,'combination');
  const wrong={...result,selection:{kind:'case',id:'CX'}};
  assert.equal(compareCommercialEngineResponses(wrong,result,{}).pass,false);
  assert.throws(()=>normalizeCommercialEngineResponse('yjk',yjk.model,raw,{selection:{kind:'combination',id:'missing'}}),/unavailable/);
});

test('explicit cases cannot fall back to a unique case or disagree with an ID hint',()=>{
  const raw={status:'success',caseResults:{D:yjk.cases.D}};
  assert.throws(()=>normalizeCommercialEngineResponse('yjk',yjk.model,raw,{selection:{kind:'case',id:'missing'}}),/unavailable/);
  assert.throws(()=>normalizeCommercialEngineResponse('yjk',yjk.model,raw,{caseKey:'D',selection:{kind:'case',id:'other'}}),/conflicting/);
  const multiple={status:'success',caseResults:{D:yjk.cases.D,L:yjk.cases.D},selectedResult:{kind:'case',id:'L'}};
  assert.equal(normalizeCommercialEngineResponse('yjk',yjk.model,multiple).caseKey,'L');
});

test('legacy dead-load selection ignores a current combination and native engine identity is mandatory',()=>{
  const raw={status:'success',caseResults:{DL:yjk.cases.D},combinationResults:{CX:yjk.combination},
    selectedResult:{kind:'combination',id:'CX'},summary:{load_cases:[{kind:1,key:'DL'}]}};
  assert.equal(normalizeCommercialEngineResponse('yjk',yjk.model,raw,{legacyDeadLoad:true}).caseKey,'DL');
  const wrong=clone(raw);wrong.caseResults.DL.nativeContext.engine='pkpm';
  assert.throws(()=>normalizeCommercialEngineResponse('yjk',yjk.model,wrong,{caseKey:'DL'}),/engine identity/);
});

test('duplicate, nonnumeric and contradictory cut rows are never authoritative',()=>{
  for(const rows of [[row(2,'left'),row(2,'left')], [row(2,'left'),row(2,'continuous')], [row('2','left')]]) {
    assert.throws(()=>readNativeStation({memberStations:{b:rows}},'b',2,'left'),/duplicate|conflicting|physical position/);
  }
  const invalid=clone(yjk.cases.D),member=Object.keys(invalid.memberStations)[0];
  const cut={...invalid.memberStations[member][0],positionM:1,side:'continuous'};
  invalid.memberStations[member].push(cut,{...cut,side:'left'});
  assert.throws(()=>normalizeCommercialEngineResponse('yjk',yjk.model,{status:'success',caseResults:{D:invalid}},{caseKey:'D'}),/conflicting/);
});

test('a reversed signed cut changes face, coordinates and left/right, not absolute values',()=>{
  // Hand-derived cut transformation: F=[-N,Vy,Vz], M=[-T,-My,-Mz].
  const reversed={N:10,Vy:2,Vz:-3,T:4,My:5,Mz:-6};
  const data={memberLengths:{b:5},memberStations:{b:[row(3,'right',reversed,reverseAxes),row(3,'left',{...reversed,Vz:-30},reverseAxes)]}};
  const mapping={elementOrientation:{b:'reversed'},physicalAxes:{b:fullAxes}};
  assert.deepEqual(readNativeStation(data,'b',2,'left',mapping),components);
  assert.equal(readNativeStation(data,'b',2,'right',mapping).Vz,30);
  assert.throws(()=>readNativeStation(data,'b',2.001,'left',mapping),/unavailable/);
});

test('a verified subdivision selects the correct side of an interior cut',()=>{
  const data={memberStations:{b1:[row(2,'left')],b2:[row(0,'right',{...components,Vz:-7})]}};
  const mappings={elementSegments:{b:[{id:'b1',start:0,end:2,orientation:'same'},{id:'b2',start:2,end:5,orientation:'same'}]}};
  assert.equal(readNativeStation(data,'b',2,'left',mappings).Vz,3);
  assert.equal(readNativeStation(data,'b',2,'right',mappings).Vz,-7);
});

test('nearby cuts cannot borrow a point-load side; only arithmetic roundoff is absorbed',()=>{
  const data={memberStations:{b:[row(1.7,'left'),row(1.7,'right',{...components,Vz:-7})]}};
  assert.equal(readNativeStation(data,'b',1.7000000000000002,'left').Vz,3);
  for(const position of [1.7-5e-10,1.7+5e-10])
    assert.throws(()=>readNativeStation(data,'b',position,'left'),/unavailable/);
  const split={memberStations:{a:[row(1.7,'left')],b:[row(0,'right',{...components,Vz:-7})]}};
  const mappings={elementSegments:{physical:[{id:'a',start:0,end:1.7},{id:'b',start:1.7,end:5}]}};
  assert.throws(()=>readNativeStation(split,'physical',1.7+5e-10,'left',mappings),/unavailable/);
});

test('requested quantities consume real native cuts with units and reject missing direction/evidence',()=>{
  const data=yjk.cases.D,member=Object.keys(data.memberStations)[0],cut=data.memberStations[member][0];
  const selection={kind:'case',id:'D'},analysis={results:{'case:D':{success:true,selection,data}}};
  const q={id:'native-cut',selection,location:{kind:'member',id:member,positionM:cut.positionM,side:cut.side},
    component:'M2',unit:'N.m',value:cut.components.My*1000,tolerance:{absolute:1e-8,relative:1e-8}};
  assert.equal(compareRequestedQuantities(analysis,[q]).pass,true);
  for(const change of [{component:'uz',unit:'m'},{location:{...q.location,side:'left'}},{selection:{kind:'case',id:'L'}}])
    assert.equal(compareRequestedQuantities(analysis,[{...q,...change}]).pass,false);
  const wrong=clone(analysis);wrong.results['case:D'].data.nativeContext.stationConventionsVerified=false;
  assert.equal(compareRequestedQuantities(wrong,[q]).pass,false);
  const noUnits=clone(analysis);delete noUnits.results['case:D'].data.units;
  assert.equal(compareRequestedQuantities(noUnits,[q]).pass,false);
});
