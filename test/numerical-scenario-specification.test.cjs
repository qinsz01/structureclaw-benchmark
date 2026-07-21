const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const { benchmarkEngineeringSpecification } = require("../runner.cjs");

const SCENARIO_DIR = path.join(__dirname, "..", "scenarios", "standard_workflow");
const MULTIMODAL_DIR = path.join(__dirname, "..", "scenarios", "multimodal_reverse_engineering");
const INTERACTIVE_DIR = path.join(__dirname, "..", "scenarios", "interactive_robustness");

test("numerically scored concrete frames declare a unique analysis model", () => {
  const scenarios = fs.readdirSync(SCENARIO_DIR)
    .filter((name) => name.endsWith(".json"))
    .map((name) => JSON.parse(fs.readFileSync(path.join(SCENARIO_DIR, name), "utf8")))
    .filter((scenario) => scenario.benchmarkStructureType === "concrete-frame")
    .filter((scenario) => scenario.expect?.assertions?.some((item) => item.type === "numerical_matches"));

  assert.ok(scenarios.length > 0);
  for (const scenario of scenarios) {
    const message = scenario.message;
    assert.match(message, /(?:2D|3D)/u, `${scenario.id}: missing declared model dimension`);
    assert.match(message, /500\s*mm\s*[×xX]\s*500\s*mm/u, `${scenario.id}: missing column section`);
    assert.match(message, /300\s*mm\s*[×xX]\s*600\s*mm/u, `${scenario.id}: missing beam section`);
    if (/(?:折算|convert)/iu.test(message)) {
      assert.match(message, /(?:仅施加|apply only)/iu, `${scenario.id}: converted load is not exclusive`);
      assert.match(message, /(?:不重复|do not also apply)/iu, `${scenario.id}: duplicate load is not prohibited`);
    }
  }
});

test("multimodal concrete frames separate geometry evidence from complete engineering properties", () => {
  const scenarios = fs.readdirSync(MULTIMODAL_DIR)
    .filter((name) => name.endsWith(".json"))
    .map((name) => JSON.parse(fs.readFileSync(path.join(MULTIMODAL_DIR, name), "utf8")))
    .filter((scenario) => scenario.benchmarkStructureType === "concrete-frame")
    .filter((scenario) => scenario.expect?.assertions?.some((item) => item.type === "numerical_matches"));

  assert.ok(scenarios.length > 0);
  for (const scenario of scenarios) {
    const specification = scenario.engineeringSpecification || "";
    assert.match(specification, /500x500/u, `${scenario.id}: missing column section specification`);
    assert.match(specification, /300x600/u, `${scenario.id}: missing beam section specification`);
    assert.match(specification, /J=0\.0088021\s*m4/u, `${scenario.id}: incorrect column torsion constant`);
    assert.match(specification, /J=0\.00370786\s*m4/u, `${scenario.id}: incorrect beam torsion constant`);
    assert.equal(scenario.inputContract?.completeness, "complete", `${scenario.id}: incomplete input contract`);
  }
});

test("interactive concrete material revision starts from a fully determined model", () => {
  const scenario = JSON.parse(fs.readFileSync(
    path.join(INTERACTIVE_DIR, "robust-update-concrete-material.json"),
    "utf8",
  ));
  const message = scenario.turns[0].message;
  assert.match(message, /2D/u);
  assert.match(message, /500\s*mm\s*×\s*500\s*mm/u);
  assert.match(message, /300\s*mm\s*×\s*600\s*mm/u);
});

