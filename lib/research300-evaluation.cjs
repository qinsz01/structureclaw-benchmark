/** Pure engineering-v2.3 evaluation. All trust inputs are supplied by the benchmark caller. */
const {isDeepStrictEqual}=require('node:util');
const {modelFingerprint,resultFingerprint,verifyExecutionEvidence}=require('./analysis-evidence.cjs');
const {comparePhysicalModels,axesFor}=require('./physical-model-fidelity.cjs');
const {readQuantity,compareRequestedQuantities,compareReportQuantities,compareDerivedQuantities,evaluateDerivedQuantities,equilibriumDifferenceIds,UNITS}=require('./requested-quantities.cjs');
const {selectAnalysisResult,selectionKey}=require('./result-selection.cjs');
const {normalizeEngineKey,verifyReferenceBinding}=require('./engine-ground-truth.cjs');
const {referenceAllowance,convertPrecision,validatePrecisionScope}=require('./reference-precision.cjs');
const {normalizeCleanReport}=require('./clean-report.cjs');
const record=x=>x&&typeof x==='object'&&!Array.isArray(x);
const compatibleUnits={m:['m','mm'],rad:['rad'],kN:['kN','N'],'kN.m':['kN.m','kN*m','kN·m','N.m','N*m']};
const unitSpelling=unit=>typeof unit==='string'?unit.replace(/[\*·]/g,'.'):unit;
const EVALUATOR_VERSION='research300-evaluator';
const RESPONSE_CONTRACT_VERSION='research300-response-v1';
const PHYSICAL_OPTIONS=Object.freeze({coordinate:1e-8,property:1e-6,load:1e-6,explicitElasticProperties:true});
const physicalOptions=(engine,convention)=>({...PHYSICAL_OPTIONS,inactiveLoadCaseClassification:normalizeEngineKey(engine)==='opensees',
  openSeesStaticDefaults:normalizeEngineKey(engine)==='opensees',
  prescribedShearAreaRatio:convention?.bendingTheory==='Timoshenko'&&convention.effectiveShearAreas?.localY==='5*A/6'
    &&convention.effectiveShearAreas?.localZ==='5*A/6'?5/6:undefined,
  staticTheory:normalizeEngineKey(engine)==='opensees'?'Euler-Bernoulli':['pkpm','yjk'].includes(normalizeEngineKey(engine))?'Timoshenko':undefined});
function identitySelections(expected,actual,analysis,mapping,engine,enabled) {
  const result={selectionMapping:{},selectionEquivalences:{}};
  if(!enabled||normalizeEngineKey(engine)!=='opensees'||!['self_weight','rigid_floor','p_delta','rigid_offsets','construction_stage']
    .every(k=>actual.analysis_control?.[k]===false&&expected.analysis_control?.[k]===false))return result;
  const sets=analysis?.results||analysis?.data?.results;
  if(!record(sets))return result;
  for(const combination of expected.load_combinations||[]) {
    const factors=Object.entries(combination.factors||{});
    if(factors.length!==1||factors[0][0]!==combination.id||factors[0][1]!==1)continue;
    const caseId=mapping.caseMapping?.[combination.id],combinationId=mapping.combinationMapping?.[combination.id];
    const actualCombination=actual.load_combinations?.find(c=>c.id===combinationId);
    if(!caseId||!actualCombination||Object.keys(actualCombination.factors).length!==1||actualCombination.factors[caseId]!==1)continue;
    for(const [kind,id,otherKind,otherId] of [['combination',combinationId,'case',caseId],['case',caseId,'combination',combinationId]]) {
      const frozenKey=`${kind}:${combination.id}`,originalKey=`${kind}:${id}`,other={kind:otherKind,id:otherId},otherKey=selectionKey(other);
      result.selectionEquivalences[frozenKey]=[otherKey];
      // An existing unsuccessful or contradictory result must never fall back
      // to another result. Only an absent identity selection may be supplied.
      if(!Object.hasOwn(sets,originalKey)&&Object.hasOwn(sets,otherKey))result.selectionMapping[frozenKey]=other;
    }
  }
  return result;
}
function figureSetFingerprint(figures) {
  return resultFingerprint({schemaVersion:'research300-figure-set-v1',figures:figures.map(f=>({outputId:f.outputId,state:f.state,
    runId:f.runId,...(f.runIds!==undefined?{runIds:f.runIds}:{}),path:f.path,sourceHash:f.sourceHash,sha256:f.sha256}))});
}
const metric=(name,pass,actual,status)=>({metric:name,pass,actual,...(status?{status}:{})});
function result(metrics) {
  const unavailable=metrics.find(m=>m.status==='configuration_error')||metrics.find(m=>m.status==='native_truth_pending')
    ||metrics.find(m=>m.status==='review_pending');
  const pass=metrics.length>0&&metrics.every(m=>m.pass);
  // A valid numerical extraction can disagree with the reference. All other
  // gates remain mandatory in both modes; engineering never controls the score.
  const evidenceValid=metrics.length>0&&metrics.every(m=>m.evidenceValid??m.pass);
  const engineeringPass=metrics.length>0&&metrics.every(m=>m.engineeringPass??m.pass);
  return {evaluationProfile:'engineering-v2.3',evaluatorVersion:EVALUATOR_VERSION,responseContractVersion:RESPONSE_CONTRACT_VERSION,
    status:unavailable?.status||(pass?'pass':'agent_failure'),allPassed:pass,evidenceValid,strictPass:pass,engineeringPass,
    passed:unavailable?null:metrics.filter(m=>m.pass).length,total:metrics.length,score:unavailable?null:metrics.filter(m=>m.pass).length/metrics.length,metrics};
}
function configuration(reason) {return result([metric('configuration',false,reason,'configuration_error')]);}

