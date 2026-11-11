const test=require('node:test');const assert=require('node:assert/strict');
const {compareRequestedQuantities,compareReportQuantities,evaluateDerivedQuantities,compareDerivedQuantities}=require('./requested-quantities.cjs');
const {classifyRequirement}=require('./requirement-semantics.cjs');
const q={id:'V-left',selection:{kind:'case',id:'D'},location:{kind:'member',id:'b',positionM:2,side:'left'},component:'V3',unit:'kN',value:.25,tolerance:{absolute:1e-10,relative:1e-8}};
const result=()=>({results:{'case:D':{success:true,selection:q.selection,data:{memberResponses:[{id:'b',state:'recovered',samples:[{x:2,side:'left',V3:.25,displacement:[0,0,-.001]},{x:2,side:'right',V3:-.25,displacement:[0,0,-.001]}]}]}}}});
test('exact physical station and left/right discontinuity are numerical requirements',()=>{
  assert.equal(compareRequestedQuantities(result(),[q]).pass,true);
  for(const changed of [{...q,location:{...q.location,side:'right'}},{...q,unit:'N'},{...q,selection:{kind:'case',id:'L'}},{...q,location:{...q.location,positionM:2.01}}]) assert.equal(compareRequestedQuantities(result(),[changed]).pass,false);
  const r=result();r.results['case:D'].data.memberResponses[0].state='interpolated';assert.equal(compareRequestedQuantities(r,[q]).pass,false);
  const missing=result();missing.results['case:D'].data.memberResponses[0].samples=[{x:2,side:'right',V3:.25}];assert.equal(compareRequestedQuantities(missing,[q]).pass,false);
  assert.equal(compareRequestedQuantities(result(),[{...q,location:{...q.location,positionM:2+5e-10}}]).pass,false);
  assert.equal(compareRequestedQuantities(result(),[{...q,unit:'N',value:250}]).pass,true);
  assert.equal(compareRequestedQuantities(result(),[{...q,unit:'mm'}]).pass,false);
  const source=result();source.results['case:D'].meta={units:{force:'N'}};
  assert.equal(compareRequestedQuantities(source,[q]).pass,false);
});
test('requested body row checks signed number, case, exact position and unit',()=>{
  const markdown='| V-left | case:D | b@2:left | V3 | 0.25 | kN |';
  assert.equal(compareReportQuantities({markdown},[q]).pass,true);
  for(const text of [markdown.replace('0.25','-0.25'),markdown.replace('kN','N'),markdown.replace('case:D','case:L'),markdown.replace('@2:left','@2:right'),'Only JSON contains the correct values']) assert.equal(compareReportQuantities({markdown:text},[q]).pass,false);
});
test('prohibitions and physical pins are not promoted to required release, offset or nonlinear capability',()=>{
  for(const text of ['中支座无内铰','不启用P-Delta','不做非线性','不新增刚性楼板、未声明刚臂或规范默认组合','全部真实弹性梁柱而非刚臂']) {
    const row=classifyRequirement(text,'engine.analysisContract');
    assert.ok(row.atoms.length);assert.ok(row.atoms.every(a=>a.kind==='forbidden'),JSON.stringify(row));
  }
  assert.equal(classifyRequirement('端部释放','task.scenario').atoms[0].kind,'required');
  assert.equal(classifyRequirement('柱底弯矩','task.expectedOutput').kind,'output');
});

