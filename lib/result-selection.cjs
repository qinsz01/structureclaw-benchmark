/** Select one identified result; never use the first/default case of a result set. */
const record=value=>value&&typeof value==='object'&&!Array.isArray(value)?value:null;
function selectionKey(selection) {
  if(typeof selection==='string') return selection;
  return selection?.kind&&selection?.id?`${selection.kind}:${selection.id}`:null;
}
function declaredKey(value) {
  if(value?.selection) return selectionKey(value.selection);
  const data=record(value?.data)||value;
  const parameters=value?.meta?.effectiveParameters||data?.meta?.effectiveParameters||data?.execution||{};
  if(parameters.loadCombinationId) return `combination:${parameters.loadCombinationId}`;
  if(Array.isArray(parameters.loadCaseIds)&&parameters.loadCaseIds.length===1) return `case:${parameters.loadCaseIds[0]}`;
  return null;
}
function selectAnalysisResult(input,selection,options={}) {
  const key=selectionKey(selection);
  const sets=record(input?.results)||record(input?.data?.results);
  let chosen=input;
  if(sets) {
    if(!key) {
      const keys=Object.keys(sets);
      if(keys.length!==1) throw Error('A multi-case result requires an explicit case/combination selection');
      chosen=sets[keys[0]];
    } else {
      if(!sets[key]) throw Error(`Required result ${key} is missing`);
      chosen=sets[key];
    }
  }
  const data=record(chosen?.data)||chosen;
  for(const value of [chosen,data]) {
    if(!record(value)) throw Error('Analysis result is not an object');
    if(value.success===false||['error','failed','failure','partial','preliminary','unsupported','rejected'].includes(value.status))
      throw Error('Selected analysis is unsuccessful or incomplete');
    if(value.capabilityStatus&&value.capabilityStatus!=='complete') throw Error('Selected result capability is incomplete');
  }
  const binding=declaredKey(chosen);
  if(key&&!sets&&binding!==key&&!options.allowLegacyUnboundResult) throw Error(`Result is not bound to required ${key}`);
  if(key&&binding&&binding!==key) throw Error(`Result selection ${binding} differs from required ${key}`);
  return {record:chosen,data,key:key||binding};
}
module.exports={selectAnalysisResult,selectionKey};