/** Slice cumulative events using benchmark-collected boundaries; never infer a turn from candidate text. */
function scopeTurnState(state,turnEvidence) {
  if(state.messages!==undefined&&!Array.isArray(state.messages)) throw Error('candidate messages must be an array');
  if(!record(turnEvidence)||typeof turnEvidence.turnId!=='string'||!turnEvidence.turnId||
    !Number.isInteger(turnEvidence.messageStartIndex)||turnEvidence.messageStartIndex<0||
    turnEvidence.messageStartIndex>(state.messages||[]).length||!Array.isArray(turnEvidence.analysisRunIds)||
    turnEvidence.analysisRunIds.some(id=>typeof id!=='string'||!id))
    throw Error('benchmark turnEvidence with message boundary and analysisRunIds is required');
  if(turnEvidence.toolEvents!==undefined&&(!Array.isArray(turnEvidence.toolEvents)||turnEvidence.toolEvents.some(event=>!record(event))))
    throw Error('benchmark toolEvents must contain captured event objects');
  if(turnEvidence.assistantEvents!==undefined&&(!Array.isArray(turnEvidence.assistantEvents)||turnEvidence.assistantEvents.some(event=>
    !record(event)||event.type!=='item.completed'||event.item?.type!=='agent_message'||typeof event.item.text!=='string')))
    throw Error('benchmark assistantEvents must contain completed Codex agent messages');
  const runs=new Set(turnEvidence.analysisRunIds);
  let analysisResult=null;
  if(state.analysisResult?.results) {
    const results=Object.fromEntries(Object.entries(state.analysisResult.results).filter(([,r])=>runs.has(r?.meta?.runId)));
    if(Object.keys(results).length) analysisResult={results};
  } else if(runs.has(state.analysisResult?.meta?.runId)) analysisResult=state.analysisResult;
  return {...state,messages:(state.messages||[]).slice(turnEvidence.messageStartIndex),analysisResult,analysisAttempted:runs.size>0};
}

