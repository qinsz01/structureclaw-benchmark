'use strict';
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {spawnSync} = require('node:child_process');
const {fixture, clone} = require('../lib/research300-test-fixtures.cjs');
const {sha256} = require('../lib/corpus-provider.cjs');
const {prepareCase} = require('./install-research300-commercial.cjs');
let implementation;
try { implementation = require('./check-research300-commercial.cjs'); }
catch (error) { if (error.code !== 'MODULE_NOT_FOUND') throw error; }
function api() { assert.ok(implementation, 'Commercial diagnostic comparison implementation is missing'); return implementation; }
function documents() {
  const q = {id:'same', selection:{kind:'case',id:'D'}, location:{kind:'member',id:'b',positionM:0,side:'right'},
    component:'M3',unit:'kN.m',tolerance:{absolute:1e-8,relative:1e-6}};
  const requests = {schemaVersion:1,states:[{state:1,quantities:[q],derived:[]}]};
  const rawTrace={origin:'raw-sdk-member-end-cut',nativeRun:'captured-test',sourceModelSha256:'c'.repeat(64),
    sourceSelection:{kind:'case',id:'D'},sourceFactors:{D:1},nativeBasicFactors:{DL:1},
    raw:[{nativeCase:'DL',factor:1}],sourceEndNodes:['a','b'],end:0};
  const reference = {schemaVersion:1,id:'STD-083',sourceHash:'a'.repeat(64),states:[{state:1,quantities:[{...clone(q),value:1,rawTrace}],derived:[]}]};
  return {requests, reference, diagnostic:clone(reference)};
}
function policy() {
  return {kind:'analytical-recovery-scale',policy:'native-f32-recovery-scale-v1',nativeArithmeticBound:false,
    acceptanceRegionChanges:true,unit:'kN.m',unitRoundoff:2**-24,terms:[1,-1,0,0],structuralTermCount:4,
    recoveryScale:2,absoluteAllowance:8.344653750215545e-7,certificateSha256:'b'.repeat(64)};
}
test('strict relative limit scales with native reference, not diagnostic value', () => {
  const f=documents(); f.reference.states[0].quantities[0].value=100;
  f.diagnostic.states[0].quantities[0].value=111;
  for (const doc of [f.requests,f.reference,f.diagnostic]) doc.states[0].quantities[0].tolerance={absolute:0,relative:.1};
  const result=api().compareDocuments(f.reference,f.diagnostic,f.requests);
  assert.equal(result.strict.failed,1); assert.equal(result.strict.failures[0].frozenLimit,10);
  assert.equal(result.strict.failures[0].delta,11); assert.equal(result.engineering.failed,1);
});
test('engineering comparison retains strict failure and the independently declared budget', () => {
  const f=documents(); f.reference.states[0].quantities[0].engineeringPrecision=policy();
  f.diagnostic.states[0].quantities[0].value=1.0000015;
  const before=clone(f.reference),result=api().compareDocuments(f.reference,f.diagnostic,f.requests);
  assert.equal(result.strict.failed,1); assert.equal(result.engineering.failed,0);
  assert.equal(result.strict.failures[0].referenceAllowance,8.344653750215545e-7);
  assert.equal(result.precisionQuantities,1); assert.deepEqual(f.reference,before);
});
test('case and combination with the same id remain separate typed selections', () => {
  const f=documents();
  for (const doc of [f.requests,f.reference,f.diagnostic]) {
    const row=clone(doc.states[0].quantities[0]);row.selection.kind='combination';
    if ('value' in row) row.value=7;
    doc.states[0].quantities.push(row);
  }
  f.diagnostic.states[0].quantities.reverse();
  assert.equal(api().compareDocuments(f.reference,f.diagnostic,f.requests).strict.passed,2);
});
test('missing, extra and duplicate quantities or states fail closed', () => {
  api();
  for (const change of [d=>d.states[0].quantities.pop(),d=>d.states[0].quantities.push(clone(d.states[0].quantities[0])),
    d=>d.states.push(clone(d.states[0])),d=>{d.states[0].quantities[0].id='other';}]) {
    const f=documents();change(f.diagnostic);
    assert.throws(()=>api().compareDocuments(f.reference,f.diagnostic,f.requests),/missing|extra|duplicate|identity/i);
  }
});
test('typed selector, location, component, unit and frozen tolerance changes are errors', () => {
  api();
  for (const change of [q=>{q.selection.kind='combination';},q=>{q.location.side='left';},
    q=>{q.component='M2';},q=>{q.unit='N.m';},q=>{q.tolerance.absolute=1;}]) {
    const f=documents();change(f.diagnostic.states[0].quantities[0]);
    assert.throws(()=>api().compareDocuments(f.reference,f.diagnostic,f.requests),/missing|identity|metadata|tolerance/i);
  }
});
test('nonfinite values and source hash changes cannot become numerical agreement', () => {
  api();
  for (const value of [null,NaN,Infinity,'1']) {
    const f=documents();f.diagnostic.states[0].quantities[0].value=value;
    assert.throws(()=>api().compareDocuments(f.reference,f.diagnostic,f.requests),/finite/i);
  }
  const f=documents();f.diagnostic.sourceHash='c'.repeat(64);
  assert.throws(()=>api().compareDocuments(f.reference,f.diagnostic,f.requests),/source/i);
});
test('invalid reference policy or a policy attached to diagnostic results is rejected', () => {
  api();
  const f=documents();f.reference.states[0].quantities[0].engineeringPrecision={...policy(),absoluteAllowance:1};
  assert.throws(()=>api().compareDocuments(f.reference,f.diagnostic,f.requests),/precision/i);
  delete f.reference.states[0].quantities[0].engineeringPrecision;
  f.diagnostic.states[0].quantities[0].engineeringPrecision=policy();
  assert.throws(()=>api().compareDocuments(f.reference,f.diagnostic,f.requests),/diagnostic|precision/i);
});
test('derived values retain their frozen limit and never inherit primitive precision', () => {
  const f=documents(),def={id:'derived',operation:'sum',operands:['same'],unit:'kN.m'};
  f.requests.states[0].derived=[def];
  for (const d of [f.reference,f.diagnostic]) d.states[0].derived=[{...clone(def),value:1,selection:{kind:'case',id:'D'},tolerance:{absolute:1e-8,relative:1e-6}}];
  f.diagnostic.states[0].derived[0].value=1.000002;
  const result=api().compareDocuments(f.reference,f.diagnostic,f.requests);
  assert.equal(result.comparisons,2);assert.equal(result.engineering.failed,1);
  assert.equal(result.strict.failures[0].family,'derived');assert.equal(result.strict.failures[0].referenceAllowance,0);
  f.reference.states[0].derived[0].engineeringPrecision=policy();
  assert.throws(()=>api().compareDocuments(f.reference,f.diagnostic,f.requests),/derived|precision/i);
});

