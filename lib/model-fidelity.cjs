const DOF_ORDER = ["ux", "uy", "uz", "rx", "ry", "rz"];
const AXES = ["x", "y", "z"];
const MATERIAL_NUMERIC_FIELDS = ["E", "nu", "rho", "fy", "fc"];
const MATERIAL_TEXT_FIELDS = ["category", "grade"];
const SECTION_NUMERIC_FIELDS = ["A", "Iy", "Iz", "J", "G"];
const SECTION_TEXT_FIELDS = ["type", "purpose", "standard_steel_name"];

function finiteNumber(value) {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim() !== "") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function entityMap(items) {
  return new Map((items || []).map((item) => [String(item.id), item]));
}

function normalizedRestraints(node) {
  const restraints = Array.isArray(node?.restraints) ? node.restraints : [];
  return DOF_ORDER.map((_, index) => Boolean(restraints[index]));
}

function inspectCoordinateContract(model) {
  const coordinateSystem = model?.coordinate_system;
  if (!coordinateSystem || typeof coordinateSystem !== "object" || Array.isArray(coordinateSystem)) {
    return { ok: false, reason: "missing typed coordinate_system" };
  }
  const dimension = coordinateSystem.dimension;
  if (coordinateSystem.semantics !== "global-z-up" || coordinateSystem.version !== 1) {
    return { ok: false, reason: "unsupported coordinate semantics/version" };
  }
  if (!['2d', '3d'].includes(dimension)) {
    return { ok: false, reason: "coordinate dimension must be 2d or 3d" };
  }
  if ((dimension === "2d" && coordinateSystem.plane !== "xz")
    || (dimension === "3d" && coordinateSystem.plane !== null)) {
    return { ok: false, reason: "coordinate plane conflicts with dimension" };
  }
  if (!Array.isArray(coordinateSystem.dof_order)
    || !DOF_ORDER.every((value, index) => coordinateSystem.dof_order[index] === value)) {
    return { ok: false, reason: "invalid canonical DOF order" };
  }
  for (const node of model.nodes || []) {
    if (!AXES.every((axis) => finiteNumber(node?.[axis]) !== null)) {
      return { ok: false, reason: `node '${node?.id ?? "?"}' lacks finite global X/Y/Z coordinates` };
    }
    if (dimension === "2d" && Math.abs(Number(node.y)) > 1e-9) {
      return { ok: false, reason: `2-D node '${node.id}' is outside the global X-Z plane` };
    }
  }
  return { ok: true, dimension };
}

function distance(a, b) {
  return Math.sqrt(AXES.reduce((sum, axis) => sum + (Number(a[axis]) - Number(b[axis])) ** 2, 0));
}

function maximumNodeMatching(expectedNodes, actualNodes, tolerance) {
  const candidates = expectedNodes.map((expected) => actualNodes
    .map((actual, actualIndex) => ({ actualIndex, distance: distance(expected, actual) }))
    .filter((candidate) => candidate.distance <= tolerance)
    .sort((left, right) => left.distance - right.distance || left.actualIndex - right.actualIndex));
  const actualToExpected = new Map();

  function augment(expectedIndex, visited) {
    for (const candidate of candidates[expectedIndex]) {
      if (visited.has(candidate.actualIndex)) continue;
      visited.add(candidate.actualIndex);
      const previous = actualToExpected.get(candidate.actualIndex);
      if (previous === undefined || augment(previous, visited)) {
        actualToExpected.set(candidate.actualIndex, expectedIndex);
        return true;
      }
    }
    return false;
  }

  for (let expectedIndex = 0; expectedIndex < expectedNodes.length; expectedIndex += 1) {
    augment(expectedIndex, new Set());
  }

  const expectedToActual = new Map();
  for (const [actualIndex, expectedIndex] of actualToExpected.entries()) {
    expectedToActual.set(String(expectedNodes[expectedIndex].id), String(actualNodes[actualIndex].id));
  }
  return expectedToActual;
}

