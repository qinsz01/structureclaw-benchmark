'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {fixture,clone}=require('./research300-test-fixtures.cjs');
const {sha256}=require('./corpus-provider.cjs');
const {validateResearchCase}=require('./research300-validation.cjs');
function setup(t){
  const f=fixture(t,'STD-083'),a=f.addAcceptance();
  const ref=JSON.parse(fs.readFileSync(path.join(f.caseDir,'independent-reference.json')));
  const descriptor=name=>({path:name,sha256:sha256(fs.readFileSync(path.join(f.caseDir,name)))});
  Object.assign(ref,{referenceKind:'native-pkpm',sameEngineTruthStatus:'verified'});
  f.write('native-commercial/evidence/raw.txt','SYNTHETIC TEST RAW');
  ref.nativeArtifacts={test:{raw:descriptor('native-commercial/evidence/raw.txt')}};
  const q=ref.states[0].quantities.find(q=>q.location.kind==='member');
  ref.states[0].model=f.contract.modelStates[0];
  const model=JSON.parse(fs.readFileSync(path.join(f.caseDir,ref.states[0].model)));
  const member=model.elements.find(e=>e.id===q.location.id);
  ref.states[0].nativeRun='native-test';
  q.rawTrace={origin:'raw-sdk-member-end-cut',nativeRun:'native-test',sourceModelSha256:descriptor(ref.states[0].model).sha256,
    sourceSelection:clone(q.selection),sourceFactors:{[q.selection.id]:1},nativeBasicFactors:{DL:1},
    raw:[{nativeCase:'DL',factor:1}],end:q.location.positionM===0?0:1,sourceEndNodes:member.nodes};
  const terms=[.2,-.1,.3,-.2],scale=terms.reduce((a,b)=>a+Math.abs(b),0),u=2**-24;
  q.engineeringPrecision={policy:'native-f32-recovery-scale-v1',kind:'analytical-recovery-scale',nativeArithmeticBound:false,
    acceptanceRegionChanges:true,unit:q.unit,unitRoundoff:u,terms,structuralTermCount:4,recoveryScale:scale,
    absoluteAllowance:7*u/(1-7*u)*scale,certificateSha256:'a'.repeat(64)};
  const {certificateSha256,...precision}=q.engineeringPrecision;
  const certificate={schemaVersion:1,engine:'PKPM',caseId:f.contract.id,sourceHash:a.sourceHash,
    quantities:[{state:1,id:q.id,selection:q.selection,component:q.component,location:q.location,unit:q.unit,precision,
      recovery:{nativeRun:'native-test'}}]};
  function bindCertificate(){
    f.write('native-commercial/evidence/precision/certificate.json',certificate);
    const d=descriptor('native-commercial/evidence/precision/certificate.json');
    ref.nativeArtifacts.precision={certificate:d};q.engineeringPrecision.certificateSha256=d.sha256;
  }
  function save(){
    const candidate={...clone(ref),id:f.contract.id,referenceKind:'native-pkpm-candidate'};
    for(const group of Object.values(candidate.nativeArtifacts))for(const descriptor of Object.values(group))
      descriptor.path=descriptor.path.replace(/^native-commercial\/evidence\//,'');
    f.write('native-commercial/candidate.json',candidate);ref.candidateArtifact=descriptor('native-commercial/candidate.json');
    const review={schemaVersion:1,reviewer:a.sameEngineTruth.reviewer,cases:[{id:f.contract.id,status:'qualified',
      sourceHash:a.sourceHash,candidateSha256:ref.candidateArtifact.sha256}]};
    f.write('native-commercial/qualification.json',review);ref.independentReview=descriptor('native-commercial/qualification.json');
    a.sameEngineTruth.evidence=ref.independentReview;
    f.write('independent-reference.json',ref);a.independentReferenceSha256=descriptor('independent-reference.json').sha256;
    f.write('acceptance.json',a);
  }
  const check=()=>validateResearchCase({root:f.root,caseDir:f.caseDir,planCase:f.planCase,stage:'reference-ready'});
  return {f,q,certificate,bindCertificate,save,check};
}
test('precision requires a retained hash-bound certificate even when candidate qualification is updated',t=>{
  const x=setup(t);x.save();assert.equal(x.check().nativeVerified,false);
  x.bindCertificate();x.save();assert.equal(x.check().nativeVerified,true,JSON.stringify(x.check()));
});
test('certificate binds exact state, source, selector and canonical precision terms',t=>{
  for(const change of [c=>c.sourceHash='b'.repeat(64),c=>c.quantities[0].state=2,
    c=>c.quantities[0].selection={kind:'combination',id:'D'},c=>c.quantities[0].precision.terms[0]*=2,
    c=>c.quantities.push(clone(c.quantities[0]))]){
    const x=setup(t);change(x.certificate);x.bindCertificate();x.save();
    assert.equal(x.check().nativeVerified,false,'Rehashing a mismatched certificate must fail');
  }
});
test('invalid precision arithmetic prevents reference readiness',t=>{
  const x=setup(t);x.q.engineeringPrecision.absoluteAllowance*=10;x.bindCertificate();x.save();
  assert.equal(x.check().referenceReady,false);
});
test('rehashed certificates cannot authorize derived traces or a different native run',t=>{
  for(const change of [x=>delete x.q.rawTrace,x=>x.q.rawTrace.origin='derived-native-superposition',
    x=>x.q.rawTrace.nativeBasicFactors={DL:2,LL:1},x=>x.certificate.quantities[0].recovery.nativeRun='other-run',
    x=>x.q.rawTrace.sourceModelSha256='c'.repeat(64),x=>x.q.rawTrace.sourceEndNodes.reverse(),
    x=>{x.q.rawTrace.end=1;x.q.location.positionM=1.5;x.q.location.side='left';}]){
    const x=setup(t);change(x);x.bindCertificate();x.save();
    assert.equal(x.check().nativeVerified,false,'Rehashed out-of-scope evidence must fail');
  }
});
test('YJK native gate rejects PKPM precision even after every enclosing binding is rehashed',t=>{
  const x=setup(t);x.bindCertificate();x.save();
  assert.equal(x.check().nativeVerified,true,'The original PKPM fixture must qualify');
  const read=name=>JSON.parse(fs.readFileSync(path.join(x.f.caseDir,name)));
  const descriptor=name=>({path:name,sha256:sha256(fs.readFileSync(path.join(x.f.caseDir,name)))});
  x.f.contract.plannedEngine='YJK';x.f.save();
  const digest=require('./research300-validation.cjs').sourceHash(x.f.caseDir,x.f.contract);
  x.certificate.sourceHash=digest;x.bindCertificate();x.save();
  const ref=read('independent-reference.json'),candidate=read('native-commercial/candidate.json');
  for(const document of [ref,candidate]){
    document.sourceHash=digest;
    document.inputHashes['contract.json']=descriptor('contract.json').sha256;
  }
  candidate.referenceKind='native-yjk-candidate';ref.referenceKind='native-yjk';
  x.f.write('native-commercial/candidate.json',candidate);
  ref.candidateArtifact=descriptor('native-commercial/candidate.json');
  const review=read('native-commercial/qualification.json');
  review.cases[0].sourceHash=digest;review.cases[0].candidateSha256=ref.candidateArtifact.sha256;
  x.f.write('native-commercial/qualification.json',review);
  ref.independentReview=descriptor('native-commercial/qualification.json');
  x.f.write('independent-reference.json',ref);
  const receipt=read('native-receipt.json');receipt.engine='YJK';x.f.write('native-receipt.json',receipt);
  const acceptance=read('acceptance.json');acceptance.sourceHash=digest;
  acceptance.sameEngineTruth.engine='YJK';acceptance.sameEngineTruth.evidence=ref.independentReview;
  Object.assign(acceptance.sameEngineTruth.receipts[0],descriptor('native-receipt.json'));
  acceptance.independentReferenceSha256=descriptor('independent-reference.json').sha256;
  x.f.write('acceptance.json',acceptance);
  const result=x.check();
  assert.equal(result.nativeVerified,false,'nativeVerified must reject independently of referenceReady');
  assert.ok(result.acceptanceErrors.some(error=>error.includes('Certified recovery precision requires PKPM')),
    JSON.stringify(result.acceptanceErrors));
});
