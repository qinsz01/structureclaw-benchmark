'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {sshTransportFault,adjudicate}=require('./review_native_environment_v32.cjs');
const fault={ok:false,engine:'YJK',error:'commercial failed: Traceback (most recent call last):\n File "/fixed/codex_trial/remote.py", line 17, in run\nRuntimeError: Numeric file transfer failed: host: Permission denied (publickey).\n'};
const row=(turnId,outcome='candidate_failure')=>({caseId:'V3-INT-014',turnId,outcome,passed:outcome==='passed',failures:[{name:'original failure'}]});
const info=(kind='static',failed=true)=>({kind,attempts:failed?[{evidenceId:'a'.repeat(32),receipt:fault,descriptor:{path:'test-only',sha256:'b'.repeat(64)}}]:[]});
test('collector SSH loss is infrastructure, but a candidate claim or model error is not',()=>{
 assert.equal(sshTransportFault(fault),true);
 assert.equal(sshTransportFault({ok:false,engine:'YJK',error:'Permission denied (publickey).'}),false);
 assert.equal(sshTransportFault({...fault,engine:'OpenSees'}),false);
 assert.equal(sshTransportFault({...fault,ok:true}),false);
 assert.equal(sshTransportFault({...fault,error:'commercial failed: invalid section property'}),false);
});
test('failed physical evidence stays failed while capability attribution becomes blocked',()=>{
 const original=row('t1'),r=adjudicate([original],new Map([['V3-INT-014/t1',info()]]));
 assert.equal(r.rows[0].outcome,'blocked_configuration');assert.equal(r.rows[0].passed,null);
 assert.deepEqual(r.rows[0].failures,original.failures);assert.equal(original.outcome,'candidate_failure');
});
test('a successful delivery that recovered remains a pass',()=>{
 const r=adjudicate([row('t1','passed')],new Map([['V3-INT-014/t1',info()]]));
 assert.equal(r.rows[0].outcome,'passed');assert.equal(r.decisions.length,0);
});
test('query depending on missing native state is blocked; an unrelated later task is not automatically excused',()=>{
 const rows=[row('t1'),row('t2'),row('t3')],turns=new Map([['V3-INT-014/t1',info()],['V3-INT-014/t2',info('query',false)],['V3-INT-014/t3',info('static',false)]]);
 assert.deepEqual(adjudicate(rows,turns).rows.map(r=>r.outcome),['blocked_configuration','blocked_configuration','candidate_failure']);
});
test('fresh successful evidence clears the blocked-state dependency',()=>{
 const rows=[row('t1'),row('t2','passed'),row('t3')],turns=new Map([['V3-INT-014/t1',info()],['V3-INT-014/t2',info('static',false)],['V3-INT-014/t3',info('query',false)]]);
 assert.deepEqual(adjudicate(rows,turns).rows.map(r=>r.outcome),['blocked_configuration','passed','candidate_failure']);
});
test('incomplete capture is not silently reclassified as an observed model failure or pass',()=>{
 const r=adjudicate([row('t1','ungradable_evidence')],new Map([['V3-INT-014/t1',info()]]));
 assert.equal(r.rows[0].outcome,'ungradable_evidence');assert.equal(r.decisions.length,0);
});