function precisionRecall(matched, actualCount, expectedCount) {
  return {
    matched,
    precision: actualCount === 0 ? (expectedCount === 0 ? 1 : 0) : matched / actualCount,
    recall: expectedCount === 0 ? 1 : matched / expectedCount,
  };
}

function thresholdPass(score, threshold) {
  return score.precision + 1e-12 >= threshold && score.recall + 1e-12 >= threshold;
}

function unorderedPair(left, right) {
  return left <= right ? `${left}\u0000${right}` : `${right}\u0000${left}`;
}

function elementEndpoints(element) {
  const nodes = Array.isArray(element?.nodes)
    ? element.nodes
    : Array.isArray(element?.nodeIds) ? element.nodeIds : [];
  return nodes.slice(0, 2).map(String);
}

function maximumElementMatching(expectedElements, actualElements, nodeMapping) {
  const candidates = expectedElements.map((expected) => {
    const [expectedStart, expectedEnd] = elementEndpoints(expected);
    const mappedStart = nodeMapping.get(expectedStart);
    const mappedEnd = nodeMapping.get(expectedEnd);
    if (mappedStart === undefined || mappedEnd === undefined) return [];
    const expectedPair = unorderedPair(mappedStart, mappedEnd);
    return actualElements.flatMap((actual, actualIndex) => {
      const [actualStart, actualEnd] = elementEndpoints(actual);
      const sameType = String(actual?.type || "") === String(expected?.type || "");
      return sameType && unorderedPair(actualStart, actualEnd) === expectedPair ? [actualIndex] : [];
    });
  });
  const actualToExpected = new Map();

  function augment(expectedIndex, visited) {
    for (const actualIndex of candidates[expectedIndex]) {
      if (visited.has(actualIndex)) continue;
      visited.add(actualIndex);
      const previous = actualToExpected.get(actualIndex);
      if (previous === undefined || augment(previous, visited)) {
        actualToExpected.set(actualIndex, expectedIndex);
        return true;
      }
    }
    return false;
  }

  for (let expectedIndex = 0; expectedIndex < expectedElements.length; expectedIndex += 1) {
    augment(expectedIndex, new Set());
  }

  const expectedToActual = new Map();
  for (const [actualIndex, expectedIndex] of actualToExpected.entries()) {
    expectedToActual.set(String(expectedElements[expectedIndex].id), String(actualElements[actualIndex].id));
  }
  return expectedToActual;
}

function numericClose(actual, expected, relativeTolerance, absoluteTolerance = 1e-12) {
  const actualNumber = finiteNumber(actual);
  const expectedNumber = finiteNumber(expected);
  if (actualNumber === null || expectedNumber === null) return false;
  return Math.abs(actualNumber - expectedNumber)
    <= Math.max(absoluteTolerance, Math.abs(expectedNumber) * relativeTolerance);
}

function compareStructuredValue(actual, expected, relativeTolerance, path, failures) {
  if (typeof expected === "number") {
    if (!numericClose(actual, expected, relativeTolerance)) failures.push(path);
    return;
  }
  if (Array.isArray(expected)) {
    if (!Array.isArray(actual) || actual.length !== expected.length) {
      failures.push(path);
      return;
    }
    expected.forEach((value, index) => compareStructuredValue(
      actual[index], value, relativeTolerance, `${path}[${index}]`, failures,
    ));
    return;
  }
  if (expected && typeof expected === "object") {
    if (!actual || typeof actual !== "object" || Array.isArray(actual)) {
      failures.push(path);
      return;
    }
    for (const [key, value] of Object.entries(expected)) {
      compareStructuredValue(actual[key], value, relativeTolerance, `${path}.${key}`, failures);
    }
    return;
  }
  if (actual !== expected) failures.push(path);
}

function hasMeaningfulValue(value) {
  if (value === null || value === undefined || value === false || value === "") return false;
  if (typeof value === "number") return Math.abs(value) > 1e-12;
  if (Array.isArray(value)) return value.some(hasMeaningfulValue);
  if (typeof value === "object") return Object.values(value).some(hasMeaningfulValue);
  return true;
}

