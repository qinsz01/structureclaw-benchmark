'use strict';
const assert=require('node:assert/strict'),test=require('node:test'),fs=require('node:fs'),os=require('node:os'),path=require('node:path'),crypto=require('node:crypto');
const {grade}=require('./grade_candidate.cjs');

function fixture(t,binding){
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'v3-candidate-scope-'));t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
 const edition=path.join(root,'edition'),work=path.join(root,'work');fs.mkdirSync(edition);fs.mkdirSync(work);
 const bytes=JSON.stringify({files:[],cases:[{id:'heldout',split:'test',turns:[{id:'t1'}]}]});
 fs.writeFileSync(path.join(edition,'manifest.json'),bytes);
 fs.writeFileSync(path.join(work,'candidate-binding.json'),JSON.stringify({manifestSha256:crypto.createHash('sha256').update(bytes).digest('hex'),model:'test-fixture',...binding}));
 return {edition,work};
}

test('development calibration cannot consume a held-out case',t=>{
 const {edition,work}=fixture(t,{cases:['heldout']});assert.throws(()=>grade(edition,work),/Calibration selection differs/);
});
test('explicit full-suite validation records missing captures as failures',t=>{
 const {edition,work}=fixture(t,{cases:['heldout'],fullSuite:true});const r=grade(edition,work);
 assert.equal(r.developmentOnly,false);assert.equal(r.formalComparisonScore,false);assert.equal(r.fullEditionCoverage,true);
 assert.equal(r.turns,1);assert.equal(r.passed,0);assert.equal(r.rows[0].status,'uncaptured');
});
test('repeating a case cannot inflate full-suite coverage',t=>{
 const {edition,work}=fixture(t,{cases:['heldout','heldout'],fullSuite:true});assert.throws(()=>grade(edition,work),/selection repeats/);
});
