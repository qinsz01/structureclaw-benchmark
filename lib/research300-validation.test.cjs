'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {fixture,clone}=require('./research300-test-fixtures.cjs');
const {validateResearchCase,validateResearchCorpus,validateSourcePlan,validateSchema,validateReference,schemas}=require('./research300-validation.cjs');
const check=(f,stage='authored')=>validateResearchCase({root:f.root,caseDir:f.caseDir,planCase:f.planCase,stage});
const invalid=(f,pattern)=>{f.save();const r=check(f);assert.equal(r.valid,false,JSON.stringify(r));assert.match(r.errors.join('\n'),pattern);return r;};

function commercialConventionFixture(t) {
  const f=fixture(t,'STD-083');
  f.contract.analysisConvention={id:'commercial-linear-static-v2',bendingTheory:'Timoshenko',
    effectiveShearAreas:{localY:'5*A/6',localZ:'5*A/6'},publicAttachment:'analysis-conventions-v2.txt'};
  f.contract.attachments.push('analysis-conventions-v2.txt');
  f.contract.turns[0].attachments.push('analysis-conventions-v2.txt');
  f.contract.requiredOutputs.push({id:'figures',state:1,kind:'figure',description:'测试图形要求',quantityIds:[]});
  f.contract.requirementCoverage[0].targets.push('output:figures');
  f.write('analysis-conventions-v2.txt','测试分析输入：Timoshenko，Asy = Asz = 5*A/6。\n');
  f.save();
  return f;
}

test('commercial physics revision rejects unknown policies before reference readiness',t=>{
  const f=commercialConventionFixture(t);
  assert.deepEqual(check(f).errors,[]);
  for (const policy of [{},false,{...f.contract.analysisConvention,effectiveShearAreas:{localY:'A',localZ:'A'}}]) {
    f.contract.analysisConvention=policy;
    invalid(f,/analysisConvention/);
  }
});
test('commercial physics convention requires the named engine and public first-turn appendix',t=>{
  const f=commercialConventionFixture(t);
  f.contract.turns[0].attachments.pop();
  invalid(f,/analysisConvention.*first.turn/);
  f.contract.turns[0].attachments.push('analysis-conventions-v2.txt');
  f.contract.plannedEngine='OpenSees';
  invalid(f,/analysisConvention.*commercial/);
});
test('v2 reference cannot silently reuse an undeclared or Euler-Bernoulli diagnostic',t=>{
  const f=commercialConventionFixture(t),ref=f.addReference();
  assert.match(check(f,'reference-ready').errors.join('\n'),/analysisConvention/);
  ref.analysisConvention=clone(f.contract.analysisConvention);
  f.write('independent-reference.json',ref);
  assert.equal(check(f,'reference-ready').valid,true);
  ref.referenceKind='independent-elastic-matrix';
  ref.checks=[{state:1,selection:{kind:'case',id:'D'},theory:'Euler-Bernoulli'}];
  f.write('independent-reference.json',ref);
  assert.match(check(f,'reference-ready').errors.join('\n'),/Timoshenko/);
  ref.checks[0].theory='Timoshenko';
  f.write('independent-reference.json',ref);
  assert.equal(check(f,'reference-ready').valid,true);
});
test('commercial native qualification binds the reviewed candidate and survives pending input blind review',t=>{
  const f=commercialConventionFixture(t),a=f.addAcceptance();
  const sha=bytes=>require('node:crypto').createHash('sha256').update(bytes).digest('hex');
  const descriptor=name=>({path:name,sha256:sha(fs.readFileSync(path.join(f.caseDir,name)))});
  const ref=JSON.parse(fs.readFileSync(path.join(f.caseDir,'independent-reference.json')));
  Object.assign(ref,{analysisConvention:clone(f.contract.analysisConvention),referenceKind:'native-pkpm',sameEngineTruthStatus:'verified'});
  f.write('native-commercial/evidence/raw.txt','synthetic unreceipted raw evidence');
  const raw=descriptor('native-commercial/evidence/raw.txt');
  ref.nativeArtifacts={test:{raw}};
  f.write('native-commercial/candidate.json',{...clone(ref),id:f.contract.id,referenceKind:'native-pkpm-candidate',
    nativeArtifacts:{test:{raw:{...raw,path:'raw.txt'}}}});
  ref.candidateArtifact=descriptor('native-commercial/candidate.json');
  f.write('independent-reference.json',ref);
  a.independentReferenceSha256=descriptor('independent-reference.json').sha256;
  a.inputBlindReview={status:'pending'};f.write('acceptance.json',a);
  assert.equal(check(f).nativeVerified,false);
  const review={schemaVersion:1,reviewer:a.sameEngineTruth.reviewer,cases:[{
    id:f.contract.id,status:'qualified',sourceHash:a.sourceHash,candidateSha256:ref.candidateArtifact.sha256,reasons:[]}]};
  f.write('native-commercial/qualification.json',review);
  a.sameEngineTruth.evidence=descriptor('native-commercial/qualification.json');
  ref.independentReview=clone(a.sameEngineTruth.evidence);
  f.write('independent-reference.json',ref);
  a.independentReferenceSha256=descriptor('independent-reference.json').sha256;f.write('acceptance.json',a);
  const result=check(f);assert.equal(result.nativeVerified,true,JSON.stringify(result.acceptanceErrors));
  assert.equal(result.inputReviewed,false);assert.equal(result.accepted,false);
  const value=ref.states[0].quantities[0].value;
  ref.states[0].quantities[0].value=value+1;f.write('independent-reference.json',ref);
  a.independentReferenceSha256=descriptor('independent-reference.json').sha256;f.write('acceptance.json',a);
  assert.equal(check(f).nativeVerified,false,'Rehashing an edited active answer must not bypass its reviewed candidate');
  ref.states[0].quantities[0].value=value;f.write('independent-reference.json',ref);
  a.independentReferenceSha256=descriptor('independent-reference.json').sha256;f.write('acceptance.json',a);
  f.write(raw.path,'changed unreceipted native evidence');
  assert.equal(check(f).nativeVerified,false,'Every candidate artifact is bound even if no receipt repeats it');
  f.write(raw.path,'synthetic unreceipted raw evidence');
  f.write('native-commercial/candidate.json',{testOnly:true,changed:true});
  assert.equal(check(f).nativeVerified,false);
});

