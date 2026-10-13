const test=require('node:test');
const assert=require('node:assert/strict');
const {normalizeCommercialEngineResponse,compareCommercialEngineResponses}=require('./cross-engine-ground-truth.cjs');
const model={nodes:[{id:'a',z:0},{id:'b',z:3}],elements:[{id:'c',type:'column',nodes:['a','b']}]};
const response=()=>({caseKey:'DL',displacements:{b:{uz:-.001}},reactions:{},forces:{c:{N:-30,V:-2,M:6}}});
const mapping={nodeMapping:{b:'b'},elementMapping:{c:'c'},elementOrientation:{c:'same'}};
test('commercial numerical correctness compares signs as well as magnitudes',()=>{
  assert.equal(compareCommercialEngineResponses(response(),response(),mapping).pass,true);
  for(const key of ['N','V','M']) {const wrong=response();wrong.forces.c[key]*=-1;assert.equal(compareCommercialEngineResponses(wrong,response(),mapping).pass,false);}
});
test('commercial result requires the requested load case, never an implicit dead-load default',()=>{
  const raw={status:'success',caseResults:{DL:response(),LL:{...response(),forces:{c:{N:-10,V:-1,M:2}}}}};
  assert.throws(()=>normalizeCommercialEngineResponse('pkpm',model,raw),/explicit load case/);
  assert.throws(()=>normalizeCommercialEngineResponse('pkpm',model,raw,{caseKey:'ULS'}),/unavailable/);
  assert.equal(normalizeCommercialEngineResponse('pkpm',model,raw,{caseKey:'LL'}).forces.c.N,-10);
});
test('an unreviewed reversed/refined native envelope mapping cannot pass on absolute values',()=>{
  assert.equal(compareCommercialEngineResponses(response(),response(),{...mapping,elementOrientation:{c:'reversed'}}).pass,false);
  assert.equal(compareCommercialEngineResponses(response(),response(),{...mapping,elementSegments:{c:[{id:'c'},{id:'c2'}]}}).pass,false);
});
