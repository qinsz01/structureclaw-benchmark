'use strict';
const fs = require('node:fs'), os = require('node:os'), path = require('node:path');
const { sha256 } = require('./corpus-provider.cjs');
const { authoredFiles, sourceHash } = require('./research300-validation.cjs');
const repo = path.resolve(__dirname, '..');
const plan = require('../planning/benchmark-plan.json');
const clone = value => JSON.parse(JSON.stringify(value));
function fixture(t, id = 'STD-001') {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'research300-test-'));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  fs.mkdirSync(path.join(root, 'planning'), { recursive: true });
  fs.copyFileSync(path.join(repo, 'planning/capability-coverage-300.json'), path.join(root, 'planning/capability-coverage-300.json'));
  fs.copyFileSync(path.join(repo, 'planning/benchmark-plan.json'), path.join(root, 'planning/benchmark-plan.json'));
  const caseDir = path.join(root, 'corpora/research-300/cases', id);
  fs.mkdirSync(caseDir, { recursive: true });
  const planCase = plan.cases.find(c => c.id === id);
  const model = { schema_version: '2.2.0', unit_system: 'SI', coordinate_system: { dimension: '2d', plane: 'xz', semantics: 'global-z-up' },
    nodes: [ {id:'a', x:0,y:0,z:0,restraints:[true,true,true,true,false,true]}, {id:'m',x:3,y:0,z:0,restraints:[false,true,false,true,false,true]}, {id:'b',x:6,y:0,z:0,restraints:[false,true,true,true,false,true]} ],
    elements: [{id:'am',type:'beam',nodes:['a','m'],material:'steel',section:'beam'}, {id:'mb',type:'beam',nodes:['m','b'],material:'steel',section:'beam'}],
    materials: [{id:'steel',E:200000,G:76923.07692307692,nu:0.3}], sections:[{id:'beam',properties:{A:0.01,Iy:0.0001,Iz:0.0001,J:0.0002}}],
    load_cases: [{id:'D',type:'dead',loads:[{id:'w1',type:'distributed',element:'am',reference_frame:'global',wz:-20,start:0,end:3},{id:'w2',type:'distributed',element:'mb',reference_frame:'global',wz:-20,start:0,end:3}]},{id:'L',type:'live',loads:[]}],
    load_combinations:[{id:'D',factors:{D:1,L:1}}], analysis_control:{self_weight:false,rigid_floor:false,p_delta:false,rigid_offsets:false,construction_stage:false} };
  const quantity = (id, location, component, unit) => ({id, selection:{kind:'case',id:'D'}, location, component, unit, tolerance:{absolute:1e-8,relative:1e-6}});
  const requests = {schemaVersion:1,states:[{state:1,model:'model-state-1.json',quantities:[quantity('D:left', {kind:'node',id:'a'},'Fz','kN'),quantity('D:right',{kind:'node',id:'b'},'Fz','kN'),quantity('D:mid-u',{kind:'node',id:'m'},'uz','m'),quantity('D:mid-M',{kind:'member',id:'am',positionM:3,side:'left'},'M2','kN.m')],derived:[]}]};
  const contract = {schemaVersion:1,evaluationProfile:'engineering-v2.3',id,modelId:planCase.modelId,family:planCase.family,language:planCase.language,locale:planCase.language==='英文'?'en':'zh',plannedEngine:planCase.plannedEngine,sourcePlan:clone(planCase.sourceRequirements),modelStates:['model-state-1.json'],attachments:['properties.json','geometry.csv'],turns:[{id:'t1',instruction:'分析6m简支梁，全跨向下20kN/m。报告左右反力、跨中位移和弯矩。单位m、kN、MPa；自重关闭，一阶弹性。',state:1,expectation:'analyze',attachments:['properties.json','geometry.csv'],unresolvedFields:[],expectedQuestions:[]}],requiredOutputs:[{id:'reactions',description:'左右反力',state:1,quantityIds:['D:left','D:right'],kind:'numerical'},{id:'midpoint',description:'跨中位移和弯矩',state:1,quantityIds:['D:mid-u','D:mid-M'],kind:'numerical'}],requirementCoverage:[],status:'authored-candidate',sameEngineTruthStatus:'pending',inputBlindReview:'pending',llmEndToEnd:'not-run'};
  for (const field of Object.keys(planCase.sourceRequirements)) contract.requirementCoverage.push({sourceField:field,requirementIds:planCase.requirements.filter(r=>r.sourceField===field).map(r=>r.id),targets:field==='task.expectedOutput'?['output:reactions','output:midpoint']:field.startsWith('engine.')?['gate:native-review']:['turn:t1'],notes:'Explicit input mapping; policy evidence remains pending.'});
  const write = (name,data) => { fs.mkdirSync(path.dirname(path.join(caseDir,name)),{recursive:true}); fs.writeFileSync(path.join(caseDir,name),typeof data==='string'?data:JSON.stringify(data,null,2)+'\n'); };
  const save = () => {write('contract.json',contract);write('reference-requests.json',requests);write('model-state-1.json',model);};
  save(); write('prompt.txt',contract.turns[0].instruction);write('properties.json',{units:{length:'m',force:'kN',stress:'MPa'},materials:model.materials,sections:model.sections,analysis_control:model.analysis_control});write('geometry.csv','id,x_m,y_m,z_m\na,0,0,0\nm,3,0,0\nb,6,0,0\n');
  const addReference = () => {
    const ref={referenceKind:'synthetic-test-only',toleranceFrozenBeforeCandidate:true,notCommercialScoringTruth:false,states:requests.states.map(s=>({state:s.state,quantities:s.quantities.map(q=>({...clone(q),value:1})),derived:[]}))};
    ref.sourceHash=sourceHash(caseDir,contract);ref.inputHashes=Object.fromEntries(['contract.json','reference-requests.json',...contract.modelStates].map(name=>[name,sha256(fs.readFileSync(path.join(caseDir,name)))]));write('independent-reference.json',ref);return ref;
  };
  const addAcceptance = () => {
    addReference();write('review.txt','Synthetic test review fixture, not real native evidence.');write('native-results.csv','synthetic test data\n');
    const descriptor=name=>({path:name,sha256:sha256(fs.readFileSync(path.join(caseDir,name)))});
    write('native-receipt.json',{engine:contract.plannedEngine,modelSha256:descriptor('model-state-1.json').sha256,state:1,selection:{kind:'case',id:'D'},status:'succeeded',runId:'synthetic-test',engineVersion:'test',artifacts:[descriptor('native-results.csv')]});
    const acceptance={schemaVersion:1,sourceHash:sourceHash(caseDir,contract),independentReferenceSha256:descriptor('independent-reference.json').sha256,inputBlindReview:{status:'passed',reviewer:'fixture-reviewer',evidence:descriptor('review.txt')},sameEngineTruth:{status:'verified',engine:contract.plannedEngine,independentlyReviewed:true,reviewer:'fixture-reviewer',receipts:[{...descriptor('native-receipt.json'),state:1,selection:{kind:'case',id:'D'}}]}};
    write('acceptance.json',acceptance);return acceptance;
  };
  return {root,caseDir,planCase,contract,model,requests,write,save,addReference,addAcceptance};
}