test('minimal complete authored case passes without reference/native evidence',t=>{const f=fixture(t),r=check(f);assert.deepEqual(r.errors,[]);assert.equal(r.authored,true);assert.equal(r.referenceReady,false);assert.equal(r.accepted,false);assert.equal(check(f,'reference-ready').valid,false);assert.equal(check(f,'accepted').valid,false);});
test('conditional inference requires an explicit policy, current numerical outputs and semantic review',t=>{
  const f=fixture(t),first=f.contract.turns[0];
  f.contract.turns.push({...clone(first),id:'t2',attachments:[]});
  Object.assign(first,{expectation:'clarify-or-analyze',clarificationPolicy:'Both endpoint distances give the same point.',unresolvedFields:['origin'],expectedQuestions:['Which origin?']});
  for(const o of f.contract.requiredOutputs)o.turnIds=['t1','t2'];
  f.contract.requiredOutputs.push({id:'inference',kind:'interaction',state:1,turnIds:['t1'],quantityIds:[],description:'Review the uniqueness of the inference or the clarification.'});
  f.contract.requirementCoverage[0].targets.push('output:inference');
  f.save();assert.equal(check(f).valid,true,JSON.stringify(check(f).errors));
  delete first.clarificationPolicy;invalid(f,/clarificationPolicy/);
  first.clarificationPolicy='Both endpoints coincide.';
  f.contract.requiredOutputs.pop();invalid(f,/turn-bound interaction/);
});
test('source plan validates all300 counts, IDs, languages, engines and requirement ranges',()=>{const original=require('../planning/benchmark-plan.json');assert.deepEqual(validateSourcePlan(original).errors,[]);for(const mutate of [p=>p.cases.pop(),p=>p.cases[0].id='STD-002',p=>p.cases[0].plannedEngine='YJK',p=>p.cases[0].language='英文',p=>p.cases[0].requirements[0].sourceRange=[0,999999]]){const p=clone(original);mutate(p);assert.equal(validateSourcePlan(p).valid,false);}});
test('current source projection preserves every approved task and only reconciles the registry digest',()=>{
 const current=require('../planning/benchmark-plan.json'),historical=clone(require('../planning/capability-coverage-300.json'));
 const crypto=require('node:crypto');
 const registry=fs.readFileSync(path.resolve(__dirname,'..',current.sources.capabilityRegistry.file));
 assert.equal(current.sources.capabilityRegistry.sha256,crypto.createHash('sha256').update(registry).digest('hex'));
 assert.notEqual(historical.sources.capabilityRegistry.sha256,current.sources.capabilityRegistry.sha256);
 historical.sources.capabilityRegistry.sha256=current.sources.capabilityRegistry.sha256;
 assert.deepEqual(current,historical);
});
test('authored identity and every original requirement string must be exact',t=>{const f=fixture(t);f.contract.plannedEngine='PKPM';invalid(f,/plannedEngine differs/);f.contract.plannedEngine='OpenSees';f.contract.sourcePlan['task.scenario']+=' ';invalid(f,/exact original/);});
test('coverage rejects omitted, invented, misattributed IDs and unresolved targets',t=>{const f=fixture(t),original=clone(f.contract.requirementCoverage);f.contract.requirementCoverage.pop();invalid(f,/Missing coverage/);f.contract.requirementCoverage=clone(original);f.contract.requirementCoverage[0].requirementIds.push(99999);invalid(f,/does not match original/);f.contract.requirementCoverage=clone(original);f.contract.requirementCoverage[0].sourceField='task.scenario';invalid(f,/does not match original/);f.contract.requirementCoverage=clone(original);f.contract.requirementCoverage[0].targets=['attachment:model-state-1.json'];invalid(f,/Unresolved coverage target/);});
test('outputs cannot be omitted, empty, unbound, or silently converted into a figure',t=>{const f=fixture(t);f.contract.requiredOutputs[0].quantityIds=[];invalid(f,/requires state and quantityIds/);f.contract.requiredOutputs[0].quantityIds=['does-not-exist'];invalid(f,/nonexistent quantity/);f.contract.requiredOutputs=[];invalid(f,/requires at least|Unresolved coverage/);});
test('source figure requirements need explicit figure outputs',t=>{const f=fixture(t);f.planCase=clone(f.planCase);f.planCase.sourceRequirements['task.expectedOutput']+=' 绘制弯矩图。';f.contract.sourcePlan=clone(f.planCase.sourceRequirements);invalid(f,/figure output/);});
test('reference requests reject authored values and duplicate quantities within selection',t=>{const f=fixture(t);f.requests.states[0].quantities[0].value=60;invalid(f,/unexpected property value/);delete f.requests.states[0].quantities[0].value;f.requests.states[0].quantities.push(clone(f.requests.states[0].quantities[0]));invalid(f,/duplicate quantity/);});
test('same-name cases and combinations are distinct; unknown selections do not pass',t=>{const f=fixture(t),q=clone(f.requests.states[0].quantities[0]);q.id='combination:D:left';q.selection={kind:'combination',id:'D'};f.requests.states[0].quantities.push(q);f.save();assert.equal(check(f).valid,true);q.selection.id='missing';invalid(f,/selection does not exist/);});
test('component units, member station and load-jump side are enforced',t=>{const f=fixture(t);f.requests.states[0].quantities[0].unit='m';invalid(f,/component\/unit mismatch/);f.requests.states[0].quantities[0].unit='kN';const q=f.requests.states[0].quantities[3];q.location.positionM=3.001;invalid(f,/outside member/);q.location.positionM=3;delete q.location.side;invalid(f,/schema alternatives/);});
test('node observations must exist and be connected; released reactions remain valid zero checks',t=>{const f=fixture(t);f.requests.states[0].quantities[0].location.id='m';f.save();assert.equal(check(f).valid,true);f.requests.states[0].quantities[0].location.id='a';f.model.elements=[];invalid(f,/unconnected|explicit elements/);});
test('nondefault tolerances require a frozen engineering decision',t=>{const f=fixture(t),q=f.requests.states[0].quantities[0];q.tolerance.relative=0.1;invalid(f,/frozen justification/);q.toleranceJustification='Synthetic test decision made before any candidate run';f.save();assert.equal(check(f).valid,true);q.tolerance.relative=-1;invalid(f,/must be >=/);});
test('derived quantities reject missing or ambiguous operands, cycles and wrong units',t=>{const f=fixture(t),s=f.requests.states[0];s.derived=[{id:'delta',operation:'difference',operands:['D:left','missing'],unit:'kN',description:'difference'}];invalid(f,/missing or ambiguous/);s.derived[0].operands=['D:left','D:right'];s.derived[0].unit='m';invalid(f,/unit mismatch/);s.derived[0].unit='kN';s.derived[0].operands=['delta','D:left'];invalid(f,/cycle/);});
test('later clarification is allowed after earlier analysis and does not reuse its state',t=>{const f=fixture(t);f.contract.turns.push({id:'t2',instruction:'请明确新增荷载。',state:null,expectation:'clarify',attachments:[],unresolvedFields:['new load'],expectedQuestions:['新增荷载是多少？']});f.save();assert.equal(check(f).valid,true);f.contract.turns[1].state=1;invalid(f,/null state/);});
test('query must reuse analyzed state; actual edits cannot claim query reuse',t=>{const f=fixture(t);f.contract.turns[0].expectation='query';invalid(f,/earlier analyzed/);f.contract.turns[0].expectation='analyze';f.contract.turns.push({...clone(f.contract.turns[0]),id:'t2',attachments:[],expectation:'query',changedFields:['/load_cases/0/loads/0/wz']});invalid(f,/actual edit/);});
test('INT original turn counts are enforced',t=>{const f=fixture(t,'INT-001');invalid(f,/Turn count differs/);});
test('reference readiness checks selection, position, signs metadata and tolerance against frozen requests',t=>{const f=fixture(t),ref=f.addReference();assert.equal(check(f,'reference-ready').valid,true);ref.states[0].quantities[0].selection.kind='combination';f.write('independent-reference.json',ref);assert.match(check(f,'reference-ready').errors.join('\n'),/Missing finite reference/);});
test('synthetic acceptance fixture requires hashes and independently reviewed matching native evidence',t=>{const f=fixture(t);f.addAcceptance();const r=check(f,'accepted');assert.equal(r.valid,true,JSON.stringify(r.errors));f.write('native-results.csv','changed raw bytes\n');const changed=check(f,'accepted');assert.equal(changed.valid,false);assert.match(changed.errors.join('\n'),/hash mismatch/);assert.equal(check(f).authored,true);});
test('wrong-engine receipt, stale model and diagnostic commercial truth never become accepted',t=>{const f=fixture(t);const a=f.addAcceptance();a.sameEngineTruth.engine='YJK';f.write('acceptance.json',a);assert.match(check(f,'accepted').errors.join('\n'),/Same-engine/);f.addAcceptance();f.model.nodes[1].x=2.5;f.save();assert.match(check(f,'accepted').errors.join('\n'),/stale|does not bind/);});
test('partial authored counts are separate from all300 completeness and native acceptance',t=>{const f=fixture(t),r=validateResearchCorpus({root:f.root,allowPartial:true});assert.equal(r.valid,true,JSON.stringify(r.errors));assert.deepEqual(r.summary,{planned:300,discovered:1,authored:1,referenceReady:0,accepted:0,inputReviewed:0,nativeVerified:0,agentNotRun:1});assert.equal(validateResearchCorpus({root:f.root}).valid,false);});
test('changed source plan bytes fail even when case identity was changed with them',t=>{const f=fixture(t),file=path.join(f.root,'planning/benchmark-plan.json');fs.appendFileSync(file,'\n');assert.match(validateResearchCorpus({root:f.root,allowPartial:true}).errors.join('\n'),/hash differs/);});
test('schema validation rejects unknown keywords rather than silently weakening constraints',()=>{assert.throws(()=>validateSchema({}, {unsupported:true}),/Unsupported schema keyword/);assert.equal(validateSchema({schemaVersion:1,states:[]},schemas['reference-requests']).length>0,true);});