function evaluateBoundQuantities({state,expectedModel,engineId,stateNumber,quantities,derived=[],sourceHash,
  referenceEvidence,turnEvidence,artifactEvidence,requireCurrentTurn=true,reportedDerived,reportedDerivedIds,inputBinding,analysisConvention}) {
  if(!record(expectedModel)) return configuration('mandatory frozen expected model is missing');
  const frozenModel=comparePhysicalModels(expectedModel,expectedModel,{coordinate:1e-8,property:1e-6,load:1e-6});
  if(!frozenModel.pass) return configuration(`frozen expected model is invalid: ${frozenModel.failures.join('; ')}`);
  const reference=verifyReferenceBinding({referenceEvidence,engineId,state:stateNumber,modelHash:modelFingerprint(expectedModel),sourceHash});
  if(!reference.pass) return result([metric('reference_binding',false,reference.failures.join('; '),reference.status)]);
  if(!Array.isArray(quantities)||!quantities.length) return configuration('independently frozen requested quantities are missing');
  const ids=new Set();
  for(const q of quantities) {
    const choices=q?.selection?.kind==='case'?expectedModel.load_cases:q?.selection?.kind==='combination'?expectedModel.load_combinations:[];
    const id=q&&`${selectionKey(q.selection)}:${q.id}`;
    if(!q?.id||ids.has(id)||!choices?.some(c=>c.id===q.selection.id)||!Number.isFinite(q.value)||!UNITS[q.component]||
      !record(q.location)||!['node','member'].includes(q.location.kind)||typeof q.location.id!=='string'||
      !Number.isFinite(q.tolerance?.absolute)||q.tolerance.absolute<0||!Number.isFinite(q.tolerance?.relative)||q.tolerance.relative<0)
      return configuration('invalid/duplicate frozen quantity or missing exact case/combination reference');
    const node=q.location.kind==='node',locations=node?expectedModel.nodes:expectedModel.elements;
    if(!compatibleUnits[UNITS[q.component]]?.includes(q.unit)||!locations.some(row=>row.id===q.location.id)||
      (node&&!/^(?:[ur][xyz]|[fFmM][xyz])$/.test(q.component))||
      (!node&&(!Number.isFinite(q.location.positionM)||q.location.positionM<0||!['left','right'].includes(q.location.side))))
      return configuration('frozen quantity has an incompatible component/unit or missing physical location/station');
    ids.add(id);
    try {
      if(q.engineeringPrecision!==undefined&&normalizeEngineKey(engineId)!=='pkpm')throw Error('Certified recovery precision requires PKPM');
      referenceAllowance(q);
      validatePrecisionScope(q,expectedModel);
    } catch(error) {return configuration(error.message);}
  }
  if(!Array.isArray(derived)) return configuration('derived reference definitions must be an array');
  if(derived.length) {
    const derivation=evaluateDerivedQuantities(quantities,derived);
    if(!derivation.pass) return configuration(`invalid independent derived references: ${derivation.failures.join('; ')}`);
  }
  try {scopeTurnState(state,turnEvidence);} catch(error) {return configuration(error.message);}
  if(turnEvidence.state!==stateNumber) return configuration('turn evidence is not bound to the requested state');
  const physical=comparePhysicalModels(state.model,expectedModel,physicalOptions(engineId,analysisConvention));
  const metrics=[metric('model_matches',physical.pass,physical.pass?physical.summary:physical.failures.join('; '))];
  if(!physical.pass) return result(metrics);
  const equivalences=identitySelections(expectedModel,state.model,state.analysisResult,physical.diagnostics,engineId,inputBinding?.inputEdition==='current');
  const selections=new Map();
  for(const q of quantities) {
    const map=q.selection.kind==='case'?physical.diagnostics.caseMapping:physical.diagnostics.combinationMapping;
    const selection=equivalences.selectionMapping[selectionKey(q.selection)]||{...q.selection,id:map[q.selection.id]};
    selections.set(selectionKey(selection),selection);
  }
  for(const [key,selection] of selections) {
    try {
      const selected=selectAnalysisResult(state.analysisResult,selection),meta=selected.record.meta||{};
      const failures=[];
      if(normalizeEngineKey(meta.engineId)!==normalizeEngineKey(engineId)) failures.push('result engine differs from frozen target engine');
      const executionRecord=selected.data.execution||selected.record.execution||meta.execution;
      if(!normalizeEngineKey(executionRecord?.solver)) failures.push('actual solver identity is not a recognized target engine');
      const engineDeclarations=[selected.record.engineId,selected.data.engineId,selected.data.meta?.engineId,executionRecord?.engineId,
        normalizeEngineKey(executionRecord?.solver)].filter(value=>value!==undefined&&value!==null);
      if(engineDeclarations.some(value=>normalizeEngineKey(value)!==normalizeEngineKey(engineId))) failures.push('conflicting engine declaration in selected result/execution');
      if(meta.state!==stateNumber) failures.push('result state differs from requested state');
      if(meta.sourceHash!==sourceHash) failures.push('result source binding differs from frozen source');
      const artifacts=artifactEvidence?.[meta.runId];
      const digest=Array.isArray(artifacts?.selections)?artifacts?.resultHashes?.[key]:artifacts?.resultHash;
      if(digest!==resultFingerprint(selected.data)) failures.push('selected results differ from trusted artifact extraction');
      if(requireCurrentTurn&&!turnEvidence.analysisRunIds.includes(meta.runId)) failures.push('analysis run was not executed during the current turn');
      const execution=verifyExecutionEvidence(state,selection,{evaluationProfile:'engineering-v2.3',artifactEvidence});
      failures.push(...execution.failures);
      metrics.push({...metric(`execution:${key}`,!failures.length,failures.join('; ')||'exact state, engine, source, run and artifact binding verified'),runId:meta.runId});
    } catch(error) {metrics.push(metric(`execution:${key}`,false,error.message));}
  }
  if(metrics.some(m=>!m.pass)) return result(metrics);
  const mappings={...physical.diagnostics,...equivalences,model:state.model};
  const comparison=compareRequestedQuantities(state.analysisResult,quantities,mappings);
  metrics.push({...metric('requested_quantities',comparison.pass,comparison.failures.join('; ')||`${comparison.comparedValues} quantities matched`),
    evidenceValid:comparison.evidenceValid,strictPass:comparison.strictPass,engineeringPass:comparison.engineeringPass,
    ...(comparison.precision?{precision:comparison.precision}:{})});
  if(derived.length) {
    const comparison=compareDerivedQuantities(state.analysisResult,quantities,derived,mappings,reportedDerived,reportedDerivedIds);
    metrics.push(metric('derived_quantities',comparison.pass,comparison.failures.join('; ')||'independent derived quantities matched'));
  }
  return result(metrics);
}

