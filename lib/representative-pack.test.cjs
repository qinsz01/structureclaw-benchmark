const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {createHash}=require('node:crypto');
const root=path.resolve(__dirname,'../acceptance/representative-18');
const manifest=require(path.join(root,'manifest.json'));
const read=name=>JSON.parse(fs.readFileSync(path.join(root,name),'utf8'));
const sha=file=>createHash('sha256').update(fs.readFileSync(file)).digest('hex');

test('representative pack freezes 18 distinct inputs and independent quantities without changing the 300 plan',()=>{
  assert.deepEqual(manifest.counts,{total:18,OpenSees:12,PKPM:3,YJK:3});
  for(const prefix of ['STD','INT','MM'])assert.equal(manifest.cases.filter(c=>c.id.startsWith(prefix)).length,6);
  for(const [name,digest] of Object.entries(manifest.sha256))assert.equal(sha(path.join(root,name)),digest,name);
  for(const [name,digest] of Object.entries(manifest.sourceHashes))assert.equal(sha(path.join(root,'../../scripts',name)),digest,name);
  for(const entry of manifest.cases){
    const contract=read(entry.contract),reference=read(`${entry.id}/${contract.numericalReference}`);
    assert.equal(contract.status,'candidate-inputs-frozen-needs-independent-review');
    assert.equal(contract.llmEndToEnd,'not-run');
    assert.equal(contract.modelStates.length,reference.states.length);
    for(const turn of contract.turns)for(const file of turn.attachments){
      assert.ok(fs.existsSync(path.join(root,entry.id,file)));
      assert.ok(!/model-state|reference/.test(file),'Answer snapshots are not user attachments');
    }
    for(const state of reference.states)for(const q of state.quantities){
      assert.ok(Number.isFinite(q.value));assert.deepEqual(q.tolerance,{absolute:1e-8,relative:1e-6});
      assert.ok(['case','combination'].includes(q.selection.kind));
      if(q.location.kind==='member'){assert.ok(Number.isFinite(q.location.positionM));assert.ok(['left','right'].includes(q.location.side));}
    }
    if(entry.engine!=='OpenSees')assert.equal(reference.notCommercialScoringTruth,true);
  }
});

test('missing-input tasks withhold unresolved support and span information until their second turn',()=>{
  const cropped=read('MM-058/contract.json');assert.equal(cropped.turns[0].mustNotAnalyze,true);
  assert.ok(!cropped.turns[0].attachments.includes('drawing-xz.png'));
  assert.ok(cropped.turns[1].attachments.includes('drawing-xz.png'));
  const span=read('INT-079/geometry-input.json');assert.ok(span.nodes.some(n=>n.y===null));
  assert.match(fs.readFileSync(path.join(root,'INT-079/loads.csv'),'utf8'),/pressure_kN_per_m2/);
  assert.equal(read('INT-079/contract.json').turns[0].mustNotAnalyze,true);
});