test('malformed structural documents return diagnostics rather than crashing',t=>{const f=fixture(t);f.requests.states=[null];f.save();assert.doesNotThrow(()=>check(f));assert.equal(check(f).valid,false);});
test('missing essential fields cannot leak through a first-turn public JSON attachment',t=>{const f=fixture(t);f.contract.turns=[{...f.contract.turns[0],state:null,expectation:'clarify',unresolvedFields:['/nodes/1/x'],expectedQuestions:['跨度是多少？']},{...clone(f.contract.turns[0]),id:'t2',attachments:[]}];f.write('properties.json',{nodes:[{id:'a',x:0},{id:'m',x:3}]});f.save();const r=check(f);assert.equal(r.valid,false);assert.match(r.errors.join('\n'),/unresolved.*exposed|exposes.*unresolved/);});
test('reference-ready cannot survive changed model bytes with old reference hashes',t=>{const f=fixture(t);f.addReference();assert.equal(check(f,'reference-ready').valid,true);fs.appendFileSync(path.join(f.caseDir,'model-state-1.json'),'\n');assert.match(check(f,'reference-ready').errors.join('\n'),/inputHashes.*stale/);});
test('per-turn output associations reject another or unknown state',t=>{const f=fixture(t);f.contract.requiredOutputs[0].turnIds=['t1'];f.save();assert.equal(check(f).valid,true);f.contract.requiredOutputs[0].turnIds=['t2'];invalid(f,/turnIds/);});
test('all schema-valid coverage target spellings resolve to actual records',t=>{const f=fixture(t);f.contract.acceptanceGates=[{id:'physical-source-review',status:'pending'}];for(const row of f.contract.requirementCoverage)row.targets=['turns:t1','properties.json','attachments:geometry.csv','requiredOutputs','reference-requests.json','gate:physical-source-review'];f.save();assert.equal(check(f).valid,true);f.contract.requirementCoverage[0].targets=['model-state-1.json'];invalid(f,/Unresolved/);});
test('MM input cannot bypass image geometry through public coordinate JSON',t=>{const f=fixture(t);f.planCase=clone(f.planCase);f.planCase.family='multimodal_reverse_engineering';f.contract.family=f.planCase.family;f.write('properties.json',{nodes:[{id:'a',x:0,y:0,z:0}]});f.save();assert.match(check(f).errors.join('\n'),/coordinate\/connection JSON bypass/);});
test('max_abs derived truth retains signed governing value and selection',t=>{const f=fixture(t);f.requests.states[0].derived=[{id:'reaction-envelope',operation:'max_abs',operands:['D:left','D:right'],unit:'kN',description:'Signed envelope'}];f.contract.requiredOutputs.push({id:'envelope',description:'Signed envelope',state:1,quantityIds:['reaction-envelope'],kind:'derived'});f.contract.requirementCoverage[0].targets.push('output:envelope');f.save();const ref=f.addReference();ref.states[0].quantities[0].value=-7;ref.states[0].quantities[1].value=3;ref.states[0].derived=[{...clone(f.requests.states[0].derived[0]),value:-7,governingOperand:'D:left',governingSelection:{kind:'case',id:'D'}}];f.write('independent-reference.json',ref);assert.equal(check(f,'reference-ready').valid,true);ref.states[0].derived[0].value=7;f.write('independent-reference.json',ref);assert.match(check(f,'reference-ready').errors.join('\n'),/arithmetic\/signed/);});
test('nested source plan preserves sourceRequirements and original numbered clauses exactly',t=>{const f=fixture(t);f.contract.sourcePlan={sourceRequirements:clone(f.planCase.sourceRequirements),requirements:clone(f.planCase.requirements),task:{original:'archived separately'}};f.save();assert.equal(check(f).valid,true);f.contract.sourcePlan.requirements[0].id=999;invalid(f,/original IDs/);});
test('declared changed/preserved pointers are checked against actual model states',t=>{const f=fixture(t);f.contract.turns.push({...clone(f.contract.turns[0]),id:'t2',attachments:[],changedFields:['/nodes/1/x']});invalid(f,/did not change/);delete f.contract.turns[1].changedFields;f.contract.turns[1].preservedFields=['/missing'];invalid(f,/missing or changed/);});
test('signed sum derived request preserves reaction totals in declared units',t=>{const f=fixture(t);f.requests.states[0].derived=[{id:'total',operation:'sum',operands:['D:left','D:right'],unit:'kN',description:'Signed reaction total'}];f.contract.requiredOutputs.push({id:'total-output',description:'Total',state:1,quantityIds:['total'],kind:'derived'});f.contract.requirementCoverage[0].targets.push('output:total-output');f.save();const ref=f.addReference();ref.states[0].quantities[0].value=-7;ref.states[0].quantities[1].value=3;ref.states[0].derived=[{...clone(f.requests.states[0].derived[0]),value:-4}];f.write('independent-reference.json',ref);assert.equal(check(f,'reference-ready').valid,true);ref.states[0].derived[0].value=10;f.write('independent-reference.json',ref);assert.match(check(f,'reference-ready').errors.join('\n'),/arithmetic\/signed/);});
test('reference-ready binds public bytes through shared sourceHash as well as hidden model hashes',t=>{const f=fixture(t);f.addReference();assert.equal(check(f,'reference-ready').valid,true);fs.appendFileSync(path.join(f.caseDir,'geometry.csv'),'b,7,0,0\n');assert.match(check(f,'reference-ready').errors.join('\n'),/sourceHash.*stale/);});