function derivedFixture() {
  const quantities=[
    {id:'dead',selection:{kind:'case',id:'D'},location:{kind:'node',id:'a'},component:'Fy',unit:'kN',value:-5,tolerance:{absolute:1e-8,relative:1e-6}},
    {id:'total',selection:{kind:'combination',id:'D'},location:{kind:'node',id:'a'},component:'Fy',unit:'N',value:4000,tolerance:{absolute:1e-5,relative:1e-6}},
  ];
  const derived=[
    {id:'delta',operation:'difference',operands:['dead','total'],unit:'kN'},
    {id:'largest',operation:'max',operands:['dead','total'],unit:'N'},
    {id:'smallest',operation:'min',operands:['dead','total'],unit:'kN'},
    {id:'envelope',operation:'max_abs',operands:['dead','total'],unit:'kN'},
  ];
  const analysis={results:{
    'case:D':{selection:{kind:'case',id:'D'},data:{reactions:{a:{fy:-5}}}},
    'combination:D':{selection:{kind:'combination',id:'D'},data:{reactions:{a:{fy:4}}}},
  }};
  return {quantities,derived,analysis};
}
test('contract reaction components Fx through Mz read lowercase or contract-cased solver fields',()=>{
  for(const [component,unit] of [['Fx','kN'],['Fy','kN'],['Fz','kN'],['Mx','kN.m'],['My','kN.m'],['Mz','kN.m']]) {
    const {quantities,analysis}=derivedFixture();
    const quantity={...quantities[0],component,unit};
    for(const source of [component,component.toLowerCase()]) {
      analysis.results['case:D'].data.reactions.a={[source]:-5};
      assert.equal(compareRequestedQuantities(analysis,[quantity]).pass,true,component);
    }
  }
});
test('independent derivation converts signed units and retains the max_abs governor',()=>{
  const {quantities,derived}=derivedFixture();
  const result=evaluateDerivedQuantities(quantities,derived);
  assert.equal(result.pass,true,result.failures.join('; '));
  assert.deepEqual(result.values.map(({id,value})=>[id,value]),[['delta',-9],['largest',4000],['smallest',-5],['envelope',-5]]);
  assert.deepEqual(result.values[3].governingSelection,{kind:'case',id:'D'});
  assert.equal(result.values[3].governingOperand,'dead');
  assert.equal(result.values[0].governingOperand,null);
  assert.equal(result.values[0].tolerance.relative,0);
  assert.ok(Math.abs(result.values[0].tolerance.absolute-0.00000902)<1e-15);
});
test('extrema ties follow frozen operand order and nested derivations resolve forward references',()=>{
  const {quantities}=derivedFixture();quantities[1].value=5000;
  const derived=[{id:'outer',operation:'max_abs',operands:['tie'],unit:'N'},
    {id:'tie',operation:'max_abs',operands:['total','dead'],unit:'kN'}];
  const result=evaluateDerivedQuantities(quantities,derived);
  assert.equal(result.pass,true,result.failures.join('; '));
  assert.equal(result.values[0].value,5000);
  assert.equal(result.values[0].governingOperand,'tie');
  assert.deepEqual(result.values[0].governingSelection,{kind:'combination',id:'D'});
  assert.equal(result.values[1].governingOperand,'total');
  derived[1].operands.reverse();
  assert.equal(evaluateDerivedQuantities(quantities,derived).values[0].value,-5000);
});
for(const [name,change] of [
  ['missing operand',f=>f.derived[0].operands[0]='missing'],
  ['duplicate primitive ID',f=>f.quantities.push({...f.quantities[0]})],
  ['duplicate derived ID',f=>f.derived.push({...f.derived[0]})],
  ['primitive/derived ID collision',f=>f.derived[0].id='dead'],
  ['cycle',f=>{f.derived[0].operands=['largest','dead'];f.derived[1].operands=['delta'];}],
  ['incompatible output unit',f=>f.derived[0].unit='mm'],
  ['incompatible operand units',f=>f.quantities[1].unit='m'],
  ['unsupported operation',f=>f.derived[0].operation='product'],
  ['difference with one operand',f=>f.derived[0].operands=['dead']],
  ['empty extrema',f=>f.derived[1].operands=[]],
  ['nonfinite independent value',f=>f.quantities[0].value=Infinity],
  ['invalid frozen tolerance',f=>f.quantities[0].tolerance.relative=-1],
  ['invalid derived tolerance',f=>f.derived[0].tolerance={absolute:-1,relative:0}],
  ['malformed primitive',f=>f.quantities[0]=null],
  ['malformed derived',f=>f.derived[0]=null],
]) test(`${name} is rejected by independent derivation`,()=>{
  const fixture=derivedFixture();change(fixture);
  assert.equal(evaluateDerivedQuantities(fixture.quantities,fixture.derived).pass,false);
});
test('derivation rejects arithmetic overflow after finite inputs',()=>{
  const {quantities,derived}=derivedFixture();
  quantities[0].value=Number.MAX_VALUE;quantities[1].value=-Number.MAX_VALUE;
  quantities[1].unit='kN';
  assert.equal(evaluateDerivedQuantities(quantities,derived).pass,false);
});
test('derived comparisons use independent frozen values and exact case/combination selection',()=>{
  const {analysis,quantities,derived}=derivedFixture();
  assert.equal(compareDerivedQuantities(analysis,quantities,derived).pass,true);
  analysis.results['case:D'].data.reactions.a.fy=3;
  analysis.derived=[{id:'delta',value:-9,unit:'kN'},{id:'envelope',value:-5,unit:'kN'}];
  assert.equal(compareDerivedQuantities(analysis,quantities,derived).pass,false);
  const other=derivedFixture();delete other.analysis.results['combination:D'];
  assert.equal(compareDerivedQuantities(other.analysis,other.quantities,other.derived).pass,false);
});
test('supplied derived reports must include each value and its signed governing selection',()=>{
  const {analysis,quantities,derived}=derivedFixture();
  const reported=evaluateDerivedQuantities(quantities,derived).values;
  assert.equal(compareDerivedQuantities(analysis,quantities,derived,{},reported).pass,true);
  for(const change of [rows=>rows.pop(),rows=>rows[3].value=5,
    rows=>rows[3].governingOperand='total',rows=>rows[3].governingSelection.kind='combination',
    rows=>rows.push({...rows[0]}),rows=>delete rows[3].governingSelection,rows=>rows[3].value=NaN,
    rows=>rows.push({id:'invented',value:0,unit:'kN'})]) {
    const rows=structuredClone(reported);change(rows);
    assert.equal(compareDerivedQuantities(analysis,quantities,derived,{},rows).pass,false);
  }
  const converted=structuredClone(reported);converted[3].unit='N';converted[3].value=-5000;
  assert.equal(compareDerivedQuantities(analysis,quantities,derived,{},converted).pass,true);
});
test('a tighter frozen derived tolerance is checked even when every primitive passes',()=>{
  const {analysis,quantities,derived}=derivedFixture();
  derived[3].tolerance={absolute:1e-10,relative:0};
  analysis.results['case:D'].data.reactions.a.fy=-5+1e-6;
  const result=compareDerivedQuantities(analysis,quantities,derived);
  assert.equal(result.primitiveComparison.pass,true);
  assert.equal(result.pass,false);
  assert.match(result.failures.join('; '),/envelope: derived/);
  assert.equal(result.values[3].value,-5);
});
test('duplicate, malformed, and omitted primitives fail without crashing',()=>{
  const {analysis,quantities,derived}=derivedFixture();
  assert.equal(compareRequestedQuantities(analysis,[quantities[0],quantities[0]]).pass,false);
  assert.equal(compareRequestedQuantities(analysis,[null]).pass,false);
  assert.equal(compareDerivedQuantities(analysis,[],derived).pass,false);
  assert.equal(evaluateDerivedQuantities(quantities.slice(1),derived).pass,false);
});
test('primitive IDs are scoped to selection and only ambiguous derived references fail',()=>{
  const {analysis,quantities}=derivedFixture();quantities[1].id='dead';
  assert.equal(compareRequestedQuantities(analysis,quantities).pass,true);
  assert.equal(evaluateDerivedQuantities(quantities,[]).pass,true);
  const result=evaluateDerivedQuantities(quantities,[{id:'ambiguous',operation:'max_abs',operands:['dead'],unit:'kN'}]);
  assert.equal(result.pass,false);
  assert.match(result.failures.join('; '),/Ambiguous operand/);
});
test('report row identity includes selection, and duplicate or malformed numeric rows fail',()=>{
  const {quantities}=derivedFixture();quantities[1].id='dead';
  const markdown='| dead | case:D | a | Fy | -5 | kN |\n| dead | combination:D | a | Fy | 4000 | N |';
  assert.equal(compareReportQuantities({markdown},quantities).pass,true);
  for(const text of [markdown+'\n| dead | case:D | a | Fy | -5 | kN |',
    markdown.replace('4000',''),markdown.replace('4000','0xFA0'),markdown.replace('4000','Infinity')])
    assert.equal(compareReportQuantities({markdown:text},quantities).pass,false);
  assert.equal(compareReportQuantities({markdown},[null]).pass,false);
  const zero={...quantities[0],value:0};
  assert.equal(compareReportQuantities({markdown:'| dead | case:D | a | Fy | | kN |'},[zero]).pass,false);
  assert.equal(compareReportQuantities({markdown:'| dead | case:D | a | Fy | +0.0e0 | kN |'},[zero]).pass,true);
});
test('sum converts signed operands and preserves small residuals after cancellation',()=>{
  const {quantities}=derivedFixture();
  const values=[{value:1e16,unit:'kN'},{value:1000,unit:'N'},{value:-1e19,unit:'N'}];
  const frozen=values.map((value,index)=>({...quantities[0],id:`reaction-${index}`,...value,tolerance:{absolute:0,relative:0}}));
  const derived=[{id:'total-reaction',operation:'sum',operands:frozen.map(q=>q.id),unit:'kN'}];
  const result=evaluateDerivedQuantities(frozen,derived);
  assert.equal(result.pass,true,result.failures.join('; '));
  assert.equal(result.values[0].value,1);
  assert.deepEqual(result.values[0].selection,{kind:'case',id:'D'});
  assert.equal(result.values[0].governingOperand,null);
  derived[0].operands.reverse();
  assert.equal(evaluateDerivedQuantities(frozen,derived).values[0].value,1);
  derived[0].operands=[];
  assert.equal(evaluateDerivedQuantities(frozen,derived).pass,false);
});
test('sum propagates converted tolerance and rejects missing, incompatible, or overflowing inputs',()=>{
  const {quantities}=derivedFixture();
  const derived=[{id:'total-reaction',operation:'sum',operands:['dead','total'],unit:'kN'}];
  const result=evaluateDerivedQuantities(quantities,derived);
  assert.equal(result.pass,true,result.failures.join('; '));
  assert.equal(result.values[0].value,-1);
  assert.ok(Math.abs(result.values[0].tolerance.absolute-0.00000902)<1e-15);
  assert.equal(result.values[0].selection,undefined);
  for(const change of [q=>q.pop(),q=>q[1].unit='mm',q=>{q[0].value=Number.MAX_VALUE;q[1].value=Number.MAX_VALUE;q[1].unit='kN';}]) {
    const changed=structuredClone(quantities);change(changed);
    assert.equal(evaluateDerivedQuantities(changed,derived).pass,false);
  }
});
test('nested drift difference and sum preserve the governing combination for envelopes',()=>{
  const {quantities}=derivedFixture();
  const combination={kind:'combination',id:'EQ-X'};
  const frozen=[-0.012,-0.002,0.001].map((value,index)=>({...quantities[0],id:`floor-${index}`,selection:combination,
    component:'ux',unit:'m',value,tolerance:{absolute:1e-8,relative:1e-6}}));
  const derived=[
    {id:'story-drift',operation:'difference',operands:['floor-0','floor-1'],unit:'m'},
    {id:'combined-drift',operation:'sum',operands:['story-drift','floor-2'],unit:'m'},
    {id:'governing-drift',operation:'max_abs',operands:['story-drift','combined-drift'],unit:'mm'},
  ];
  const result=evaluateDerivedQuantities(frozen,derived);
  assert.equal(result.pass,true,result.failures.join('; '));
  assert.deepEqual(result.values[0].selection,combination);
  assert.deepEqual(result.values[1].selection,combination);
  assert.equal(result.values[2].value,-10);
  assert.equal(result.values[2].governingOperand,'story-drift');
  assert.deepEqual(result.values[2].governingSelection,combination);
  frozen[1].selection={kind:'case',id:'EQ-X'};
  const mixed=evaluateDerivedQuantities(frozen,derived);
  assert.equal(mixed.pass,true);
  assert.equal(mixed.values[0].selection,undefined);
  assert.equal(mixed.values[1].selection,undefined);
  assert.equal(mixed.values[2].governingSelection,null);
});
test('derived report sum is recomputed from signed solver responses',()=>{
  const {quantities,analysis}=derivedFixture();
  const derived=[{id:'sum-reaction',operation:'sum',operands:['dead','total'],unit:'kN'}];
  const report=[{id:'sum-reaction',value:-1,unit:'kN',governingOperand:null,governingSelection:null}];
  assert.equal(compareDerivedQuantities(analysis,quantities,derived,{},report).pass,true);
  report[0].value=1;
  assert.equal(compareDerivedQuantities(analysis,quantities,derived,{},report).pass,false);
});
test('derived reports accept public node governors with exact case or combination identity',()=>{
  const {quantities,analysis,derived}=derivedFixture();
  const frozen=evaluateDerivedQuantities(quantities,derived).values;
  const report=structuredClone(frozen);
  for(const row of report) if(row.governingOperand!==null) row.governingOperand='a';
  const result=compareDerivedQuantities(analysis,quantities,derived,{},report);
  assert.equal(result.pass,true,result.failures.join('; '));
  assert.equal(result.values[3].governingOperand,'dead');
  for(const change of [rows=>rows[3].governingOperand='other-node',rows=>rows[3].governingSelection.kind='combination',
    rows=>rows[3].value=5,rows=>rows[3].governingLocation={kind:'member',id:'a',positionM:0,side:'right'}]) {
    const changed=structuredClone(report);change(changed);
    assert.equal(compareDerivedQuantities(analysis,quantities,derived,{},changed).pass,false);
  }
});
test('public member governors require exact station location when member identity is ambiguous',()=>{
  const quantities=[{...q,id:'hidden-left'}, {...q,id:'hidden-right',value:-.25,location:{...q.location,side:'right'}}];
  const derived=[{id:'shear-envelope',operation:'max_abs',operands:['hidden-left','hidden-right'],unit:'kN'}];
  const report=[{id:'shear-envelope',value:.25,unit:'kN',governingOperand:'b',governingSelection:q.selection}];
  const ambiguous=compareDerivedQuantities(result(),quantities,derived,{},report);
  assert.equal(ambiguous.pass,false);
  assert.match(ambiguous.failures.join('; '),/governingLocation/);
  report[0].governingLocation={...q.location};
  assert.equal(compareDerivedQuantities(result(),quantities,derived,{},report).pass,true);
  for(const change of [row=>row.governingLocation.side='right',row=>row.governingLocation.positionM=2.01,
    row=>row.governingLocation.kind='node',row=>delete row.governingLocation.side,
    row=>{row.governingOperand='hidden-left';row.governingLocation.side='right';}]) {
    const changed=structuredClone(report);change(changed[0]);
    assert.equal(compareDerivedQuantities(result(),quantities,derived,{},changed).pass,false);
  }
  report[0].governingOperand='hidden-left';delete report[0].governingLocation;
  assert.equal(compareDerivedQuantities(result(),quantities,derived,{},report).pass,true);
});
test('nested extrema map public governors through the computed winning primitive',()=>{
  const {quantities,analysis}=derivedFixture();
  const derived=[{id:'inner',operation:'max_abs',operands:['dead','total'],unit:'kN'},
    {id:'outer',operation:'max_abs',operands:['inner'],unit:'kN'}];
  const report=evaluateDerivedQuantities(quantities,derived).values.map(row=>({...row,governingOperand:'a'}));
  assert.equal(compareDerivedQuantities(analysis,quantities,derived,{},report).pass,true);
  report[1].governingOperand='dead';
  assert.equal(compareDerivedQuantities(analysis,quantities,derived,{},report).pass,true);
  report[1].governingOperand='total';
  assert.equal(compareDerivedQuantities(analysis,quantities,derived,{},report).pass,false);
});
test('public member aliases cannot alter the actual deterministic governing station',()=>{
  const quantities=[{...q,id:'hidden-left'}, {...q,id:'hidden-right',value:-.25,location:{...q.location,side:'right'}}];
  const derived=[{id:'shear-envelope',operation:'max_abs',operands:['hidden-left','hidden-right'],unit:'kN',tolerance:{absolute:1e-10,relative:0}}];
  const analysis=result();analysis.results['case:D'].data.memberResponses[0].samples[1].V3=-.250000001;
  const report=[{id:'shear-envelope',value:.25,unit:'kN',governingOperand:'b',governingSelection:q.selection,governingLocation:q.location}];
  const compared=compareDerivedQuantities(analysis,quantities,derived,{},report);
  assert.equal(compared.primitiveComparison.pass,true);
  assert.equal(compared.pass,false);
  assert.match(compared.failures.join('; '),/derived governing operand or selection differs/);
});
test('moment aliases are compatible in source, frozen, report, and derived units',()=>{
  const {quantities,analysis}=derivedFixture();
  quantities[0]={...quantities[0],component:'Mz',unit:'kN*m'};
  quantities[1]={...quantities[1],component:'Mz',unit:'N*m'};
  analysis.results['case:D'].data={units:{moment:'N*m'},reactions:{a:{mz:-5000}}};
  analysis.results['combination:D'].data={units:{moment:'kN·m'},reactions:{a:{mz:4}}};
  assert.equal(compareRequestedQuantities(analysis,quantities).pass,true);
  const markdown='| dead | case:D | a | Mz | -5 | kN.m |\n| total | combination:D | a | Mz | 4000 | N.m |';
  assert.equal(compareReportQuantities({markdown},quantities).pass,true);
  const derived=[{id:'moment-difference',operation:'difference',operands:['dead','total'],unit:'kN·m'}];
  const report=[{id:'moment-difference',value:-9000,unit:'N*m'}];
  assert.equal(compareDerivedQuantities(analysis,quantities,derived,{},report).pass,true);
  assert.equal(compareReportQuantities({markdown:markdown.replace('kN.m','kN')},quantities).pass,false);
  assert.equal(evaluateDerivedQuantities(quantities,[{...derived[0],unit:'kN'}]).pass,false);
});
function tieFixture() {
  const selection={kind:'case',id:'AXIAL'};
  const quantities=[['TC2',-19.2],['BC3',19.2+2e-14],['OTHER',19.199]].map(([id,value])=>({
    ...q,id:`private-${id}`,selection,location:{kind:'member',id,positionM:0,side:'right'},component:'N',value,
    tolerance:{absolute:1e-8,relative:1e-6},
  }));
  const analysis={results:{'case:AXIAL':{selection,data:{memberResponses:quantities.map(q=>({id:q.location.id,state:'recovered',
    samples:[{x:0,side:'right',N:q.value}]}))}}}};
  const derived=[{id:'axial-envelope',operation:'max_abs',operands:quantities.map(q=>q.id),unit:'kN'}];
  return {quantities,analysis,derived};
}
test('opposite-sign roundoff ties canonically choose the first frozen tolerance co-governor',()=>{
  const {quantities,analysis,derived}=tieFixture();
  const frozen=evaluateDerivedQuantities(quantities,derived);
  assert.equal(frozen.pass,true,frozen.failures.join('; '));
  assert.equal(frozen.values[0].value,-19.2);
  assert.equal(frozen.values[0].governingOperand,'private-TC2');
  assert.deepEqual(frozen.values[0].coGoverningOperands,['private-TC2','private-BC3']);
  analysis.results['case:AXIAL'].data.memberResponses[1].samples[0].N=19.2-2e-14;
  assert.equal(compareDerivedQuantities(analysis,quantities,derived).pass,true);
  const row={id:'axial-envelope',value:19.2,unit:'kN',governingOperand:'BC3',governingSelection:quantities[1].selection};
  assert.equal(compareDerivedQuantities(analysis,quantities,derived,{},[row]).pass,false);
  derived[0].tolerance={absolute:0,relative:0};
  const exact=evaluateDerivedQuantities(quantities,derived);
  assert.deepEqual(exact.values[0].coGoverningOperands,['private-BC3']);
  assert.equal(exact.values[0].value,quantities[1].value);
});
test('any tie policy checks signed values against the specifically selected public co-governor',()=>{
  const {quantities,analysis,derived}=tieFixture();derived[0].tiePolicy='any';
  const row={id:'axial-envelope',value:-19.2,unit:'kN',governingOperand:'TC2',governingSelection:quantities[0].selection};
  assert.equal(compareDerivedQuantities(analysis,quantities,derived,{},[row]).pass,true);
  row.value=19.2;row.governingOperand='BC3';
  assert.equal(compareDerivedQuantities(analysis,quantities,derived,{},[row]).pass,true);
  for(const changed of [{...row,value:-19.2},{...row,governingOperand:'TC2'},
    {...row,governingOperand:'OTHER',value:19.199},{...row,governingSelection:{kind:'combination',id:'AXIAL'}},
    {...row,governingLocation:{kind:'member',id:'BC3',positionM:0,side:'left'}}])
    assert.equal(compareDerivedQuantities(analysis,quantities,derived,{},[changed]).pass,false);
  assert.equal(compareDerivedQuantities(analysis,quantities,derived,{},[row]).values[0].value,-19.2);
});
test('max and min use score-based frozen co-sets and reject invalid tie policy or recorded co-set',()=>{
  const {quantities,derived}=tieFixture();
  quantities[0].value=19.2;
  derived[0].operation='max';
  assert.deepEqual(evaluateDerivedQuantities(quantities,derived).values[0].coGoverningOperands,['private-TC2','private-BC3']);
  quantities[0].value=-19.2;quantities[1].value=-19.2-2e-14;quantities[2].value=-19.199;
  derived[0].operation='min';
  assert.equal(evaluateDerivedQuantities(quantities,derived).values[0].value,-19.2);
  derived[0].coGoverningOperands=['private-BC3'];
  assert.equal(evaluateDerivedQuantities(quantities,derived).pass,false);
  delete derived[0].coGoverningOperands;derived[0].tiePolicy='random';
  assert.equal(evaluateDerivedQuantities(quantities,derived).pass,false);
  derived[0].tiePolicy='any';derived[0].operation='sum';
  assert.equal(evaluateDerivedQuantities(quantities,derived).pass,false);
});
test('public arithmetic reports need no hidden null governor fields',()=>{
  const {quantities,analysis}=derivedFixture();
  for(const operation of ['difference','sum']) {
    const derived=[{id:'arithmetic',operation,operands:['dead','total'],unit:'kN'}];
    const report=[{id:'arithmetic',value:operation==='difference'?-9:-1,unit:'kN'}];
    assert.equal(compareDerivedQuantities(analysis,quantities,derived,{},report).pass,true);
    report[0].governingOperand='a';report[0].governingSelection=quantities[0].selection;
    assert.equal(compareDerivedQuantities(analysis,quantities,derived,{},report).pass,false);
  }
});
test('a unique public selection identifies a nested arithmetic governor without hidden IDs',()=>{
  const {quantities:base}=derivedFixture();
  const selections=[{kind:'combination',id:'ULS-1'},{kind:'combination',id:'ULS-2'}];
  const quantities=[-.012,-.002,.003,.001].map((value,index)=>({...base[0],id:`hidden-${index}`,
    selection:selections[Math.floor(index/2)],location:{kind:'node',id:`node-${index}`},component:'ux',unit:'m',value}));
  const derived=[{id:'private-drift-1',operation:'difference',operands:['hidden-0','hidden-1'],unit:'m'},
    {id:'private-drift-2',operation:'difference',operands:['hidden-2','hidden-3'],unit:'m'},
    {id:'drift-envelope',operation:'max_abs',operands:['private-drift-1','private-drift-2'],unit:'mm'}];
  const analysis={results:Object.fromEntries(selections.map(selection=>[`${selection.kind}:${selection.id}`,{selection,
    data:{displacements:Object.fromEntries(quantities.filter(q=>q.selection===selection).map(q=>[q.location.id,{ux:q.value}]))}}]))};
  const report=[{id:'drift-envelope',value:-10,unit:'mm',governingOperand:'combination:ULS-1',governingSelection:selections[0]}];
  const compare=()=>compareDerivedQuantities(analysis,quantities,derived,{},report,['drift-envelope']);
  assert.equal(compare().pass,true,compare().failures.join('; '));
  report[0].governingOperand='combination:ULS-2';
  assert.equal(compare().pass,false);
  report[0].governingOperand='combination:ULS-1';report[0].governingSelection={kind:'case',id:'ULS-1'};
  assert.equal(compare().pass,false);
  report[0].governingSelection=selections[0];report[0].governingOperand='node-0';
  assert.equal(compare().pass,false);
  report[0].governingOperand='combination:ULS-1';
  for(const quantity of quantities.slice(2)) {
    quantity.selection=selections[0];
    analysis.results['combination:ULS-1'].data.displacements[quantity.location.id]={ux:quantity.value};
  }
  const ambiguous=compare();
  assert.equal(ambiguous.pass,false);
  assert.match(ambiguous.failures.join('; '),/selection.*ambiguous/);
});

