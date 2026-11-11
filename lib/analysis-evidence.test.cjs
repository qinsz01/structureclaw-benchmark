const test=require('node:test');
const assert=require('node:assert/strict');
const {createHash}=require('node:crypto');
const {modelFingerprint,verifyExecutionEvidence}=require('./analysis-evidence.cjs');
const model={nodes:[{id:'a',x:0,y:0,z:0}],load_cases:[{id:'D',loads:[]}],metadata:{elementReferenceVectors:{b:[0,0,1]}}};
const selection={kind:'case',id:'D'};
function state(){return {model:structuredClone(model),analysisResult:{results:{'case:D':{selection,status:'success',
  meta:{runId:'immutable-run',modelHash:modelFingerprint(model)},data:{execution:{executed:true,solver:'OpenSees',solverVersion:'test',analysisReturnCode:0}}}}}};}
test('complete versioned execution is tied to the selected current model',()=>assert.equal(verifyExecutionEvidence(state(),selection).pass,true));
for(const [name,change] of [
  ['stale geometry',s=>s.model.nodes[0].z=1],
  ['stale local axes',s=>s.model.metadata.elementReferenceVectors.b=[0,1,0]],
  ['pending update',s=>s.modelPending=true],
  ['declared engine without execution',s=>delete s.analysisResult.results['case:D'].data.execution],
  ['unversioned solver',s=>delete s.analysisResult.results['case:D'].data.execution.solverVersion],
  ['missing immutable run',s=>delete s.analysisResult.results['case:D'].meta.runId],
  ['failed convergence',s=>s.analysisResult.results['case:D'].data.execution.analysisReturnCode=-3],
  ['partial computation',s=>s.analysisResult.results['case:D'].status='partial'],
]) test(`${name} cannot count as actual engineering verification`,()=>{const s=state();change(s);assert.equal(verifyExecutionEvidence(s,selection).pass,false);});
test('other cases and display annotations do not substitute the requested case',()=>{
  const s=state();s.model.metadata.title='New title';assert.equal(verifyExecutionEvidence(s,selection).pass,true);
  assert.equal(verifyExecutionEvidence(s,{kind:'case',id:'L'}).pass,false);
});