test('nonblocking output ambiguity permits current analysis and subsequent query',t=>{
  const f=fixture(t),first=f.contract.turns[0];
  Object.assign(first,{clarificationBlocksAnalysis:false,unresolvedFields:['/requestedOutputs/maximumAxialForce/scope'],expectedQuestions:['Which members should the maximum include?'],requiredOutputIds:['reactions','midpoint']});
  f.contract.turns.push({...clone(first),id:'t2',expectation:'query',attachments:[],unresolvedFields:[],expectedQuestions:[]});
  delete f.contract.turns[1].clarificationBlocksAnalysis;
  f.save();assert.deepEqual(check(f).errors,[]);
  delete first.clarificationBlocksAnalysis;
  invalid(f,/requires resolved state and no pending questions/);
});

test('nonblocking clarification exemption fails closed for physical omissions and invalid state or expectation',t=>{
  const f=fixture(t),first=f.contract.turns[0];
  Object.assign(first,{clarificationBlocksAnalysis:false,unresolvedFields:['/requestedOutputs/maximumAxialForce/scope'],expectedQuestions:['Which members should the maximum include?']});
  const approved=clone(first);
  const mutations=[
    turn=>turn.unresolvedFields=['/nodes/1/x'],
    turn=>turn.unresolvedFields=['/requestedOutputs/maximumAxialForce/scope','/load_cases/D/loads'],
    turn=>turn.unresolvedFields=['/requestedOutputs'],
    turn=>turn.unresolvedFields=['/requestedOutputs/'],
    turn=>turn.unresolvedFields=['/requestedOutputs/~2invalid/scope'],
    turn=>turn.unresolvedFields=[],
    turn=>turn.expectedQuestions=[],
    turn=>turn.state=null,
    turn=>turn.state=2,
    turn=>turn.expectation='clarify',
    turn=>turn.expectation='query',
    turn=>turn.clarificationBlocksAnalysis='false',
  ];
  for(const mutate of mutations){
    const turn=clone(approved);mutate(turn);f.contract.turns[0]=turn;
    invalid(f,/clarificationBlocksAnalysis|schema alternatives|state does not exist/);
  }
  for(const mutate of mutations.filter((_,i)=>i!==8)){
    const turn=clone(approved);mutate(turn);
    assert.notDeepEqual(validateSchema(turn,schemas.contract.properties.turns.items),[],JSON.stringify(turn));
  }
});

