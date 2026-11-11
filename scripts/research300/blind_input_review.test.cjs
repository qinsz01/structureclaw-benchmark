'use strict';
const test=require('node:test');const assert=require('node:assert/strict');const fs=require('node:fs');const path=require('node:path');const os=require('node:os');
const review=require('../../lib/public-input-review.cjs');
const {decodePacket}=require('./blind-input-review-public.cjs');
function temp(t){const dir=fs.mkdtempSync(path.join(os.tmpdir(),'blind-packet-'));t.after(()=>fs.rmSync(dir,{recursive:true,force:true}));return dir;}
function packetFixture(t){const root=temp(t),packet=path.join(root,'packet');fs.mkdirSync(path.join(packet,'t1'),{recursive:true});
  const properties={materials:[{id:'M',E:123,G:45,nu:0.3,rho:7800}],sections:[{id:'S',properties:{A:0.1,Iy:0.2,Iz:0.3,J:0.4}}],analysis_control:{self_weight:false},coordinate_system:{dimension:'2d',plane:'xz'}};
  const files={'t1/properties.json':review.jsonBytes(properties),'t1/input.png':Buffer.from('a public test drawing'), 't1/assignments.json':review.jsonBytes([{id:'beam',type:'beam',material:'M',section:'S',rotation_angle:0,referenceVector:null}])};
  for(const [name,data]of Object.entries(files))fs.writeFileSync(path.join(packet,name),data);
  const descriptor={schemaVersion:1,caseId:'MM-001',turnId:'t1',inputBinding:{schemaVersion:1,caseId:'MM-001',inputEdition:'current',publicInputSha256:'1'.repeat(64)},history:[{turnId:'t1',attachments:Object.keys(files).map(file=>({path:file,name:path.basename(file)}))}],files:Object.entries(files).map(([file,data])=>({path:file,sha256:review.sha256(data),bytes:data.length}))};
  fs.writeFileSync(path.join(packet,'packet.json'),review.jsonBytes(descriptor));return {root,packet,descriptor};}
function submission(packet){return {schemaVersion:1,caseId:'MM-001',turnId:'t1',packetSha256:review.sha256(fs.readFileSync(path.join(packet,'packet.json'))),reviewer:{id:'fresh-agent-session',kind:'agent',independent:true},method:'public-only-reconstruction',model:{},unresolved:[],observations:[]};}
function provenance(s){return {schemaVersion:1,reviewer:s.reviewer,method:s.method,packetSha256:s.packetSha256,inputScope:'packet-only',authoringParticipation:false,hiddenAccess:false,freshContext:true,dispatchEvidence:'Local orchestration session ID fresh-agent-session; dispatched with packet directory only.'};}

