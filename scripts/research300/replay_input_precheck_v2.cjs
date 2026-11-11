#!/usr/bin/env node
'use strict';
// Diagnostic replay of the retained 2026-10-26 model calls. No model dispatch,
// acceptance installation, rewritten submission, or new independent review.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const review=require('../../lib/public-input-review-v2.cjs'),legacy=require('../../lib/public-input-review.cjs'),provider=require('../../lib/corpus-provider.cjs');
function main(argv=process.argv.slice(2)){
  const args={};for(let i=0;i<argv.length;i+=2){assert(['--evidence','--out'].includes(argv[i])&&argv[i+1],'Use --evidence EXTRACTED_ARCHIVE [--out NEW_FILE]');args[argv[i].slice(2)]=argv[i+1];}
  assert(args.evidence,'An extracted evidence directory is required');
  const root=path.resolve(__dirname,'../..'),evidence=path.resolve(args.evidence),reportDir=path.join(root,'docs/implementation/reviews/backend-and-codex-precheck-20261026');
  const manifest=legacy.readJson(path.join(reportDir,'codex-archive-manifest.json'));
  assert.equal(legacy.sha256(fs.readFileSync(path.join(reportDir,'codex-blind-evidence.zip.bin'))),manifest.archiveSha256);
  for(const f of manifest.files){const bytes=fs.readFileSync(legacy.safeFile(evidence,f.path));assert.equal(bytes.length,f.bytes,f.path);assert.equal(legacy.sha256(bytes),f.sha256,f.path);}
  const executions=legacy.readJson(path.join(reportDir,'blind-executions.json')),corpus=provider.loadCorpus({root,corpus:'research-300'}),turns=[];
  for(const row of executions){
    const run=path.join(evidence,'blind-runs-v2',`${row.caseId}-${row.turnId}`),raw=fs.readFileSync(path.join(run,'submission.json'));
    const events=fs.readFileSync(path.join(run,'events.jsonl'),'utf8').trim().split('\n').map(JSON.parse),final=events.filter(e=>e.type==='item.completed'&&e.item?.type==='agent_message').at(-1)?.item.text;
    assert.equal(raw.toString().replace(/\n$/,''),final.replace(/\n$/,''));assert.equal(events.find(e=>e.type==='thread.started').thread_id,row.threadId);
    const dispatch=legacy.readJson(path.join(run,'dispatch.json'));assert.deepEqual(dispatch.reviewer,row.reviewer);assert.equal(legacy.sha256(fs.readFileSync(path.join(run,'prompt.txt'))),dispatch.promptSha256);
    const sealed=path.join(evidence,'blind-sealed',`${row.caseId}-${row.turnId}`),packetDir=fs.existsSync(sealed)?path.join(sealed,'packet'):path.join(evidence,'unsealed-packets',`${row.caseId}-${row.turnId}`);
    const {packet,packetSha256}=legacy.verifyPacket(packetDir);if(fs.existsSync(sealed))legacy.verifySeal(sealed);
    const submission=JSON.parse(raw);assert.equal(submission.packetSha256,packetSha256);assert.equal(dispatch.packetSha256,packetSha256);
    const record=provider.loadCase(corpus,row.caseId),i=record.contract.turns.findIndex(t=>t.id===row.turnId),publicInputs=record.contract.turns.map((_,j)=>provider.getPublicTurnInput(record,j));
    assert.deepEqual(packet,legacy.buildPacketFiles(publicInputs,i).descriptor,'Legacy packet must still match original public input/protocol');
    const context=review.contextFor(record,i,packet),grade=review.compareReconstruction(submission,review.expectedFor(record,i),context,packet);
    turns.push({caseId:row.caseId,turnId:row.turnId,submissionSha256:legacy.sha256(raw),packetSha256,threadId:row.threadId,...grade,relativeGeometrySources:context.conventions.geometrySources});
  }
  const cases=[...new Set(turns.map(t=>t.caseId))].sort().map(caseId=>{
    const rows=turns.filter(t=>t.caseId===caseId),dimensions={};
    for(const key of ['physical','protocol','clarification','observations']){const statuses=rows.map(t=>t.dimensions[key].status);dimensions[key]=statuses.some(s=>['failed','ungradable'].includes(s))?'failed':statuses.includes('partial')?'partial':'passed';}
    return {caseId,dimensions,diagnosticStatus:Object.values(dimensions).includes('failed')?'failed':Object.values(dimensions).includes('partial')?'partial':'passed'};
  });
  const result={schemaVersion:1,scope:'Existing legacy calls assessed with v2 physical semantics; not fresh v2 input reviews or engineering trials',diagnosticOnly:true,acceptanceWritten:false,modelCalls:0,
    filesByteVerified:manifest.files.length,finalMessagesVerified:turns.length,originalArchiveSha256:manifest.archiveSha256,grader:{version:review.VERSION,sources:review.sourceHashes()},
    summary:{cases:cases.length,turns:turns.length,physicalPassed:cases.filter(c=>c.dimensions.physical==='passed').length,physicalFailed:cases.filter(c=>c.dimensions.physical==='failed').length,
      protocolPassed:cases.filter(c=>c.dimensions.protocol==='passed').length,protocolFailed:cases.filter(c=>c.dimensions.protocol==='failed').length,allMandatoryDimensionsPassed:cases.filter(c=>c.diagnosticStatus==='passed').length},cases,turns};
  if(args.out)fs.writeFileSync(path.resolve(args.out),legacy.jsonBytes(result),{flag:'wx'});
  return result;
}
if(require.main===module)try{const result=main();process.stdout.write(JSON.stringify({scope:result.scope,summary:result.summary,acceptanceWritten:false,modelCalls:0},null,2)+'\n');}catch(e){process.stderr.write(e.message+'\n');process.exitCode=1;}
module.exports={main};
