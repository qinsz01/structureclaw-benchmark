'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {fixture}=require('./research300-test-fixtures.cjs');
const {buildManifest}=require('../scripts/build-research300-manifest.cjs');
const {validateResearchCase}=require('./research300-validation.cjs');
const {getResponseContract,RESPONSE_CONTRACT_VERSION,sha256}=require('./corpus-provider.cjs');
const repo=path.resolve(__dirname,'..');

test('manifest is byte deterministic across roots, with separate public/private hashes and original source links',t=>{
 const a=fixture(t),b=fixture(t);const first=buildManifest({root:a.root,allowPartial:true}),second=buildManifest({root:b.root,allowPartial:true});
 assert.equal(JSON.stringify(first),JSON.stringify(second));const c=first.cases[0];assert.deepEqual(c.publicFiles.map(f=>f.path),['geometry.csv','prompt.txt','properties.json']);assert.ok(c.privateFiles.some(f=>f.path==='model-state-1.json'));assert.equal(first.originalSources.find(s=>s.role==='tasks').path,'planning/sources/all-tasks-engines-v2.json');assert.equal(first.summary.authored,1);assert.equal(first.summary.accepted,0);assert.doesNotMatch(JSON.stringify(first),/\/tmp\/|research300-test-/);
});
test('public and private changes affect only corresponding content hashes',t=>{const f=fixture(t);const before=buildManifest({root:f.root,allowPartial:true}).cases[0];fs.appendFileSync(path.join(f.caseDir,'geometry.csv'),'# units m\n');const publicChange=buildManifest({root:f.root,allowPartial:true}).cases[0];assert.notEqual(publicChange.publicSha256,before.publicSha256);assert.equal(publicChange.privateSha256,before.privateSha256);f.write('author-notes.txt','Private documented appendix decision.');const privateChange=buildManifest({root:f.root,allowPartial:true}).cases[0];assert.equal(privateChange.publicSha256,publicChange.publicSha256);assert.notEqual(privateChange.privateSha256,publicChange.privateSha256);});
test('independent input review status remains separate from pending native evidence',t=>{const f=fixture(t);const a=f.addAcceptance();a.sameEngineTruth.status='pending';a.sameEngineTruth.receipts=[];f.write('acceptance.json',a);const result=validateResearchCase({root:f.root,caseDir:f.caseDir});assert.equal(result.inputReviewed,true);assert.equal(result.nativeVerified,false);assert.equal(result.accepted,false);const m=buildManifest({root:f.root,allowPartial:true});assert.equal(m.cases[0].statuses.inputReview,'independently-reviewed');assert.equal(m.cases[0].statuses.native,'pending');assert.equal(m.summary.inputReviewed,1);assert.equal(m.summary.accepted,0);});
function invoke(main,args) {
 const saved={out:process.stdout.write,err:process.stderr.write,exit:process.exitCode};let stdout='',stderr='';
 process.stdout.write=chunk=>{stdout+=chunk;return true;};process.stderr.write=chunk=>{stderr+=chunk;return true;};process.exitCode=0;
 try {main(args);return {status:process.exitCode,stdout,stderr};} finally {process.stdout.write=saved.out;process.stderr.write=saved.err;process.exitCode=saved.exit;}
}
test('manifest CLI has no implicit output and refuses invalid/full-incomplete corpus or overwrite',t=>{const f=fixture(t),main=require('../scripts/build-research300-manifest.cjs').main,output=path.join(f.root,'manifest.json');let r=invoke(main,['--root',f.root]);assert.notEqual(r.status,0);assert.equal(fs.existsSync(output),false);r=invoke(main,['--root',f.root,'--output',output]);assert.notEqual(r.status,0);assert.equal(fs.existsSync(output),false);r=invoke(main,['--root',f.root,'--allow-partial','--output',output]);assert.equal(r.status,0,r.stderr);const bytes=fs.readFileSync(output);r=invoke(main,['--root',f.root,'--allow-partial','--output',output]);assert.notEqual(r.status,0);assert.deepEqual(fs.readFileSync(output),bytes);});
test('validation CLI reports authored success and accepted pending as distinct exit statuses',t=>{const f=fixture(t),main=require('../scripts/validate-research300.cjs').main;const authored=invoke(main,['--root',f.root,'--case','STD-001','--json']);assert.equal(authored.status,0,authored.stderr);assert.equal(JSON.parse(authored.stdout).summary.authored,1);const accepted=invoke(main,['--root',f.root,'--case','STD-001','--stage','accepted','--json']);assert.equal(accepted.status,1);assert.equal(JSON.parse(accepted.stdout).summary.accepted,0);});
test('public hash includes turn instructions and attachment release schedule stored in private contract',t=>{const f=fixture(t),before=buildManifest({root:f.root,allowPartial:true}).cases[0];f.contract.turns[0].instruction+=' Preserve the sign.';f.save();const after=buildManifest({root:f.root,allowPartial:true}).cases[0];assert.deepEqual(after.publicFiles,before.publicFiles);assert.notEqual(after.publicSha256,before.publicSha256);});