test('standalone decoder copies public table facts and never invents geometry or connectivity',t=>{
  const {packet}=packetFixture(t);const s=decodePacket(packet,'fresh-agent-session');
  assert.equal(s.model.materials[0].E,123);assert.equal(s.model.elements[0].id,'beam');assert.equal(s.model.elements[0].nodes,undefined);assert.deepEqual(s.model.nodes,[]);
  assert.deepEqual(s.observations,[]);assert.deepEqual(s.unresolved,[]);
});
test('sealing retains the exact submission bytes and rejects altered packet/submission/provenance',t=>{
  const {root,packet}=packetFixture(t),s=submission(packet);const sub=path.join(root,'submission.json'),prov=path.join(root,'provenance.json'),out=path.join(root,'sealed');
  fs.writeFileSync(sub,review.jsonBytes(s));fs.writeFileSync(prov,review.jsonBytes(provenance(s)));
  const receipt=review.sealSubmission({packetDir:packet,submissionFile:sub,provenanceFile:prov,outDir:out});
  assert.equal(receipt.submissionSha256,review.sha256(fs.readFileSync(sub)));assert.equal(review.verifySeal(out).submission.caseId,'MM-001');
  fs.appendFileSync(path.join(out,'submission.json'),' ');assert.throws(()=>review.verifySeal(out),/submission.*hash/);
  fs.writeFileSync(path.join(out,'submission.json'),review.jsonBytes(s));fs.appendFileSync(path.join(out,'packet','t1/input.png'),'tamper');assert.throws(()=>review.verifySeal(out),/packet.*hash/);
});
test('packets fail closed on undeclared hidden files, SVG, traversal and missing reviewer provenance',t=>{
  const {root,packet}=packetFixture(t);fs.writeFileSync(path.join(packet,'model-state-1.json'),'{}');assert.throws(()=>review.verifyPacket(packet),/undeclared/);fs.unlinkSync(path.join(packet,'model-state-1.json'));
  const s=submission(packet),sub=path.join(root,'submission.json'),prov=path.join(root,'provenance.json');fs.writeFileSync(sub,review.jsonBytes(s));const p=provenance(s);delete p.freshContext;fs.writeFileSync(prov,review.jsonBytes(p));
  assert.throws(()=>review.sealSubmission({packetDir:packet,submissionFile:sub,provenanceFile:prov,outDir:path.join(root,'sealed')}),/provenance/);
  const descriptor=JSON.parse(fs.readFileSync(path.join(packet,'packet.json')));descriptor.files[0].path='../secret';fs.writeFileSync(path.join(packet,'packet.json'),review.jsonBytes(descriptor));assert.throws(()=>review.verifyPacket(packet),/unsafe|undeclared/);
});
test('old packet bindings are rejected instead of inheriting archived reviews', t => {
  const {packet,descriptor}=packetFixture(t);descriptor.inputBinding.inputEdition='visual-v2';
  fs.writeFileSync(path.join(packet,'packet.json'),review.jsonBytes(descriptor));
  assert.throws(()=>review.verifyPacket(packet),/schema/);
});
test('export creates isolated history through the requested turn and excludes authoring files',t=>{
  const {root}=packetFixture(t),dir=path.join(root,'source');fs.mkdirSync(dir);fs.writeFileSync(path.join(dir,'first.png'),'first');fs.writeFileSync(path.join(dir,'later.png'),'later');
  const binding={schemaVersion:1,caseId:'MM-007',inputEdition:'current',publicInputSha256:'2'.repeat(64)};
  const turns=['t1','t2'].map((turnId,i)=>({id:'MM-007',turnId,inputBinding:binding,instruction:i?'resolved instruction':'initial instruction',responseContract:{stage:turnId},attachments:[{name:i?'later.png':'first.png',path:path.join(dir,i?'later.png':'first.png')}]}));
  const exported=review.buildPacketFiles(turns,0);assert.equal(exported.descriptor.history.length,1);assert.ok(!JSON.stringify(exported.descriptor).includes('later.png'));assert.ok(!JSON.stringify(exported.descriptor).includes('unresolvedFields'));
  assert.equal(review.buildPacketFiles(turns,1).descriptor.history.length,2);
  turns[0].attachments.push({name:'author.svg',path:path.join(dir,'first.png')});assert.throws(()=>review.buildPacketFiles(turns,0),/SVG|authoring/);
});

test('the sole MM packet contains only its current drawing and decoder invents no raster facts',t=>{
  const provider=require('../../lib/corpus-provider.cjs');
  const record=provider.loadCase(provider.loadCorpus({corpus:'research-300'}),'MM-001');
  const built=review.buildPacketFiles([provider.getPublicTurnInput(record,0)],0),root=temp(t);
  for(const [name,data]of built.files){fs.mkdirSync(path.dirname(path.join(root,name)),{recursive:true});fs.writeFileSync(path.join(root,name),data);}
  fs.writeFileSync(path.join(root,'packet.json'),review.jsonBytes(built.descriptor));
  assert.deepEqual(built.descriptor.history[0].attachments.map(a=>a.name),['drawing.png']);
  const s=decodePacket(root,'drawing-reviewer');assert.deepEqual(s.model.nodes,[]);assert.deepEqual(s.model.elements,[]);
  assert.deepEqual(s.observations,[]);assert.deepEqual(s.unresolved,[]);
});

