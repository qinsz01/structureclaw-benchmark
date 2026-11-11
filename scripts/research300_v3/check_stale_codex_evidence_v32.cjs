'use strict';
// A prior run is a valid identity, but after a physical change it cannot
// substantiate the current answer. Mutate only in-memory reference fields.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {loadControlledIndex,readSealed}=require('./controlled-evidence-v32.cjs');
const {evaluate}=require('./evaluate-v32.cjs');
const sha=x=>crypto.createHash('sha256').update(x).digest('hex');
const [rootArg,pinPath,pinSha256,editionArg,output]=process.argv.slice(2);
const root=fs.realpathSync(rootArg),edition=fs.realpathSync(editionArg),pinBytes=fs.readFileSync(pinPath);
if(!/^[a-f0-9]{64}$/.test(pinSha256)||sha(pinBytes)!==pinSha256)throw Error('External pin required');
const pin=JSON.parse(pinBytes),spec=JSON.parse(readSealed(root,pin.specification)),index=JSON.parse(readSealed(root,pin.index));
const manifestBytes=fs.readFileSync(path.join(edition,'manifest.json')),manifest=JSON.parse(manifestBytes);
if(sha(manifestBytes)!==spec.editionManifestSha256)throw Error('Edition differs');
const reader=loadControlledIndex({root,indexPath:pin.index.path,indexSha256:pin.index.sha256,
 editionManifestSha256:spec.editionManifestSha256,sutCommit:spec.sutCommit,inputProtocol:spec.inputProtocol,
 executionSpecificationSha256:pin.specification.sha256});
const rows=[];
for(const row of index.turns.filter(t=>t.caseId.startsWith('V3-INT-')&&Number(t.turnId.slice(1))>1)){
 const previous='t'+(Number(row.turnId.slice(1))-1),current=reader.readAnswer(row.caseId,row.turnId),old=reader.readAnswer(row.caseId,previous);
 const c=manifest.cases.find(c=>c.id===row.caseId),t=c.turns.find(t=>t.id===row.turnId);
 const ref=JSON.parse(readSealed(edition,manifest.files.find(f=>f.path===t.private)));
 const baseline=evaluate(ref,current.answer,current.jobs,current.currentJobIds);
 if(!baseline.passed)throw Error('Control requires an actually passing original');
 const answer=structuredClone(current.answer),group=['jobIds','jobIdsByScenario','jobIdsByModel'].find(k=>answer[k]!==undefined);
 answer[group]=structuredClone(old.answer[group]);
 const resolved=reader.resolveAnswer(answer,row.caseId,row.turnId),result=evaluate(ref,resolved.answer,resolved.jobs,resolved.currentJobIds);
 rows.push({caseId:row.caseId,turnId:row.turnId,previousTurn:previous,
  name:'stale-native-evidence-after-issued-physical-change',priorIdentityAccepted:true,
  originalPassed:baseline.passed,originalAnswerSha256:current.originalAnswerSha256,
  expectedOutcome:'candidate_failure',actualOutcome:result.outcome,passed:result.outcome==='candidate_failure',
  failures:result.metrics.filter(m=>!m.pass)});
}
if(!rows.length)throw Error('No executed interactive change controls available');
const result={kind:'research300-v32-actual-stale-evidence-controls',operatorPinSha256:pinSha256,
 formalComparisonScore:false,candidateInvocations:0,nativeSolverInvocations:0,originalAnswersModified:false,
 controls:rows.length,controlsPassed:rows.filter(r=>r.passed).length,allPassed:rows.every(r=>r.passed),
 checkCodeSha256:sha(fs.readFileSync(__filename)),rows};
fs.writeFileSync(output,JSON.stringify(result,null,2)+'\n',{flag:'wx'});
process.stdout.write(JSON.stringify({controls:result.controls,controlsPassed:result.controlsPassed})+'\n');
if(!result.allPassed)process.exitCode=1;
