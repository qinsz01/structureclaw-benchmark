const { sha256 } = require("./numerical-ground-truth.cjs");
const {COMPONENTS,axes,requireNativeStations,readNativeStation,validateStationRows,samePosition}=require('./commercial-stations.cjs');

const ENGINE_ORDER = ["opensees", "pkpm", "yjk"];

function finite(value) {
  if (value === null || value === undefined || value === "") return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function maximum(values) {
  const valid = values.map(finite).filter((value) => value !== null);
  return valid.length > 0 ? Math.max(...valid) : null;
}

function caseSelection(engine, result, requestedKey, options = {}) {
  if (engine === "opensees") return { key: "selected", result };
  const selection=options.selection||(!requestedKey&&!options.legacyDeadLoad?result?.selectedResult:undefined);
  if(selection&&(!['case','combination'].includes(selection.kind)||typeof selection.id!=='string'||!selection.id))
    throw Error(`${engine}: an exact case/combination selection is required`);
  if(selection&&requestedKey&&requestedKey!==selection.id) throw Error(`${engine}: conflicting requested case/combination IDs`);
  if(selection?.kind==='combination') {
    const value=result?.combinationResults?.[selection.id];
    if(!value) throw Error(`${engine}: requested combination '${selection.id}' is unavailable`);
    return {key:selection.id,kind:'combination',result:value};
  }
  if(selection?.kind==='case') requestedKey=selection.id;
  const cases = result?.caseResults;
  if (!cases || typeof cases !== "object") {
    throw new Error(`${engine}: per-load-case results are required`);
  }
  if(requestedKey) {
    if(!cases[requestedKey]) throw new Error(`${engine}: requested case '${requestedKey}' is unavailable`);
    return {key:requestedKey,result:cases[requestedKey]};
  }
  if(!options.legacyDeadLoad) {
    const keys=Object.keys(cases);
    if(keys.length!==1) throw new Error(`${engine}: an explicit load case is required; no DL default is used`);
    return {key:keys[0],result:cases[keys[0]]};
  }
  if (engine === "pkpm") {
    if (!cases.DL) throw new Error("pkpm: DL result is unavailable");
    return { key: "DL", result: cases.DL };
  }
  const descriptors = result?.summary?.load_cases || [];
  const dead = descriptors.find((item) => item?.kind === 1)
    || descriptors.find((item) => /(^|\b)DL(\b|$)|恒载/i.test(String(item?.name || item?.expName || "")));
  const key = String(dead?.key || (dead?.id !== undefined ? `lc_${dead.id}` : "lc_1"));
  if (!cases[key]) throw new Error(`yjk: dead-load result '${key}' is unavailable`);
  return { key, result: cases[key] };
}

function forceMetrics(engine, force) {
  if (!force || typeof force !== "object") return null;
  if (engine === "opensees") {
    const ends = [force.n1, force.n2].filter(Boolean);
    return {
      axial: maximum([force.axial, ...ends.map((item) => Math.abs(finite(item.N) || 0))]),
      shear: maximum(ends.map((item) => Math.abs(finite(item.V) || 0))),
      moment: maximum(ends.map((item) => Math.abs(finite(item.M) || 0))),
    };
  }
  return {
    axial: finite(force.N) === null ? null : Math.abs(Number(force.N)),
    shear: finite(force.V) === null ? null : Math.abs(Number(force.V)),
    moment: finite(force.M) === null ? null : Math.abs(Number(force.M)),
  };
}

function modelIndex(model) {
  const nodes = new Map((model.nodes || []).map((node) => [String(node.id), node]));
  const baseZ = Math.min(...[...nodes.values()].map((node) => Number(node.z || 0)));
  const bottomColumns = new Set();
  const columns = new Set();
  const beams = new Set();
  for (const element of model.elements || []) {
    const id = String(element.id);
    if (element.type === "beam") beams.add(id);
    if (element.type !== "column") continue;
    columns.add(id);
    const endNodes = (element.nodes || []).map((nodeId) => nodes.get(String(nodeId))).filter(Boolean);
    if (endNodes.some((node) => Math.abs(Number(node.z || 0) - baseZ) <= 1e-9)) {
      bottomColumns.add(id);
    }
  }
  const baseNodes = new Set(
    [...nodes.entries()]
      .filter(([, node]) => Math.abs(Number(node.z || 0) - baseZ) <= 1e-9)
      .map(([id]) => id),
  );
  return { baseNodes, beams, bottomColumns, columns };
}

const DISPLACEMENT_COMPONENTS = ["ux", "uy", "uz", "rx", "ry", "rz"];
const REACTION_COMPONENTS = ["fx", "fy", "fz", "mx", "my", "mz", "R"];
const COMMERCIAL_FORCE_COMPONENTS = ["N", "V", "M", "Vy", "Vz", "My", "Mz", "T"];

function normalizeComponents(collection, components, label) {
  return Object.fromEntries(Object.entries(collection || {}).map(([id, raw]) => {
    const values = {};
    for (const component of components) {
      if (raw?.[component] === undefined) continue;
      const value = finite(raw[component]);
      if (value === null) throw new Error(`${label}.${id}.${component}: finite value is required`);
      values[component] = value;
    }
    if (Object.keys(values).length === 0) throw new Error(`${label}.${id}: no numeric components`);
    return [String(id), values];
  }));
}

function sameIds(actual, expected) {
  const left = [...actual].map(String).sort();
  const right = [...expected].map(String).sort();
  return JSON.stringify(left) === JSON.stringify(right);
}

function normalizeCommercialEngineResponse(engine, model, rawResult, options = {}) {
  if (!["pkpm", "yjk"].includes(engine)) throw new Error(`Unsupported commercial engine '${engine}'`);
  if (rawResult?.status !== "success") throw new Error(`${engine}: analysis did not succeed`);
  const selected = caseSelection(engine, rawResult, options.caseKey, options);
  if (selected.result?.status && selected.result.status !== "success") {
    throw new Error(`${engine}: selected load case did not succeed`);
  }
  if(selected.result?.memberStations) {
    const data=selected.result;
    requireNativeStations(data);
    if(data.nativeContext.engine!==engine) throw Error(`${engine}: native engine identity differs from the requested engine`);
    const units={displacement:'m',rotation:'rad',force:'kN',moment:'kN.m'};
    if(Object.entries(units).some(([key,value])=>data.units?.[key]!==value)) throw Error(`${engine}: explicit canonical native units required`);
    const nodes=new Map(model.nodes.map(node=>[String(node.id),node]));
    const supports=model.nodes.filter(node=>node.restraints?.some(Boolean)).map(node=>String(node.id));
    const take=(source,ids,components,label)=>Object.fromEntries(ids.map(id=>{
      const row=source?.[id];
      if(components.some(key=>typeof row?.[key]!=='number'||!Number.isFinite(row[key]))) throw Error(`${engine}: complete ${label}.${id} required`);
      return [id,Object.fromEntries(components.map(key=>[key,row[key]]))];
    }));
    const memberLengths={},memberStations={};
    for(const element of model.elements) {
      const [a,b]=element.nodes.map(id=>nodes.get(String(id)));
      const length=Math.hypot(b.x-a.x,b.y-a.y,b.z-a.z),rows=data.memberStations[element.id];
      if(!Array.isArray(rows)||rows.length<2) throw Error(`${engine}: native stations missing for ${element.id}`);
      validateStationRows(rows);
      memberLengths[element.id]=length;
      memberStations[element.id]=rows.map(row=>{
        axes(row.localAxes);
        if(typeof row.positionM!=='number'||!Number.isFinite(row.positionM)||row.positionM<0||(row.positionM>length&&!samePosition(row.positionM,length))
          ||!['left','right','continuous'].includes(row.side)||row.referenceFrame!=='element-local'
          ||COMPONENTS.some(key=>typeof row.components?.[key]!=='number'||!Number.isFinite(row.components[key]))) throw Error(`${engine}: invalid signed station ${element.id}`);
        const x=[(b.x-a.x)/length,(b.y-a.y)/length,(b.z-a.z)/length];
        if(row.localAxes[0].some((v,i)=>Math.abs(v-x[i])>1e-9)) throw Error(`${engine}: station axis differs from physical member ${element.id}`);
        return {positionM:row.positionM,side:row.side,referenceFrame:row.referenceFrame,
          localAxes:row.localAxes.map(axis=>[...axis]),components:{...row.components}};
      });
      for(const [x,side] of [[0,'right'],[length,'left']]) readNativeStation({memberStations},element.id,x,side);
    }
    return {format:'signed-stations-v1',caseKey:selected.key,selection:{kind:selected.kind||'case',id:selected.key},units,
      displacements:take(data.displacements,[...nodes.keys()],DISPLACEMENT_COMPONENTS,'displacements'),
      reactions:take(data.reactions,supports,REACTION_COMPONENTS.filter(k=>k!=='R'),'reactions'),
      memberLengths,memberStations};
  }
  const index = modelIndex(model);
  const nodeIds = new Set((model.nodes || []).map((node) => String(node.id)));
  const elementIds = new Set((model.elements || []).map((element) => String(element.id)));
  const expectedDisplacements = engine === "pkpm"
    ? new Set([...nodeIds].filter((id) => !index.baseNodes.has(id)))
    : nodeIds;
  const expectedReactions = engine === "pkpm" ? new Set() : nodeIds;
  const displacements = normalizeComponents(
    selected.result?.displacements,
    DISPLACEMENT_COMPONENTS,
    `${engine}.displacements`,
  );
  const reactions = normalizeComponents(
    selected.result?.reactions,
    REACTION_COMPONENTS,
    `${engine}.reactions`,
  );
  const forces = normalizeComponents(
    selected.result?.forces,
    COMMERCIAL_FORCE_COMPONENTS,
    `${engine}.forces`,
  );
  for (const [label, actual, expected] of [
    ["displacements", new Set(Object.keys(displacements)), expectedDisplacements],
    ["reactions", new Set(Object.keys(reactions)), expectedReactions],
    ["forces", new Set(Object.keys(forces)), elementIds],
  ]) {
    if (!sameIds(actual, expected)) {
      throw new Error(`${engine}: ${label} do not exactly cover the expected model entities`);
    }
  }
  return {
    caseKey: selected.key,
    units: { displacement: "m", force: "kN", moment: "kN.m" },
    unavailable: engine === "pkpm" ? ["reactions"] : [],
    displacements,
    reactions,
    forces,
  };
}

function compareCommercialEngineResponses(actual, expected, mappings, tolerances = {}) {
  const relativeTolerance = tolerances.numeric ?? tolerances.relative ?? 0.01;
  const absoluteTolerance = tolerances.numericAbsolute ?? tolerances.absolute ?? 1e-8;
  const failures = [];
  let comparedValues = 0;
  let maxAbsoluteDifference = 0;
  let maxRelativeDifference = 0;
  function compareNumber(actualValue, expectedValue, path) {
    let left = finite(actualValue);
    let right = finite(expectedValue);
    if (left === null || right === null) {
      failures.push(`${path}: missing finite value`);
      return;
    }
    comparedValues += 1;
    const absoluteDifference = Math.abs(left - right);
    const relative = relativeDifference(left, right, absoluteTolerance);
    maxAbsoluteDifference = Math.max(maxAbsoluteDifference, absoluteDifference);
    maxRelativeDifference = Math.max(maxRelativeDifference, relative);
    if (absoluteDifference > absoluteTolerance && relative > relativeTolerance) {
      failures.push(`${path}: ${left} vs ${right}`);
    }
  }
  function compareCollection(name, mapping) {
    const expectedCollection = expected?.[name] || {};
    const actualCollection = actual?.[name] || {};
    const expectedIds = Object.keys(expectedCollection);
    const mappedIds = expectedIds.map((id) => String(mapping?.[id] ?? id));
    const comparableIds=Object.keys(actualCollection).filter(id=>name!=='displacements'||!mappings?.interiors?.[id]);
    if (!sameIds(new Set(mappedIds), new Set(comparableIds))) {
      failures.push(`${name}: result entity coverage mismatch`);
    }
    for (const expectedId of expectedIds) {
      const actualId = String(mapping?.[expectedId] ?? expectedId);
      const expectedValues = expectedCollection[expectedId];
      const actualValues = actualCollection[actualId];
      if (!actualValues) {
        failures.push(`${name}.${expectedId}: missing mapped entity`);
        continue;
      }
      for (const [component, expectedValue] of Object.entries(expectedValues)) {
        compareNumber(
          actualValues[component],
          expectedValue,
          `${name}.${expectedId}.${component}`,
        );
      }
    }
  }
  compareCollection("displacements", mappings?.nodeMapping);
  compareCollection("reactions", mappings?.nodeMapping);
  if(actual?.format==='signed-stations-v1'||expected?.format==='signed-stations-v1') {
    if(actual?.format!==expected?.format) failures.push('Independent signed-station reference required; historical envelopes cannot certify complete responses');
    else for(const [id,rows] of Object.entries(expected.memberStations||{})) for(const row of rows) {
      try {
        for(const side of row.side==='continuous'?['left','right']:[row.side]) {
          const value=readNativeStation(actual,id,row.positionM,side,mappings,row.localAxes);
          for(const key of COMPONENTS) compareNumber(value[key],row.components[key],`stations.${id}@${row.positionM}:${side}.${key}`);
        }
      } catch(error) {failures.push(error.message);}
    }
    const mappedCase=tolerances.caseKeyMapping?.[expected?.caseKey]??expected?.caseKey;
    if(actual?.caseKey!==mappedCase||actual?.selection?.kind!==expected?.selection?.kind) failures.push('Exact case/combination selection differs');
    if(Object.entries(expected?.units||{}).some(([key,value])=>actual?.units?.[key]!==value)) failures.push('Explicit native result units differ');
    if(!comparedValues) failures.push('No comparable native response values');
    return {pass:!failures.length,comparedValues,maxAbsoluteDifference,maxRelativeDifference,
      tolerances:{absolute:absoluteTolerance,relative:relativeTolerance},failures};
  }
  for(const [id,orientation] of Object.entries(mappings?.elementOrientation||{})) {
    if(orientation==='reversed') failures.push(`forces.${id}: commercial signed envelope requires an independently verified orientation/station transform`);
  }
  for(const [id,segments] of Object.entries(mappings?.elementSegments||{})) {
    if(segments.length!==1) failures.push(`forces.${id}: commercial envelope cannot represent physical endpoints of refined members`);
  }
  compareCollection("forces", mappings?.elementMapping);
  const mappedCase=tolerances.caseKeyMapping?.[expected?.caseKey]??expected?.caseKey;
  if (actual?.caseKey !== mappedCase) failures.push(`caseKey: ${actual?.caseKey} vs ${mappedCase}`);
  return {
    pass: failures.length === 0,
    comparedValues,
    maxAbsoluteDifference,
    maxRelativeDifference,
    tolerances: { absolute: absoluteTolerance, relative: relativeTolerance },
    failures,
  };
}

function extractEngineMetrics(engine, model, rawResult) {
  if (!ENGINE_ORDER.includes(engine)) throw new Error(`Unknown engine '${engine}'`);
  if (rawResult?.status !== "success") throw new Error(`${engine}: analysis did not succeed`);
  // Historical cross-engine calibration intentionally compares its documented dead-load setup.
  const result = caseSelection(engine, rawResult, undefined, {legacyDeadLoad:true}).result;
  if (result?.status && result.status !== "success") throw new Error(`${engine}: dead-load case did not succeed`);
  const index = modelIndex(model);
  const forces = result?.forces || {};
  const bottomForces = [...index.bottomColumns].map((id) => forceMetrics(engine, forces[id])).filter(Boolean);
  const bottomAxial = bottomForces.map((value) => value.axial);
  const beamForces = [...index.beams].map((id) => forceMetrics(engine, forces[id])).filter(Boolean);
  const verticalDisplacements = Object.entries(result?.displacements || {})
    .filter(([id]) => !index.baseNodes.has(String(id)))
    .map(([, displacement]) => Math.abs(finite(displacement?.uz) || 0));
  const reactionTotal = Object.entries(result?.reactions || {})
    .filter(([id]) => index.baseNodes.has(String(id)))
    .reduce((sum, [, reaction]) => sum + (finite(reaction?.fz) || 0), 0);
  const bottomColumnAxialSum = bottomAxial.reduce((sum, value) => sum + (finite(value) || 0), 0);
  return {
    case: engine === "opensees" ? "DL + member self-weight" : engine === "pkpm" ? "DL" : "dead-load case",
    totalGravity: Math.abs(reactionTotal) > 1e-9 ? Math.abs(reactionTotal) : bottomColumnAxialSum,
    bottomColumnAxialSum,
    maxBottomColumnAxial: maximum(bottomAxial),
    maxBottomColumnMoment: maximum(bottomForces.map((value) => value.moment)),
    maxBeamShear: maximum(beamForces.map((value) => value.shear)),
    maxBeamMoment: maximum(beamForces.map((value) => value.moment)),
    maxVerticalDisplacement: maximum(verticalDisplacements),
    counts: {
      bottomColumns: index.bottomColumns.size,
      columns: index.columns.size,
      beams: index.beams.size,
      displacementNodes: verticalDisplacements.length,
    },
  };
}

function relativeDifference(left, right, scaleFloor = 1e-12) {
  const denominator = Math.max(Math.abs(left), Math.abs(right), scaleFloor);
  return Math.abs(left - right) / denominator;
}

function compareEngineMetrics(actual, expected, tolerances = {}) {
  const relativeTolerance = tolerances.numeric ?? tolerances.relative ?? 0.01;
  const absoluteTolerance = tolerances.numericAbsolute ?? tolerances.absolute ?? 1e-8;
  const failures = [];
  let comparedValues = 0;
  let maxAbsoluteDifference = 0;
  let maxRelativeDifference = 0;
  const scalarMetrics = [
    "totalGravity",
    "bottomColumnAxialSum",
    "maxBottomColumnAxial",
    "maxBottomColumnMoment",
    "maxBeamShear",
    "maxBeamMoment",
    "maxVerticalDisplacement",
  ];
  for (const metric of scalarMetrics) {
    const actualValue = finite(actual?.[metric]);
    const expectedValue = finite(expected?.[metric]);
    if (expectedValue === null) continue;
    if (actualValue === null) {
      failures.push(`${metric}: missing finite value`);
      continue;
    }
    comparedValues += 1;
    const absoluteDifference = Math.abs(actualValue - expectedValue);
    const difference = relativeDifference(actualValue, expectedValue, absoluteTolerance);
    maxAbsoluteDifference = Math.max(maxAbsoluteDifference, absoluteDifference);
    maxRelativeDifference = Math.max(maxRelativeDifference, difference);
    if (absoluteDifference > absoluteTolerance && difference > relativeTolerance) {
      failures.push(`${metric}: ${actualValue} vs ${expectedValue}`);
    }
  }
  for (const [metric, expectedValue] of Object.entries(expected?.counts || {})) {
    const actualValue = finite(actual?.counts?.[metric]);
    if (actualValue === null || actualValue !== finite(expectedValue)) {
      failures.push(`counts.${metric}: ${actualValue ?? "missing"} vs ${expectedValue}`);
    }
  }
  if (comparedValues === 0) failures.push("no comparable engine metrics");
  return {
    pass: failures.length === 0,
    comparedValues,
    maxAbsoluteDifference,
    maxRelativeDifference,
    tolerances: { absolute: absoluteTolerance, relative: relativeTolerance },
    failures,
  };
}

function assessCrossEngine(engineMetrics, policy) {
  const metrics = {};
  let pass = true;
  for (const [metric, rule] of Object.entries(policy)) {
    const engines = rule.engines || ENGINE_ORDER;
    const values = Object.fromEntries(engines.map((engine) => [engine, finite(engineMetrics?.[engine]?.[metric])]));
    const missing = engines.filter((engine) => values[engine] === null);
    const pairs = [];
    for (let leftIndex = 0; leftIndex < engines.length; leftIndex += 1) {
      for (let rightIndex = leftIndex + 1; rightIndex < engines.length; rightIndex += 1) {
        const left = engines[leftIndex];
        const right = engines[rightIndex];
        if (values[left] === null || values[right] === null) continue;
        pairs.push({
          engines: [left, right],
          relativeDifference: relativeDifference(values[left], values[right], rule.scaleFloor),
        });
      }
    }
    const maxRelativeDifference = pairs.length > 0
      ? Math.max(...pairs.map((pair) => pair.relativeDifference))
      : null;
    const metricPass = missing.length === 0
      && maxRelativeDifference !== null
      && maxRelativeDifference <= rule.relativeTolerance;
    pass = pass && metricPass;
    metrics[metric] = {
      pass: metricPass,
      values,
      engines,
      excludedEngines: ENGINE_ORDER.filter((engine) => !engines.includes(engine)),
      exclusionReason: rule.exclusionReason || null,
      tier: rule.tier || "response",
      relativeTolerance: rule.relativeTolerance,
      maxRelativeDifference,
      pairs,
      missing,
    };
  }
  const tierNames = [...new Set(Object.values(metrics).map((metric) => metric.tier))];
  const tiers = Object.fromEntries(tierNames.map((tier) => {
    const tierMetrics = Object.entries(metrics).filter(([, metric]) => metric.tier === tier);
    return [tier, {
      pass: tierMetrics.every(([, metric]) => metric.pass),
      metrics: tierMetrics.map(([name]) => name),
    }];
  }));
  const status = pass
    ? "fully_validated"
    : tiers.equilibrium?.pass ? "equilibrium_validated" : "divergent";
  return { pass, status, tiers, metrics };
}

function buildValidationEntry({ caseId, model, engineRuns, policy, provenance = {} }) {
  const engineMetrics = Object.fromEntries(
    ENGINE_ORDER.map((engine) => [engine, extractEngineMetrics(engine, model, engineRuns[engine].result)]),
  );
  return {
    caseId,
    inputSha256: sha256(model),
    provenance,
    engines: Object.fromEntries(ENGINE_ORDER.map((engine) => [engine, {
      identity: engineRuns[engine].identity,
      inputSha256: engineRuns[engine].inputSha256,
      normalizedMetricSha256: sha256(engineMetrics[engine]),
      metrics: engineMetrics[engine],
      ...(engine === "opensees" ? {} : (() => {
        const response = normalizeCommercialEngineResponse(engine, model, engineRuns[engine].result, {legacyDeadLoad:true});
        return { normalizedResponseSha256: sha256(response), response };
      })()),
    }])),
    validation: assessCrossEngine(engineMetrics, policy),
  };
}

module.exports = {
  ENGINE_ORDER,
  assessCrossEngine,
  buildValidationEntry,
  compareCommercialEngineResponses,
  compareEngineMetrics,
  extractEngineMetrics,
  normalizeCommercialEngineResponse,
  relativeDifference,
};
