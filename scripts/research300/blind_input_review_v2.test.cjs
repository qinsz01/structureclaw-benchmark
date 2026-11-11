'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const review=require('../../lib/public-input-review-v2.cjs');
const provider=require('../../lib/corpus-provider.cjs');
const provenance=s=>({schemaVersion:1,reviewer:s.reviewer,method:s.method,packetSha256:s.packetSha256,inputScope:'packet-only',authoringParticipation:false,hiddenAccess:false,freshContext:true,dispatchEvidence:'Synthetic test dispatcher, never actual independent evidence.'});
test('v2 exported contract is real JSON schema and contains no future-turn inputs',t=>{
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'review-v2-export-'));t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
  fs.writeFileSync(path.join(root,'first.png'),'fixture');fs.writeFileSync(path.join(root,'later.png'),'later');
  const binding={inputEdition:'current'},turns=['t1','t2'].map((turnId,i)=>({id:'MM-007',turnId,inputBinding:binding,instruction:'test',attachments:[{name:i?'later.png':'first.png',path:path.join(root,i?'later.png':'first.png')}]}));
  const b=review.buildPacketFiles(turns,0);assert.equal(b.descriptor.protocolVersion,review.PROTOCOL_VERSION);assert.equal(b.descriptor.history.length,1);assert.ok(!JSON.stringify(b.descriptor).includes('later.png'));
  const schema=JSON.parse(b.files.get('submission-schema.json'));assert.equal(schema.properties.model.additionalProperties,false);assert.ok(schema.properties.model.properties.analysis_control.properties.stiffness_reductions);assert.match(b.files.get('README.md').toString(),/NEVER fractions/);
});
test('v2 export/seal/grade/verify retains invalid raw JSON, replays dimensions and rejects stale or tampered evidence',t=>{
  const {fixture,publishInputs}=require('../../lib/research300-test-fixtures.cjs'),f=fixture(t,'MM-001');
  f.write('drawing.svg','<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100"><rect width="200" height="100" fill="white"/><line x1="10" y1="50" x2="190" y2="50" stroke="black"/><text x="50" y="30">6 m</text></svg>');
  fs.writeFileSync(path.join(f.caseDir,'drawing.png'),Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAFklEQVR4nGP4z8DA8J+BkYHh////DAAe9gT9Ce00PgAAAABJRU5ErkJggg==','base64'));
  f.contract.attachments.push('drawing.svg','drawing.png');f.contract.turns[0].attachments.push('drawing.svg','drawing.png');f.save();publishInputs(f);
  const record=provider.loadCase(provider.loadCorpus({root:f.root,corpus:'research-300'}),'MM-001'),packet=path.join(f.root,'packet');review.exportPacket(record,0,packet);
  const s={schemaVersion:1,caseId:record.id,turnId:'t1',packetSha256:review.sha256(fs.readFileSync(path.join(packet,'packet.json'))),reviewer:{id:'test-only',kind:'agent',independent:true},method:review.METHOD,
    model:{...structuredClone(f.model),axes:{mode:'xz',elementDirection:'listed-node-order',rotationDefaultDegrees:0}},unresolved:[],observations:review.CATEGORIES.map(category=>({category,files:['t1/drawing.png'],observation:'Synthetic fixture only.'}))};
  const sub=path.join(f.root,'submission.json'),prov=path.join(f.root,'provenance.json'),sealed=path.join(f.root,'sealed');fs.writeFileSync(sub,review.jsonBytes(s));fs.writeFileSync(prov,review.jsonBytes(provenance(s)));
  review.sealSubmission({packetDir:packet,submissionFile:sub,provenanceFile:prov,outDir:sealed});
  assert.deepEqual(fs.readFileSync(sub),fs.readFileSync(path.join(sealed,'submission.json')));
  const report=review.gradeEvidence(record,['sealed/receipt.json']);assert.equal(report.status,'passed');assert.equal(report.grader.version,review.VERSION);assert.equal(report.dimensions.physical.status,'passed');
  const file=review.reviewPath(record,report.inputBinding);fs.mkdirSync(path.dirname(file),{recursive:true});fs.writeFileSync(file,review.jsonBytes(report));assert.equal(review.getPublicInputReview(record,report.inputBinding).verified,true);
  const changed=structuredClone(report);changed.dimensions.physical.status='failed';fs.writeFileSync(file,review.jsonBytes(changed));assert.equal(review.getPublicInputReview(record,report.inputBinding).status,'invalid');fs.writeFileSync(file,review.jsonBytes(report));
  assert.throws(()=>review.gradeEvidence(record,['sealed/receipt.json','sealed/receipt.json']),/duplicate/);
  fs.appendFileSync(path.join(sealed,'submission.json'),' ');assert.throws(()=>review.verifySeal(sealed),/hash mismatch/);fs.writeFileSync(path.join(sealed,'submission.json'),review.jsonBytes(s));
  const receipt=fs.readFileSync(path.join(sealed,'receipt.json')),r=JSON.parse(receipt);r.reviewer.id='other';fs.writeFileSync(path.join(sealed,'receipt.json'),review.jsonBytes(r));assert.throws(()=>review.verifySeal(sealed),/identity/);fs.writeFileSync(path.join(sealed,'receipt.json'),receipt);
  const bad=structuredClone(s);bad.model.materials[0].E='200000';fs.writeFileSync(sub,review.jsonBytes(bad));
  review.sealSubmission({packetDir:packet,submissionFile:sub,provenanceFile:prov,outDir:path.join(f.root,'invalid')});const g=review.gradeEvidence(record,['invalid/receipt.json']);assert.equal(g.status,'failed');assert.equal(g.turns[0].dimensions.protocol.status,'failed');assert.equal(g.turns[0].dimensions.physical.status,'ungradable');
  const packetFile=path.join(sealed,'packet','t1/drawing.png');fs.appendFileSync(packetFile,'tamper');assert.throws(()=>review.verifySeal(sealed),/packet.*hash/);
});
