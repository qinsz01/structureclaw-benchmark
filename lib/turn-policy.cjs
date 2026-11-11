'use strict';

// This permission belongs to the frozen author contract, never to candidate
// text. Both paths retain a response-bound semantic review; analysis also
// retains the full current native execution/model/numeric/report gates.
function conditionalInferenceError(contract,turn) {
  if(turn.expectation!=='clarify-or-analyze')return null;
  if(!Number.isInteger(turn.state)||turn.state<1||!contract.modelStates?.[turn.state-1]
    ||typeof turn.clarificationPolicy!=='string'||!turn.clarificationPolicy.trim()
    ||!turn.unresolvedFields?.length||!turn.expectedQuestions?.length||turn.changedFields?.length)
    return 'clarify-or-analyze requires a known state, authored clarificationPolicy, unresolvedFields and expectedQuestions, without edits';
  const outputs=(contract.requiredOutputs||[]).filter(o=>o.state===turn.state&&o.turnIds?.includes(turn.id)
    &&(!turn.requiredOutputIds||turn.requiredOutputIds.includes(o.id)));
  if(!outputs.some(o=>o.kind==='interaction')||!outputs.some(o=>o.kind==='numerical'&&o.quantityIds?.length))
    return 'clarify-or-analyze requires explicitly turn-bound interaction review and numerical outputs';
  return null;
}
module.exports={conditionalInferenceError};