test('turn output selectors reject unknown IDs, private operands, wrong-state and future-only outputs',t=>{
  const f=fixture(t),turn=f.contract.turns[0];
  Object.assign(turn,{requiredOutputIds:['reactions'],requiredQuantityIds:['D:left']});
  f.save();assert.deepEqual(check(f).errors,[]);
  turn.requiredOutputIds=['missing'];invalid(f,/requiredOutputIds/);
  turn.requiredOutputIds=['reactions'];turn.requiredQuantityIds=['D:mid-u'];invalid(f,/requiredQuantityIds/);
  turn.requiredQuantityIds=['missing'];invalid(f,/requiredQuantityIds/);
  turn.requiredQuantityIds=['D:left'];f.contract.turns.push({...clone(turn),id:'t2',expectation:'query',attachments:[]});
  f.contract.requiredOutputs[0].turnIds=['t2'];invalid(f,/requiredOutputIds.*turn/);
  delete f.contract.requiredOutputs[0].turnIds;f.contract.requiredOutputs[0].state=2;invalid(f,/requiredOutputIds.*state/);
});

test('turn output selector arrays have explicit schema and empty lists never expand scope',t=>{
  const f=fixture(t),turn=f.contract.turns[0];
  for(const field of ['requiredOutputIds','requiredQuantityIds']){
    for(const value of ['reactions',[1],[''],['reactions','reactions']]){
      turn[field]=value;invalid(f,new RegExp(field));
    }
    delete turn[field];
  }
  turn.requiredOutputIds=[];turn.requiredQuantityIds=['D:left'];invalid(f,/requiredQuantityIds/);
  turn.requiredQuantityIds=[];f.save();assert.deepEqual(check(f).errors,[]);
});

