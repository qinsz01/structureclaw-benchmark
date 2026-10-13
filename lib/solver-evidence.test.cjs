const test=require('node:test');
const assert=require('node:assert/strict');
const {spawnSync}=require('node:child_process');
const path=require('node:path');
const {randomUUID}=require('node:crypto');
const {verifyExecutionEvidence,modelFingerprint}=require('./analysis-evidence.cjs');
const python=process.env.SCLAW_TEST_PYTHON;
test('actual OpenSees output satisfies the benchmark evidence gate after host run binding',
  {skip:!python?'Set SCLAW_TEST_PYTHON to an OpenSees-enabled Python runtime':false},()=>{
    const root=path.resolve(__dirname,'../../..');
    const model=structuredClone(require('../fixtures/ground-truth-models.json').find(x=>x.id==='beam-simple-6m').model);
    model.schema_version='2.1.0';model.analysis_control={self_weight:false,rigid_floor:false};
    const script=`import sys,json\nfrom pathlib import Path\nr=Path(sys.argv[1])\nfor p in [r/'backend/src/skill-shared/python',r/'backend/src/agent-skills/analysis/runtime',r/'backend/src/agent-skills/analysis/opensees-static']:sys.path.insert(0,str(p))\nfrom structure_protocol.structure_model_v2 import StructureModelV2\nfrom runtime import run_analysis\nm=StructureModelV2.model_validate(json.load(sys.stdin))\nv=run_analysis(m,{'loadCombinationId':'ULS'})\nprint(json.dumps({'model':m.model_dump(mode='json',exclude_unset=True),'result':v},allow_nan=False))`;
    const run=spawnSync(python,['-c',script,root],{input:JSON.stringify(model),encoding:'utf8',timeout:30000});
    assert.equal(run.status,0,run.stderr);
    const payload=JSON.parse(run.stdout),selection={kind:'combination',id:'ULS'};
    const meta={...payload.result.meta,runId:randomUUID(),modelHash:modelFingerprint(payload.model)};
    const state={model:payload.model,analysisResult:{results:{'combination:ULS':{selection,meta,data:payload.result}}}};
    const proof=verifyExecutionEvidence(state,selection);assert.equal(proof.pass,true,proof.failures.join(';'));
    assert.equal(payload.result.meta.execution.executed,true);
    assert.match(payload.result.execution.artifacts.solverResponseSha256,/^[a-f0-9]{64}$/);
    assert.match(payload.result.execution.artifacts.normalizedInputSha256,/^[a-f0-9]{64}$/);
    assert.equal(payload.result.execution.effectiveSettings.self_weight.value,false);
    assert.ok(Math.abs(payload.result.reactions['1'].fz-60)<1e-8);
    state.model.load_cases[0].loads[0].wz=-22;
    assert.equal(verifyExecutionEvidence(state,selection).pass,false);
  });