function compareAssignedProperties(expectedModel, actualModel, elementMapping, propertyTolerance) {
  const expectedElements = entityMap(expectedModel.elements);
  const actualElements = entityMap(actualModel.elements);
  const expectedMaterials = entityMap(expectedModel.materials);
  const actualMaterials = entityMap(actualModel.materials);
  const expectedSections = entityMap(expectedModel.sections);
  const actualSections = entityMap(actualModel.sections);
  const failures = [];

  for (const [expectedElementId, actualElementId] of elementMapping.entries()) {
    const expectedElement = expectedElements.get(expectedElementId);
    const actualElement = actualElements.get(actualElementId);
    const expectedMaterial = expectedMaterials.get(String(expectedElement?.material));
    const actualMaterial = actualMaterials.get(String(actualElement?.material));
    const expectedSection = expectedSections.get(String(expectedElement?.section));
    const actualSection = actualSections.get(String(actualElement?.section));

    if (!expectedMaterial || !actualMaterial) {
      failures.push(`${expectedElementId}: missing assigned material`);
    } else {
      for (const field of MATERIAL_NUMERIC_FIELDS) {
        if (expectedMaterial[field] !== undefined
          && !numericClose(actualMaterial[field], expectedMaterial[field], propertyTolerance)) {
          failures.push(`${expectedElementId}: material.${field}`);
        }
      }
      for (const field of MATERIAL_TEXT_FIELDS) {
        if (expectedMaterial[field] !== undefined
          && String(actualMaterial[field] || "").toLowerCase() !== String(expectedMaterial[field]).toLowerCase()) {
          failures.push(`${expectedElementId}: material.${field}`);
        }
      }
    }

    if (!expectedSection || !actualSection) {
      failures.push(`${expectedElementId}: missing assigned section`);
    } else {
      for (const field of SECTION_TEXT_FIELDS) {
        if (expectedSection[field] !== undefined
          && String(actualSection[field] || "").toLowerCase() !== String(expectedSection[field]).toLowerCase()) {
          failures.push(`${expectedElementId}: section.${field}`);
        }
      }
      if (expectedSection.shape !== undefined) {
        compareStructuredValue(
          actualSection.shape,
          expectedSection.shape,
          propertyTolerance,
          `${expectedElementId}: section.shape`,
          failures,
        );
      }
      for (const field of ["width", "height", "diameter", "thickness"]) {
        if (expectedSection[field] !== undefined
          && !numericClose(actualSection[field], expectedSection[field], propertyTolerance)) {
          failures.push(`${expectedElementId}: section.${field}`);
        }
      }
      for (const field of SECTION_NUMERIC_FIELDS) {
        if (expectedSection.properties?.[field] !== undefined
          && !numericClose(
            actualSection.properties?.[field],
            expectedSection.properties[field],
            propertyTolerance,
          )) {
          failures.push(`${expectedElementId}: section.${field}`);
        }
      }
    }
  }
  return failures;
}

function compareElementModifiers(expectedModel, actualModel, elementMapping, propertyTolerance) {
  const expectedElements = entityMap(expectedModel.elements);
  const actualElements = entityMap(actualModel.elements);
  const failures = [];
  const overrideFields = [
    "releases", "offsets", "concrete_grade", "steel_grade", "rebar_grade", "seismic_grade",
  ];
  for (const [expectedId, actualId] of elementMapping.entries()) {
    const expected = expectedElements.get(expectedId);
    const actual = actualElements.get(actualId);
    if (!numericClose(actual?.rotation_angle ?? 0, expected?.rotation_angle ?? 0, propertyTolerance)) {
      failures.push(`${expectedId}: rotation_angle`);
    }
    for (const field of overrideFields) {
      if (expected?.[field] !== undefined) {
        compareStructuredValue(actual?.[field], expected[field], propertyTolerance, `${expectedId}: ${field}`, failures);
      } else if (hasMeaningfulValue(actual?.[field])) {
        failures.push(`${expectedId}: unexpected ${field}`);
      }
    }
  }

  const expectedVectors = expectedModel.metadata?.elementReferenceVectors || {};
  const actualVectors = actualModel.metadata?.elementReferenceVectors || {};
  const expectedVectorIds = new Set(Object.keys(expectedVectors));
  for (const [expectedId, actualId] of elementMapping.entries()) {
    if (expectedVectorIds.has(expectedId)) {
      compareStructuredValue(
        actualVectors[actualId],
        expectedVectors[expectedId],
        propertyTolerance,
        `${expectedId}: reference vector`,
        failures,
      );
    } else if (hasMeaningfulValue(actualVectors[actualId])) {
      failures.push(`${expectedId}: unexpected reference vector`);
    }
  }
  return failures;
}