test('outputUnits validates current output keys, supported units and physical dimensions',t=>{
  const f=fixture(t),turn=f.contract.turns[0];
  Object.assign(turn,{requiredOutputIds:['midpoint'],requiredQuantityIds:['D:mid-u','D:mid-M'],outputUnits:{uz:'mm','D:mid-M':'N*m'}});
  f.save();assert.deepEqual(check(f).errors,[]);
  for(const value of [null,[],{uz:1},{uz:'feet'},{uz:'kN'},{Fx:'kN'},{'D:left':'N'},{'not-current':'m'}]){
    turn.outputUnits=value;invalid(f,/outputUnits/);
  }
});

test('shared-state turns require explicit current output scope before authored acceptance',t=>{
  const f=fixture(t);
  f.contract.turns.push({...clone(f.contract.turns[0]),id:'t2',expectation:'query',attachments:[]});
  invalid(f,/turn 1: Ambiguous turn output scope/);
  f.contract.requiredOutputs[0].turnIds=['t1'];
  f.contract.requiredOutputs[1].turnIds=['t2'];
  f.save();assert.deepEqual(check(f).errors,[]);
  f.contract.turns[0].requiredQuantityIds=['D:mid-u'];
  invalid(f,/turn 1: requiredQuantityIds/);
});