const BEHAVIOR_REVIEW_ID='benchmark:should-not-analyze';
const CLARIFICATION_REVIEW_ID='benchmark:clarification';
function activityFingerprint(messages,toolEvents=[],assistantEvents=[]) {return resultFingerprint({schemaVersion:1,messages,toolEvents,assistantEvents});}
function analysisActivity(messages,toolEvents=[]) {
  const names=[],unknown=[];
  const nonAnalysisTools=new Set(['ask_user_clarification','query_model','validate_model','review_input','query_results',
    'analyze_file','edit_model','extract_draft_params']);
  function add(name,fact) {if(typeof name==='string') names.push(name);else unknown.push(fact);}
  for(const message of messages) {
    const name=message.name??message.kwargs?.name;
    if(name!==undefined) add(name,message);
    for(const call of message.tool_calls??message.kwargs?.tool_calls??[]) add(call.name??call.function?.name,call);
    if((message.role==='tool'||message.type==='tool'||message.id?.at?.(-1)==='ToolMessage')&&name===undefined) unknown.push(message);
  }
  for(const event of toolEvents) {
    if(event.type==='step_upsert') add(event.step?.tool,event);
    else if(event.item?.type==='mcp_tool_call') add(event.item.tool,event);
    else if(event.type==='snapshot_messages'&&event.scope==='current'&&Array.isArray(event.messages)&&event.messages.every(record)) {
      const snapshot=analysisActivity(event.messages);
      if(snapshot.analyzed) names.push('run_analysis');
      if(snapshot.uncertain) unknown.push(event);
    }
    // These native Codex item types do not execute a solver. Arbitrary shell
    // commands and unrecognized events require review; never inspect stdout for
    // a candidate's own claim that execution did or did not happen.
    else if(!['file_change','web_search','image_view','todo_list'].includes(event.item?.type)) unknown.push(event);
  }
  return {analyzed:names.includes('run_analysis'),uncertain:unknown.length>0||names.some(name=>name!=='run_analysis'&&!nonAnalysisTools.has(name))};
}
function semanticAssessment(evidence,turn,current,outputId) {
  const activitySha256=activityFingerprint(current.messages,evidence.turnEvidence.toolEvents||[],evidence.turnEvidence.assistantEvents||[]);
  return (evidence.interactionEvidence||[]).find(item=>item.outputId===outputId&&item.turnId===turn.id&&
    item.state===turn.state&&item.sourceHash===evidence.sourceHash&&typeof item.pass==='boolean'&&
    item.activitySha256===activitySha256&&item.currentResponseSha256===evidence.turnEvidence.currentResponseSha256&&
    /^[a-f0-9]{64}$/.test(item.currentResponseSha256||''));
}
function clarificationQuestions(messages) {
  const questions=[];
  for(const message of messages) {
    for(const call of message.tool_calls??message.kwargs?.tool_calls??[]) if((call.name??call.function?.name)==='ask_user_clarification') {
      let args=call.args??call.function?.arguments;
      try {if(typeof args==='string') args=JSON.parse(args);} catch {continue;}
      if(typeof args?.question==='string') questions.push({question:args.question,field:args.field});
      if(Array.isArray(args?.questions)) questions.push(...args.questions.map(q=>typeof q==='string'?{question:q}:q));
    }
    if((message.name??message.kwargs?.name)==='extract_draft_params') {
      let content=message.content??message.kwargs?.content;
      try {if(typeof content==='string') content=JSON.parse(content);} catch {continue;}
      if(Array.isArray(content?.clarificationQuestions)) questions.push(...content.clarificationQuestions);
    }
  }
  return questions.filter(q=>typeof q?.question==='string'&&q.question.trim());
}
function assistantText(messages) {
  return messages.filter(m=>m.role==='assistant'||m.type==='ai'||m.id?.at?.(-1)==='AIMessage'||m._getType?.()==='ai').map(m=>{
    const content=m.content??m.kwargs?.content;
    return typeof content==='string'?content:Array.isArray(content)?content.filter(x=>x?.type==='text').map(x=>x.text).join('\n'):'';
  }).join('\n');
}
const DERIVED_REPORT_FORMAT='| derived | id | signedValue | unit | governingOperand or - | case:ID / combination:ID or - |';
/** Public current-answer protocol; no candidate pass flags are interpreted. */
function parseCurrentTurnReport(messages) {
  const markdown=assistantText(messages),derivedQuantities=[];
  const blocks=[...markdown.matchAll(/```json\s*\n?([\s\S]*?)```/g)].map(match=>match[1]);
  if(markdown.trim().startsWith('{')) blocks.push(markdown.trim());
  for(const block of blocks) {
    try {
      const parsed=JSON.parse(block);
      if(Array.isArray(parsed.derivedQuantities)) derivedQuantities.push(...parsed.derivedQuantities);
    } catch { /* A missing/unparseable required derived record fails comparison. */ }
  }
  const numeric=/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/;
  for(const line of markdown.split(/\r?\n/)) {
    if(!line.trim().startsWith('|')) continue;
    const row=line.trim().split('|').slice(1,-1).map(s=>s.trim());
    if(row[0]!=='derived') continue;
    const [kind,...id]=String(row[5]||'').split(':');
    derivedQuantities.push({id:row[1],value:numeric.test(row[2])?Number(row[2]):NaN,unit:row[3],
      governingOperand:row[4]==='-'?null:row[4],
      governingSelection:row[5]==='-'?null:{kind,id:id.join(':')}});
  }
  return {markdown,derivedQuantities};
}
function currentTurnReport(state,current,turnEvidence) {
  // reportHash must be recorded by the benchmark when a report is emitted in
  // this turn. Merely hashing a persisted report snapshot is not evidence.
  if(state.report&&turnEvidence.reportHash===resultFingerprint(state.report)) return state.report;
  return parseCurrentTurnReport(current.messages);
}
function compareClarification(turn,current,locale,evidence={},contract={}) {
  const questions=clarificationQuestions(current.messages),missing=turn.unresolvedFields||[],expected=turn.expectedQuestions||[];
  const normalize=value=>String(value||'').normalize('NFKC').replace(/[\s，。？！、,.?!:：;；]/g,'').toLocaleLowerCase(locale);
  const text=normalize([...questions.map(q=>q.question),assistantText(current.messages)].join('\n'));
  const exactQuestions=expected.length>0&&expected.every(question=>{
    const wording=typeof question==='string'?question:question.question;
    return wording&&text.includes(normalize(wording));
  });
  const fieldQuestions=questions.length>0&&missing.every(field=>questions.some(q=>q.field===field||q.fields?.includes(field)||q.question.includes(field)));
  let outputIds=(contract.requiredOutputs||[]).filter(o=>o.kind==='interaction'&&o.state===turn.state&&
    (!Array.isArray(turn.requiredOutputIds)||turn.requiredOutputIds.includes(o.id))&&(!Array.isArray(o.turnIds)||o.turnIds.includes(turn.id))).map(o=>o.id);
  if(!outputIds.length) outputIds=[CLARIFICATION_REVIEW_ID];
  const reviews=outputIds.map(id=>semanticAssessment(evidence,turn,current,id));
  const pending=Boolean(text)&&reviews.some(review=>!review),negative=reviews.find(review=>review?.pass===false);
  const pass=Boolean(text)&&reviews.every(review=>review?.pass===true);
  return {...metric('clarification',pass,negative?.reason||(pass?'independent assessment accepted the current clarification':
    pending?'current clarification requires an independent semantic assessment':'missing concrete current clarification for unresolved fields'),
    pending&&!negative?'review_pending':undefined),diagnostics:{exactQuestions,fieldQuestions},
    ...(pending&&!negative?{outputIds:outputIds.filter((_,index)=>!reviews[index])}:{} )};
}
function selectTurnRequirements(contract,turn,request) {
  const stateOutputs=(contract.requiredOutputs||[]).filter(o=>o.state===turn.state);
  if(turn.requiredOutputIds?.some(id=>!stateOutputs.some(o=>o.id===id))) throw Error('turn names a missing required output');
  let outputs=stateOutputs.filter(o=>(!Array.isArray(turn.requiredOutputIds)||turn.requiredOutputIds.includes(o.id))&&
    (!Array.isArray(o.turnIds)||o.turnIds.includes(turn.id)));
  const sharedState=contract.turns.filter(t=>t.state===turn.state&&t.expectation!=='clarify').length>1;
  if(sharedState&&!Array.isArray(turn.requiredOutputIds)&&!Array.isArray(turn.requiredQuantityIds)&&outputs.some(o=>!Array.isArray(o.turnIds)))
    throw Error('outputs for turns sharing a state need explicit current-turn selectors');
  const outputIds=new Set(outputs.flatMap(o=>o.quantityIds||[]));
  if(turn.requiredQuantityIds?.some(id=>!outputIds.has(id))) throw Error('requiredQuantityIds must belong to current required outputs');
  const ids=new Set(turn.requiredQuantityIds??outputIds);
  outputs=outputs.map(o=>({...o,quantityIds:(o.quantityIds||[]).filter(id=>ids.has(id))}))
    .filter(o=>o.quantityIds.length||['figure','interaction'].includes(o.kind));
  const all=new Set([...(request.quantities||[]),...(request.derived||[])].map(q=>q.id));
  for(const id of ids) if(!all.has(id)) throw Error(`turn quantity ${id} has no frozen request`);
  // Include independently frozen operands but do not demand intermediate output
  // rows unless this turn actually asks for them.
  let changed=true;
  while(changed) {
    changed=false;
    for(const d of request.derived||[]) if(ids.has(d.id)) for(const id of d.operands||[]) if(!ids.has(id)) {ids.add(id);changed=true;}
  }
  return {outputs,quantities:(request.quantities||[]).filter(q=>ids.has(q.id)),derived:(request.derived||[]).filter(d=>ids.has(d.id))};
}
function outputQuantity(quantity,turn) {
  const unit=turn.outputUnits?.[quantity.id]??turn.outputUnits?.[quantity.component]??quantity.unit;
  const factors={m:1,mm:.001,rad:1,kN:1,N:.001,'kN.m':1,'kN*m':1,'kN·m':1,'N.m':.001,'N*m':.001};
  if(!compatibleUnits[UNITS[quantity.component]]?.includes(unit)) throw Error('incompatible turn output unit');
  const factor=factors[quantity.unit]/factors[unit];
  return {...quantity,unit,value:quantity.value*factor,tolerance:{...quantity.tolerance,absolute:quantity.tolerance.absolute*factor},
    ...(quantity.engineeringPrecision?{engineeringPrecision:convertPrecision(quantity,unit,factor)}:{})};
}
function modelAt(record,state) {return Array.isArray(record.models)?record.models[state-1]:record.models?.[state]||record.models?.[record.contract.modelStates[state-1]];}