function loadTarget(load) {
  const node = load?.node ?? load?.nodeId ?? load?.node_id;
  const element = load?.element ?? load?.elementId ?? load?.element_id;
  if (node !== undefined) return { kind: "node", id: String(node) };
  if (element !== undefined) return { kind: "element", id: String(element) };
  return null;
}

function loadType(load) {
  const target = loadTarget(load);
  if (target?.kind === "node") return "nodal";
  if (target?.kind === "element") return "distributed";
  return String(load?.type || "unknown").toLowerCase();
}

function loadComponents(load) {
  if (loadType(load) === "distributed") {
    return ["wx", "wy", "wz"].map((field) => finiteNumber(load?.[field]) ?? 0);
  }
  const forces = Array.isArray(load?.forces) ? load.forces : [];
  return ["fx", "fy", "fz", "mx", "my", "mz"]
    .map((field, index) => finiteNumber(load?.[field]) ?? finiteNumber(forces[index]) ?? 0);
}

function flattenLoads(model) {
  return (model.load_cases || []).flatMap((loadCase) => (loadCase.loads || []).map((load) => ({
    ...load,
    loadCaseType: String(loadCase.type || "other").toLowerCase(),
  })));
}

function compareLoads(expectedModel, actualModel, nodeMapping, elementMapping, loadTolerance) {
  const expectedLoads = flattenLoads(expectedModel);
  const actualLoads = flattenLoads(actualModel);
  const candidates = expectedLoads.map((expected) => {
    const expectedTarget = loadTarget(expected);
    const mappedTarget = expectedTarget?.kind === "node"
      ? nodeMapping.get(expectedTarget.id)
      : elementMapping.get(expectedTarget?.id);
    if (!expectedTarget || mappedTarget === undefined) return [];
    return actualLoads.flatMap((actual, actualIndex) => {
      const actualTarget = loadTarget(actual);
      if (!actualTarget
        || actualTarget.kind !== expectedTarget.kind
        || actualTarget.id !== mappedTarget
        || loadType(actual) !== loadType(expected)
        || String(actual.reference_frame || "global") !== String(expected.reference_frame || "global")
        || actual.loadCaseType !== expected.loadCaseType) return [];
      const expectedComponents = loadComponents(expected);
      const actualComponents = loadComponents(actual);
      const componentsMatch = expectedComponents.every((value, index) => numericClose(
        actualComponents[index], value, loadTolerance, 1e-9,
      ));
      return componentsMatch ? [actualIndex] : [];
    });
  });
  const actualToExpected = new Map();

  function augment(expectedIndex, visited) {
    for (const actualIndex of candidates[expectedIndex]) {
      if (visited.has(actualIndex)) continue;
      visited.add(actualIndex);
      const previous = actualToExpected.get(actualIndex);
      if (previous === undefined || augment(previous, visited)) {
        actualToExpected.set(actualIndex, expectedIndex);
        return true;
      }
    }
    return false;
  }

  for (let expectedIndex = 0; expectedIndex < expectedLoads.length; expectedIndex += 1) {
    augment(expectedIndex, new Set());
  }
  return precisionRecall(actualToExpected.size, actualLoads.length, expectedLoads.length);
}

