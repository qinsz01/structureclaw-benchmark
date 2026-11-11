const test=require('node:test');
const assert=require('node:assert/strict');
const {compareRequestedQuantities,compareReportQuantities,evaluateDerivedQuantities}=require('./requested-quantities.cjs');
function fixture(){
  const terms=[.25,-.24,.20,-.21573248237696908],n=terms.length,u=2**-24;
  const scale=terms.reduce((a,b)=>a+Math.abs(b),0);
  const q={id:'moment',selection:{kind:'case',id:'D'},location:{kind:'member',id:'b',positionM:0,side:'right'},
    component:'M3',unit:'kN.m',value:-.005732506513595581,tolerance:{absolute:1e-8,relative:1e-6},
    rawTrace:{origin:'raw-sdk-member-end-cut',nativeRun:'native-test',sourceModelSha256:'b'.repeat(64),
      sourceSelection:{kind:'case',id:'D'},sourceFactors:{D:1},nativeBasicFactors:{DL:1},
      raw:[{nativeCase:'DL',factor:1}],end:0,sourceEndNodes:['a','z']},
    engineeringPrecision:{policy:'native-f32-recovery-scale-v1',kind:'analytical-recovery-scale',
      nativeArithmeticBound:false,acceptanceRegionChanges:true,unit:'kN.m',unitRoundoff:u,
      structuralTermCount:n,terms,recoveryScale:scale,absoluteAllowance:(2*n-1)*u/(1-(2*n-1)*u)*scale,
      certificateSha256:'a'.repeat(64)}};
  const analysis=value=>({results:{'case:D':{selection:q.selection,data:{memberResponses:[{id:'b',state:'recovered',
    samples:[{x:0,side:'right',M3:value}]}]}}}});
  return {q,analysis};
}
test('engineering allowance is diagnostic and cannot pass a strict frozen comparison',()=>{
  const {q,analysis}=fixture(),before=structuredClone(q);
  const result=compareRequestedQuantities(analysis(-.005732482376969078),[q]);
  assert.equal(result.pass,false,JSON.stringify(result));
  assert.equal(result.evidenceValid,true);assert.equal(result.strictPass,false);assert.equal(result.engineeringPass,true);
  assert.equal(result.failures.length,1);
  assert.equal(result.precision.strictPass,false);
  assert.equal(result.precision.engineeringPass,true);assert.equal(result.precision.diagnosticOnly,true);
  assert.equal(result.precision.strictFailures.length,1);
  assert.equal(result.precision.acceptanceRegionChanges,true);
  assert.deepEqual(q,before,'Frozen raw value and tolerance must not be overwritten');
  const {engineeringPrecision,...strict}=q;
  assert.equal(compareRequestedQuantities(analysis(-.005732482376969078),[strict]).pass,false);
});
test('reported body uses strict scoring with engineering diagnostics and rejects identity mistakes',()=>{
  const {q}=fixture();
  const markdown='| moment | case:D | b@0:right | M3 | -0.005732482376969078 | kN.m |';
  const result=compareReportQuantities({markdown},[q]);
  assert.equal(result.pass,false,JSON.stringify(result));assert.equal(result.precision.strictPass,false);
  assert.equal(result.evidenceValid,true);assert.equal(result.strictPass,false);assert.equal(result.engineeringPass,true);
  for(const text of [markdown.replace('-0.005','0.005'),markdown.replace('kN.m','N.m'),
    markdown.replace('case:D','combination:D'),markdown.replace('@0:right','@0:left')])
    assert.equal(compareReportQuantities({markdown:text},[q]).pass,false);
});
test('default tolerance is unchanged; engineering tolerance is explicitly diagnostic',()=>{
  const {comparisonTolerance,engineeringComparisonTolerance}=require('./reference-precision.cjs');
  const {q}=fixture(),before=structuredClone(q);
  assert.deepEqual(comparisonTolerance(q),q.tolerance);
  assert.ok(engineeringComparisonTolerance(q).absolute>q.tolerance.absolute);
  assert.deepEqual(q,before);
});
test('exact native values pass both modes including source-unit conversion',()=>{
  const {q,analysis}=fixture(),actual=analysis(q.value*1000);
  actual.results['case:D'].data.units={moment:'N.m'};
  const result=compareRequestedQuantities(actual,[q]);
  assert.equal(result.pass,true,JSON.stringify(result));assert.equal(result.evidenceValid,true);
  assert.equal(result.strictPass,true);assert.equal(result.engineeringPass,true);
  const report=compareReportQuantities({markdown:`| moment | case:D | b@0:right | M3 | ${q.value} | kN.m |`},[q]);
  assert.equal(report.pass,true);assert.equal(report.evidenceValid,true);
  assert.equal(report.strictPass,true);assert.equal(report.engineeringPass,true);
});
test('unit conversion does not change strict failure or turn engineering diagnostics into scoring',()=>{
  const {q,analysis}=fixture(),actual=analysis(-.005732482376969078*1000);
  actual.results['case:D'].data.units={moment:'N.m'};
  const result=compareRequestedQuantities(actual,[q]);
  assert.equal(result.evidenceValid,true);assert.equal(result.pass,false);
  assert.equal(result.strictPass,false);assert.equal(result.engineeringPass,true);
});
test('overflow during unit conversion is invalid evidence in both comparison modes',()=>{
  const {convertPrecision}=require('./reference-precision.cjs'),{q,analysis}=fixture();
  const target={...q,unit:'N.m',value:q.value*1000,
    tolerance:{...q.tolerance,absolute:q.tolerance.absolute*1000},engineeringPrecision:convertPrecision(q,'N.m',1000)};
  const result=compareRequestedQuantities(analysis(Number.MAX_VALUE),[target]);
  assert.equal(result.evidenceValid,false);assert.equal(result.pass,false);
  assert.equal(result.strictPass,false);assert.equal(result.engineeringPass,false);
});
test('missing, nonfinite and malformed evidence fail both modes even with an allowance',()=>{
  const {q,analysis}=fixture();
  for(const result of [compareRequestedQuantities(analysis(NaN),[q]),
    compareRequestedQuantities(analysis(q.value),[]),
    compareReportQuantities({markdown:'| moment | case:D | b@0:right | M3 | 1e999 | kN.m |'},[q]),
    compareReportQuantities({markdown:''},[q]),compareReportQuantities({},[])]){
    assert.equal(result.pass,false);assert.equal(result.evidenceValid,false);
    assert.equal(result.strictPass,false);assert.equal(result.engineeringPass,false);
  }
});
test('candidate self-declared uncertainty cannot expand a frozen strict reference',()=>{
  const {q,analysis}=fixture(),{engineeringPrecision,...strict}=q;
  const actual=analysis(-.005732482376969078);actual.engineeringPrecision={absoluteAllowance:1e6};
  actual.results['case:D'].data.engineeringPrecision={absoluteAllowance:1e6};
  assert.equal(compareRequestedQuantities(actual,[strict]).pass,false);
});
for(const [name,change] of [
  ['unknown policy',p=>p.policy='any-error-accepted'],
  ['false vendor error-bound claim',p=>p.nativeArithmeticBound=true],
  ['hidden region change',p=>p.acceptanceRegionChanges=false],
  ['wrong unit',p=>p.unit='N.m'],
  ['wrong arithmetic precision',p=>p.unitRoundoff=2**-20],
  ['wrong structural count',p=>p.structuralTermCount--],
  ['empty terms',p=>{p.terms=[];p.structuralTermCount=0;}],
  ['nonfinite term',p=>p.terms[0]=NaN],
  ['negative scale',p=>p.recoveryScale=-1],
  ['inflated scale',p=>p.recoveryScale*=2],
  ['inflated budget',p=>p.absoluteAllowance*=2],
  ['unbound certificate',p=>delete p.certificateSha256],
])test(`malformed reference precision rejects ${name}`,()=>{
  const {q,analysis}=fixture();change(q.engineeringPrecision);
  const result=compareRequestedQuantities(analysis(q.value),[q]);
  assert.equal(result.pass,false);assert.equal(result.evidenceValid,false);assert.equal(result.engineeringPass,false);
});
test('the first policy does not authorize reaction, displacement, combination or derived allowances',()=>{
  const {q,analysis}=fixture();
  for(const changed of [{...q,component:'My',location:{kind:'node',id:'a'}},
    {...q,component:'ux',unit:'m'},{...q,selection:{kind:'combination',id:'D'}}])
    assert.equal(compareRequestedQuantities(analysis(q.value),[changed]).pass,false);
  const d=[{id:'derived',operation:'sum',operands:[q.id],unit:q.unit}];
  assert.equal(evaluateDerivedQuantities([q],d).pass,false,'Derived propagation requires its own reviewed policy');
});
test('differences outside the independently computed engineering allowance still fail',()=>{
  const {q,analysis}=fixture();
  assert.equal(compareRequestedQuantities(analysis(q.value+1e-4),[q]).pass,false);
  assert.equal(compareRequestedQuantities(analysis(NaN),[q]).pass,false);
});
test('precision requires an original native basic-case endpoint trace',()=>{
  for(const change of [q=>delete q.rawTrace,q=>q.rawTrace.origin='derived-native-superposition',
    q=>q.rawTrace.nativeBasicFactors={DL:2,LL:1},q=>q.rawTrace.raw[0].factor=2,
    q=>q.rawTrace.sourceFactors={D:2},q=>q.rawTrace.sourceSelection.kind='combination',
    q=>q.location.positionM=1.5,q=>q.location.side='left',q=>q.rawTrace.end=2]){
    const {q,analysis}=fixture();change(q);
    assert.equal(compareRequestedQuantities(analysis(q.value),[q]).pass,false);
  }
});