test("numerical beam targets expose observation nodes required only for response comparison", () => {
  const groundTruth = JSON.parse(fs.readFileSync(
    path.join(__dirname, "..", "fixtures", "ground-truth-models.json"),
    "utf8",
  ));
  const observationTargets = new Set(groundTruth
    .filter((entry) => {
      const model = entry.model;
      if (entry.inferredType !== "beam") return false;
      const nodes = new Map(model.nodes.map((node) => [String(node.id), node]));
      const neighbors = new Map(model.nodes.map((node) => [String(node.id), []]));
      for (const element of model.elements) {
        const [start, end] = element.nodes.map(String);
        neighbors.get(start)?.push(end);
        neighbors.get(end)?.push(start);
      }
      const loadedNodes = new Set(model.load_cases
        .flatMap((loadCase) => loadCase.loads || [])
        .filter((load) => load.node !== undefined)
        .map((load) => String(load.node)));
      return model.nodes.some((node) => {
        const adjacent = neighbors.get(String(node.id)) || [];
        if (adjacent.length !== 2 || loadedNodes.has(String(node.id))) return false;
        if (Array.isArray(node.restraints) && node.restraints.some(Boolean)) return false;
        const first = nodes.get(adjacent[0]);
        const second = nodes.get(adjacent[1]);
        const a = [first.x - node.x, first.y - node.y, first.z - node.z];
        const b = [second.x - node.x, second.y - node.y, second.z - node.z];
        const cross = [
          a[1] * b[2] - a[2] * b[1],
          a[2] * b[0] - a[0] * b[2],
          a[0] * b[1] - a[1] * b[0],
        ];
        const dot = a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
        return Math.hypot(...cross) < 1e-9 && dot < 0;
      });
    })
    .map((entry) => entry.id));

  assert.deepEqual([...observationTargets].sort(), [
    "beam-complex-12m",
    "beam-overhang-5m-1p5m-udl15",
    "beam-simple-6m",
    "beam-simple-7p5m-udl18",
    "beam-simple-8m-udl15",
    "beam-simple-8m-udl18",
    "beam-simple-8m-udl20",
  ]);

  const scenariosRoot = path.join(__dirname, "..", "scenarios");
  const scenarioFiles = fs.readdirSync(scenariosRoot, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .flatMap((entry) => fs.readdirSync(path.join(scenariosRoot, entry.name))
      .filter((name) => name.endsWith(".json"))
      .map((name) => path.join(scenariosRoot, entry.name, name)));
  let checkedGroups = 0;
  for (const file of scenarioFiles) {
    const scenario = JSON.parse(fs.readFileSync(file, "utf8"));
    const groups = scenario.turns || [scenario];
    for (const group of groups) {
      const assertions = group.assertions || group.expect?.assertions || [];
      const targetIds = new Set(assertions
        .map((item) => item.groundTruthId)
        .filter((id) => observationTargets.has(id)));
      if (targetIds.size === 0) continue;
      checkedGroups += 1;
      const specification = [
        group.message,
        scenario.engineeringSpecification,
        group.engineeringSpecification,
      ].filter(Boolean).join(" ");
      assert.match(specification, /(?:midspan|跨中)/iu, `${scenario.id}: hidden observation location`);
      assert.match(specification, /(?:analysis node|分析节点)/iu, `${scenario.id}: hidden observation node`);
      assert.match(specification, /(?:connected|连接)/iu, `${scenario.id}: hidden element subdivision`);
      assert.match(specification, /(?:deflection|displacement|挠度|位移)/iu, `${scenario.id}: hidden response quantity`);
    }
  }
  assert.ok(checkedGroups >= 15);
});

test("response-specific semantic checks are stated in the scenario input", () => {
  const scenarios = fs.readdirSync(SCENARIO_DIR)
    .filter((name) => name.endsWith(".json"))
    .map((name) => JSON.parse(fs.readFileSync(path.join(SCENARIO_DIR, name), "utf8")));
  const driftScenarios = scenarios.filter((scenario) => scenario.expect?.assertions?.some((item) => (
    item.type === "natural_language" && /(?:story drift|inter-story displacement)/iu.test(item.description)
  )));

  assert.equal(driftScenarios.length, 2);
  for (const scenario of driftScenarios) {
    assert.match(
      scenario.message,
      /(?:层间位移|inter-story displacement)/iu,
      `${scenario.id}: hidden story-response requirement`,
    );
  }
});

test("every strict model target receives common analysis properties without answer leakage", () => {
  const scenariosRoot = path.join(__dirname, "..", "scenarios");
  const scenarioFiles = fs.readdirSync(scenariosRoot, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .flatMap((entry) => fs.readdirSync(path.join(scenariosRoot, entry.name))
      .filter((name) => name.endsWith(".json"))
      .map((name) => path.join(scenariosRoot, entry.name, name)));
  let targetCount = 0;

  for (const file of scenarioFiles) {
    const scenario = JSON.parse(fs.readFileSync(file, "utf8"));
    const assertionGroups = [
      scenario.expect?.assertions,
      ...(scenario.turns || []).map((turn) => turn.assertions),
    ].filter(Array.isArray);
    for (const assertions of assertionGroups) {
      if (!assertions.some((item) => item.type === "model_matches")) continue;
      targetCount += 1;
      const specification = benchmarkEngineeringSpecification(assertions, scenario.locale || "zh");
      assert.match(specification, /"coordinate_system"/u, `${scenario.id}: missing coordinate specification`);
      assert.match(specification, /"materials"/u, `${scenario.id}: missing material specification`);
      assert.match(specification, /"sections"/u, `${scenario.id}: missing section specification`);
      assert.doesNotMatch(specification, /"nodes"|"elements"|"loads"\s*:/u, `${scenario.id}: leaked target model answer`);
    }
  }
  assert.ok(targetCount >= 100);
});
