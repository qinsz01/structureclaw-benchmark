const SIMPLE_UDL_IDS = new Set([
  "beam-simple-6m",
  "beam-simple-8m-udl15",
  "beam-simple-8m-udl18",
  "beam-simple-7p5m-udl18",
]);
const SIMPLE_POINT_IDS = new Set(["beam-simple-4m-point25"]);
const CANTILEVER_POINT_IDS = new Set(["beam-cantilever-3m-point10"]);

function close(actual, expected, relativeTolerance = 1e-8, absoluteTolerance = 1e-10) {
  const difference = Math.abs(actual - expected);
  return {
    pass: difference <= absoluteTolerance || difference / Math.max(Math.abs(expected), absoluteTolerance) <= relativeTolerance,
    difference,
    relativeError: difference / Math.max(Math.abs(expected), absoluteTolerance),
  };
}

function checkAnalyticalOracle(modelId, model, result) {
  const family = SIMPLE_UDL_IDS.has(modelId)
    ? "simply-supported-uniform-load"
    : SIMPLE_POINT_IDS.has(modelId)
      ? "simply-supported-midspan-point-load"
      : CANTILEVER_POINT_IDS.has(modelId)
        ? "cantilever-tip-point-load"
        : null;
  if (!family) return { applicable: false, pass: true, checks: [] };

  const nodes = new Map(model.nodes.map((node) => [String(node.id), node]));
  const materials = new Map(model.materials.map((material) => [String(material.id), material]));
  const sections = new Map(model.sections.map((section) => [String(section.id), section]));
  const firstElement = model.elements[0];
  const elasticModulus = Number(materials.get(String(firstElement.material)).E) * 1000;
  const inertia = Number(sections.get(String(firstElement.section)).properties.Iy);
  const xCoordinates = model.nodes.map((node) => Number(node.x));
  const minX = Math.min(...xCoordinates);
  const maxX = Math.max(...xCoordinates);
  const length = maxX - minX;
  const combination = model.load_combinations[0];
  const loadCases = new Map(model.load_cases.map((loadCase) => [String(loadCase.id), loadCase]));
  const scaledLoads = Object.entries(combination.factors).flatMap(([caseId, factor]) => (
    (loadCases.get(String(caseId))?.loads || []).map((load) => ({ load, factor: Number(factor) }))
  ));
  const checks = [];
  const failures = [];

  function record(name, actualValue, expectedValue) {
    const comparison = close(Math.abs(Number(actualValue)), Math.abs(Number(expectedValue)));
    checks.push({ name, actual: Number(actualValue), expected: Number(expectedValue), ...comparison });
    if (!comparison.pass) failures.push(name);
  }

  const supportNodes = model.nodes
    .filter((node) => Array.isArray(node.restraints) && node.restraints[2])
    .sort((left, right) => left.x - right.x);

  if (family === "simply-supported-uniform-load") {
    const distributed = scaledLoads.filter(({ load }) => load.element !== undefined);
    const intensities = distributed.map(({ load, factor }) => Math.abs(Number(load.wz || 0) * factor));
    const intensity = intensities[0];
    if (distributed.length !== model.elements.length
      || intensities.some((value) => !close(value, intensity).pass)) {
      return { applicable: true, pass: false, checks, failures: ["uniform-load precondition"] };
    }
    const midpoint = model.nodes.find((node) => close(node.x, (minX + maxX) / 2).pass);
    const expectedReaction = intensity * length / 2;
    record("left reaction", result.reactions?.[supportNodes[0].id]?.fz, expectedReaction);
    record("right reaction", result.reactions?.[supportNodes.at(-1).id]?.fz, expectedReaction);
    record("midspan displacement", result.displacements?.[midpoint.id]?.uz, 5 * intensity * length ** 4 / (384 * elasticModulus * inertia));
    record("maximum moment", result.envelope?.maxAbsMoment, intensity * length ** 2 / 8);
  } else if (family === "simply-supported-midspan-point-load") {
    const point = scaledLoads.find(({ load }) => load.node !== undefined);
    const force = Math.abs(Number(point.load.fz || 0) * point.factor);
    const loadNode = nodes.get(String(point.load.node));
    record("left reaction", result.reactions?.[supportNodes[0].id]?.fz, force / 2);
    record("right reaction", result.reactions?.[supportNodes.at(-1).id]?.fz, force / 2);
    record("midspan displacement", result.displacements?.[loadNode.id]?.uz, force * length ** 3 / (48 * elasticModulus * inertia));
    record("maximum moment", result.envelope?.maxAbsMoment, force * length / 4);
  } else {
    const point = scaledLoads.find(({ load }) => load.node !== undefined);
    const force = Math.abs(Number(point.load.fz || 0) * point.factor);
    const loadNode = nodes.get(String(point.load.node));
    const fixedNode = supportNodes[0];
    record("vertical reaction", result.reactions?.[fixedNode.id]?.fz, force);
    record("fixed-end reaction moment", result.reactions?.[fixedNode.id]?.my, force * length);
    record("tip displacement", result.displacements?.[loadNode.id]?.uz, force * length ** 3 / (3 * elasticModulus * inertia));
    record("maximum moment", result.envelope?.maxAbsMoment, force * length);
  }
  return { applicable: true, family, pass: failures.length === 0, checks, failures };
}

module.exports = { checkAnalyticalOracle };
