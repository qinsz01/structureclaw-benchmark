/** Pure engineering-v2.3 evaluation. All trust inputs are supplied by the benchmark caller. */
const {isDeepStrictEqual}=require('node:util');
const {modelFingerprint,resultFingerprint,verifyExecutionEvidence}=require('./analysis-evidence.cjs');
const {comparePhysicalModels}=require('./physical-model-fidelity.cjs');
const {compareRequestedQuantities,compareReportQuantities,compareDerivedQuantities,evaluateDerivedQuantities,UNITS}=require('./requested-quantities.cjs');
const {selectAnalysisResult,selectionKey}=require('./result-selection.cjs');
const {normalizeEngineKey,verifyReferenceBinding}=require('./engine-ground-truth.cjs');
const {referenceAllowance,convertPrecision,validatePrecisionScope}=require('./reference-precision.cjs');
const record=x=>x&&typeof x==='object'&&!Array.isArray(x);
const compatibleUnits={m:['m','mm'],rad:['rad'],kN:['kN','N'],'kN.m':['kN.m','kN*m','kN·m','N.m','N*m']};
const unitSpelling=unit=>typeof unit==='string'?unit.replace(/[\*·]/g,'.'):unit;
const EVALUATOR_VERSION='research300-evaluator-v2';
const RESPONSE_CONTRACT_VERSION='research300-response-v1';
const metric=(name,pass,actual,status)=>({metric:name,pass,actual,...(status?{status}:{})});
function result(metrics) {
  const unavailable=metrics.find(m=>m.status==='configuration_error')||metrics.find(m=>m.status==='native_truth_pending');
  const pass=metrics.length>0&&metrics.every(m=>m.pass);
  return {evaluationProfile:'engineering-v2.3',evaluatorVersion:EVALUATOR_VERSION,responseContractVersion:RESPONSE_CONTRACT_VERSION,
    status:unavailable?.status||(pass?'pass':'agent_failure'),allPassed:pass,
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
  const runs=new Set(turnEvidence.analysisRunIds);
  let analysisResult=null;
  if(state.analysisResult?.results) {
    const results=Object.fromEntries(Object.entries(state.analysisResult.results).filter(([,r])=>runs.has(r?.meta?.runId)));
    if(Object.keys(results).length) analysisResult={results};
  } else if(runs.has(state.analysisResult?.meta?.runId)) analysisResult=state.analysisResult;
  return {...state,messages:(state.messages||[]).slice(turnEvidence.messageStartIndex),analysisResult,analysisAttempted:runs.size>0};
}

function evaluateBoundQuantities({state,expectedModel,engineId,stateNumber,quantities,derived=[],sourceHash,
  referenceEvidence,turnEvidence,artifactEvidence,requireCurrentTurn=true,reportedDerived,reportedDerivedIds}) {
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
  const physical=comparePhysicalModels(state.model,expectedModel,{coordinate:1e-8,property:1e-6,load:1e-6});
  const metrics=[metric('model_matches',physical.pass,physical.pass?physical.summary:physical.failures.join('; '))];
  if(!physical.pass) return result(metrics);
  const selections=new Map();
  for(const q of quantities) {
    const map=q.selection.kind==='case'?physical.diagnostics.caseMapping:physical.diagnostics.combinationMapping;
    const selection={...q.selection,id:map[q.selection.id]};
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
  const comparison=compareRequestedQuantities(state.analysisResult,quantities,physical.diagnostics);
  metrics.push({...metric('requested_quantities',comparison.pass,comparison.failures.join('; ')||`${comparison.comparedValues} quantities matched`),
    ...(comparison.precision?{precision:comparison.precision}:{})});
  if(derived.length) {
    const comparison=compareDerivedQuantities(state.analysisResult,quantities,derived,physical.diagnostics,reportedDerived,reportedDerivedIds);
    metrics.push(metric('derived_quantities',comparison.pass,comparison.failures.join('; ')||'independent derived quantities matched'));
  }
  return result(metrics);
}

function hasAnalysisCall(messages) {
  return messages.some(m=>(m.name??m.kwargs?.name)==='run_analysis'||(m.tool_calls??m.kwargs?.tool_calls??[])
    .some(t=>(t.name??t.function?.name)==='run_analysis'));
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
  const outputIds=(contract.requiredOutputs||[]).filter(o=>o.kind==='interaction'&&o.state===turn.state&&
    (!Array.isArray(turn.requiredOutputIds)||turn.requiredOutputIds.includes(o.id))&&(!Array.isArray(o.turnIds)||o.turnIds.includes(turn.id))).map(o=>o.id);
  const reviewed=(evidence.interactionEvidence||[]).find(item=>outputIds.includes(item.outputId)&&item.turnId===turn.id&&
    item.state===turn.state&&item.sourceHash===evidence.sourceHash&&typeof item.pass==='boolean');
  const pass=reviewed?reviewed.pass:exactQuestions||fieldQuestions;
  const pending=!pass&&!reviewed&&Boolean(text);
  return metric('clarification',pass,reviewed?.reason||(pass?'current clarification covers expected questions or unresolved fields':
    pending?'current paraphrase requires a trusted semantic assessment':'missing concrete current clarification for unresolved fields'),pending?'configuration_error':undefined);
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
  if(turn.expectation==='clarify') {
    const noRun=!evidence.turnEvidence.analysisRunIds.length&&!hasAnalysisCall(current.messages)&&!current.analysisResult;
    return result([metric('should_not_analyze',noRun,noRun?'no current-turn analysis':'current-turn analysis preceded clarification'),
      compareClarification(turn,current,contract.locale,evidence,contract)]);
  }
  if(!['analyze','query'].includes(turn.expectation)) return configuration('unknown turn expectation');
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
  const report=currentTurnReport(state,current,evidence.turnEvidence);
  const evaluated=evaluateBoundQuantities({...evidence,state,expectedModel,engineId:contract.plannedEngine,stateNumber:turn.state,quantities,derived,
    requireCurrentTurn:turn.expectation==='analyze',reportedDerived:report.derivedQuantities||[],
    reportedDerivedIds:[...outputs.filter(o=>o.kind==='derived').flatMap(o=>o.quantityIds),...(turn.requiredQuantityIds||[]).filter(id=>derived.some(d=>d.id===id))]});
  if(['configuration_error','native_truth_pending'].includes(evaluated.status)) return evaluated;
  if(turn.clarificationBlocksAnalysis===false) evaluated.metrics.push(compareClarification(turn,current,contract.locale,evidence,contract));
  for(const output of outputs) if(output.kind==='interaction') {
    const reviewed=(evidence.interactionEvidence||[]).find(item=>item.outputId===output.id&&item.turnId===turn.id&&
      item.state===turn.state&&item.sourceHash===evidence.sourceHash&&typeof item.pass==='boolean');
    evaluated.metrics.push(metric(`interaction:${output.id}`,reviewed?.pass===true,reviewed?.reason||'trusted semantic output assessment is missing',
      reviewed?undefined:'configuration_error'));
  }
  const renderedIds=new Set([...outputs.filter(o=>o.kind==='numerical').flatMap(o=>o.quantityIds),...(turn.requiredQuantityIds||[])]);
  let renderedQuantities;
  try {renderedQuantities=quantities.filter(q=>renderedIds.has(q.id)).map(q=>outputQuantity(q,turn));} catch(error) {return configuration(error.message);}
  if(renderedQuantities.length) {
    const rendered=compareReportQuantities(report,renderedQuantities);
    evaluated.metrics.push({...metric('requested_output_body',rendered.pass,rendered.failures.join('; ')||'requested quantities rendered with exact case, location, sign and unit'),
      ...(rendered.precision?{precision:rendered.precision}:{})});
  }
  for(const output of outputs) if(output.kind==='figure') {
    const supplied=(evidence.figureEvidence||[]).some(f=>f.outputId===output.id&&f.state===turn.state&&f.sourceHash===evidence.sourceHash&&
      /^[a-f0-9]{64}$/i.test(f.sha256||'')&&f.verified===true&&typeof f.runId==='string'&&
      evaluated.metrics.some(m=>m.metric.startsWith('execution:')&&m.pass&&m.runId===f.runId));
    evaluated.metrics.push(metric(`figure:${output.id}`,supplied,supplied?'verified figure artifact':'required figure artifact is missing'));
  }
  return result(evaluated.metrics);
}
module.exports={evaluateBoundQuantities,evaluateResearchTurn,scopeTurnState,parseCurrentTurnReport,DERIVED_REPORT_FORMAT,EVALUATOR_VERSION,RESPONSE_CONTRACT_VERSION};