// Synthetic qualification fixture exercises I/O only, never native solver correctness.
function staged(t, withPrecision=false) {
  const f=fixture(t,'STD-083'),bundle=path.join(f.root,'bundle');fs.mkdirSync(bundle);
  const save=(name,value)=>fs.writeFileSync(path.join(bundle,name),typeof value==='string'?value:JSON.stringify(value)+'\n');
  const descriptor=name=>({path:name,sha256:sha256(fs.readFileSync(path.join(bundle,name)))});
  const matrix={...f.addReference(),schemaVersion:1,id:f.contract.id,modelId:f.contract.modelId,referenceKind:'independent-elastic-matrix'};
  f.write('independent-reference.json',matrix);
  save('raw.txt','synthetic diagnostic CLI fixture, not native evidence\n');
  const candidate={...clone(matrix),referenceKind:'native-pkpm-candidate',notCommercialScoringTruth:true,
    nativeArtifacts:{test:{raw:descriptor('raw.txt')}}};
  candidate.states.forEach(s=>{s.model='model-state-1.json';});
  if (withPrecision) {
    candidate.states[0].nativeRun='synthetic-test';
    const q=candidate.states[0].quantities.find(row=>row.location.kind==='member');
    const {certificateSha256,...precision}=policy();
    save('precision.json',{schemaVersion:1,engine:'PKPM',caseId:f.contract.id,sourceHash:candidate.sourceHash,
      quantities:[{state:1,id:q.id,selection:q.selection,location:q.location,component:q.component,unit:q.unit,precision,recovery:{nativeRun:'synthetic-test'}}]});
    q.engineeringPrecision={...precision,certificateSha256:descriptor('precision.json').sha256};
    q.rawTrace={origin:'raw-sdk-member-end-cut',nativeRun:'synthetic-test',sourceModelSha256:matrix.inputHashes['model-state-1.json'],
      sourceSelection:q.selection,sourceFactors:{D:1},nativeBasicFactors:{DL:1},raw:[{nativeCase:'DL',factor:1}],
      sourceEndNodes:['a','m'],end:1};
    candidate.nativeArtifacts.precision={'certificate.json':descriptor('precision.json')};
    matrix.states[0].quantities.find(row=>row.id===q.id).value=1.0000015;
    f.write('independent-reference.json',matrix);
  }
  save('candidate.json',candidate);
  save('review.json',{schemaVersion:1,reviewer:'synthetic-test-reviewer',cases:[{id:f.contract.id,status:'qualified',sourceHash:matrix.sourceHash,candidateSha256:descriptor('candidate.json').sha256}]});
  const entry={id:f.contract.id,candidate:descriptor('candidate.json'),review:descriptor('review.json'),evidenceRoot:'.',artifacts:[descriptor('raw.txt'),...(withPrecision?[descriptor('precision.json')]:[])],
    receipts:[{state:1,selection:{kind:'case',id:'D'},runId:'synthetic-only',engineVersion:'TEST',artifacts:[descriptor('raw.txt')]}]};
  const casesDir=path.join(f.root,'staging'),output=path.join(casesDir,f.contract.id);
  prepareCase({caseDir:f.caseDir,bundleRoot:bundle,entry,output});
  fs.writeFileSync(path.join(output,'native-opensees-reference.json'),JSON.stringify({...clone(matrix),referenceKind:'native-opensees'}));
  return {...f,casesDir,stagedCase:output};
}
test('CLI supports staging, binds all source artifacts and does not write absent explicit output', t => {
  api();const f=staged(t),before=fs.readFileSync(path.join(f.stagedCase,'acceptance.json'));
  const cmd=path.join(__dirname,'check-research300-commercial.cjs');
  const args=['--root',f.root,'--cases-dir',f.casesDir,'--case',f.contract.id];
  const run=spawnSync(process.execPath,[cmd,...args],{encoding:'utf8'});
  assert.equal(run.status,0,run.stderr);const report=JSON.parse(run.stdout);
  assert.equal(report.evidenceValid,true);assert.equal(report.strictPass,true);assert.equal(report.engineeringPass,true);
  assert.equal(report.comparisonPolicy.default,'strict');assert.equal(report.comparisonPolicy.engineeringDiagnosticOnly,true);
  assert.equal(report.schemaVersion,2);assert.equal(report.summary.matrix.comparisons,4);
  assert.equal(report.summary.combined.comparisons,8);assert.equal(report.cases[0].artifacts.length>=5,true);
  assert.deepEqual(fs.readFileSync(path.join(f.stagedCase,'acceptance.json')),before);
  const file=path.join(f.root,'report.json');
  const written=spawnSync(process.execPath,[cmd,...args,'--output',file],{encoding:'utf8'});
  assert.equal(written.status,0,written.stderr);assert.deepEqual(JSON.parse(fs.readFileSync(file)),report);
  assert.notEqual(spawnSync(process.execPath,[cmd,...args,'--output',file],{encoding:'utf8'}).status,0);
});
test('CLI refuses report outputs inside either active or staging cases, including symlink aliases', t => {
  api();const f=staged(t);const alias=path.join(f.root,'alias');fs.symlinkSync(f.stagedCase,alias);
  for (const output of [path.join(f.caseDir,'report.json'),path.join(f.stagedCase,'report.json'),path.join(alias,'report.json')]) {
    const run=spawnSync(process.execPath,[path.join(__dirname,'check-research300-commercial.cjs'),'--root',f.root,'--cases-dir',f.casesDir,'--case',f.contract.id,'--output',output],{encoding:'utf8'});
    assert.notEqual(run.status,0);assert.equal(fs.existsSync(output),false);
  }
});
test('CLI rejects a stale native qualification instead of treating it as diagnostic truth', t => {
  api();const f=staged(t);fs.appendFileSync(path.join(f.stagedCase,'native-commercial/evidence/raw.txt'),'changed');
  assert.throws(()=>implementation.auditCommercial({root:f.root,casesDir:f.casesDir,caseIds:[f.contract.id]}),/qualification|native|hash/i);
  const run=spawnSync(process.execPath,[path.join(__dirname,'check-research300-commercial.cjs'),
    '--root',f.root,'--cases-dir',f.casesDir,'--case',f.contract.id],{encoding:'utf8'});
  assert.equal(run.status,2);assert.equal(run.stdout,'');
});
test('CLI exits one for strict disagreement even when engineering diagnostics pass', t => {
  api();const f=staged(t,true);
  const run=spawnSync(process.execPath,[path.join(__dirname,'check-research300-commercial.cjs'),
    '--root',f.root,'--cases-dir',f.casesDir,'--case',f.contract.id],{encoding:'utf8'});
  assert.equal(run.status,1,run.stderr);
  const report=JSON.parse(run.stdout);
  assert.equal(report.evidenceValid,true);assert.equal(report.strictPass,false);assert.equal(report.engineeringPass,true);assert.equal(report.valid,false);
  assert.equal(report.summary.matrix.strict.failed,1);assert.equal(report.summary.matrix.engineering.failed,0);
  assert.equal(report.summary.combined.strict.failed,2);
  assert.equal(report.cases[0].comparisons.matrix.strict.failures[0].engineeringPass,true);
});
test('real STD-089 keeps its two strict differences but native self-comparison passes',()=>{
  const dir=path.join(__dirname,'../corpora/research-300/cases/STD-089');
  const read=name=>JSON.parse(fs.readFileSync(path.join(dir,name),'utf8'));
  const native=read('independent-reference.json'),matrix=read('independent-reference-matrix-diagnostic.json');
  const requests=read('reference-requests.json'),before=JSON.stringify(native);
  const comparison=api().compareDocuments(native,matrix,requests);
  const ids=['case-D-member-x0-0-1-s0-right-M3','case-D-member-x0-0-2-s0-right-M3'];
  assert.equal(comparison.strict.failed,2);assert.equal(comparison.engineering.failed,0);
  assert.deepEqual(comparison.strict.failures.map(row=>row.id).sort(),ids);
  const {compareRequestedQuantities}=require('../lib/requested-quantities.cjs');
  const frozen=native.states[0].quantities.filter(q=>ids.includes(q.id));
  assert.equal(frozen.length,2);
  const actual=document=>({results:{'case:D':{selection:{kind:'case',id:'D'},data:{units:{moment:'kN.m'},
    memberResponses:document.states[0].quantities.filter(q=>ids.includes(q.id)).map(q=>({id:q.location.id,
      state:'recovered',samples:[{x:q.location.positionM,side:q.location.side,[q.component]:q.value}]}))}}}});
  const cross=compareRequestedQuantities(actual(matrix),frozen);
  assert.equal(cross.evidenceValid,true);assert.equal(cross.pass,false);assert.equal(cross.strictPass,false);
  assert.equal(cross.engineeringPass,true);assert.equal(cross.failures.length,2);
  const self=compareRequestedQuantities(actual(native),frozen);
  assert.equal(self.evidenceValid,true);assert.equal(self.pass,true);assert.equal(self.strictPass,true);assert.equal(self.engineeringPass,true);
  assert.equal(JSON.stringify(native),before,'The native values, certificates and frozen tolerance remain intact');
});
