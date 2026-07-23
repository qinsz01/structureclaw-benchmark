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

test("3-D frame ground truths keep floor loads canonical until analysis", () => {
  const groundTruth = JSON.parse(fs.readFileSync(
    path.join(__dirname, "..", "fixtures", "ground-truth-models.json"),
    "utf8",
  ));
  const frames = groundTruth.filter((entry) => (
    entry.model?.coordinate_system?.dimension === "3d"
    && entry.inferredType === "frame"
  ));
  assert.ok(frames.length >= 6);
  for (const entry of frames) {
    assert.ok(entry.model.stories.every((story) => (
      Array.isArray(story.floor_loads)
      && story.floor_loads.some((load) => load.type === "dead")
      && Number.isFinite(story.dead_load)
      && Number.isFinite(story.elevation)
    )), entry.id);
    assert.ok(entry.model.load_cases.every((loadCase) => (
      (loadCase.loads || []).every((load) => load.source !== "story_floor_loads")
    )), entry.id);
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

test("interactive frame nodal-load revision specifies the loaded node", () => {
  const scenario = JSON.parse(fs.readFileSync(
    path.join(INTERACTIVE_DIR, "robust-update-generic-increase-load.json"),
    "utf8",
  ));
  for (const turn of scenario.turns) {
    assert.match(turn.message, /右上节点/u, `${scenario.id}: ambiguous nodal-load location`);
  }
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
      assert.match(specification, /(?:midspan|midpoint|跨中|中点)/iu, `${scenario.id}: hidden observation location`);
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
      assert.match(specification, /(?:Coordinate system|坐标系):/u, `${scenario.id}: missing coordinate specification`);
      assert.match(specification, /(?:Materials|材料):/u, `${scenario.id}: missing material specification`);
      assert.match(specification, /(?:Sections|截面):/u, `${scenario.id}: missing section specification`);
      assert.match(
        specification,
        /(?:extract_draft_params|parameter extraction|参数提取)/u,
        `${scenario.id}: engineering properties are not explicitly propagated to parameter extraction`,
      );
      assert.doesNotMatch(specification, /(?:Nodes|节点|Elements|构件|Loads|荷载)\s*:/u, `${scenario.id}: leaked target model answer`);
    }
  }
  assert.ok(targetCount >= 100);
});

test("portal-frame analysis properties expose a parseable complete H-section name", () => {
  const scenario = JSON.parse(fs.readFileSync(
    path.join(SCENARIO_DIR, "portal-frame-static-18m.json"),
    "utf8",
  ));
  const specification = benchmarkEngineeringSpecification(scenario.expect.assertions, scenario.locale);
  assert.match(specification, /member=H600x250x10x16/u);
});

test("portal-frame ground truth uses complete and geometrically consistent H-sections", () => {
  const groundTruth = JSON.parse(fs.readFileSync(
    path.join(__dirname, "..", "fixtures", "ground-truth-models.json"),
    "utf8",
  ));
  const portalModels = groundTruth.filter((entry) => entry.inferredType === "portal-frame");
  assert.ok(portalModels.length >= 7);

  for (const entry of portalModels) {
    for (const section of entry.model.sections) {
      const { H, B, tw, tf } = section.shape || {};
      assert.ok([H, B, tw, tf].every(Number.isFinite), `${entry.id}: incomplete H-section shape`);
      const hw = H - 2 * tf;
      const expected = {
        A: (tw * hw + 2 * B * tf) / 1e6,
        Iy: ((tw * hw ** 3) / 12 + (2 * B * tf ** 3) / 12 + 2 * B * tf * ((hw + tf) / 2) ** 2) / 1e12,
        Iz: ((2 * tf * B ** 3) / 12 + (hw * tw ** 3) / 12) / 1e12,
        J: (2 * B * tf ** 3 + hw * tw ** 3) / 3 / 1e12,
      };
      for (const [key, value] of Object.entries(expected)) {
        assert.ok(
          Math.abs(section.properties[key] - value) <= Math.max(1e-12, Math.abs(value) * 1e-12),
          `${entry.id}: ${key} is inconsistent with the declared shape`,
        );
      }
    }
  }
});

test("portal-frame ground truth distinguishes columns from beams", () => {
  const groundTruth = JSON.parse(fs.readFileSync(
    path.join(__dirname, "..", "fixtures", "ground-truth-models.json"),
    "utf8",
  ));
  const portalModels = groundTruth.filter((entry) => entry.inferredType === "portal-frame");

  for (const entry of portalModels) {
    const nodes = new Map(entry.model.nodes.map((node) => [String(node.id), node]));
    for (const element of entry.model.elements) {
      const [start, end] = element.nodes.map((id) => nodes.get(String(id)));
      assert.ok(start && end, `${entry.id}: element '${element.id}' references missing nodes`);
      const isVertical = Math.abs(start.x - end.x) <= 1e-9
        && Math.abs(start.y - end.y) <= 1e-9
        && Math.abs(start.z - end.z) > 1e-9;
      if (isVertical) {
        assert.equal(element.type, "column", `${entry.id}: vertical element '${element.id}' must be a column`);
      }
    }
  }
});

test("steel column benchmark declares a complete executable catalog section", () => {
  const scenario = JSON.parse(fs.readFileSync(
    path.join(SCENARIO_DIR, "std-column-steel-5m-en.json"),
    "utf8",
  ));
  const groundTruth = JSON.parse(fs.readFileSync(
    path.join(__dirname, "..", "fixtures", "ground-truth-models.json"),
    "utf8",
  ));
  const target = groundTruth.find((entry) => entry.id === "column-steel-5m-700")?.model;

  assert.match(scenario.message, /HW300x300/u);
  assert.ok(target);
  assert.deepEqual(target.sections[0], {
    id: "1",
    name: "HW300x300",
    type: "H",
    purpose: "column",
    shape: { kind: "H", H: 300, B: 300, tw: 10, tf: 15 },
    properties: {
      A: 0.01192,
      Iy: 2.04e-4,
      Iz: 6.75e-5,
      J: 4.23e-6,
      G: 79000,
    },
  });
  const specification = benchmarkEngineeringSpecification(scenario.expect.assertions, scenario.locale);
  assert.match(specification, /name=HW300x300/u);
  assert.match(specification, /shape\(kind=H, H=300, B=300, tw=10, tf=15\)/u);
});

test("steel frame ground truth uses executable catalog sections without duplicate load metadata", () => {
  const groundTruth = JSON.parse(fs.readFileSync(
    path.join(__dirname, "..", "fixtures", "ground-truth-models.json"),
    "utf8",
  ));
  const target = groundTruth.find((entry) => entry.id === "frame-2s1b-6m-10k")?.model;
  assert.ok(target);
  assert.deepEqual(target.sections[0].properties, {
    A: 0.01739,
    Iy: 4.03e-4,
    Iz: 1.36e-4,
    J: 8.63e-6,
    G: 79000,
  });
  assert.deepEqual(target.sections[1].properties, {
    A: 0.01143,
    Iy: 5.02e-4,
    Iz: 2.14e-5,
    J: 1.24e-6,
    G: 79000,
  });
  assert.ok(target.stories.every((story) => (
    story.floorLoad === undefined
    && story.tributaryWidthM === undefined
    && story.equivalentLineLoad === undefined
  )));
  assert.equal(target.load_cases[0].loads.length, 2);
});