test('closed schema objects reject inherited constructor, __proto__ and toString property names',()=>{
  const schema={type:'object',properties:{allowed:{type:'string'}},additionalProperties:false};
  for(const key of ['constructor','__proto__','toString']){
    const input=JSON.parse(`{"${key}":{"value":"unlisted field"}}`);
    assert.match(validateSchema(input,schema).join('\n'),new RegExp(`unexpected property ${key}`));
    const explicit={type:'object',properties:JSON.parse(`{"${key}":{"type":"string"}}`),additionalProperties:false};
    assert.match(validateSchema(input,explicit).join('\n'),/must be string/);
    assert.deepEqual(validateSchema(JSON.parse(`{"${key}":"explicitly declared"}`),explicit),[]);
  }
});

test('all twelve inherited-key attacks fail inside real quantity, selection, location and tolerance schemas',t=>{
  const f=fixture(t),original=clone(f.requests.states[0].quantities[0]);
  for(const field of [null,'selection','location','tolerance'])for(const key of ['constructor','__proto__','toString']){
    const quantity=clone(original),target=field?quantity[field]:quantity;
    Object.defineProperty(target,key,{value:{private:'unlisted field'},enumerable:true});
    f.requests.states[0].quantities[0]=quantity;
    invalid(f,/unexpected property|schema alternatives/);
  }
  f.requests.states[0].quantities[0]=original;f.save();assert.deepEqual(check(f).errors,[]);
});

function arithmeticFixture(values,definition,extra={}){
  const quantities=values.map((value,i)=>({id:['a','b','c'][i],selection:{kind:'case',id:'D'},location:{kind:'node',id:`n${i}`},component:'Fz',unit:'kN',tolerance:{absolute:1e-8,relative:1e-6},value}));
  const request={id:'extreme',operation:'max_abs',operands:quantities.map(q=>q.id),unit:'kN',description:'Signed extreme',...definition};
  const requests={schemaVersion:1,states:[{state:1,quantities:quantities.map(({value,...q})=>clone(q)),derived:[request]}]};
  const reference={toleranceFrozenBeforeCandidate:true,states:[{state:1,quantities,derived:[{...clone(request),value:values[0],governingOperand:'a',governingSelection:{kind:'case',id:'D'},...extra}]}]};
  return {request,requests,reference,actual:reference.states[0].derived[0],check(){const errors=[];validateReference(reference,requests,errors);return errors;}};
}

test('canonical extrema choose first tolerance co-governor and preserve opposite signs for every report tie policy',()=>{
  for(const tiePolicy of [undefined,'first','any']){
    const f=arithmeticFixture([-19.2,19.20000000000002],tiePolicy?{tiePolicy}:{},{coGoverningOperands:['a','b'],governingLeafOperands:['a'],governingSelections:[{kind:'case',id:'D'}]});
    assert.deepEqual(f.check(),[],String(tiePolicy));
    f.actual.value=19.20000000000002;f.actual.governingOperand='b';
    assert.match(f.check().join('\n'),/arithmetic\/signed|governing operand/);
  }
});

