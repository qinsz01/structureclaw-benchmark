'use strict';
// Install newly bound references only after the independent numerical and raw
// physical audits both succeed. Public-input review remains a separate gate.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {createHash}=require('node:crypto');
const {sourceHash,validateResearchCase}=require('../../lib/research300-validation.cjs');
const {modelFingerprint}=require('../../lib/analysis-evidence.cjs');
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const read=file=>JSON.parse(fs.readFileSync(file));
function qualify({root,diagnostics,physics,numerical}) {
  root=path.resolve(root);diagnostics=path.resolve(diagnostics);
  assert(root.includes(`${path.sep}.bench-work${path.sep}`),'Use an isolated working edition');
  const audit=read(physics),cross=read(numerical);
  assert.equal(audit.valid,true);assert.equal(cross.valid,true);
  assert.equal(path.resolve(audit.roots.benchmark),root);
  assert.equal(path.resolve(cross.roots.authored),root);
  const results=[];
  for(const check of cross.cases) {
    const id=check.id,folder=path.join(root,'corpora/research-300/cases',id),native=path.join(diagnostics,id);
    const contract=read(path.join(folder,'contract.json')),digest=sourceHash(folder,contract);
    assert.equal(check.sourceHash,digest);assert.equal(check.referenceValidated,true);assert.equal(check.nativeAgreement,true);
    const physical=audit.cases.find(c=>c.caseId===id);assert.equal(physical.pass,true);assert.equal(physical.sourceHash,digest);
    const reference=fs.readFileSync(path.join(native,'independent-reference.json'));
    assert.equal(sha(reference),physical.independentReferenceSha256);
    const save=(name,bytes)=>{fs.writeFileSync(path.join(folder,name),bytes,{flag:'wx'});return {path:name,sha256:sha(bytes)};};
    const json=(name,object)=>save(name,Buffer.from(JSON.stringify(object,null,2)+'\n'));
    const ref=save('independent-reference.json',reference);
    if(contract.plannedEngine!=='OpenSees'){results.push({id,role:'matrix-diagnostic-only'});continue;}
    const artifacts=[];
    for(const name of ['native-opensees-reference.json','native-input-receipt.json','native-solver-receipt.json','native-raw-responses.json','native-checks.json']) {
      const bytes=fs.readFileSync(path.join(native,name));
      const expected=name==='native-opensees-reference.json'?physical.nativeReferenceSha256:physical.artifacts.find(a=>a.path===name)?.sha256;
      assert.equal(sha(bytes),expected);artifacts.push(save(name,bytes));
    }
    const reviewer='codex-root-operator-independent-physics-review-20261027';
    const review=json('native-independent-review.json',{schemaVersion:1,caseId:id,sourceHash:digest,reviewer,
      reviewKind:'independent-matrix-and-raw-physics-audit',decision:'verified',
      independentReferenceSha256:ref.sha256,nativeReferenceSha256:physical.nativeReferenceSha256,
      reviewerCodeSha256:audit.reviewerCodeSha256,numericalComparison:check,physicalAudit:physical,
      inputBlindReview:'pending',externalHumanBlindReview:false});
    const receipts=physical.runs.map((run,index)=>{
      assert.equal(run.analysisReturnCode,0);
      const receipt=json(`native-run-${index+1}.json`,{schemaVersion:1,caseId:id,state:run.state,
        selection:run.selection,modelSha256:run.modelSha256,engine:'OpenSees',engineVersion:physical.solver.version,
        status:'succeeded',runId:`diversity-${digest.slice(0,16)}-${run.state}-${run.selection.kind}-${run.selection.id}`,
        receiptRole:'Wrapper of retained actual OpenSees run; no new solve or model call inferred',artifacts:[...artifacts,review]});
      return {...receipt,state:run.state,selection:run.selection};
    });
    json('acceptance.json',{schemaVersion:1,sourceHash:digest,independentReferenceSha256:ref.sha256,
      inputBlindReview:{status:'pending'},sameEngineTruth:{status:'verified',engine:'OpenSees',independentlyReviewed:true,reviewer,evidence:review,receipts}});
    json('reference-provenance.json',{schemaVersion:1,caseId:id,sourceHash:digest,referenceSha256:ref.sha256,
      states:contract.modelStates.map((file,index)=>({state:index+1,modelHash:modelFingerprint(read(path.join(folder,file))),engineId:'OpenSees',status:'native-verified'}))});
    assert.equal(sourceHash(folder,contract),digest);
    const validation=validateResearchCase({root,caseDir:folder,stage:'reference-ready'});
    assert.equal(validation.referenceReady,true,JSON.stringify(validation));assert.equal(validation.nativeVerified,true,JSON.stringify(validation));
    results.push({id,role:'same-engine-reference',sourceHash:digest,referenceSha256:ref.sha256,nativeVerified:true,inputReviewed:false});
  }
  return {schemaVersion:1,cases:results,qualified:results.filter(c=>c.nativeVerified).length};
}
module.exports={qualify};
if(require.main===module){
  const [root,diagnostics,physics,numerical,output]=process.argv.slice(2);
  const result=qualify({root,diagnostics,physics,numerical});
  fs.writeFileSync(output,JSON.stringify(result,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify({qualified:result.qualified,cases:result.cases.length}));
}
