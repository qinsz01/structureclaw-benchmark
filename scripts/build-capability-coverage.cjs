/** Read-only plan projection. Text rules suggest review links; they NEVER prove support. */
const fs=require('node:fs');
const path=require('node:path');
const {createHash}=require('node:crypto');
const registry=require('../analysis-capabilities.json');
const {annotateCoverage}=require('../lib/requirement-semantics.cjs');
const sha=value=>createHash('sha256').update(value).digest('hex');

const supplementalFeatures=[
  {id:'input.complete-properties',status:'case-inputs-not-authored',evidence:'backend/src/agent-runtime/explicit-model.ts',limits:'Complete numeric properties and units must be supplied per case; a parser does not author or validate the missing appendix.'},
  {id:'input.multimodal-source-binding',status:'unknown',evidence:'backend/src/engineering/input-evidence.ts',limits:'Code location only; each unseen image and its entity/source binding needs acceptance.'},
  {id:'input.dxf-topology',status:'unknown',evidence:'backend/src/engineering/input-evidence.ts',limits:'Each DXF requires unit, topology, connection and entity provenance acceptance.'},
  {id:'input.multiview-reconstruction',status:'unknown',evidence:'backend/src/engineering/input-evidence.ts',limits:'Multiple views must be reconciled against independently reviewed geometry.'},
  {id:'interaction.state-updates',status:'integration-not-audited-here',evidence:'backend/src/engineering/model-state.ts',limits:'General transaction implementation is not a pass for the planned sequence of edits.'},
  {id:'interaction.clarification',status:'unknown',evidence:'backend/src/engineering/model-boundary.ts',limits:'A case-specific missing/conflicting input must stop formal calculation until resolved.'},
  {id:'coordinates.units-and-axes',status:'mechanics-and-schema-tested',evidence:'backend/src/agent-skills/analysis/opensees-static/__tests__/test_solver_mesh.py; backend/src/skill-shared/python/structure_protocol/regression/test_schema_v2.py',limits:'Canonical schema rejects conflicting explicit load units; source-to-canonical extraction still needs case-specific verification.'},
  {id:'member.response-stations',status:'integration-not-audited-here',evidence:'backend/src/skill-shared/member-response.ts',limits:'Shared postprocessing source exists; each requested station/component needs independent truth, loads and provenance acceptance.'},
  {id:'truth.same-engine-independent',status:'new-truth-not-generated',evidence:'tests/llm-benchmark/docs/evaluation-contract.md',limits:'The existing frozen truths do not certify new task physics, settings or outputs.'},
  {id:'report.requested-quantities',status:'unknown',evidence:'tests/llm-benchmark/lib/evaluate.cjs',limits:'Every requested position, signed component, unit and case must be enumerated and asserted.'},
];
const ruleDefinitions=[
  ['member.partial-point-and-piecewise-load',['局部均布','部分均布','分段不均匀','分段线性','三角形荷载','点载','集中力','分布荷载','均布载','线载']],
  ['member.response-stations',['跨中','跨内','观测','中点','挠度','截面弯矩','最大位移','指定位置']],
  ['selection.cases-and-linear-combinations',['工况','组合','D+','D＋','D、L','D/L']],
  ['coordinates.units-and-axes',['单位','局部轴','坐标','Ry','My','方向','强弱轴']],
  ['gravity.explicit-self-weight',['自重']],
  ['diaphragm.rigid-floor',['刚性楼板','刚性约束','楼板假定']],
  ['member.release-offset-pdelta',['内铰','梁端释放','端部释放','刚域','刚臂','P-Delta','P-Δ','二阶','施工阶段']],
  ['elastic.truss-and-frame-brace',['仅承轴力','轴力杆','轴向杆','桁架','斜撑','支撑']],
  ['interaction.state-updates',['逐轮','修改','更新','状态','撤销','保留未','未变字段']],
  ['interaction.clarification',['澄清','缺项','缺失','冲突','不确定']],
  ['input.multimodal-source-binding',['图中','图像','PNG','标签','图表']],
  ['input.dxf-topology',['DXF']],
  ['input.multiview-reconstruction',['多视图','多视角']],
  ['truth.same-engine-independent',['独立','真值','解析解','平衡','标答']],
  ['evaluation.execution-freshness',['运行ID','版本','原始结果','成功日志','输入模型','执行日志','当前模型状态']],
];
const definitions=new Map([...registry.features,...supplementalFeatures].map(x=>[x.id,x]));

