'use strict';
// Synthetic installation-boundary tests, never native solver evidence.
const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {fixture,clone}=require('../lib/research300-test-fixtures.cjs');
const {sha256}=require('../lib/corpus-provider.cjs');
const {prepareCase,main}=require('./install-research300-commercial.cjs');
function setup(t){
  const f=fixture(t,'STD-083'),base=path.join(f.root,'bundle');fs.mkdirSync(base);
  const save=(name,data)=>fs.writeFileSync(path.join(base,name),typeof data==='string'?data:JSON.stringify(data)+'\n');
  const descriptor=name=>({path:name,sha256:sha256(fs.readFileSync(path.join(base,name)))});
  const matrix=f.addReference();matrix.referenceKind='independent-elastic-matrix';f.write('independent-reference.json',matrix);
  save('raw.txt','TEST ONLY raw data\n');
  const candidate={...clone(matrix),id:f.contract.id,referenceKind:'native-pkpm-candidate',notCommercialScoringTruth:true,nativeArtifacts:{test:{raw:descriptor('raw.txt')}}};
  candidate.states.forEach(state=>{state.model='model-state-1.json';});
  save('candidate.json',candidate);
  const review={schemaVersion:1,reviewer:'synthetic-test-reviewer',cases:[{id:f.contract.id,status:'qualified',sourceHash:matrix.sourceHash,candidateSha256:descriptor('candidate.json').sha256}]};
  save('review.json',review);
  save('review-dependency.txt','TEST ONLY independent review dependency\n');
  const entry={id:f.contract.id,candidate:descriptor('candidate.json'),review:descriptor('review.json'),evidenceRoot:'.',
    supplementalArtifacts:[descriptor('review-dependency.txt')],
    artifacts:[descriptor('raw.txt')],receipts:[{state:1,selection:{kind:'case',id:'D'},runId:'synthetic-test',engineVersion:'TEST ONLY',artifacts:[descriptor('raw.txt')]}]};
  return {...f,base,save,descriptor,candidate,review,entry,output:path.join(f.root,'prepared',f.contract.id)};
}
test('native trace signed zeros survive JSON serialization without changing reviewed bytes',t=>{
  const f=setup(t);
  // Python/native exports can retain -0.0 in axis vectors and raw arrays.
  f.candidate.states[0].quantities[0].rawTrace={axis:[1,-0,0]};
  const serialized=JSON.stringify(f.candidate).replace('"axis":[1,0,0]','"axis":[1,-0.0,0]');
  f.save('candidate.json',serialized);f.entry.candidate=f.descriptor('candidate.json');
  f.review.cases[0].candidateSha256=f.entry.candidate.sha256;f.save('review.json',f.review);f.entry.review=f.descriptor('review.json');
  prepareCase({caseDir:f.caseDir,bundleRoot:f.base,entry:f.entry,output:f.output});
  const ref=JSON.parse(fs.readFileSync(path.join(f.output,'independent-reference.json')));
  assert.equal(Object.is(ref.states[0].quantities[0].rawTrace.axis[1],-0),true);
});
test('preparation preserves source and matrix bytes, binds native review and leaves blind acceptance pending',t=>{
  const f=setup(t),before=fs.readFileSync(path.join(f.caseDir,'independent-reference.json'));
  prepareCase({caseDir:f.caseDir,bundleRoot:f.base,entry:f.entry,output:f.output});
  assert.deepEqual(fs.readFileSync(path.join(f.caseDir,'independent-reference.json')),before);
  assert.deepEqual(fs.readFileSync(path.join(f.output,'independent-reference-matrix-diagnostic.json')),before);
  const ref=JSON.parse(fs.readFileSync(path.join(f.output,'independent-reference.json')));
  assert.equal(ref.referenceKind,'native-pkpm');assert.equal(ref.notCommercialScoringTruth,false);
  const a=JSON.parse(fs.readFileSync(path.join(f.output,'acceptance.json')));
  assert.equal(a.sameEngineTruth.status,'verified');assert.equal(a.inputBlindReview.status,'pending');
  const receipt=JSON.parse(fs.readFileSync(path.join(f.output,a.sameEngineTruth.receipts[0].path)));
  assert.ok(receipt.artifacts.some(row=>row.path==='native-commercial/supplements/review-dependency.txt'));
  assert.deepEqual(fs.readFileSync(path.join(f.output,'contract.json')),fs.readFileSync(path.join(f.caseDir,'contract.json')));
  assert.throws(()=>prepareCase({caseDir:f.caseDir,bundleRoot:f.base,entry:f.entry,output:f.output}),/exists/);
});
test('blocked review, stale bytes and incomplete raw evidence fail before output is created',t=>{
  for(const mutation of [f=>{f.review.cases[0].status='blocked';f.save('review.json',f.review);f.entry.review=f.descriptor('review.json');},
    f=>f.save('raw.txt','changed'),f=>f.save('review-dependency.txt','changed'),f=>{f.entry.artifacts=[];},f=>{f.entry.receipts=[];}]){
    const f=setup(t);mutation(f);
    assert.throws(()=>prepareCase({caseDir:f.caseDir,bundleRoot:f.base,entry:f.entry,output:f.output}));
    assert.equal(fs.existsSync(f.output),false);
  }
});
test('a reviewed but missing quantity or changed frozen tolerance cannot be installed',t=>{
  for(const mutation of [c=>c.states[0].quantities.pop(),c=>{c.states[0].quantities[0].tolerance.relative=.5;}]){
    const f=setup(t);mutation(f.candidate);f.save('candidate.json',f.candidate);f.entry.candidate=f.descriptor('candidate.json');
    f.review.cases[0].candidateSha256=f.entry.candidate.sha256;f.save('review.json',f.review);f.entry.review=f.descriptor('review.json');
    assert.throws(()=>prepareCase({caseDir:f.caseDir,bundleRoot:f.base,entry:f.entry,output:f.output}),/reference|quantit/i);
    assert.equal(fs.existsSync(f.output),false);
  }
});
test('a symlinked output parent cannot redirect preparation into the active corpus',t=>{
  const f=setup(t),alias=path.join(f.root,'output-alias');fs.symlinkSync(f.caseDir,alias);
  assert.throws(()=>prepareCase({caseDir:f.caseDir,bundleRoot:f.base,entry:f.entry,output:path.join(alias,'new')}),/symlink|active|outside/i);
  assert.equal(fs.existsSync(path.join(f.caseDir,'new')),false);
});
test('a later case failure leaves no partially published batch',t=>{
  const f=setup(t),output=path.join(f.root,'batch');
  f.save('bundle.json',{schemaVersion:1,cases:[f.entry,{...clone(f.entry),id:'STD-082'}]});
  assert.throws(()=>main(['--bundle',path.join(f.base,'bundle.json'),'--cases-root',path.dirname(f.caseDir),'--output',output]));
  assert.equal(fs.existsSync(output),false);
});