// Publish test-only canonical inputs explicitly after source writes. Production
// delivery never synthesizes missing input files or falls back to source inputs.
function publishInputs(f) {
  const { buildManifest } = require('../scripts/build-research300-manifest.cjs');
  const { spawnSync } = require('node:child_process');
  fs.writeFileSync(path.join(f.root, 'corpora/research-300/manifest.json'), JSON.stringify(buildManifest({ root: f.root, allowPartial: true }), null, 2) + '\n');
  const generated = spawnSync('python3', [path.join(repo, 'scripts/research300/public_input_clean.py'), '--root', f.root, ...(f.contract?.id ? ['--case', f.contract.id] : [])], { encoding: 'utf8', timeout: 60000 });
  if (generated.error || generated.status !== 0) throw new Error(generated.error?.message || generated.stderr || generated.stdout);
}

// Exact response-relevant author snapshots captured 2026-10-15 after turn-scope fixes.
// They intentionally retain hidden request tolerances and operands to test public projection.
// No fixture reads another worktree, generated references, or author models at test runtime.
const authoredResponseSnapshots = {
  'INT-003': {
    contract: {
      turns: [
        {"instruction":"建立并分析附件梁，报告x=3.25 m与外伸自由端x=6.5 m的Uz。 使用所附输入表与OpenSees，输出须注明符号、位置、方向、单位、工况和当前轮次。","state":1,"expectation":"analyze","attachments":["input-tables.txt"],"unresolvedFields":[],"expectedQuestions":[],"id":"t1"},
        {"instruction":"把第一个位移观测位置改为支承跨中x=2.5 m，外伸自由端x=6.5 m保持。结构、截面分界和全部荷载不变；可复用当前有效结果，报告这两个位置的Uz。","state":1,"expectation":"query","attachments":[],"unresolvedFields":[],"expectedQuestions":[],"preservedFields":["/nodes","/elements","/materials","/sections","/load_cases","/load_combinations"],"id":"t2"}
      ],
      requiredOutputs: [
        {"id":"requested-output-1","description":"第1轮工况D：x=3.25 m与x=6.5 m的Uz。","state":1,"quantityIds":["D-x3p25-uz","D-x6p5-uz"],"kind":"numerical","turnIds":["t1"]},
        {"id":"requested-output-2","description":"第2轮工况D：x=2.5 m与x=6.5 m的Uz。","state":1,"quantityIds":["D-x2p5-uz","D-x6p5-uz"],"kind":"numerical","turnIds":["t2"]},
        {"id":"s1:D-x3p25-uz","description":"case D: {'kind': 'node', 'id': 'n2'}; uz [m], signed","state":1,"quantityIds":["D-x3p25-uz"],"kind":"numerical","turnIds":["t1"]},
        {"id":"s1:D-x6p5-uz","description":"case D: {'kind': 'node', 'id': 'n4'}; uz [m], signed","state":1,"quantityIds":["D-x6p5-uz"],"kind":"numerical","turnIds":["t1","t2"]},
        {"id":"s1:D-x2p5-uz","description":"case D: {'kind': 'node', 'id': 'n1'}; uz [m], signed","state":1,"quantityIds":["D-x2p5-uz"],"kind":"numerical","turnIds":["t2"]},
        {"id":"t1:interaction","description":"建立并分析附件梁，报告x=3.25 m与外伸自由端x=6.5 m的Uz。 使用所附输入表与OpenSees，输出须注明符号、位置、方向、单位、工况和当前轮次。","state":1,"quantityIds":[],"kind":"interaction","turnIds":["t1"]},
        {"id":"t2:interaction","description":"把第一个位移观测位置改为支承跨中x=2.5 m，外伸自由端x=6.5 m保持。结构、截面分界和全部荷载不变；可复用当前有效结果，报告这两个位置的Uz。","state":1,"quantityIds":[],"kind":"interaction","turnIds":["t2"]}
      ]
    },
    referenceRequests: {schemaVersion:1,states:[
      {state:1,model:"model-state-1.json",quantities:[
        {"id":"D-x3p25-uz","selection":{"kind":"case","id":"D"},"location":{"kind":"node","id":"n2"},"component":"uz","unit":"m","tolerance":{"absolute":1e-8,"relative":0.000001}},
        {"id":"D-x6p5-uz","selection":{"kind":"case","id":"D"},"location":{"kind":"node","id":"n4"},"component":"uz","unit":"m","tolerance":{"absolute":1e-8,"relative":0.000001}},
        {"id":"D-x2p5-uz","selection":{"kind":"case","id":"D"},"location":{"kind":"node","id":"n1"},"component":"uz","unit":"m","tolerance":{"absolute":1e-8,"relative":0.000001}}
      ],derived:[]}
    ]}
  },
  // Root's frozen extrema-tie-policy.md subsequently authorizes tiePolicy:any for INT033.
  'INT-033': {
    contract: {
      turns: [
        {"instruction":"按附件建立平行弦M-INT-033，另外报告“三角形的最大轴力”。现有物理模型及下列五项常规输出的输入已完整，请先分析并报告这五项结果；额外的最大轴力范围待澄清，先询问其具体含义，不猜测该项数值。报告x=6m上弦T2的带符号Ux、Uz，左支座B0反力Fx、Fz，以及首根下弦BC0轴力N。每个结果注明节点/杆件ID、位置、全局方向或轴力拉压符号、m或kN单位、工况D和当前轮次；轴力拉为正。物理状态修改后使用OpenSees重新计算，保留输入、版本、设置、成功日志、运行ID及原始结果对应关系。必需输入未明确前先澄清，不编造数值。","state":1,"expectation":"analyze","attachments":["input-tables.txt"],"unresolvedFields":["/requestedOutputs/maximumAxialForce/scope"],"expectedQuestions":["“三角形的最大轴力”具体指哪些杆件，且按带符号最大还是轴力绝对值最大取值？"],"clarificationBlocksAnalysis":false,"id":"t1"},
        {"instruction":"这里指本题连接表全部21根杆的轴力绝对值最大者。报告控制杆ID、带符号轴力及拉/压、单位和工况D；保留平行弦12节点21杆及仅B1/B3各10kN向下力。模型未改变，可以复用可追溯的当前状态结果。报告x=6m上弦T2的带符号Ux、Uz，左支座B0反力Fx、Fz，以及首根下弦BC0轴力N。每个结果注明节点/杆件ID、位置、全局方向或轴力拉压符号、m或kN单位、工况D和当前轮次；轴力拉为正。物理状态修改后使用OpenSees重新计算，保留输入、版本、设置、成功日志、运行ID及原始结果对应关系。必需输入未明确前先澄清，不编造数值。","state":1,"expectation":"query","attachments":[],"unresolvedFields":[],"expectedQuestions":[],"changedFields":[],"preservedFields":["/nodes","/elements","/materials","/sections","/load_cases","/analysis_control"],"id":"t2"}
      ],
      requiredOutputs: [
        {"id":"s1:case:D:node:T2:ux","description":"case D: {'kind': 'node', 'id': 'T2'}; ux [m], signed","state":1,"quantityIds":["case:D:node:T2:ux"],"kind":"numerical","turnIds":["t1","t2"]},
        {"id":"s1:case:D:node:T2:uz","description":"case D: {'kind': 'node', 'id': 'T2'}; uz [m], signed","state":1,"quantityIds":["case:D:node:T2:uz"],"kind":"numerical","turnIds":["t1","t2"]},
        {"id":"s1:case:D:node:B0:Fx","description":"case D: {'kind': 'node', 'id': 'B0'}; Fx [kN], signed","state":1,"quantityIds":["case:D:node:B0:Fx"],"kind":"numerical","turnIds":["t1","t2"]},
        {"id":"s1:case:D:node:B0:Fz","description":"case D: {'kind': 'node', 'id': 'B0'}; Fz [kN], signed","state":1,"quantityIds":["case:D:node:B0:Fz"],"kind":"numerical","turnIds":["t1","t2"]},
        {"id":"s1:case:D:member:BC0:0:right:N","description":"case D: {'kind': 'member', 'id': 'BC0', 'positionM': 0, 'side': 'right'}; N [kN], signed","state":1,"quantityIds":["case:D:member:BC0:0:right:N"],"kind":"numerical","turnIds":["t1","t2"]},
        {"id":"s1:case:D:all-members:max-abs-N","description":"全部21根杆轴力绝对值最大者，保留控制杆ID、带符号轴力、拉压及工况D。","state":1,"quantityIds":["case:D:all-members:max-abs-N"],"kind":"derived","turnIds":["t2"]},
        {"id":"t1:interaction","description":"按附件建立平行弦M-INT-033，另外报告“三角形的最大轴力”。现有物理模型及下列五项常规输出的输入已完整，请先分析并报告这五项结果；额外的最大轴力范围待澄清，先询问其具体含义，不猜测该项数值。报告x=6m上弦T2的带符号Ux、Uz，左支座B0反力Fx、Fz，以及首根下弦BC0轴力N。每个结果注明节点/杆件ID、位置、全局方向或轴力拉压符号、m或kN单位、工况D和当前轮次；轴力拉为正。物理状态修改后使用OpenSees重新计算，保留输入、版本、设置、成功日志、运行ID及原始结果对应关系。必需输入未明确前先澄清，不编造数值。","state":1,"quantityIds":[],"kind":"interaction","turnIds":["t1"]},
        {"id":"t2:interaction","description":"这里指本题连接表全部21根杆的轴力绝对值最大者。报告控制杆ID、带符号轴力及拉/压、单位和工况D；保留平行弦12节点21杆及仅B1/B3各10kN向下力。模型未改变，可以复用可追溯的当前状态结果。报告x=6m上弦T2的带符号Ux、Uz，左支座B0反力Fx、Fz，以及首根下弦BC0轴力N。每个结果注明节点/杆件ID、位置、全局方向或轴力拉压符号、m或kN单位、工况D和当前轮次；轴力拉为正。物理状态修改后使用OpenSees重新计算，保留输入、版本、设置、成功日志、运行ID及原始结果对应关系。必需输入未明确前先澄清，不编造数值。","state":1,"quantityIds":[],"kind":"interaction","turnIds":["t2"]}
      ]
    },
    referenceRequests: {schemaVersion:1,states:[
      {state:1,model:"model-state-1.json",quantities:[
        {"id":"case:D:node:T2:ux","selection":{"kind":"case","id":"D"},"location":{"kind":"node","id":"T2"},"component":"ux","unit":"m","tolerance":{"absolute":1e-8,"relative":0.000001}},
        {"id":"case:D:node:T2:uz","selection":{"kind":"case","id":"D"},"location":{"kind":"node","id":"T2"},"component":"uz","unit":"m","tolerance":{"absolute":1e-8,"relative":0.000001}},
        {"id":"case:D:node:B0:Fx","selection":{"kind":"case","id":"D"},"location":{"kind":"node","id":"B0"},"component":"Fx","unit":"kN","tolerance":{"absolute":1e-8,"relative":0.000001}},
        {"id":"case:D:node:B0:Fz","selection":{"kind":"case","id":"D"},"location":{"kind":"node","id":"B0"},"component":"Fz","unit":"kN","tolerance":{"absolute":1e-8,"relative":0.000001}},
        {"id":"case:D:member:BC0:0:right:N","selection":{"kind":"case","id":"D"},"location":{"kind":"member","id":"BC0","positionM":0,"side":"right"},"component":"N","unit":"kN","tolerance":{"absolute":1e-8,"relative":0.000001}},
        {"id":"case:D:member:TC0:0:right:N","selection":{"kind":"case","id":"D"},"location":{"kind":"member","id":"TC0","positionM":0,"side":"right"},"component":"N","unit":"kN","tolerance":{"absolute":1e-8,"relative":0.000001}},
        {"id":"case:D:member:BC1:0:right:N","selection":{"kind":"case","id":"D"},"location":{"kind":"member","id":"BC1","positionM":0,"side":"right"},"component":"N","unit":"kN","tolerance":{"absolute":1e-8,"relative":0.000001}},
        {"id":"case:D:member:TC1:0:right:N","selection":{"kind":"case","id":"D"},"location":{"kind":"member","id":"TC1","positionM":0,"side":"right"},"component":"N","unit":"kN","tolerance":{"absolute":1e-8,"relative":0.000001}},
        {"id":"case:D:member:BC2:0:right:N","selection":{"kind":"case","id":"D"},"location":{"kind":"member","id":"BC2","positionM":0,"side":"right"},"component":"N","unit":"kN","tolerance":{"absolute":1e-8,"relative":0.000001}},
        {"id":"case:D:member:TC2:0:right:N","selection":{"kind":"case","id":"D"},"location":{"kind":"member","id":"TC2","positionM":0,"side":"right"},"component":"N","unit":"kN","tolerance":{"absolute":1e-8,"relative":0.000001}},
        {"id":"case:D:member:BC3:0:right:N","selection":{"kind":"case","id":"D"},"location":{"kind":"member","id":"BC3","positionM":0,"side":"right"},"component":"N","unit":"kN","tolerance":{"absolute":1e-8,"relative":0.000001}},
        {"id":"case:D:member:TC3:0:right:N","selection":{"kind":"case","id":"D"},"location":{"kind":"member","id":"TC3","positionM":0,"side":"right"},"component":"N","unit":"kN","tolerance":{"absolute":1e-8,"relative":0.000001}},
        {"id":"case:D:member:BC4:0:right:N","selection":{"kind":"case","id":"D"},"location":{"kind":"member","id":"BC4","positionM":0,"side":"right"},"component":"N","unit":"kN","tolerance":{"absolute":1e-8,"relative":0.000001}},
        {"id":"case:D:member:TC4:0:right:N","selection":{"kind":"case","id":"D"},"location":{"kind":"member","id":"TC4","positionM":0,"side":"right"},"component":"N","unit":"kN","tolerance":{"absolute":1e-8,"relative":0.000001}},
        {"id":"case:D:member:V0:0:right:N","selection":{"kind":"case","id":"D"},"location":{"kind":"member","id":"V0","positionM":0,"side":"right"},"component":"N","unit":"kN","tolerance":{"absolute":1e-8,"relative":0.000001}},
        {"id":"case:D:member:V1:0:right:N","selection":{"kind":"case","id":"D"},"location":{"kind":"member","id":"V1","positionM":0,"side":"right"},"component":"N","unit":"kN","tolerance":{"absolute":1e-8,"relative":0.000001}},
        {"id":"case:D:member:V2:0:right:N","selection":{"kind":"case","id":"D"},"location":{"kind":"member","id":"V2","positionM":0,"side":"right"},"component":"N","unit":"kN","tolerance":{"absolute":1e-8,"relative":0.000001}},
        {"id":"case:D:member:V3:0:right:N","selection":{"kind":"case","id":"D"},"location":{"kind":"member","id":"V3","positionM":0,"side":"right"},"component":"N","unit":"kN","tolerance":{"absolute":1e-8,"relative":0.000001}},
        {"id":"case:D:member:V4:0:right:N","selection":{"kind":"case","id":"D"},"location":{"kind":"member","id":"V4","positionM":0,"side":"right"},"component":"N","unit":"kN","tolerance":{"absolute":1e-8,"relative":0.000001}},
        {"id":"case:D:member:V5:0:right:N","selection":{"kind":"case","id":"D"},"location":{"kind":"member","id":"V5","positionM":0,"side":"right"},"component":"N","unit":"kN","tolerance":{"absolute":1e-8,"relative":0.000001}},
        {"id":"case:D:member:DG0:0:right:N","selection":{"kind":"case","id":"D"},"location":{"kind":"member","id":"DG0","positionM":0,"side":"right"},"component":"N","unit":"kN","tolerance":{"absolute":1e-8,"relative":0.000001}},
        {"id":"case:D:member:DG1:0:right:N","selection":{"kind":"case","id":"D"},"location":{"kind":"member","id":"DG1","positionM":0,"side":"right"},"component":"N","unit":"kN","tolerance":{"absolute":1e-8,"relative":0.000001}},
        {"id":"case:D:member:DG2:0:right:N","selection":{"kind":"case","id":"D"},"location":{"kind":"member","id":"DG2","positionM":0,"side":"right"},"component":"N","unit":"kN","tolerance":{"absolute":1e-8,"relative":0.000001}},
        {"id":"case:D:member:DG3:0:right:N","selection":{"kind":"case","id":"D"},"location":{"kind":"member","id":"DG3","positionM":0,"side":"right"},"component":"N","unit":"kN","tolerance":{"absolute":1e-8,"relative":0.000001}},
        {"id":"case:D:member:DG4:0:right:N","selection":{"kind":"case","id":"D"},"location":{"kind":"member","id":"DG4","positionM":0,"side":"right"},"component":"N","unit":"kN","tolerance":{"absolute":1e-8,"relative":0.000001}}
      ],derived:[{"id":"case:D:all-members:max-abs-N","operation":"max_abs","tiePolicy":"any","operands":["case:D:member:BC0:0:right:N","case:D:member:TC0:0:right:N","case:D:member:BC1:0:right:N","case:D:member:TC1:0:right:N","case:D:member:BC2:0:right:N","case:D:member:TC2:0:right:N","case:D:member:BC3:0:right:N","case:D:member:TC3:0:right:N","case:D:member:BC4:0:right:N","case:D:member:TC4:0:right:N","case:D:member:V0:0:right:N","case:D:member:V1:0:right:N","case:D:member:V2:0:right:N","case:D:member:V3:0:right:N","case:D:member:V4:0:right:N","case:D:member:V5:0:right:N","case:D:member:DG0:0:right:N","case:D:member:DG1:0:right:N","case:D:member:DG2:0:right:N","case:D:member:DG3:0:right:N","case:D:member:DG4:0:right:N"],"unit":"kN","description":"全部21根杆轴力绝对值最大者，保留控制杆ID、带符号轴力、拉压及工况D。"}]}
    ]}
  },
  'INT-097': {
    contract: {
      turns: [
        {"instruction":"用OpenSees建立附件5m钢柱，柱底固定，柱顶向下700kN，z=2m连续节点沿全局+X施加12kN。采用附件HW300×300完整属性。先用m报告柱顶Uz和Ux，附符号、位置和工况D。仅作一阶弹性静力分析。\n每个可计算的新状态使用题定OpenSees引擎进行一阶线弹性分析；自重、P-delta、刚性楼板、刚域及施工阶段关闭。未明确更改的字段保持。每个数值附节点或构件、全局方向、单位、工况或组合、轮次、模型状态与可追溯运行ID。Rz表示竖向支反力Fz。保留原工况并分别计算所有明示组合。关键缺项或矛盾解决前不得编造新数值。","state":1,"expectation":"analyze","attachments":["input.json"],"unresolvedFields":[],"expectedQuestions":[],"outputUnits":{"uz":"m","ux":"m"},"id":"t1","requiredOutputIds":["s1--case-D--top--uz","s1--case-D--top--ux","t1-interaction","t1-displacements-m"],"requiredQuantityIds":["case-D--top--uz","case-D--top--ux"]},
        {"instruction":"把同一分析状态、同一柱顶位置及工况D的Uz和Ux都改用mm表示；保留符号。仅转换输出单位，模型与荷载保持，不重复追加12kN或700kN，也不将本静力结果表述为稳定验算通过。","state":1,"expectation":"query","attachments":[],"unresolvedFields":[],"expectedQuestions":[],"outputUnits":{"uz":"mm","ux":"mm"},"preservedFields":["/"],"id":"t2","requiredOutputIds":["s1--case-D--top--uz--mm","s1--case-D--top--ux--mm","t2-interaction","t2-displacements-mm"],"requiredQuantityIds":["case-D--top--uz--mm","case-D--top--ux--mm"]}
      ],
      requiredOutputs: [
        {"id":"s1--case-D--top--uz","description":"case D: top uz [m]","state":1,"quantityIds":["case-D--top--uz"],"kind":"numerical"},
        {"id":"s1--case-D--top--ux","description":"case D: top ux [m]","state":1,"quantityIds":["case-D--top--ux"],"kind":"numerical"},
        {"id":"s1--case-D--top--uz--mm","description":"case D: top uz [mm]","state":1,"quantityIds":["case-D--top--uz--mm"],"kind":"numerical"},
        {"id":"s1--case-D--top--ux--mm","description":"case D: top ux [mm]","state":1,"quantityIds":["case-D--top--ux--mm"],"kind":"numerical"},
        {"id":"t1-interaction","description":"用OpenSees建立附件5m钢柱，柱底固定，柱顶向下700kN，z=2m连续节点沿全局+X施加12kN。采用附件HW300×300完整属性。先用m报告柱顶Uz和Ux，附符号、位置和工况D。仅作一阶弹性静力分析。\n每个可计算的新状态使用题定OpenSees引擎进行一阶线弹性分析；自重、P-delta、刚性楼板、刚域及施工阶段关闭。未明确更改的字段保持。每个数值附节点或构件、全局方向、单位、工况或组合、轮次、模型状态与可追溯运行ID。Rz表示竖向支反力Fz。保留原工况并分别计算所有明示组合。关键缺项或矛盾解决前不得编造新数值。","state":1,"quantityIds":[],"kind":"interaction"},
        {"id":"t2-interaction","description":"把同一分析状态、同一柱顶位置及工况D的Uz和Ux都改用mm表示；保留符号。仅转换输出单位，模型与荷载保持，不重复追加12kN或700kN，也不将本静力结果表述为稳定验算通过。","state":1,"quantityIds":[],"kind":"interaction"},
        {"id":"t1-displacements-m","description":"T1: top Uz and Ux in m, signed, case D, state 1.","state":1,"quantityIds":["case-D--top--uz","case-D--top--ux"],"kind":"numerical"},
        {"id":"t2-displacements-mm","description":"T2: same top Uz and Ux in mm, signed, case D, same state 1; numerical values are 1000 times the m values.","state":1,"quantityIds":["case-D--top--uz--mm","case-D--top--ux--mm"],"kind":"numerical"}
      ]
    },
    referenceRequests: {schemaVersion:1,states:[
      {state:1,model:"model-state-1.json",quantities:[
        {"id":"case-D--top--uz","selection":{"kind":"case","id":"D"},"location":{"kind":"node","id":"top"},"component":"uz","unit":"m","tolerance":{"absolute":1e-8,"relative":0.000001}},
        {"id":"case-D--top--ux","selection":{"kind":"case","id":"D"},"location":{"kind":"node","id":"top"},"component":"ux","unit":"m","tolerance":{"absolute":1e-8,"relative":0.000001}},
        {"id":"case-D--top--uz--mm","selection":{"kind":"case","id":"D"},"location":{"kind":"node","id":"top"},"component":"uz","unit":"mm","tolerance":{"absolute":1e-8,"relative":0.000001}},
        {"id":"case-D--top--ux--mm","selection":{"kind":"case","id":"D"},"location":{"kind":"node","id":"top"},"component":"ux","unit":"mm","tolerance":{"absolute":1e-8,"relative":0.000001}}
      ],derived:[]}
    ]}
  },
};
function authoredResponseRecord(id) {
  if (!authoredResponseSnapshots[id]) throw new Error(`Missing response snapshot: ${id}`);
  return {id,corpus:'research-300',...clone(authoredResponseSnapshots[id])};
}
module.exports={fixture,clone,authoredResponseRecord,publishInputs};