test('constant axial-only member evidence permits an interior cut without inventing sampled stations',()=>{
  const model={analysis_control:{self_weight:false},nodes:[{id:'a',x:0,y:0,z:0},{id:'b',x:4,y:0,z:0}],elements:[{id:'b',type:'truss',nodes:['a','b']}],load_cases:[{id:'D',loads:[{type:'nodal',node:'b',fz:-1}]}]};
  const axial={...q,component:'N',location:{...q.location,positionM:1.25},value:-2};
  const analysis={results:{'case:D':{selection:q.selection,data:{memberResponses:[{id:'b',state:'truss',length:4,samples:[{x:0,side:'right',N:-2},{x:2,N:-2},{x:4,side:'left',N:-2}]}]}}}};
  assert.equal(compareRequestedQuantities(analysis,[axial],{model}).pass,true);
  assert.equal(compareRequestedQuantities(analysis,[axial]).pass,false);
  for(const mutate of [m=>m.analysis_control.self_weight=true,m=>m.elements[0].type='beam',m=>m.load_cases[0].loads.push({type:'distributed',element:'b',fz:-1})]) {
    const changed=structuredClone(model);mutate(changed);assert.equal(compareRequestedQuantities(analysis,[axial],{model:changed}).pass,false);
  }
  for(const mutate of [r=>r.samples[1].N=-2.1,r=>r.samples.pop(),r=>r.state='recovered',r=>r.length=5]) {
    const changed=structuredClone(analysis);mutate(changed.results['case:D'].data.memberResponses[0]);assert.equal(compareRequestedQuantities(changed,[axial],{model}).pass,false);
  }
  assert.equal(compareRequestedQuantities(analysis,[{...axial,location:{...axial.location,positionM:4.1}}],{model}).pass,false);
});

