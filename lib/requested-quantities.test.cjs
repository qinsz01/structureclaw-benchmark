const test=require('node:test');const assert=require('node:assert/strict');
const {compareRequestedQuantities,compareReportQuantities}=require('./requested-quantities.cjs');
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
