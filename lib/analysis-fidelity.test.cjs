const test=require('node:test');
const assert=require('node:assert/strict');
const {compareAnalysisResults}=require('./analysis-fidelity.cjs');
const end=(N,V3,M2)=>({N,V2:0,V3,T:0,M2,M3:0,V:V3,M:M2});
const expected={status:'success',analysisMode:'opensees_2d_frame',responseCoordinateConvention:'global-xyz',forces:{beam:{n1:end(10,5,-3),n2:end(-10,-5,3),localAxes:{x:[1,0,0],y:[0,1,0],z:[0,0,1]}}}};
const mappings={nodeMapping:{},elementMapping:{beam:'reverse'},elementOrientation:{beam:'reversed'},
  physicalAxes:{beam:[[1,0,0],[0,1,0],[0,0,1]]},elementSegments:{beam:[{id:'reverse',orientation:'reversed',localAxes:[[-1,0,0],[0,1,0],[0,0,-1]]}]}};
const actual=()=>({status:'success',analysisMode:'opensees_2d_frame',responseCoordinateConvention:'global-xyz',forces:{reverse:{n1:end(10,5,3),n2:end(-10,-5,-3),localAxes:{x:[-1,0,0],y:[0,1,0],z:[0,0,-1]}}}});
test('signed forces transform through actual local axes for reversed elements',()=>{
  const comparison=compareAnalysisResults(actual(),expected,mappings);assert.equal(comparison.pass,true,comparison.failures.join(';'));
});
test('an opposite signed moment cannot pass on equal magnitude',()=>{
  const wrong=actual();wrong.forces.reverse.n2.M2=3;wrong.forces.reverse.n2.M=3;
  assert.equal(compareAnalysisResults(wrong,expected,mappings).pass,false);
});
test('comparison selects the required case from the result collection',()=>{
  const wrong=actual();wrong.forces.reverse.n2.M2=100;
  const result={results:{'case:D':{data:wrong,selection:{kind:'case',id:'D'}},'combination:ULS':{data:actual(),selection:{kind:'combination',id:'ULS'}}}};
  assert.equal(compareAnalysisResults(result,expected,mappings,{selection:{kind:'combination',id:'ULS'}}).pass,true);
  assert.equal(compareAnalysisResults(result,expected,mappings,{selection:{kind:'case',id:'D'}}).pass,false);
  assert.equal(compareAnalysisResults(result,expected,mappings,{selection:{kind:'case',id:'missing'}}).pass,false);
});
test('unbound flat result and partial results cannot satisfy a required case',()=>{
  assert.equal(compareAnalysisResults(actual(),expected,mappings,{selection:{kind:'case',id:'D'}}).pass,false);
  const partial={...actual(),status:'partial'};
  assert.equal(compareAnalysisResults(partial,expected,mappings).pass,false);
});
test('physical endpoints come from first and last refined segments',()=>{
  const candidate=actual();candidate.forces={first:{n1:end(10,5,-3),n2:end(0,0,20)},last:{n1:end(0,0,-20),n2:end(-10,-5,3)}};
  const map={...mappings,elementMapping:{beam:'first'},elementSegments:{beam:[{id:'first',orientation:'same',localAxes:mappings.physicalAxes.beam},{id:'last',orientation:'same',localAxes:mappings.physicalAxes.beam}]}};
  const result=compareAnalysisResults(candidate,expected,map);assert.equal(result.pass,true,result.failures.join(';'));
  delete candidate.forces.last;
  assert.equal(compareAnalysisResults(candidate,expected,map).pass,false);
});