test('only a free unloaded crossing permits either orientation of its zero balance residual',()=>{
  const {equilibriumDifferenceIds}=require('./requested-quantities.cjs');
  const model={coordinate_system:{dimension:'2d'},analysis_control:{self_weight:false},nodes:[{id:'c',x:0,y:0,z:0,restraints:[false,true,false,true,true,true]},...[[1,1],[-1,-1],[1,-1],[-1,1]].map(([x,z],i)=>({id:'n'+i,x,y:0,z}))],elements:[0,1,2,3].map(i=>({id:'e'+i,type:'truss',nodes:['c','n'+i]})),load_cases:[{id:'D',loads:[]}]};
  const qs=[0,1,2,3].map(i=>({...q,id:'q'+i,component:'N',location:{kind:'member',id:'e'+i,positionM:0,side:'right'}}));
  const ds=[{id:'balance',operation:'difference',operands:['q0','q1']},{id:'other',operation:'difference',operands:['q0','q2']}];
  const instruction='Force equilibrium at c along its two independent crossing-diagonal directions';
  assert.deepEqual(equilibriumDifferenceIds(model,qs,ds,instruction),['balance']);
  for(const mutate of [m=>m.nodes[0].restraints[0]=true,m=>m.load_cases[0].loads.push({type:'nodal',node:'c',fx:1}),m=>m.elements[2].type='beam',m=>m.nodes[2].z=-1.1,m=>m.elements.pop(),m=>m.analysis_control.self_weight=true]) {
    const changed=structuredClone(model);mutate(changed);assert.deepEqual(equilibriumDifferenceIds(changed,qs,ds,instruction),[]);
  }
  assert.deepEqual(equilibriumDifferenceIds(model,qs,ds,'Report q0 minus q1'),[]);
});