function loadCombinationSignatures(model) {
  const cases = entityMap(model.load_cases);
  return (model.load_combinations || []).map((combination) => Object.entries(combination.factors || {})
    .map(([caseId, factor]) => [String(cases.get(String(caseId))?.type || "unknown").toLowerCase(), finiteNumber(factor)])
    .sort(([leftType, leftFactor], [rightType, rightFactor]) => (
      leftType.localeCompare(rightType) || Number(leftFactor) - Number(rightFactor)
    ))
    .map(([type, factor]) => `${type}:${factor}`)
    .join("|"))
    .sort();
}

function compareStories(expectedModel, actualModel, nodeMapping, elementMapping, coordinateTolerance, loadTolerance) {
  const expectedStories = expectedModel.stories || [];
  const actualStories = actualModel.stories || [];
  const failures = [];
  if (expectedStories.length !== actualStories.length) return ["story count"];
  const storyMapping = new Map();
  for (let index = 0; index < expectedStories.length; index += 1) {
    const expected = expectedStories[index];
    const actual = actualStories[index];
    storyMapping.set(String(expected.id), String(actual.id));
    if (!numericClose(actual.height, expected.height, 0, coordinateTolerance)) failures.push(`${expected.id}: height`);
    for (const field of ["floorLoad", "liveLoad", "tributaryWidthM", "equivalentLineLoad"]) {
      if (expected[field] !== undefined && !numericClose(actual[field], expected[field], loadTolerance, 1e-9)) {
        failures.push(`${expected.id}: ${field}`);
      }
    }
    for (const field of ["floorLoadUnit", "liveLoadUnit"]) {
      if (expected[field] !== undefined && String(actual[field] || "") !== String(expected[field])) {
        failures.push(`${expected.id}: ${field}`);
      }
    }
  }
  const expectedNodes = entityMap(expectedModel.nodes);
  const actualNodes = entityMap(actualModel.nodes);
  for (const [expectedId, actualId] of nodeMapping.entries()) {
    const expectedStory = expectedNodes.get(expectedId)?.story;
    const actualStory = actualNodes.get(actualId)?.story;
    if (expectedStory !== undefined && storyMapping.get(String(expectedStory)) !== String(actualStory)) {
      failures.push(`node ${expectedId}: story`);
    }
  }
  const expectedElements = entityMap(expectedModel.elements);
  const actualElements = entityMap(actualModel.elements);
  for (const [expectedId, actualId] of elementMapping.entries()) {
    const expectedStory = expectedElements.get(expectedId)?.story;
    const actualStory = actualElements.get(actualId)?.story;
    if (expectedStory !== undefined && storyMapping.get(String(expectedStory)) !== String(actualStory)) {
      failures.push(`element ${expectedId}: story`);
    }
  }
  return failures;
}