test('manifest pins the public response protocol and hashes the exact generated contract in turn order',t=>{
 const f=fixture(t),manifest=buildManifest({root:f.root,allowPartial:true}),entry=manifest.cases[0];
 const responseContract=getResponseContract({contract:f.contract,referenceRequests:f.requests},0);
 const digest=value=>sha256(Buffer.from(JSON.stringify(value)));
 assert.equal(manifest.responseContractVersion,'research300-response-v1');assert.equal(manifest.responseContractVersion,RESPONSE_CONTRACT_VERSION);
 assert.deepEqual(entry.responseContractTurnHashes,[{turnId:'t1',sha256:digest(responseContract)}]);
 assert.equal(entry.responseContractSha256,digest([{turnId:'t1',responseContract}]));
 assert.equal(entry.publicSha256,digest({files:entry.publicFiles,turns:[{id:'t1',instruction:f.contract.turns[0].instruction,attachments:f.contract.turns[0].attachments,responseContract}]}));
 assert.equal(Object.hasOwn(entry,'responseContract'),false,'manifest publishes hashes rather than copying selectors or private requests');
});

test('public selectors and per-turn reporting units bind response and public hashes while sourceHash stays the authored-file algorithm',t=>{
 const f=fixture(t),before=buildManifest({root:f.root,allowPartial:true}).cases[0];
 f.requests.states[0].quantities[0].selection.kind='combination';f.save();
 const selectionChange=buildManifest({root:f.root,allowPartial:true}).cases[0];
 assert.deepEqual(selectionChange.publicFiles,before.publicFiles);assert.notEqual(selectionChange.publicSha256,before.publicSha256);assert.notEqual(selectionChange.responseContractSha256,before.responseContractSha256);assert.notEqual(selectionChange.sourceHash,before.sourceHash);
 f.contract.turns[0].outputUnits={'D:mid-u':'mm'};f.save();
 const unitsChange=buildManifest({root:f.root,allowPartial:true}).cases[0];
 assert.notEqual(unitsChange.publicSha256,selectionChange.publicSha256);assert.notEqual(unitsChange.responseContractTurnHashes[0].sha256,selectionChange.responseContractTurnHashes[0].sha256);
 const files=[...new Set(['contract.json','prompt.txt','reference-requests.json',...f.contract.modelStates,...f.contract.attachments])].sort((a,b)=>Buffer.compare(Buffer.from(a),Buffer.from(b))).map(name=>({path:name,sha256:sha256(fs.readFileSync(path.join(f.caseDir,name)))}));
 assert.equal(unitsChange.sourceHash,sha256(Buffer.from(JSON.stringify({schemaVersion:1,files}))));
});

