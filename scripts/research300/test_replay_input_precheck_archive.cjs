'use strict';
const {test}=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),crypto=require('node:crypto');
const {main}=require('./replay_input_precheck_archive.cjs');
test('retained input routing runs the frozen replay and restores fs on success and failure',()=>{
  const temp=fs.mkdtempSync(path.join(os.tmpdir(),'legacy-inputs-')),original=fs.readFileSync;
  try{
    const review=path.join(temp,'docs/implementation/reviews/backend-and-codex-precheck-20261026');fs.mkdirSync(review,{recursive:true});
    const zip=Buffer.from('empty archive routing fixture');
    fs.writeFileSync(path.join(review,'codex-blind-evidence.zip.bin'),zip);
    fs.writeFileSync(path.join(review,'codex-archive-manifest.json'),JSON.stringify({archiveSha256:crypto.createHash('sha256').update(zip).digest('hex'),files:[]}));
    fs.writeFileSync(path.join(review,'blind-executions.json'),'[]');
    const result=main(['--archive-root',temp,'--evidence',temp]);
    assert.equal(result.modelCalls,0);assert.equal(result.acceptanceWritten,false);assert.equal(result.turns.length,0);
    assert.equal(fs.readFileSync,original);
    fs.unlinkSync(path.join(review,'blind-executions.json'));
    assert.throws(()=>main(['--archive-root',temp,'--evidence',temp]),/ENOENT/);
    assert.equal(fs.readFileSync,original);
    assert.throws(()=>main(['--archive-root',temp,'--evidence',temp,'--out',path.join(temp,'new.json')]),/read-only archive/);
    assert.equal(fs.existsSync(path.join(temp,'new.json')),false);
    const alias=temp+'-link';fs.symlinkSync(temp,alias,'dir');
    try{assert.throws(()=>main(['--archive-root',temp,'--evidence',temp,'--out',path.join(alias,'new.json')]),/read-only archive/);}
    finally{fs.unlinkSync(alias);}
  }finally{fs.rmSync(temp,{recursive:true,force:true});}
});