test('compatible displayed units are accepted only when explicitly authorized, using unchanged frozen tolerance',()=>{
  const requested={...q,location:{kind:'node',id:'n'},component:'uz',unit:'m',value:-.001};
  const report={markdown:`| ${q.id} | case:D | n | uz | -1 | mm |`};
  assert.equal(compareReportQuantities(report,[requested]).pass,false);
  assert.equal(compareReportQuantities(report,[requested],{equivalentUnitIds:[q.id]}).pass,true);
  for(const markdown of [report.markdown.replace('-1','1'),report.markdown.replace('-1','-0.001'),report.markdown.replace('mm','kN'),report.markdown.replace('-1','-1.01')])assert.equal(compareReportQuantities({markdown},[requested],{equivalentUnitIds:[q.id]}).pass,false);
});

test('loads on other frame members do not invalidate an unloaded axial brace proof',()=>{
  const {unloadedAxialMember}=require('./requested-quantities.cjs');
  const model={analysis_control:{self_weight:false},nodes:[{id:'a',x:0,y:0,z:0},{id:'b',x:4,y:0,z:0}],elements:[{id:'brace',type:'truss',nodes:['a','b']},{id:'beam',type:'beam',nodes:['a','b']}],load_cases:[{id:'D',loads:[{type:'distributed',element:'beam',wz:-8}]}],load_combinations:[{id:'D',factors:{D:1}}]};
  assert.ok(unloadedAxialMember(model,'brace',{kind:'combination',id:'D'}));
  model.load_cases[0].loads[0].element='brace';assert.equal(unloadedAxialMember(model,'brace',{kind:'case',id:'D'}),null);
  model.load_cases[0].loads[0].element='unknown';assert.equal(unloadedAxialMember(model,'brace',{kind:'case',id:'D'}),null);
});