test('extrema co-governors are measured from best score after unit conversion, including signed max and min',()=>{
  const converted=arithmeticFixture([-19.2,19.20000000000002],{unit:'N'},{value:-19200,coGoverningOperands:['a','b']});
  assert.deepEqual(converted.check(),[]);
  for(const [operation,values] of [['max',[10,10.000005]],['min',[-10,-10.000005]]]){
    const f=arithmeticFixture(values,{operation},{coGoverningOperands:['a','b']});
    assert.deepEqual(f.check(),[],operation);
  }
  const outside=arithmeticFixture([-19.1999,19.2],{},{coGoverningOperands:['b']});
  assert.match(outside.check().join('\n'),/arithmetic\/signed|governing operand/);
  Object.assign(outside.actual,{value:19.2,governingOperand:'b'});
  assert.deepEqual(outside.check(),[]);
  const nontransitive=arithmeticFixture([9.999982,9.999991,10],{},{value:9.999991,governingOperand:'b',coGoverningOperands:['b','c']});
  assert.deepEqual(nontransitive.check(),[]);
});

test('explicit frozen derived tolerance controls ties and ordered recorded co-set cannot be forged',()=>{
  const f=arithmeticFixture([9.9995,10],{tolerance:{absolute:.001,relative:0}},{coGoverningOperands:['a','b']});
  assert.deepEqual(f.check(),[]);
  for(const coSet of [[],['b','a'],['a'],['a','a','b'],['a','b','c'],'a,b',null]){
    f.actual.coGoverningOperands=coSet;
    assert.match(f.check().join('\n'),/coGoverningOperands/);
  }
  delete f.actual.coGoverningOperands;assert.deepEqual(f.check(),[]);
  f.request.tolerance={absolute:1e-8,relative:1e-6};
  assert.match(f.check().join('\n'),/governing operand|tolerance.*frozen/);
});

test('derived leaf identities and governing selections must retain canonical first provenance',()=>{
  const f=arithmeticFixture([-19.2,19.20000000000002],{},{coGoverningOperands:['a','b'],governingLeafOperands:['a'],governingSelections:[{kind:'case',id:'D'}]});
  assert.deepEqual(f.check(),[]);
  f.actual.governingLeafOperands=['b'];assert.match(f.check().join('\n'),/governingLeafOperands/);
  f.actual.governingLeafOperands=['a'];f.actual.governingSelections=[{kind:'combination',id:'D'}];
  assert.match(f.check().join('\n'),/governingSelections/);
});

test('signed derived sum retains small residual after severe cancellation',()=>{
  const f=arithmeticFixture([1e16,1,-1e16],{operation:'sum'},{value:1,governingOperand:null,governingSelection:null});
  assert.deepEqual(f.check(),[]);
  f.actual.value=0;assert.match(f.check().join('\n'),/arithmetic\/signed/);
});

test('derived request tolerance and tie policy retain frozen authoring requirements',t=>{
  const f=fixture(t),record={id:'env',operation:'max_abs',operands:['D:left','D:right'],unit:'kN',description:'Signed reaction envelope'};
  f.requests.states[0].derived=[record];f.save();assert.deepEqual(check(f).errors,[]);
  record.tolerance={absolute:1e-8,relative:1e-6};record.tiePolicy='any';f.save();assert.deepEqual(check(f).errors,[]);
  record.tolerance.absolute=.01;invalid(f,/frozen justification/);
  record.toleranceJustification='Frozen synthetic engineering decision';f.save();assert.deepEqual(check(f).errors,[]);
  record.tolerance={absolute:0,relative:0};invalid(f,/identically zero/);
  record.tolerance={absolute:-1,relative:0};invalid(f,/must be >=/);
  record.tolerance={absolute:1e-8,relative:1e-6};record.operation='sum';invalid(f,/tiePolicy.*extrema|schema alternatives/);
  record.operation='max_abs';record.tiePolicy='largest';invalid(f,/tiePolicy/);
});

test('derived calculation order rejects forward dependencies as well as cycles',t=>{
  const f=fixture(t);
  f.requests.states[0].derived=[{id:'outer',operation:'max_abs',operands:['inner','D:left'],unit:'kN',description:'Outer'},{id:'inner',operation:'sum',operands:['D:left','D:right'],unit:'kN',description:'Inner'}];
  invalid(f,/forward.*operand|earlier derived/);
  f.requests.states[0].derived.reverse();f.save();assert.deepEqual(check(f).errors,[]);
});