const sha256=bytes=>createHash('sha256').update(bytes).digest('hex');
function artifactFixture() {
  const s=state();
  const artifactBytes={normalizedInput:Buffer.from('{"case":"D","load":-10}\n'),
    solverResponse:Buffer.from('{"displacements":{"a":{"uz":-0.001}}}\n')};
  const hashes=Object.fromEntries(Object.entries(artifactBytes).map(([name,bytes])=>[`${name}Sha256`,sha256(bytes)]));
  s.analysisResult.results['case:D'].data.execution.artifacts=hashes;
  const options={evaluationProfile:'engineering-v2.3',artifactEvidence:{'immutable-run':{
    selection,modelHash:modelFingerprint(model),artifactBytes}}};
  return {s,options,evidence:options.artifactEvidence['immutable-run']};
}
test('engineering-v2.3 verifies exact artifact bytes against selected execution receipt',()=>{
  const {s,options}=artifactFixture();
  const proof=verifyExecutionEvidence(s,selection,options);
  assert.equal(proof.pass,true,proof.failures.join('; '));
  assert.equal(proof.artifactsVerified,2);
});
test('artifact enforcement is explicit and legacy version-bound evidence stays compatible',()=>{
  assert.equal(verifyExecutionEvidence(state(),selection).pass,true);
  assert.equal(verifyExecutionEvidence(state(),selection,{evaluationProfile:'engineering-v2.2'}).pass,true);
  assert.equal(verifyExecutionEvidence(state(),selection,{requireArtifactHashes:true}).pass,false);
  assert.equal(verifyExecutionEvidence(state(),selection,{evaluationProfile:'engineering-v2.3',requireArtifactHashes:false}).pass,false);
});
for(const [name,change,pattern] of [
  ['tampered solver output',({evidence})=>evidence.artifactBytes.solverResponse[0]=32,/solverResponse.*hash mismatch/],
  ['altered claimed hash',({s})=>s.analysisResult.results['case:D'].data.execution.artifacts.solverResponseSha256='0'.repeat(64),/solverResponse.*hash mismatch/],
  ['missing hash',({s})=>delete s.analysisResult.results['case:D'].data.execution.artifacts.normalizedInputSha256,/normalizedInput.*missing/],
  ['malformed hash',({s})=>s.analysisResult.results['case:D'].data.execution.artifacts.solverResponseSha256='not-a-hash',/solverResponse.*SHA256/],
  ['missing bytes',({evidence})=>delete evidence.artifactBytes.solverResponse,/solverResponse.*missing/],
  ['absent receipt',({s})=>delete s.analysisResult.results['case:D'].data.execution.artifacts,/artifact.*receipt.*missing/],
  ['absent evaluator evidence',({options})=>delete options.artifactEvidence,/artifact.*evidence.*missing/],
  ['stale run',({s})=>s.analysisResult.results['case:D'].meta.runId='later-run',/artifact.*evidence.*missing/],
  ['stale model binding',({evidence})=>evidence.modelHash='0'.repeat(64),/artifact.*model/],
  ['same-name combination binding',({evidence})=>evidence.selection={kind:'combination',id:'D'},/artifact.*selection/],
  ['different load case binding',({evidence})=>evidence.selection={kind:'case',id:'L'},/artifact.*selection/],
]) test(`${name} fails artifact verification`,()=>{
  const fixture=artifactFixture();change(fixture);
  const result=verifyExecutionEvidence(fixture.s,selection,fixture.options);
  assert.equal(result.pass,false);
  assert.match(result.failures.join('; '),pattern);
});
test('trusted benchmark precomputed hashes are accepted only through explicit evidence options',()=>{
  const {s,options,evidence}=artifactFixture();
  evidence.trustedArtifactHashes=Object.fromEntries(Object.entries(evidence.artifactBytes).map(([key,bytes])=>[key,sha256(bytes)]));
  delete evidence.artifactBytes;
  assert.equal(verifyExecutionEvidence(s,selection,options).pass,true);
  s.artifactEvidence=options.artifactEvidence;
  assert.equal(verifyExecutionEvidence(s,selection,{requireArtifactHashes:true}).pass,false);
  evidence.trustedArtifactHashes.solverResponse='0'.repeat(64);
  assert.equal(verifyExecutionEvidence(s,selection,options).pass,false);
});
test('supplied bytes cannot be overridden by a matching trusted digest',()=>{
  const {s,options,evidence}=artifactFixture();
  evidence.trustedArtifactHashes={solverResponse:sha256(evidence.artifactBytes.solverResponse)};
  evidence.artifactBytes.solverResponse[0]=32;
  assert.equal(verifyExecutionEvidence(s,selection,options).pass,false);
});
test('native receipt artifact names are opaque identifiers and never filesystem inputs',()=>{
  const {s,options,evidence}=artifactFixture();
  const bytes=Buffer.from('native result bytes');
  s.analysisResult.results['case:D'].data.execution.artifacts=[{path:'../../outside/native.dat',sha256:sha256(bytes)}];
  evidence.artifactBytes={'../../outside/native.dat':bytes};
  assert.equal(verifyExecutionEvidence(s,selection,options).pass,true);
  evidence.artifactBytes={'../../outside/native.dat':{path:'../../outside/native.dat'}};
  const result=verifyExecutionEvidence(s,selection,options);
  assert.equal(result.pass,false);
  assert.match(result.failures.join('; '),/bytes/);
});
test('duplicate native receipt artifact identifiers fail even with matching hashes',()=>{
  const {s,options,evidence}=artifactFixture();
  const bytes=Buffer.from('native result bytes'),artifact={name:'result.dat',sha256:sha256(bytes)};
  s.analysisResult.results['case:D'].data.execution.artifacts=[artifact,{...artifact}];
  evidence.artifactBytes={'result.dat':bytes};
  assert.equal(verifyExecutionEvidence(s,selection,options).pass,false);
});