function compareStructuralModels(actualModel, expectedModel, options = {}) {
  const coordinateTolerance = options.coordinate ?? options.span ?? 0.5;
  const propertyTolerance = options.property ?? 0.05;
  const loadTolerance = options.load ?? 0.2;
  const entityThreshold = 1;
  const actualContract = inspectCoordinateContract(actualModel);
  const expectedContract = inspectCoordinateContract(expectedModel);
  const failures = [];

  if (!actualContract.ok || !expectedContract.ok) {
    return {
      pass: false,
      summary: !actualContract.ok
        ? `agent model: ${actualContract.reason}`
        : `ground truth: ${expectedContract.reason}`,
      metrics: {},
      failures: [!actualContract.ok ? actualContract.reason : expectedContract.reason],
    };
  }
  if (actualContract.dimension !== expectedContract.dimension) failures.push("dimension");
  if (String(actualModel.schema_version || "") !== String(expectedModel.schema_version || "")) {
    failures.push("schema version");
  }
  if (String(actualModel.unit_system || "") !== String(expectedModel.unit_system || "")) {
    failures.push("unit system");
  }

  const expectedNodes = expectedModel.nodes || [];
  const actualNodes = actualModel.nodes || [];
  const nodeMapping = maximumNodeMatching(expectedNodes, actualNodes, coordinateTolerance);
  const nodeScore = precisionRecall(nodeMapping.size, actualNodes.length, expectedNodes.length);
  if (!thresholdPass(nodeScore, entityThreshold)) failures.push("nodes");

  const expectedElements = expectedModel.elements || [];
  const actualElements = actualModel.elements || [];
  const elementMapping = maximumElementMatching(expectedElements, actualElements, nodeMapping);
  const elementScore = precisionRecall(elementMapping.size, actualElements.length, expectedElements.length);
  if (!thresholdPass(elementScore, entityThreshold)) failures.push("topology");

  const expectedNodeMap = entityMap(expectedNodes);
  const actualNodeMap = entityMap(actualNodes);
  const restraintFailures = [];
  for (const [expectedNodeId, actualNodeId] of nodeMapping.entries()) {
    const expected = normalizedRestraints(expectedNodeMap.get(expectedNodeId));
    const actual = normalizedRestraints(actualNodeMap.get(actualNodeId));
    if (!expected.every((value, index) => value === actual[index])) restraintFailures.push(expectedNodeId);
  }
  if (restraintFailures.length > 0) failures.push("restraints");

  const propertyFailures = compareAssignedProperties(
    expectedModel, actualModel, elementMapping, propertyTolerance,
  );
  if (propertyFailures.length > 0) failures.push("properties");
  const modifierFailures = compareElementModifiers(
    expectedModel, actualModel, elementMapping, propertyTolerance,
  );
  if (modifierFailures.length > 0) failures.push("element modifiers");

  const loadScore = compareLoads(expectedModel, actualModel, nodeMapping, elementMapping, loadTolerance);
  if (!thresholdPass(loadScore, entityThreshold)) failures.push("loads");
  const expectedCombinations = loadCombinationSignatures(expectedModel);
  const actualCombinations = loadCombinationSignatures(actualModel);
  const loadCombinationsMatch = JSON.stringify(actualCombinations) === JSON.stringify(expectedCombinations);
  if (!loadCombinationsMatch) failures.push("load combinations");
  const storyFailures = compareStories(
    expectedModel,
    actualModel,
    nodeMapping,
    elementMapping,
    coordinateTolerance,
    loadTolerance,
  );
  if (storyFailures.length > 0) failures.push("stories");

  const metrics = {
    nodes: nodeScore,
    elements: elementScore,
    loads: loadScore,
    restraintFailures: restraintFailures.length,
    propertyFailures: propertyFailures.length,
    modifierFailures: modifierFailures.length,
    loadCombinationsMatch,
    storyFailures: storyFailures.length,
  };
  const formatScore = (label, score) => `${label} ${score.matched} `
    + `(P=${score.precision.toFixed(3)}, R=${score.recall.toFixed(3)})`;
  const details = [
    `dimension ${actualContract.dimension}/${expectedContract.dimension}`,
    formatScore("nodes", nodeScore),
    formatScore("elements", elementScore),
    `restraints ${nodeMapping.size - restraintFailures.length}/${nodeMapping.size}`,
    `properties ${propertyFailures.length === 0 ? "OK" : `${propertyFailures.length} mismatches`}`,
    `element modifiers ${modifierFailures.length === 0 ? "OK" : `${modifierFailures.length} mismatches`}`,
    formatScore("loads", loadScore),
    `load combinations ${loadCombinationsMatch ? "OK" : "FAIL"}`,
    `stories ${storyFailures.length === 0 ? "OK" : `${storyFailures.length} mismatches`}`,
  ];

  return {
    pass: failures.length === 0,
    summary: details.join("; "),
    metrics,
    failures,
    diagnostics: {
      restraintFailures,
      propertyFailures,
      modifierFailures,
      storyFailures,
      nodeMapping: Object.fromEntries(nodeMapping),
      elementMapping: Object.fromEntries(elementMapping),
    },
  };
}

module.exports = {
  compareStructuralModels,
  inspectCoordinateContract,
};
