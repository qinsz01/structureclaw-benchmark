function finiteNumber(value) {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function entityMap(items) {
  return new Map((items || []).map((item) => [String(item.id), item]));
}

function vector(x = 0, y = 0, z = 0) {
  return [Number(x || 0), Number(y || 0), Number(z || 0)];
}

function add(left, right) {
  return left.map((value, index) => value + right[index]);
}

function scale(value, factor) {
  return value.map((component) => component * factor);
}

function cross(left, right) {
  return [
    left[1] * right[2] - left[2] * right[1],
    left[2] * right[0] - left[0] * right[2],
    left[0] * right[1] - left[1] * right[0],
  ];
}

function magnitude(value) {
  return Math.sqrt(value.reduce((sum, component) => sum + component ** 2, 0));
}

function validateOpenSeesTruthInput(model) {
  const issues = [];
  const dimension = model?.coordinate_system?.dimension;
  const elements = model?.elements || [];
  const materials = entityMap(model?.materials);
  const sections = entityMap(model?.sections);
  const nodes = entityMap(model?.nodes);
  const elementsById = entityMap(elements);
  const loadCases = entityMap(model?.load_cases);
  const isTruss = elements.length > 0 && elements.every((element) => element.type === "truss");
  const isFrame = elements.length > 0 && elements.every((element) => ["beam", "column"].includes(element.type));

  if (!['2d', '3d'].includes(dimension)) issues.push("unsupported coordinate dimension");
  if (!isTruss && !isFrame && dimension === "2d") issues.push("mixed 2-D frame/truss model is unsupported");
  if (elements.length === 0) issues.push("model has no elements");
  if ((model.load_combinations || []).length !== 1) issues.push("exactly one load combination is required");

  const combination = model.load_combinations?.[0];
  if (combination && Object.keys(combination.factors || {}).length === 0) {
    issues.push("load combination must contain at least one factor");
  }
  for (const [caseId, factor] of Object.entries(combination?.factors || {})) {
    if (!loadCases.has(String(caseId))) issues.push(`combination references unknown load case '${caseId}'`);
    if (finiteNumber(factor) === null) issues.push(`combination factor '${caseId}' is not finite`);
  }

  for (const element of elements) {
    const material = materials.get(String(element.material));
    const section = sections.get(String(element.section));
    if (!material || finiteNumber(material.E) === null || material.E <= 0) {
      issues.push(`element '${element.id}' requires material E > 0`);
    }
    const requiredProperties = element.type === "truss"
      ? ["A"]
      : dimension === "2d" ? ["A", "Iy"] : ["A", "Iy", "Iz", "J"];
    for (const property of requiredProperties) {
      if (!section || finiteNumber(section.properties?.[property]) === null || section.properties[property] <= 0) {
        issues.push(`element '${element.id}' requires section ${property} > 0`);
      }
    }
    if (dimension === "3d" && element.type !== "truss"
      && (finiteNumber(material?.nu) === null || material.nu < 0 || material.nu > 0.5)) {
      issues.push(`element '${element.id}' requires 0 <= material nu <= 0.5`);
    }
  }

  for (const loadCase of model.load_cases || []) {
    for (const load of loadCase.loads || []) {
      const nodeId = load.node ?? load.nodeId ?? load.node_id;
      const elementId = load.element ?? load.elementId ?? load.element_id;
      if ((nodeId === undefined) === (elementId === undefined)) {
        issues.push(`load case '${loadCase.id}' must target exactly one node or element`);
      }
      if (String(load.reference_frame || "global") !== "global") {
        issues.push(`load case '${loadCase.id}' must use the global reference frame`);
      }
      if (isTruss && elementId !== undefined) issues.push("truss truth generation accepts nodal loads only");
      if (nodeId !== undefined && !nodes.has(String(nodeId))) issues.push(`load targets unknown node '${nodeId}'`);
      if (elementId !== undefined && !elementsById.has(String(elementId))) {
        issues.push(`load targets unknown element '${elementId}'`);
      }
      for (const field of ["fx", "fy", "fz", "mx", "my", "mz", "wx", "wy", "wz"]) {
        if (load[field] !== undefined && finiteNumber(load[field]) === null) {
          issues.push(`load component '${field}' is not finite`);
        }
      }
    }
  }
  return { pass: issues.length === 0, issues };
}

function checkStaticEquilibrium(model, result, analysisSelection, tolerances = {}) {
  const nodes = entityMap(model.nodes);
  const elements = entityMap(model.elements);
  const loadCases = entityMap(model.load_cases);
  const combination = (model.load_combinations || [])
    .find((entry) => entry.id === analysisSelection?.loadCombinationId);
  const failures = [];
  if (!combination) return { pass: false, failures: ["selected load combination not found"] };

  let externalForce = vector();
  let externalMoment = vector();
  let forceScale = 0;
  let momentScale = 0;
  for (const [caseId, factor] of Object.entries(combination.factors || {})) {
    const loadCase = loadCases.get(String(caseId));
    for (const load of loadCase?.loads || []) {
      const nodeId = load.node ?? load.nodeId ?? load.node_id;
      const elementId = load.element ?? load.elementId ?? load.element_id;
      let applicationPoint;
      let force;
      let appliedMoment = vector();
      if (nodeId !== undefined) {
        const node = nodes.get(String(nodeId));
        applicationPoint = vector(node.x, node.y, node.z);
        force = scale(vector(load.fx, load.fy, load.fz), factor);
        appliedMoment = scale(vector(load.mx, load.my, load.mz), factor);
      } else {
        const element = elements.get(String(elementId));
        const start = nodes.get(String(element.nodes[0]));
        const end = nodes.get(String(element.nodes[1]));
        const startPoint = vector(start.x, start.y, start.z);
        const endPoint = vector(end.x, end.y, end.z);
        const length = magnitude(add(endPoint, scale(startPoint, -1)));
        applicationPoint = scale(add(startPoint, endPoint), 0.5);
        force = scale(vector(load.wx, load.wy, load.wz), factor * length);
      }
      const moment = add(cross(applicationPoint, force), appliedMoment);
      externalForce = add(externalForce, force);
      externalMoment = add(externalMoment, moment);
      forceScale += magnitude(force);
      momentScale += magnitude(moment);
    }
  }

  const reactions = result?.reactions || result?.nodeReactions || {};
  let reactionForce = vector();
  let reactionMoment = vector();
  for (const [nodeId, reaction] of Object.entries(reactions)) {
    const node = nodes.get(String(nodeId));
    if (!node) {
      failures.push(`reaction references unknown node '${nodeId}'`);
      continue;
    }
    const force = vector(reaction.fx, reaction.fy, reaction.fz);
    const moment = add(
      cross(vector(node.x, node.y, node.z), force),
      vector(reaction.mx, reaction.my, reaction.mz),
    );
    reactionForce = add(reactionForce, force);
    reactionMoment = add(reactionMoment, moment);
    forceScale += magnitude(force);
    momentScale += magnitude(moment);
  }

  const forceResidual = add(externalForce, reactionForce);
  const momentResidual = add(externalMoment, reactionMoment);
  const relativeTolerance = tolerances.relative ?? 1e-8;
  const forceAbsoluteTolerance = tolerances.forceAbsolute ?? 1e-7;
  const momentAbsoluteTolerance = tolerances.momentAbsolute ?? 1e-7;
  const forceLimit = Math.max(forceAbsoluteTolerance, forceScale * relativeTolerance);
  const momentLimit = Math.max(momentAbsoluteTolerance, momentScale * relativeTolerance);
  if (magnitude(forceResidual) > forceLimit) failures.push("global force equilibrium residual exceeds tolerance");
  if (magnitude(momentResidual) > momentLimit) failures.push("global moment equilibrium residual exceeds tolerance");
  return {
    pass: failures.length === 0,
    failures,
    externalForce,
    reactionForce,
    forceResidual,
    externalMoment,
    reactionMoment,
    momentResidual,
    limits: { force: forceLimit, moment: momentLimit },
  };
}

module.exports = {
  checkStaticEquilibrium,
  validateOpenSeesTruthInput,
};
