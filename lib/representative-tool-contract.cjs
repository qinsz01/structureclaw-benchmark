/** Developer acceptance helpers; frozen inputs and independent references stay unchanged. */
async function createNormalizedStateEdits(current, physical, normalize) {
  const targetModel = await normalize(physical);
  const edits = [];
  for (const collection of ['elements', 'materials', 'load_combinations']) {
    for (const target of targetModel[collection] || []) {
      const old = current[collection].find(row => row.id === target.id);
      const values = Object.fromEntries(Object.entries(target).filter(([key, value]) =>
        key !== 'id' && JSON.stringify(value) !== JSON.stringify(old?.[key])));
      if (Object.keys(values).length) edits.push({operation: 'update', collection, id: target.id, values});
    }
  }
  for (const loadCase of targetModel.load_cases) {
    for (const target of loadCase.loads) {
      const old = current.load_cases.find(row => row.id === loadCase.id)?.loads.find(row => row.id === target.id);
      if (!old) edits.push({operation: 'add', collection: 'loads', caseId: loadCase.id, id: target.id, values: target});
      else {
        const values = Object.fromEntries(Object.entries(target).filter(([key, value]) =>
          key !== 'id' && JSON.stringify(value) !== JSON.stringify(old[key])));
        if (Object.keys(values).length) edits.push({operation: 'update', collection: 'loads', caseId: loadCase.id, id: target.id, values});
      }
    }
  }
  return edits;
}

/** A free rotation at a joint connected only to axial bars is not a physical response.
 * Identify this from the independent model, never from a candidate's missing output.
 * Keep every frozen quantity in the numerical comparison; only exclude these exact
 * zero placeholders from the engineering query/report contract and disclose them.
 */
function partitionRepresentativeQueries(model, quantities) {
  const queryable = [], notApplicable = [];
  for (const quantity of quantities) {
    const index = ['rx', 'ry', 'rz'].indexOf(quantity.component);
    const node = quantity.location.kind === 'node' && model.nodes.find(row => row.id === quantity.location.id);
    const connected = node ? model.elements.filter(row => row.nodes.includes(node.id)) : [];
    const freeTrussRotation = index >= 0 && node && node.restraints?.[index + 3] !== true
      && connected.length > 0 && connected.every(row => row.type === 'truss');
    if (!freeTrussRotation) { queryable.push(quantity); continue; }
    if (quantity.value !== 0) throw Error(`${quantity.id}: nonzero reference for undetermined free truss rotation`);
    notApplicable.push({...quantity, reason: 'undetermined-free-truss-rotation', referenceRole: 'zero-placeholder-not-physical-response'});
  }
  return {queryable, notApplicable};
}

async function verifyUnavailableRotationQuery(quantity, data, query) {
  if (data?.nodalResponseAvailability?.[quantity.location.id]?.[quantity.component] !== false) {
    throw Error(`${quantity.id}: free truss rotation must be explicitly marked unavailable`);
  }
  try { await query(); }
  catch (error) {
    if (error.message === 'NODE_DOF_RESPONSE_UNAVAILABLE') return {...quantity, publicQuery: 'correctly-rejected'};
    throw error;
  }
  throw Error(`${quantity.id}: public query exposed an undetermined rotation as a physical response`);
}
module.exports = {createNormalizedStateEdits, partitionRepresentativeQueries, verifyUnavailableRotationQuery};