test('a future-turn selector changes only its own response contract hash',t=>{
 const f=fixture(t);f.contract.turns[0].requiredOutputIds=['reactions'];
 f.contract.turns.push({id:'t2',instruction:'报告跨中位移和弯矩。',state:1,expectation:'query',attachments:[],unresolvedFields:[],expectedQuestions:[],requiredOutputIds:['midpoint']});
 f.contract.requiredOutputs[0].turnIds=['t1'];f.contract.requiredOutputs[1].turnIds=['t2'];f.save();
 const before=buildManifest({root:f.root,allowPartial:true}).cases[0];
 assert.equal(before.validation.authored,true,before.validation.errors.join('; '));
 f.contract.turns[1].outputUnits={'D:mid-u':'mm'};f.save();
 const after=buildManifest({root:f.root,allowPartial:true}).cases[0];
 assert.equal(after.responseContractTurnHashes[0].sha256,before.responseContractTurnHashes[0].sha256);
 assert.notEqual(after.responseContractTurnHashes[1].sha256,before.responseContractTurnHashes[1].sha256);assert.notEqual(after.responseContractSha256,before.responseContractSha256);assert.notEqual(after.publicSha256,before.publicSha256);
});

test('private tolerance and authored value metadata change sourceHash without changing the public response digest',t=>{
 const f=fixture(t),before=buildManifest({root:f.root,allowPartial:true}).cases[0];
 f.requests.states[0].quantities[0].tolerance.absolute=1e-7;f.requests.states[0].quantities[0].toleranceJustification='Frozen synthetic fixture tolerance for regression.';
 f.contract.authoringMetadata={privateValue:987654321.123};f.save();
 const after=buildManifest({root:f.root,allowPartial:true}).cases[0];
 assert.equal(after.validation.authored,true,after.validation.errors.join('; '));
 assert.equal(after.publicSha256,before.publicSha256);assert.equal(after.responseContractSha256,before.responseContractSha256);assert.deepEqual(after.responseContractTurnHashes,before.responseContractTurnHashes);
 assert.notEqual(after.sourceHash,before.sourceHash);assert.notEqual(after.privateSha256,before.privateSha256);assert.doesNotMatch(JSON.stringify(after),/987654321/);
 f.write('independent-reference.json',{privateValue:123456789.987});
 const referenceChange=buildManifest({root:f.root,allowPartial:true}).cases[0];
 assert.equal(referenceChange.sourceHash,after.sourceHash);assert.equal(referenceChange.publicSha256,after.publicSha256);assert.equal(referenceChange.responseContractSha256,after.responseContractSha256);assert.notEqual(referenceChange.privateSha256,after.privateSha256);
});

test('ambiguous response projection is an invalid authored diagnostic and cannot be persisted by the CLI',t=>{
 const f=fixture(t);f.contract.turns.push({id:'t2',instruction:'报告同一状态的新结果。',state:1,expectation:'query',attachments:[],unresolvedFields:[],expectedQuestions:[]});f.save();
 const manifest=buildManifest({root:f.root,allowPartial:true}),entry=manifest.cases[0];
 assert.equal(manifest.validation.valid,false);assert.equal(manifest.summary.authored,0);assert.equal(entry.statuses.authorship,'invalid');assert.equal(entry.validation.authored,false);assert.equal(entry.responseContractSha256,null);
 assert.ok(entry.responseContractTurnHashes.some(turn=>turn.sha256===null));assert.ok(entry.validation.errors.some(error=>error.startsWith('Public response contract unavailable for turn ')));
 assert.equal(Object.hasOwn(entry,'responseContract'),false);
 const output=path.join(f.root,'invalid-response-manifest.json');
 const result=invoke(require('../scripts/build-research300-manifest.cjs').main,['--root',f.root,'--allow-partial','--output',output]);
 assert.equal(result.status,1);assert.equal(fs.existsSync(output),false);assert.match(result.stderr,/Refusing invalid authored manifest/);
});
