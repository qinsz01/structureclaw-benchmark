'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {spawnSync}=require('node:child_process');
const {fixture,publishInputs}=require('../../../lib/research300-test-fixtures.cjs');
const {caseContext}=require('../../../lib/result-import.cjs');
test('trial preparation pins the selected edition and rejects stale packets before dispatch',t=>{
  const f=fixture(t);publishInputs(f);
  const work=path.join(f.root,'trial'),base=path.join(f.root,'trial-public-packets');
  const run=()=>spawnSync(process.execPath,[path.join(__dirname,'prepare.cjs'),work,base,f.root],{encoding:'utf8'});
  const first=run();assert.equal(first.status,0,first.stderr);
  const binding=JSON.parse(fs.readFileSync(path.join(work,'corpus-binding.json')));
  assert.equal(binding.root,f.root);assert.equal(binding.contexts.length,1);
  assert.deepEqual(JSON.parse(fs.readFileSync(path.join(base,'STD-001/t1/capture-context.json'))),caseContext('STD-001',f.root).context);
  assert.equal(run().status,0,'unchanged prepared packets are resumable');
  const contextPath=path.join(base,'STD-001/t1/capture-context.json');
  const staleContext=JSON.parse(fs.readFileSync(contextPath));staleContext.sourceHash='0'.repeat(64);
  fs.writeFileSync(contextPath,JSON.stringify(staleContext));
  const stale=run();assert.notEqual(stale.status,0);assert.match(stale.stderr,/different corpus edition/i);
  assert.deepEqual(JSON.parse(fs.readFileSync(path.join(work,'corpus-binding.json'))),binding,'failure must retain the original trial identity');
});
test('repair-trial case selection rejects unknown or duplicate IDs before writing dispatch evidence',t=>{
  const f=fixture(t);publishInputs(f);
  const work=path.join(f.root,'trial'),base=path.join(f.root,'packets');
  const run=cases=>spawnSync(process.execPath,[path.join(__dirname,'prepare.cjs'),work,base,f.root,'--cases',cases],{encoding:'utf8'});
  for(const cases of ['STD-002','STD-001,STD-001','']){
    assert.notEqual(run(cases).status,0);assert.equal(fs.existsSync(path.join(work,'plan.json')),false);
  }
  const valid=run('STD-001');assert.equal(valid.status,0,valid.stderr);
  assert.deepEqual(JSON.parse(fs.readFileSync(path.join(work,'plan.json'))).map(c=>c.caseId),['STD-001']);
});