test('real provider export, sealing, grading and replay reject stale or modified claims',t=>{
  // Synthetic fixture only. It is never written as an actual case review.
  const {fixture}=require('../../lib/research300-test-fixtures.cjs'),provider=require('../../lib/corpus-provider.cjs');
  const {buildManifest}=require('../build-research300-manifest.cjs'),{spawnSync}=require('node:child_process');
  const f=fixture(t,'MM-001'),repo=path.resolve(__dirname,'../..');
  f.write('drawing.svg','<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100"><rect width="200" height="100" fill="white"/><line x1="10" y1="50" x2="190" y2="50" stroke="black"/><text x="50" y="30">6 m</text></svg>');
  fs.writeFileSync(path.join(f.caseDir,'drawing.png'),Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAFklEQVR4nGP4z8DA8J+BkYHh////DAAe9gT9Ce00PgAAAABJRU5ErkJggg==','base64'));
  f.write('analysis-conventions-v2.txt',fs.readFileSync(path.join(repo,'corpora/research-300/cases/MM-084/analysis-conventions-v2.txt'),'utf8'));
  f.contract.attachments.push('drawing.svg','drawing.png','analysis-conventions-v2.txt');f.contract.turns[0].attachments.push('drawing.svg','drawing.png','analysis-conventions-v2.txt');f.save();
  fs.writeFileSync(path.join(f.root,'corpora/research-300/manifest.json'),review.jsonBytes(buildManifest({root:f.root,allowPartial:true})));
  const generated=spawnSync('python3',[path.join(repo,'scripts/research300/public_input_clean.py'),'--root',f.root,'--case','MM-001'],{encoding:'utf8',timeout:30000});assert.equal(generated.status,0,generated.stderr||generated.stdout);
  const record=provider.loadCase(provider.loadCorpus({corpus:'research-300',root:f.root}),'MM-001'),packet=path.join(f.root,'staged');review.exportPacket(record,0,packet);
  const s=submission(packet);s.model={...structuredClone(f.model),axes:{mode:'xz',elementDirection:'listed-node-order',rotationDefaultDegrees:0}};
  // This readback explicitly includes the released convention. Gold omits it;
  // the grade/replay path must derive its expectation from the bound public file.
  s.model.sections[0].properties.Asy=0.008333333333333333;s.model.sections[0].properties.Asz=0.008333333333333333;
  s.observations=review.CATEGORIES.map(category=>({category,files:['t1/drawing.png'],observation:'Synthetic test observation, never actual review evidence.'}));
  const sub=path.join(f.root,'submission.json'),prov=path.join(f.root,'provenance.json'),out=path.join(f.root,'sealed');fs.writeFileSync(sub,review.jsonBytes(s));fs.writeFileSync(prov,review.jsonBytes(provenance(s)));
  review.sealSubmission({packetDir:packet,submissionFile:sub,provenanceFile:prov,outDir:out});
  const report=review.gradeEvidence(record,['sealed/receipt.json']);assert.equal(report.status,'passed');assert.ok(report.turns[0].evidence.publicConvention1.path.endsWith('analysis-conventions-v2.txt'));
  const file=review.reviewPath(record,report.inputBinding);fs.mkdirSync(path.dirname(file),{recursive:true});fs.writeFileSync(file,review.jsonBytes(report));
  let verified=review.getPublicInputReview(record,report.inputBinding);assert.equal(verified.status,'passed');assert.equal(verified.verified,true);
  assert.ok(verified.evidence.some(e=>e.path==='lib/public-input-review.cjs'));assert.ok(verified.evidence.some(e=>e.path==='scripts/research300/blind_input_review.cjs'));assert.ok(verified.evidence.some(e=>e.path==='sealed/packet/t1/drawing.png'));assert.ok(verified.evidence.every(e=>!path.isAbsolute(e.path)&&!e.path.startsWith('..')));
  const changed=structuredClone(report);changed.coverage.loads.matched++;fs.writeFileSync(file,review.jsonBytes(changed));assert.equal(review.getPublicInputReview(record,report.inputBinding).status,'invalid');fs.writeFileSync(file,review.jsonBytes(report));
  assert.equal(review.getPublicInputReview(record,{...report.inputBinding,publicInputSha256:'f'.repeat(64)}).status,'invalid');
  const receiptFile=path.join(out,'receipt.json'),receipt=fs.readFileSync(receiptFile);fs.writeFileSync(receiptFile,review.jsonBytes({...JSON.parse(receipt),reviewer:{id:'other',kind:'agent',independent:true}}));assert.equal(review.getPublicInputReview(record,report.inputBinding).status,'invalid');fs.writeFileSync(receiptFile,receipt);
  fs.appendFileSync(path.join(out,'provenance.json'),' ');assert.equal(review.getPublicInputReview(record,report.inputBinding).status,'invalid');
});
