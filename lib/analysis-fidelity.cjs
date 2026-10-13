const {selectAnalysisResult}=require('./result-selection.cjs');

function finiteNumber(value) {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function resultData(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return {};
  const data = value.data;
  if (data && typeof data === "object" && !Array.isArray(data)) {
    const keys = ["displacements", "nodeDisplacements", "reactions", "nodeReactions", "forces", "memberForces"];
    if (keys.some((key) => data[key] !== undefined)) return data;
  }
  return value;
}

function normalizeResponseCoordinates(result) {
  if (result?.analysisMode !== "opensees_2d_frame") {
    return result;
  }
  const normalized = { ...result, responseCoordinateConvention: "global-xyz" };
  for (const alias of result.responseCoordinateConvention === 'global-xyz' ? [] : ["displacements", "nodeDisplacements"]) {
    const values = result[alias];
    if (!values || typeof values !== "object" || Array.isArray(values)) continue;
    normalized[alias] = Object.fromEntries(Object.entries(values).map(([nodeId, value]) => [
      nodeId,
      value && typeof value === "object" && !Array.isArray(value)
        ? { ...value, ry: finiteNumber(value.ry) === null ? value.ry : -value.ry }
        : value,
    ]));
  }
  for (const alias of result.responseCoordinateConvention === 'global-xyz' ? [] : ["reactions", "nodeReactions"]) {
    const values = result[alias];
    if (!values || typeof values !== "object" || Array.isArray(values)) continue;
    normalized[alias] = Object.fromEntries(Object.entries(values).map(([nodeId, value]) => [
      nodeId,
      value && typeof value === "object" && !Array.isArray(value)
        ? { ...value, my: finiteNumber(value.my) === null ? value.my : -value.my }
        : value,
    ]));
  }
  if(result.forces) normalized.forces=Object.fromEntries(Object.entries(result.forces).map(([id,force])=>{
    // Frozen fixtures already corrected global Ry/My but retained raw planar local M.
    // The full V2/V3/M2/M3 end-action schema distinguishes the canonical new output.
    if(!force.n1||!force.n2||force.n1.M2!==undefined) return [id,force];
    const convert=end=>({...end,M:finiteNumber(end.M)===null?end.M:-end.M,
      V2:0,V3:end.V,T:0,M2:finiteNumber(end.M)===null?end.M:-end.M,M3:0});
    return [id,{...force,n1:convert(force.n1),n2:convert(force.n2)}];
  }));
  return normalized;
}

function collection(result, aliases) {
  for (const alias of aliases) {
    const value = result?.[alias];
    if (value && typeof value === "object" && !Array.isArray(value)) return value;
  }
  return {};
}

function compareAnalysisResults(actualInput, expectedInput, mappings, tolerances = {}) {
  let actual,expected;
  try {
    actual=normalizeResponseCoordinates(resultData(selectAnalysisResult(actualInput,tolerances.selection,
      {allowLegacyUnboundResult:!!tolerances.allowLegacyUnboundResult}).data));
    expected=normalizeResponseCoordinates(resultData(selectAnalysisResult(expectedInput,tolerances.expectedSelection,
      {allowLegacyUnboundResult:true}).data));
  } catch(error) {
    return {pass:false,comparedValues:0,failures:[error.message],maxAbsoluteDifference:0,maxRelativeDifference:0,
      tolerances:{absolute:tolerances.numericAbsolute??1e-8,relative:tolerances.numeric??.05}};
  }
  const relativeTolerance = tolerances.numeric ?? tolerances.relative ?? 0.05;
  const absoluteTolerance = tolerances.numericAbsolute ?? tolerances.absolute ?? 1e-8;
  const failures = [];
  let comparedValues = 0;
  let maxAbsoluteDifference = 0;
  let maxRelativeDifference = 0;

  function compareNumber(actualValue, expectedValue, path) {
    let actualNumber = finiteNumber(actualValue);
    let expectedNumber = finiteNumber(expectedValue);
    if (actualNumber === null || expectedNumber === null) {
      failures.push(`${path}: missing finite numeric value`);
      return;
    }
    comparedValues += 1;
    const absoluteDifference = Math.abs(actualNumber - expectedNumber);
    const expectedIsNearZero = Math.abs(expectedNumber) <= absoluteTolerance;
    const relativeDifference = expectedIsNearZero
      ? 0
      : absoluteDifference / Math.abs(expectedNumber);
    maxAbsoluteDifference = Math.max(maxAbsoluteDifference, absoluteDifference);
    maxRelativeDifference = Math.max(maxRelativeDifference, relativeDifference);
    if (
      (expectedIsNearZero && absoluteDifference > absoluteTolerance)
      || (!expectedIsNearZero
        && absoluteDifference > absoluteTolerance
        && relativeDifference > relativeTolerance)
    ) {
      failures.push(`${path}: ${actualNumber} vs ${expectedNumber}`);
    }
  }

  function compareNodeCollection(expectedAliases, actualAliases, label) {
    const expectedCollection = collection(expected, expectedAliases);
    const actualCollection = collection(actual, actualAliases);
    for (const [expectedNodeId, expectedValues] of Object.entries(expectedCollection)) {
      const actualNodeId = mappings.nodeMapping?.[expectedNodeId];
      const actualValues = actualNodeId === undefined ? null : actualCollection[actualNodeId];
      if (!actualValues || typeof actualValues !== "object") {
        failures.push(`${label}.${expectedNodeId}: missing mapped result`);
        continue;
      }
      for (const [component, expectedValue] of Object.entries(expectedValues)) {
        if (finiteNumber(expectedValue) !== null) {
          compareNumber(actualValues[component], expectedValue, `${label}.${expectedNodeId}.${component}`);
        }
      }
    }
  }

  compareNodeCollection(["displacements", "nodeDisplacements"], ["displacements", "nodeDisplacements"], "displacements");
  compareNodeCollection(["reactions", "nodeReactions"], ["reactions", "nodeReactions"], "reactions");

  const expectedForces = collection(expected, ["forces", "memberForces"]);
  const actualForces = collection(actual, ["forces", "memberForces"]);
  function projectedEnds(expectedId, force) {
    const expectedAxes=force.localAxes?['x','y','z'].map(k=>force.localAxes[k]):mappings.physicalAxes?.[expectedId];
    const segments=mappings.elementSegments?.[expectedId];
    if(!expectedAxes||!segments?.length) return null;
    const result=[];
    for(const [record,isFirst] of [[segments[0],true],[segments.at(-1),false]]) {
      const segmentForce=actualForces[record.id];
      if(!segmentForce) return null;
      const same=record.orientation==='same';
      const end=segmentForce[isFirst===same?'n1':'n2'];
      if(!end) return null;
      const axes=segmentForce.localAxes?['x','y','z'].map(k=>segmentForce.localAxes[k]):record.localAxes;
      if(!axes) return null;
      const vector=keys=>{
        const values=keys.map(k=>finiteNumber(end[k]));
        if(values.some(v=>v===null)) return null;
        const global=[0,1,2].map(i=>values.reduce((sum,v,j)=>sum+v*axes[j][i],0));
        return expectedAxes.map(axis=>axis.reduce((sum,v,i)=>sum+v*global[i],0));
      };
      // Axial-only trusses are invariant under orientation when reported tension-positive.
      if(finiteNumber(end.N)!==null&&end.V2===undefined&&end.V3===undefined) {
        const sign=expectedAxes[0].reduce((sum,v,i)=>sum+v*axes[0][i],0);
        result.push({N:end.N*sign});continue;
      }
      const f=vector(['N','V2','V3']),m=vector(['T','M2','M3']);
      if(!f||!m) return null;
      const planar=String(expected.analysisMode||'').includes('_2d_');
      result.push({N:f[0],V2:f[1],V3:f[2],T:m[0],M2:m[1],M3:m[2],
        V:planar?f[2]:Math.hypot(f[1],f[2]),M:planar?m[1]:Math.hypot(m[1],m[2])});
    }
    return result;
  }
  for (const [expectedElementId, expectedForce] of Object.entries(expectedForces)) {
    const actualElementId = mappings.elementMapping?.[expectedElementId];
    const actualForce = actualElementId === undefined ? null : actualForces[actualElementId];
    if (!actualForce || typeof actualForce !== "object") {
      failures.push(`forces.${expectedElementId}: missing mapped result`);
      continue;
    }
    for (const component of expectedForce.n1 ? [] : ["axial", "stress"] ) {
      if (finiteNumber(expectedForce[component]) !== null) {
        compareNumber(actualForce[component], expectedForce[component], `forces.${expectedElementId}.${component}`);
      }
    }
    const expectedEnds = [expectedForce.n1, expectedForce.n2];
    const physicalEnds=projectedEnds(expectedElementId,expectedForce);
    if (mappings.elementSegments?.[expectedElementId]?.length > 1 && !physicalEnds && expectedEnds.some(Boolean)) {
      failures.push(`forces.${expectedElementId}: refined member lacks complete physical endpoint evidence`);
      continue;
    }
    let actualEnds = physicalEnds || [actualForce.n1, actualForce.n2];
    if (expectedEnds.some((end) => end && typeof end === "object")) {
      if (!actualEnds.every((end) => end && typeof end === "object")) {
        failures.push(`forces.${expectedElementId}: missing end-force results`);
        continue;
      }
      const components = new Set(expectedEnds.flatMap((end) => Object.keys(end || {})));
      if (!physicalEnds && mappings.elementOrientation?.[expectedElementId] === "reversed") {
        const hasVectorComponents = components.has("V2") || components.has("V3")
          || components.has("M2") || components.has("M3");
        const reversedSign = (component) => {
          if (["N", "V2", "T", "M2"].includes(component)) return -1;
          if (component === "V" && !hasVectorComponents) return -1;
          return 1;
        };
        actualEnds = [actualEnds[1], actualEnds[0]].map((end) => Object.fromEntries(
          Object.entries(end).map(([component, value]) => [
            component,
            finiteNumber(value) === null ? value : value * reversedSign(component),
          ]),
        ));
      }
      for (const component of components) {
        const expectedPair = expectedEnds.map((end) => finiteNumber(end?.[component]));
        const actualPair = actualEnds.map((end) => finiteNumber(end?.[component]));
        if (expectedPair.some((value) => value === null)) continue;
        if (actualPair.some((value) => value === null)) {
          failures.push(`forces.${expectedElementId}.${component}: missing endpoint value`);
          continue;
        }
        compareNumber(actualPair[0], expectedPair[0], `forces.${expectedElementId}.${component}.n1`);
        compareNumber(actualPair[1], expectedPair[1], `forces.${expectedElementId}.${component}.n2`);
      }
    }
  }

  if (comparedValues === 0) failures.push("no comparable numerical response values");
  return {
    pass: failures.length === 0,
    comparedValues,
    maxAbsoluteDifference,
    maxRelativeDifference,
    tolerances: { absolute: absoluteTolerance, relative: relativeTolerance },
    failures,
  };
}

module.exports = { compareAnalysisResults };