function buildCoverage(tasks,models,sources={}) {
  if(tasks.length!==300||models.length!==300) throw Error('Expected exactly 300 tasks and physical model descriptors');
  const modelIndex=new Map(models.map(x=>[x.taskId,x]));
  if(modelIndex.size!==300||new Set(tasks.map(x=>x.id)).size!==300) throw Error('Duplicate task/model identifiers');
  if(new Set(models.map(x=>x.id)).size!==300) throw Error('Duplicate planned physical model IDs');
  const expectedIds=['STD','INT','MM'].flatMap(prefix=>Array.from({length:100},(_,i)=>`${prefix}-${String(i+1).padStart(3,'0')}`));
  if(expectedIds.some(id=>!modelIndex.has(id)||!tasks.some(t=>t.id===id))) throw Error('Missing STD/INT/MM task identifier');

  const cases=tasks.map(task=>{
    const model=modelIndex.get(task.id), engine=task.enginePlan?.plannedEngine;
    if(model.id!==task.baseGroup) throw Error(`Task/model source join mismatch for ${task.id}`);
    if(!['OpenSees','YJK','PKPM'].includes(engine)) throw Error(`Unreviewed engine label for ${task.id}`);
    const sourceValues={
      'task.inputForm':task.inputForm, 'task.scenario':task.scenario, 'task.modelingFocus':task.modelingFocus,
      'task.expectedOutput':task.expectedOutput, 'task.gradingFocus':task.gradingFocus, 'task.prerequisite':task.prerequisite,
      'model.topologyKey':model.topologyKey, 'model.boundaryKey':model.boundaryKey,
      'model.loadKey':model.loadKey, 'model.propertyKey':model.propertyKey,
      'engine.analysisContract':task.enginePlan.analysisContract,
      'engine.executionRequirement':task.enginePlan.executionRequirement,
      'engine.requiredEvidence':task.enginePlan.requiredEvidence,
      'engine.adapterGap':task.enginePlan.adapterGap, 'engine.truthPlan':task.enginePlan.truthPlan,
    };
    const requirements=[];
    for(const [field,text] of Object.entries(sourceValues)) {
      if(typeof text!=='string'||!text.trim()) {
        requirements.push({id:`${task.id}:${field}:0`,sourceField:field,sourceText:text??null,status:'unknown',candidateFeatures:[],reason:'Source requirement is missing'});
        continue;
      }
      // Store every source clause, including unmapped content. No requirement is deleted.
      const pieces=[...text.matchAll(/[^；。\n]+[；。]?/gu)];
      for(let index=0;index<pieces.length;index++) {
        const match=pieces[index], quote=match[0];
        const candidates=ruleDefinitions.flatMap(([featureId,terms])=>{
          const matched=terms.filter(term=>quote.includes(term));
          return matched.length?[{featureId,matchedTerms:matched,mapping:'text-candidate-needs-review'}]:[];
        });
        requirements.push({id:`${task.id}:${field}:${index+1}`,sourceField:field,sourceOffset:match.index,sourceText:quote,
          status:'unknown',candidateFeatures:candidates,
          reason:candidates.length?'Candidate links identify what to review; no case input, solve or result was validated':'No confirmed feature mapping; retain this requirement for manual decomposition'});
      }
    }
    const direct=[
      ['input.complete-properties','The source plan says appendices/task inputs remain to be authored'],
      ['coordinates.units-and-axes',`Explicit model.dimension=${model.dimension}`],
      ['evaluation.physical-equivalence','Every planned task requires physical model correctness'],
      ['evaluation.signed-case-results','Every task retains its complete signed output/case contract'],
      ['evaluation.execution-freshness','New planned corpus requires a current actual run'],
      ['truth.same-engine-independent','Every new case requires independently reviewed target-engine truth'],
      ['report.requested-quantities','task.expectedOutput is retained without reduction'],
    ];
    if(engine==='OpenSees') direct.push([model.structure==='桁架'?'elastic.truss-and-frame-brace':'elastic.frame.2d-3d',`Exact model.structure=${model.structure}; enginePlan.plannedEngine=${engine}`]);
    else direct.push(['commercial.building-native',`Exact enginePlan.plannedEngine=${engine}; feature evidence is recorded separately and does not accept this planned case`]);
    if(task.family==='interactive_robustness') direct.push(['interaction.state-updates','Exact task.family=interactive_robustness'],['interaction.clarification','Each planned turn must be independently reviewed for missing-input behavior']);
    if(task.family==='multimodal_reverse_engineering') {
      const feature={'结构DXF':'input.dxf-topology','建筑DXF':'input.dxf-topology','多视图重建':'input.multiview-reconstruction'}[task.subcategory]||'input.multimodal-source-binding';
      direct.push([feature,`Exact task.family and subcategory=${task.subcategory}`]);
    }
    const links=new Map(direct.map(([id,basis])=>[id,{featureId:id,mapping:'declared-category-or-shared-contract',basis:[basis],requirementIds:[]}]));
    for(const req of requirements) for(const candidate of req.candidateFeatures) {
      if(!links.has(candidate.featureId)) links.set(candidate.featureId,{featureId:candidate.featureId,mapping:'text-candidate-needs-review',basis:[],requirementIds:[]});
      links.get(candidate.featureId).requirementIds.push(req.id);
    }
    const requirementNumbers=new Map(requirements.map((r,i)=>[r.id,i+1]));
    const features=[...links.values()].map(link=>{
      const definition=definitions.get(link.featureId);
      const relevantEngine=!definition.engine||definition.engine==='all'||definition.engine===engine||definition.engine==='YJK/PKPM'&&['YJK','PKPM'].includes(engine);
      return {featureId:link.featureId,mapping:link.mapping,...(link.basis.length?{basis:link.basis}:{}),
        requiredBy:link.requirementIds.map(id=>requirementNumbers.get(id)),
        targetEngineFeatureEvidence:relevantEngine?definition.status:'unknown-evidence-is-for-another-engine'};
    });
    return {id:task.id,modelId:model.id,title:task.title,family:task.family,subcategory:task.subcategory,
      difficulty:task.difficulty,language:task.language,structure:model.structure,dimension:model.dimension,
      plannedEngine:engine,sourcePlanStatus:task.status,sourceAdapterStatus:task.enginePlan.adapterStatus,
      oldPrimaryId:task.oldPrimaryId,oldSecondaryId:task.oldSecondaryId,sourceRequirements:sourceValues,
      requirements:requirements.map((r,i)=>({id:i+1,sourceField:r.sourceField,
        sourceRange:[r.sourceOffset||0,(r.sourceOffset||0)+(r.sourceText?.length||0)],
        candidateFeatures:r.candidateFeatures.map(c=>c.featureId)})),features,
      acceptance:{status:'not-accepted',caseSupportStatus:'unknown',acceptedEvidence:[],
        nextSteps:['Review candidate feature links against every retained requirement','Author and independently review complete per-case inputs',
          'Verify target-engine mapping/settings and native execution','Generate target-engine truth and independent checks',
          'Run every required state/case and assert every requested output'],
        requirementStatus:'unknown',unknownRequirementCount:requirements.length,
        unmappedRequirementIds:requirements.flatMap((x,i)=>x.candidateFeatures.length?[]:[i+1])}};
  });
  const counts=key=>cases.reduce((a,x)=>(a[x[key]]=(a[x[key]]||0)+1,a),{});
  return annotateCoverage({schemaVersion:1,modelProtocol:'2.2.0',evaluationVersion:'physical-v1',sources,
    featureDefinitions:[...definitions.values()],candidateLinkRules:ruleDefinitions,
    policy:{wholeCaseAcceptanceNeverInferred:true,keywordMatchesAreCandidateLinksOnly:true,
      unknownIsNotUnsupported:true,featureTestIsNotCasePass:true,frozenCorpusUnchanged:true,
      candidateLinksMayBeProhibitionsOrAlternatives:true,
      sourceRangeConvention:'UTF-16 string indices into sourceRequirements[sourceField], end exclusive',
      description:'Every original requirement is retained. No workbook or task was edited. Candidate links need review; all 300 cases still require acceptance.'},
    summary:{cases:cases.length,byFamily:counts('family'),byEngine:counts('plannedEngine'),acceptedCases:0,unknownCases:300,
      requirementClauses:cases.reduce((n,c)=>n+c.requirements.length,0),
      unmappedClauses:cases.reduce((n,c)=>n+c.requirements.filter(r=>!r.candidateFeatures.length).length,0)},cases});
}

