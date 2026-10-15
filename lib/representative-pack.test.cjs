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

const {createNormalizedStateEdits,partitionRepresentativeQueries,verifyUnavailableRotationQuery}=require('./representative-tool-contract.cjs');

test('candidate state edits normalize legacy targets without editing frozen physical inputs',async()=>{
  const current={elements:[],materials:[{id:'M1',category:'steel',E:206000}],load_combinations:[],load_cases:[{id:'D',loads:[]}]};
  const physical={...structuredClone(current),materials:[{id:'M1',type:'steel',E:210000}]};
  const frozen=JSON.stringify(physical);let normalized=0;
  const edits=await createNormalizedStateEdits(current,physical,async input=>{
    assert.equal(input,physical);normalized++;
    return {...structuredClone(input),materials:[{id:'M1',category:'steel',E:input.materials[0].E}]};
  });
  assert.equal(normalized,1);
  assert.deepEqual(edits,[{operation:'update',collection:'materials',id:'M1',values:{E:210000}}]);
  assert.equal(JSON.stringify(physical),frozen);
  assert.equal(current.materials[0].E,206000);
});

test('STD-036 preserves all 93 independent references and discloses exactly 10 nonphysical rotation placeholders',()=>{
  const model=read('STD-036/model-state-1.json');
  const quantities=read('STD-036/independent-reference.json').states[0].quantities;
  const frozen=JSON.stringify(quantities);
  const scope=partitionRepresentativeQueries(model,quantities);
  assert.equal(quantities.length,93);assert.equal(scope.queryable.length,83);assert.equal(scope.notApplicable.length,10);
  assert.ok(scope.notApplicable.every(q=>q.component==='ry'&&q.value===0&&q.referenceRole==='zero-placeholder-not-physical-response'));
  assert.equal(JSON.stringify(quantities),frozen);
  assert.equal(new Set([...scope.queryable,...scope.notApplicable].map(q=>q.id)).size,93);
});

test('query applicability cannot discard nonzero references, translations, beam joints or prescribed rotations',()=>{
  const model={nodes:[{id:'n',restraints:[false,false,false,false,false,false]}],elements:[{id:'e',type:'truss',nodes:['n','other']}]};
  const quantity={id:'n:ry',location:{kind:'node',id:'n'},component:'ry',value:0};
  assert.throws(()=>partitionRepresentativeQueries(model,[{...quantity,value:1e-30}]),/nonzero reference/);
  assert.equal(partitionRepresentativeQueries(model,[{...quantity,component:'uz'}]).queryable.length,1);
  assert.equal(partitionRepresentativeQueries({...model,elements:[{...model.elements[0],type:'beam'}]},[quantity]).queryable.length,1);
  assert.equal(partitionRepresentativeQueries({...model,nodes:[{id:'n',restraints:[false,false,false,false,true,false]}]},[quantity]).queryable.length,1);
  assert.equal(partitionRepresentativeQueries({...model,elements:[]},[quantity]).queryable.length,1);
});

test('unavailable rotations require explicit solver evidence and the exact public rejection',async()=>{
  const quantity={id:'n:ry',location:{kind:'node',id:'n'},component:'ry',value:0};
  const data={nodalResponseAvailability:{n:{ry:false}}};
  const rejected=await verifyUnavailableRotationQuery(quantity,data,async()=>{throw Error('NODE_DOF_RESPONSE_UNAVAILABLE');});
  assert.equal(rejected.publicQuery,'correctly-rejected');
  await assert.rejects(()=>verifyUnavailableRotationQuery(quantity,{},async()=>{}),/explicitly marked unavailable/);
  await assert.rejects(()=>verifyUnavailableRotationQuery(quantity,data,async()=>({value:0})),/exposed an undetermined rotation/);
  await assert.rejects(()=>verifyUnavailableRotationQuery(quantity,data,async()=>{throw Error('RESULT_NODE_NOT_FOUND');}),/RESULT_NODE_NOT_FOUND/);
});