function evaluateResearchTurn({caseRecord,turnIndex=0,state,evidence={}}) {
  const contract=caseRecord?.contract,turn=contract?.turns?.[turnIndex];
  if(contract?.evaluationProfile!=='engineering-v2.3'||!turn||!state) return configuration('v2.3 case, exact turn and candidate state are required');
  let current;
  try {current=scopeTurnState(state,evidence.turnEvidence);} catch(error) {return configuration(error.message);}
  if(evidence.turnEvidence.turnId!==turn.id||evidence.turnEvidence.state!==turn.state) return configuration('turn evidence identity/state differs from contract');
  const policyError=require('./turn-policy.cjs').conditionalInferenceError(contract,turn);
  if(policyError)return configuration(policyError);
  const conditional=turn.expectation==='clarify-or-analyze';
  const activity=analysisActivity(current.messages,evidence.turnEvidence.toolEvents||[]);
  const analyzed=evidence.turnEvidence.analysisRunIds.length||activity.analyzed||current.analysisResult;
  if(turn.expectation==='clarify'||conditional&&!analyzed) {
    if(evidence.turnEvidence.analysisRunIds.length||activity.analyzed||current.analysisResult) {
      return result([metric('should_not_analyze',false,'current-turn analysis or analysis attempt preceded clarification')]);
    }
    const reviewed=activity.uncertain?semanticAssessment(evidence,turn,current,BEHAVIOR_REVIEW_ID):undefined;
    const behavior={...metric('should_not_analyze',!activity.uncertain||reviewed?.pass===true,reviewed?.reason||
      (activity.uncertain?'tool activity requires independent review to determine whether analysis was attempted':'no current-turn analysis activity'),
      activity.uncertain&&!reviewed?'review_pending':undefined),...(activity.uncertain&&!reviewed?{outputIds:[BEHAVIOR_REVIEW_ID]}:{})};
    if(reviewed?.pass===false) return result([behavior]);
    return result([behavior,compareClarification(turn,current,contract.locale,evidence,contract)]);
  }
  if(!['analyze','query','clarify-or-analyze'].includes(turn.expectation)) return configuration('unknown turn expectation');
  if(turn.clarificationBlocksAnalysis===false&&(turn.expectation!=='analyze'||!Number.isInteger(turn.state)||
    !turn.unresolvedFields?.length||turn.unresolvedFields.some(field=>!field.startsWith('/requestedOutputs/'))))
    return configuration('non-blocking clarification is restricted to output ambiguity with a known analyzed model state');
  const expectedModel=modelAt(caseRecord,turn.state),request=caseRecord.referenceRequests?.states?.find(s=>s.state===turn.state);
  const reference=caseRecord.reference?.states?.find(s=>s.state===turn.state);
  if(!request||!expectedModel) return configuration('frozen model or reference requests are missing for the selected state');
  if(!reference) return result([metric('reference_binding',false,'independent reference is missing',
    normalizeEngineKey(contract.plannedEngine)==='opensees'?'configuration_error':'native_truth_pending')]);
  if(normalizeEngineKey(contract.plannedEngine)!=='opensees'&&caseRecord.reference.notCommercialScoringTruth!==false)
    return result([metric('reference_binding',false,'commercial reference remains diagnostic','native_truth_pending')]);
  if(caseRecord.reference.toleranceFrozenBeforeCandidate!==true) return configuration('reference tolerances were not frozen before candidate execution');
  let requirements;
  try {requirements=selectTurnRequirements(contract,turn,request);} catch(error) {return configuration(error.message);}
  for(const q of requirements.quantities) {
    const rows=(reference.quantities||[]).filter(r=>r.id===q.id&&selectionKey(r.selection)===selectionKey(q.selection));
    if(rows.length!==1||!['selection','location','component','tolerance'].every(k=>isDeepStrictEqual(rows[0][k],q[k]))||
      unitSpelling(rows[0]?.unit)!==unitSpelling(q.unit))
      return configuration(`independent reference for requested quantity ${q.id} is missing or inconsistent`);
  }
  const quantities=requirements.quantities.map(q=>reference.quantities.find(r=>r.id===q.id&&selectionKey(r.selection)===selectionKey(q.selection)));
  const {derived,outputs}=requirements;
  const known=new Set([...quantities,...derived].map(q=>q.id));
  if(outputs.some(o=>['numerical','derived'].includes(o.kind)&&(!o.quantityIds?.length||o.quantityIds.some(id=>!known.has(id)))))
    return configuration('a required output has no independent quantity reference');
  if(outputs.some(o=>!['numerical','derived','figure','interaction'].includes(o.kind))) return configuration('unknown required output kind');
  if(outputs.some(o=>o.kind==='derived'&&o.quantityIds.some(id=>!derived.some(d=>d.id===id))))
    return configuration('a required derived output has no independent derivation');
  if(outputs.some(o=>o.kind==='numerical'&&o.quantityIds.some(id=>!quantities.some(q=>q.id===id))))
    return configuration('a required numerical output has no primitive quantity');
  const reportedDerivedIds=[...outputs.filter(o=>o.kind==='derived').flatMap(o=>o.quantityIds),
    ...(turn.requiredQuantityIds||[]).filter(id=>derived.some(d=>d.id===id))];
  let report=currentTurnReport(state,current,evidence.turnEvidence),cleanReportFailure,reportMappings;
  if(evidence.inputBinding?.inputEdition==='current') {
    const mapping=comparePhysicalModels(state.model,expectedModel,physicalOptions(contract.plannedEngine,contract.analysisConvention));
    if(mapping.pass)reportMappings={...mapping.diagnostics,model:state.model,
      ...identitySelections(expectedModel,state.model,state.analysisResult,mapping.diagnostics,contract.plannedEngine,true)};
    try {report=normalizeCleanReport(report,quantities,derived,reportedDerivedIds,state.model,{
      currentTurnId:turn.id,
      physicalMappingVerified:mapping.pass,
      endActionCompatibleMembers:mapping.pass?expectedModel.elements.filter(element=>{
        const segments=mapping.diagnostics.elementSegments[element.id];
        if(segments?.length!==1||segments[0].orientation!=='same')return false;
        const axes=axesFor(expectedModel,element);
        return axes.every((axis,i)=>axis.every((value,j)=>Math.abs(value-segments[0].localAxes[i][j])<=1e-10));
      }).map(element=>element.id):[],
      ...(mapping.pass?identitySelections(expectedModel,state.model,state.analysisResult,mapping.diagnostics,contract.plannedEngine,true):{}),
      equilibriumDifferenceIds:mapping.pass?equilibriumDifferenceIds(expectedModel,quantities,derived,turn.instruction):[],
      ...(mapping.pass?{nodeAliases:mapping.diagnostics.nodeMapping,elementAliases:mapping.diagnostics.elementMapping,
        elementSegments:mapping.diagnostics.elementSegments,caseAliases:mapping.diagnostics.caseMapping,
        combinationAliases:mapping.diagnostics.combinationMapping,publicNodeIds:expectedModel.nodes.map(n=>n.id),
        publicCaseIds:expectedModel.load_cases.map(c=>c.id),publicCombinationIds:expectedModel.load_combinations.map(c=>c.id)}:{}),
      priorTurnIds:contract.turns.slice(0,turnIndex).map(t=>t.id),
      priorResponsesByTurn:Object.fromEntries((evidence.turnEvidence.priorMessageRanges||[])
        .filter(r=>Number.isInteger(r.start)&&Number.isInteger(r.end)&&r.start>=0&&r.end>=r.start&&r.end<=evidence.turnEvidence.messageStartIndex)
        .map(r=>[r.turnId,(state.messages||[]).slice(r.start,r.end).filter(m=>m.role==='assistant'||m.type==='ai')
          .map(m=>typeof m.content==='string'?m.content:'')])),
      priorAssistantMessages:(state.messages||[]).slice(0,evidence.turnEvidence.messageStartIndex)
        .filter(m=>m.role==='assistant'||m.type==='ai').map(m=>typeof m.content==='string'?m.content:'')
    });}
    catch(error) {cleanReportFailure=error.message;}
  }
  const evaluated=evaluateBoundQuantities({...evidence,state,expectedModel,engineId:contract.plannedEngine,stateNumber:turn.state,quantities,derived,
    analysisConvention:contract.analysisConvention,
    requireCurrentTurn:turn.expectation!=='query',reportedDerived:report.derivedQuantities||[],
    reportedDerivedIds});
  if(['configuration_error','native_truth_pending'].includes(evaluated.status)) return evaluated;
  if(cleanReportFailure) evaluated.metrics.push(metric('clean_report_format',false,cleanReportFailure));
  if(turn.clarificationBlocksAnalysis===false) evaluated.metrics.push(compareClarification(turn,current,contract.locale,evidence,contract));
  for(const output of outputs) if(output.kind==='interaction') {
    const reviewed=semanticAssessment(evidence,turn,current,output.id);
    evaluated.metrics.push({...metric(`interaction:${output.id}`,reviewed?.pass===true,reviewed?.reason||'trusted semantic output assessment is missing',
      reviewed?undefined:'review_pending'),outputIds:[output.id]});
  }
  const renderedIds=new Set([...outputs.filter(o=>o.kind==='numerical').flatMap(o=>o.quantityIds),...(turn.requiredQuantityIds||[])]);
  let renderedQuantities;
  try {renderedQuantities=quantities.filter(q=>renderedIds.has(q.id)).map(q=>outputQuantity(q,turn));} catch(error) {return configuration(error.message);}
  if(renderedQuantities.length) {
    const equivalentUnitIds=evidence.inputBinding?.inputEdition==='current'?renderedQuantities
      .filter(q=>turn.outputUnits?.[q.id]===undefined&&turn.outputUnits?.[q.component]===undefined).map(q=>q.id):[];
    const verifiedNativeValues={};
    if(reportMappings&&evaluated.metrics.some(m=>m.metric==='requested_quantities'&&m.pass))
      for(const q of renderedQuantities)try {verifiedNativeValues[q.id]=readQuantity(state.analysisResult,q,reportMappings);}catch {}
    const rendered=compareReportQuantities(report,renderedQuantities,{equivalentUnitIds,verifiedNativeValues});
    evaluated.metrics.push({...metric('requested_output_body',rendered.pass,rendered.failures.join('; ')||'requested quantities rendered with exact case, location, sign and unit'),
      evidenceValid:rendered.evidenceValid,strictPass:rendered.strictPass,engineeringPass:rendered.engineeringPass,
      ...(rendered.reportRounding?{reportRounding:rendered.reportRounding}:{}),...(rendered.precision?{precision:rendered.precision}:{})});
  }
  for(const output of outputs) if(output.kind==='figure') {
    const bound=f=>{
      const ids=f.runIds===undefined?[f.runId]:f.runId===undefined&&Array.isArray(f.runIds)?f.runIds:[];
      return f.outputId===output.id&&f.state===turn.state&&f.sourceHash===evidence.sourceHash
        &&/^[a-f0-9]{64}$/i.test(f.sha256||'')&&f.decoded===true&&ids.length>0
        &&new Set(ids).size===ids.length&&ids.every(id=>typeof id==='string'&&id.trim()
          &&evaluated.metrics.some(m=>m.metric.startsWith('execution:')&&m.pass&&m.runId===id));
    };
    const supplied=(evidence.figureEvidence||[]).find(f=>Array.isArray(f.figures)
      ?f.outputId===output.id&&f.state===turn.state&&f.sourceHash===evidence.sourceHash&&f.decoded===true
        &&f.figures.length>1&&new Set(f.figures.map(m=>m.path)).size===f.figures.length
        &&f.figures.every(bound)&&f.sha256===figureSetFingerprint(f.figures)
      :bound(f));
    const assessment=semanticAssessment(evidence,turn,current,output.id);
    const reviewed=supplied&&assessment?.figureSha256===supplied.sha256?assessment:undefined;
    const decoded=(evidence.figureEvidence||[]).some(f=>f.outputId===output.id&&f.state===turn.state&&f.sourceHash===evidence.sourceHash&&f.decoded===true);
    evaluated.metrics.push({...metric(`figure:${output.id}`,Boolean(supplied)&&reviewed?.pass===true,
      !supplied?(decoded?'figure is decodable, but its complete current solver-run binding is unverified'
        :'required decodable figure is missing'):reviewed?.reason||'decoded figure requires independent content and consistency review',
      supplied&&!reviewed?'review_pending':undefined),...(supplied&&!reviewed?{outputIds:[output.id]}:{})});
  }
  return result(evaluated.metrics);
}
module.exports={evaluateBoundQuantities,evaluateResearchTurn,scopeTurnState,parseCurrentTurnReport,activityFingerprint,figureSetFingerprint,BEHAVIOR_REVIEW_ID,CLARIFICATION_REVIEW_ID,DERIVED_REPORT_FORMAT,EVALUATOR_VERSION,RESPONSE_CONTRACT_VERSION};