test('reversing an unloaded truss preserves positive-tension N, while reversed beams remain strict',()=>{
  const model={analysis_control:{self_weight:false},nodes:[{id:'a',x:0,y:0,z:0},{id:'b',x:4,y:0,z:0}],elements:[{id:'bar',type:'truss',nodes:['b','a']}],load_cases:[{id:'D',loads:[]}]};
  const axial={...q,component:'N',location:{kind:'member',id:'public',positionM:0,side:'right'},value:-2};
  const analysis={results:{'case:D':{selection:q.selection,data:{memberResponses:[{id:'bar',state:'truss',length:4,samples:[{x:0,side:'right',N:-2},{x:4,side:'left',N:-2}]}]}}}};
  const mappings={model,elementSegments:{public:[{id:'bar',start:0,end:4,orientation:'reversed'}]}};
  assert.equal(compareRequestedQuantities(analysis,[axial],mappings).pass,true);
  model.elements[0].type='beam';assert.equal(compareRequestedQuantities(analysis,[axial],mappings).pass,false);
});

test('human-readable rounding requires a strictly correct verified native value and bounded report resolution',()=>{
  for(const [native,text] of [[37.89945652173914,'37.8995'],[-.203143243,'-0.203143'],[.045177745,'0.045178']]) {
    const requested={...q,component:'N',value:native};const report={markdown:`| ${q.id} | case:D | b@2:left | N | ${text} | kN |`};
    assert.equal(compareReportQuantities(report,[requested]).pass,false);
    const verifiedNativeValues={[q.id]:native};const result=compareReportQuantities(report,[requested],{verifiedNativeValues});assert.equal(result.pass,true);assert.equal(result.reportRounding.accepted.length,1);
    for(const number of [String(-Number(text)),String(Number(text)+.01),'0.2','38'])assert.equal(compareReportQuantities({markdown:report.markdown.replace(text,number)},[requested],{verifiedNativeValues}).pass,false);
    assert.equal(compareReportQuantities(report,[requested],{verifiedNativeValues:{[q.id]:native+.001}}).pass,false);
  }
  const requested={...q,component:'uz',unit:'m',value:-.00123456};const markdown=`| ${q.id} | case:D | b@2:left | uz | -0.001235 | m |`;
  assert.equal(compareReportQuantities({markdown},[requested],{verifiedNativeValues:{[q.id]:requested.value}}).pass,false,'micrometre rounding cannot hide displacement error beyond the report resolution policy');
});

test('constant truss samples permit only floating-point endpoint overshoot',()=>{
  const length=Math.hypot(3,1.5),model={analysis_control:{self_weight:false},nodes:[{id:'a',x:0,y:0,z:0},{id:'b',x:3,y:0,z:1.5}],elements:[{id:'bar',type:'truss',nodes:['a','b']}],load_cases:[{id:'D',loads:[]}]};
  const quantity={...q,component:'N',location:{kind:'member',id:'bar',positionM:1.67705098312,side:'right'},value:-2};
  const analysis={results:{'case:D':{selection:quantity.selection,data:{memberResponses:[{id:'bar',state:'truss',length,samples:[{x:0,side:'right',N:-2},{x:length+2*Number.EPSILON*length,side:'left',N:-2}]}]}}}};
  assert.equal(compareRequestedQuantities(analysis,[quantity],{model}).pass,true);
  analysis.results['case:D'].data.memberResponses[0].samples[1].x=length+1e-9;
  assert.equal(compareRequestedQuantities(analysis,[quantity],{model}).pass,false);
});