if(require.main===module) {
  const [sourceDir,output]=process.argv.slice(2);
  if(!sourceDir||!output) throw Error('Usage: node scripts/build-capability-coverage.cjs SOURCE_PLAN_DIRECTORY OUTPUT.json');
  const read=name=>{const bytes=fs.readFileSync(path.join(sourceDir,name));return {name,bytes,data:JSON.parse(bytes),sha256:sha(bytes)};};
  const tasks=read('all-tasks-engines-v2.json'),models=read('all-models-engines-v2.json');
  const sources={tasks:{file:tasks.name,sha256:tasks.sha256},models:{file:models.name,sha256:models.sha256},
    capabilityRegistry:{file:'analysis-capabilities.json',sha256:sha(fs.readFileSync(path.join(__dirname,'../analysis-capabilities.json')))}};
  const workbook='StructureClaw_Bench_300题规划_求解器补充版_20261013.xlsx';
  if(fs.existsSync(path.join(sourceDir,workbook))) sources.workbook={file:workbook,sha256:sha(fs.readFileSync(path.join(sourceDir,workbook))),usage:'Identity only; analysis reads the associated complete JSON planning tables, not cached formula values'};
  const result=buildCoverage(tasks.data,models.data,sources);
  const {cases,...header}=result;
  const serialized=JSON.stringify(header,null,2).slice(0,-2)+',\n  "cases": [\n'+cases.map(c=>'    '+JSON.stringify(c)).join(',\n')+'\n  ]\n}\n';
  fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,serialized);
  if(sha(fs.readFileSync(path.join(sourceDir,tasks.name)))!==tasks.sha256||sha(fs.readFileSync(path.join(sourceDir,models.name)))!==models.sha256) throw Error('Source changed during read-only projection');
  console.log(JSON.stringify(result.summary));
}
module.exports={buildCoverage};
