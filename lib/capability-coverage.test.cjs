const test=require('node:test');
const assert=require('node:assert/strict');
const coverage=require('../planning/capability-coverage-300.json');
test('coverage contains all 300 independent planned task IDs with original engine assignments',()=>{
  const expected=['STD','INT','MM'].flatMap(p=>Array.from({length:100},(_,i)=>`${p}-${String(i+1).padStart(3,'0')}`));
  assert.deepEqual(coverage.cases.map(c=>c.id).sort(),expected.sort());
  assert.deepEqual(coverage.summary.byEngine,{OpenSees:267,PKPM:16,YJK:17});
  for(const [id,engine] of [['STD-080','PKPM'],['STD-081','YJK'],['STD-082','PKPM'],['STD-083','PKPM'],['STD-084','YJK']])
    assert.equal(coverage.cases.find(c=>c.id===id).plannedEngine,engine);
});
test('every requirement clause points to retained verbatim source and known candidate features',()=>{
  const ids=new Set(coverage.featureDefinitions.map(f=>f.id));let clauses=0;
  for(const c of coverage.cases) {
    assert.ok(c.sourceRequirements['task.expectedOutput']);assert.ok(c.sourceRequirements['engine.analysisContract']);
    const sources=new Set();
    for(const r of c.requirements) {
      sources.add(r.sourceField);clauses++;
      const text=c.sourceRequirements[r.sourceField];assert.equal(typeof text,'string');
      const [a,b]=r.sourceRange;assert.ok(a>=0&&b>a&&b<=text.length);
      assert.ok(text.slice(a,b).trim());r.candidateFeatures.forEach(id=>assert.ok(ids.has(id)));
    }
    Object.keys(c.sourceRequirements).forEach(field=>assert.ok(sources.has(field)));
  }
  assert.equal(clauses,coverage.summary.requirementClauses);
});
test('tested features and text keywords never promote a whole case or another engine to accepted',()=>{
  for(const c of coverage.cases) {
    assert.equal(c.acceptance.status,'not-accepted');assert.equal(c.acceptance.caseSupportStatus,'unknown');
    assert.deepEqual(c.acceptance.acceptedEvidence,[]);
    for(const f of c.features) {
      const def=coverage.featureDefinitions.find(x=>x.id===f.featureId);
      if(def.engine==='OpenSees'&&c.plannedEngine!=='OpenSees') assert.equal(f.targetEngineFeatureEvidence,'unknown-evidence-is-for-another-engine');
    }
  }
  assert.equal(coverage.summary.acceptedCases,0);
});