function selectionArtifactFixture() {
  const s=state();
  s.model.load_cases.push({id:'L',loads:[]});
  s.model.load_combinations=[{id:'D',factors:{D:1,L:1}}];
  const selections=[{kind:'case',id:'D'},{kind:'case',id:'L'},{kind:'combination',id:'D'}];
  const evidence={selections,modelHash:modelFingerprint(s.model),
    artifactBytes:{normalizedInput:Buffer.from(JSON.stringify({model:s.model,selections})),
      solverResponse:Buffer.from('{"hostCapture":"full response envelope"}')},selectionArtifacts:{}};
  s.analysisResult.results={};
  for(const selected of selections) {
    const key=`${selected.kind}:${selected.id}`;
    const bytes={normalizedInput:Buffer.from(JSON.stringify({model:s.model,selection:key})),
      settings:Buffer.from(JSON.stringify({loadSelection:key})),
      solverResponse:Buffer.from(JSON.stringify({selection:key,displacements:{a:{uz:key==='case:D'?-.001:-.002}}}))};
    evidence.selectionArtifacts[key]={artifactBytes:bytes,
      trustedArtifactHashes:Object.fromEntries(Object.entries(bytes).map(([name,value])=>[name,sha256(value)]))};
    s.analysisResult.results[key]={selection:selected,status:'success',meta:{runId:'immutable-run',modelHash:evidence.modelHash},
      data:{execution:{executed:true,solver:'OpenSees',solverVersion:'3.7.1',analysisReturnCode:0,
        artifacts:Object.fromEntries(Object.entries(bytes).map(([name,value])=>[`${name}Sha256`,sha256(value)]))}}};
  }
  return {s,evidence,selections,options:{evaluationProfile:'engineering-v2.3',artifactEvidence:{'immutable-run':evidence}}};
}

test('native receipts verify exact selection bytes independently from full host capture bytes',()=>{
  const f=selectionArtifactFixture();
  for(const selected of f.selections) {
    const verified=verifyExecutionEvidence(f.s,selected,f.options);
    assert.equal(verified.pass,true,verified.failures.join('; '));
    assert.equal(verified.artifactsVerified,3);
  }
  assert.notEqual(sha256(f.evidence.artifactBytes.normalizedInput),f.s.analysisResult.results['case:D'].data.execution.artifacts.normalizedInputSha256);
});

test('tampered selected canonical bytes fail even while other selections and stored digests remain valid',()=>{
  const f=selectionArtifactFixture();
  f.evidence.selectionArtifacts['case:D'].artifactBytes.solverResponse[0]=32;
  const failed=verifyExecutionEvidence(f.s,selection,f.options);
  assert.equal(failed.pass,false);
  assert.match(failed.failures.join('; '),/solverResponse.*hash mismatch/);
  assert.equal(verifyExecutionEvidence(f.s,{kind:'case',id:'L'},f.options).pass,true);
});

test('missing selected native evidence cannot fall back to matching top-level capture receipts',()=>{
  const f=selectionArtifactFixture();
  f.evidence.artifactBytes=f.evidence.selectionArtifacts['case:D'].artifactBytes;
  delete f.evidence.selectionArtifacts['case:D'];
  const failed=verifyExecutionEvidence(f.s,selection,f.options);
  assert.equal(failed.pass,false);
  assert.match(failed.failures.join('; '),/native artifact evidence is missing/);
  assert.equal(failed.artifactsVerified,0);
  assert.equal(verifyExecutionEvidence(f.s,{kind:'case',id:'L'},f.options).pass,true);
});

test('cross-case or same-name combination native evidence cannot satisfy another selection receipt',()=>{
  for(const key of ['case:L','combination:D']) {
    const f=selectionArtifactFixture();
    f.evidence.selectionArtifacts['case:D']=f.evidence.selectionArtifacts[key];
    const failed=verifyExecutionEvidence(f.s,selection,f.options);
    assert.equal(failed.pass,false,key);
    assert.match(failed.failures.join('; '),/hash mismatch/);
    assert.equal(verifyExecutionEvidence(f.s,{kind:key.split(':')[0],id:key.split(':')[1]},f.options).pass,true);
  }
});

test('selection artifact receipt names remain complete and map keys must be own properties',()=>{
  const f=selectionArtifactFixture();
  delete f.evidence.selectionArtifacts['case:D'].artifactBytes.settings;
  delete f.evidence.selectionArtifacts['case:D'].trustedArtifactHashes.settings;
  assert.match(verifyExecutionEvidence(f.s,selection,f.options).failures.join('; '),/settings.*missing/);
  const g=selectionArtifactFixture();
  g.evidence.selectionArtifacts=Object.create(g.evidence.selectionArtifacts);
  assert.match(verifyExecutionEvidence(g.s,selection,g.options).failures.join('; '),/native artifact evidence is missing/);
});
