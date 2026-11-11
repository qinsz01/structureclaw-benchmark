const ENGINE_KEYS = {
  "builtin-opensees": "opensees",
  "builtin-pkpm": "pkpm",
  "builtin-yjk": "yjk",
  opensees: "opensees",
  openseespy: "opensees",
  pkpm: "pkpm",
  yjk: "yjk",
};

function normalizeEngineKey(value) {
  return ENGINE_KEYS[String(value || "").toLowerCase()] || null;
}

function findEngineGroundTruth(payload, modelId, engineId) {
  const engine = normalizeEngineKey(engineId);
  if (!engine || engine === "opensees") return null;
  const entry = (payload?.cases || []).find(
    (candidate) => candidate?.provenance?.sourceModelId === modelId,
  );
  const truth = entry?.engines?.[engine];
  return truth ? { engine, entry, truth } : null;
}

/** Reference availability is benchmark configuration, never an agent error. */
function verifyReferenceBinding({referenceEvidence,engineId,state,modelHash,sourceHash}) {
  const engine=normalizeEngineKey(engineId), failures=[];
  if(!engine) failures.push('explicit target engine is missing or unknown');
  if(!Number.isInteger(state)||state<1) failures.push('exact reference state is missing');
  if(!/^[a-f0-9]{64}$/i.test(sourceHash||'')) failures.push('frozen source hash is missing');
  if(failures.length) return {pass:false,status:'configuration_error',failures};
  if(!referenceEvidence) return {pass:false,status:engine==='opensees'?'configuration_error':'native_truth_pending',
    failures:['independently validated same-engine reference is missing']};
  if(normalizeEngineKey(referenceEvidence.engineId)!==engine) failures.push('reference engine differs from target engine');
  if(referenceEvidence.state!==state) failures.push('reference belongs to a different state');
  if(referenceEvidence.modelHash!==modelHash) failures.push('reference is not bound to the frozen expected model');
  if(referenceEvidence.sourceHash!==sourceHash) failures.push('reference source binding differs from frozen source');
  if(engine!=='opensees'&&referenceEvidence.status!=='native-verified') return {pass:false,status:'native_truth_pending',
    failures:[...failures,'commercial same-engine native reference is pending independent verification']};
  if(!['validated','native-verified'].includes(referenceEvidence.status)) failures.push('reference validation is pending');
  return {pass:!failures.length,status:failures.length?'configuration_error':'ready',failures};
}

module.exports = { findEngineGroundTruth, normalizeEngineKey, verifyReferenceBinding };
