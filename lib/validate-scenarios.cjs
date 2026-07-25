const fs = require("node:fs");
const path = require("node:path");
const { canonicalJson, sha256 } = require("./numerical-ground-truth.cjs");
const { checkStaticEquilibrium } = require("./opensees-truth-validation.cjs");
const { checkAnalyticalOracle } = require("./analytical-oracle.cjs");
const { compareAnalysisResults } = require("./analysis-fidelity.cjs");
const { findEngineGroundTruth, normalizeEngineKey } = require("./engine-ground-truth.cjs");
const {
  INDEPENDENT_SOLVER_VERSION,
  solveIndependentLinearModel,
} = require("./independent-linear-solver.cjs");

const BENCH_ROOT = path.resolve(__dirname, "..");
const SCLAW_ROOT = process.env.SCLAW_ROOT || path.resolve(BENCH_ROOT, "../..");
const SCENARIOS_DIR = path.join(BENCH_ROOT, "scenarios");
const GROUND_TRUTH_FILE = path.join(BENCH_ROOT, "fixtures", "ground-truth-models.json");
const NUMERICAL_GROUND_TRUTH_FILE = path.join(BENCH_ROOT, "fixtures", "opensees-ground-truth.json");
const CROSS_ENGINE_GROUND_TRUTH_FILE = path.join(
  BENCH_ROOT,
  "fixtures",
  "cross-engine-ground-truth-validation.json",
);
const OPENSEES_REQUIREMENTS_FILE = path.resolve(
  SCLAW_ROOT,
  "backend/src/agent-skills/analysis/runtime/requirements.txt",
);

const TASK_FAMILIES = {
  standard_workflow: { count: 50, split: "core" },
  interactive_robustness: { count: 50, split: "core" },
  multimodal_reverse_engineering: { count: 50, split: "auxiliary" },
};

const SCENARIO_MAX_RETRIES = 0;
const STRICT_MODEL_TOLERANCES = {
  coordinate: 0.05,
  load: 0.05,
};
const STRICT_NUMERICAL_TOLERANCES = {
  numeric: 0.01,
  numericAbsolute: 1e-8,
};
const NEUTRAL_DRAWING_NAME = /^drawing-\d{3}\.(?:png|dxf)$/;
const COMPLETE_IMAGE_FIELDS = ["topology", "dimensions", "supports", "loads"];
const COMPLETE_SPECIFICATION_FIELDS = ["materials", "sections", "analysis-settings"];
const ARCHITECTURAL_DXF_FIELDS = ["topology", "dimensions"];
const ARCHITECTURAL_DXF_SPECIFICATION_FIELDS = [
  "materials",
  "sections",
  "supports",
  "loads",
  "analysis-settings",
];
const IMAGE_ONLY_SPECIFICATION_TERMS = /kN|跨度|层高|跨宽|支座|铰支|滚动|固定端|\bspan\b|bay width|story height|\bpinned\b|\broller\b|fixed support|\d(?:\.\d+)?\s*m(?![m²³24])\b/i;

const REQUIRED_FIELDS = [
  "id",
  "split",
  "taskFamily",
  "inputModality",
  "structureType",
  "benchmarkStructureType",
  "difficulty",
  "skillTarget",
  "locale",
  "evaluationFocus",
];

const EVALUATION_FOCUS = new Set([
  "routing",
  "modeling",
  "model_match",
  "analysis",
  "numerical_match",
  "engine_match",
  "interaction",
  "report",
  "semantic",
]);
const ASSERTION_TYPES = new Set([
  "structural_type",
  "has_model",
  "has_analysis",
  "engine_match",
  "has_report",
  "report_numerical_consistency",
  "skill_match",
  "has_interaction_questions",
  "analysis_or_interaction",
  "should_not_analyze",
  "safe_non_execution",
  "no_bad_model",
  "natural_language",
  "model_matches",
  "numerical_matches",
]);
const ISSUE_SPECIFIC_INTERACTION_CATEGORIES = new Set([
  "error-recovery",
  "invalid-values",
  "conflicting-requirements",
  "unit-ambiguity",
]);

const ANALYSIS_SKILL_ENGINE_IDS = {
  "opensees-static": "builtin-opensees",
  "pkpm-static": "builtin-pkpm",
  "yjk-static": "builtin-yjk",
};

const ALLOWED_STRUCTURAL_TYPE_PAIRS = new Set([
  "concrete-frame/frame",
  "frame/generic",
]);

const BENCHMARK_STRUCTURE_TYPE = {
  beam: "beam",
  column: "column",
  "concrete-frame": "concrete-frame",
  "double-span-beam": "continuous-beam",
  frame: "steel-frame",
  generic: "generic",
  "portal-frame": "portal-frame",
  truss: "truss",
};

function collectJsonFiles(dir) {
  const entries = fs.readdirSync(dir, { withFileTypes: true })
    .sort((a, b) => a.name.localeCompare(b.name));
  return entries.flatMap((entry) => {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) return collectJsonFiles(fullPath);
    if (entry.isFile() && entry.name.endsWith(".json")) return [fullPath];
    return [];
  });
}

function rel(file) {
  return path.relative(BENCH_ROOT, file).replace(/\\/g, "/");
}

function collectAttachments(scenario) {
  const attachments = [];
  if (Array.isArray(scenario.attachments)) attachments.push(...scenario.attachments);
  if (Array.isArray(scenario.turns)) {
    for (const turn of scenario.turns) {
      if (Array.isArray(turn.attachments)) attachments.push(...turn.attachments);
    }
  }
  return attachments;
}

function resolveAttachment(relPath) {
  if (path.isAbsolute(relPath)) return relPath;
  const normalized = relPath.replace(/^tests[\\/]+llm-benchmark[\\/]+/, "");
  return path.resolve(BENCH_ROOT, normalized);
}

function scenarioPromptText(scenario) {
  if (typeof scenario.message === "string") return scenario.message;
  if (Array.isArray(scenario.turns)) {
    return scenario.turns.map((turn) => turn.message || "").join(" | ");
  }
  return "";
}

function normalizePromptSignature(text) {
  return String(text || "")
    .toLowerCase()
    .replace(/[\d.]+\s*(m|米|kn\/m2|kn\/m²|kn\/m|kn|mm|t|层|跨|story|bay|bays|panel|panels|节间)/g, "#")
    .replace(/[，。,.、;；:：()（）\s]+/g, " ")
    .trim();
}

function hasCjk(text) {
  return /[\u3400-\u9fff]/.test(String(text || ""));
}

function validateGroundTruthCoordinateContract(entry, errors) {
  const model = entry?.model;
  const coordinateSystem = model?.coordinate_system;
  const expectedDofs = ["ux", "uy", "uz", "rx", "ry", "rz"];
  const prefix = `ground truth ${entry?.id || "(missing id)"}`;
  if (!coordinateSystem || coordinateSystem.semantics !== "global-z-up" || coordinateSystem.version !== 1) {
    errors.push(`${prefix}: missing canonical coordinate semantics/version`);
    return;
  }
  const dimension = coordinateSystem.dimension;
  if ((dimension !== "2d" && dimension !== "3d")
    || (dimension === "2d" && coordinateSystem.plane !== "xz")
    || (dimension === "3d" && coordinateSystem.plane !== null)) {
    errors.push(`${prefix}: invalid dimension/plane contract`);
  }
  if (!Array.isArray(coordinateSystem.dof_order)
    || !expectedDofs.every((value, index) => coordinateSystem.dof_order[index] === value)
    || coordinateSystem.dof_order.length !== expectedDofs.length) {
    errors.push(`${prefix}: invalid canonical DOF order`);
  }
  for (const node of model?.nodes || []) {
    if (![node?.x, node?.y, node?.z].every((value) => typeof value === "number" && Number.isFinite(value))) {
      errors.push(`${prefix}: node '${node?.id || "?"}' lacks finite global X/Y/Z coordinates`);
    } else if (dimension === "2d" && Math.abs(node.y) > 1e-9) {
      errors.push(`${prefix}: node '${node.id}' is outside the canonical X-Z plane`);
    }
  }
  const metadata = model?.metadata;
  if (metadata && typeof metadata === "object" && !Array.isArray(metadata)) {
    if (metadata.coordinateSemantics !== undefined
      && metadata.coordinateSemantics !== "global-z-up") {
      errors.push(`${prefix}: metadata coordinate semantics conflict`);
    }
    if (metadata.coordinateContractVersion !== undefined
      && metadata.coordinateContractVersion !== 1) {
      errors.push(`${prefix}: metadata coordinate contract version conflicts`);
    }
    if (metadata.frameDimension !== undefined && metadata.frameDimension !== dimension) {
      errors.push(`${prefix}: metadata frame dimension conflicts`);
    }
  }
}

function engineeringSpecifications(scenario) {
  return [
    scenario.engineeringSpecification,
    ...(Array.isArray(scenario.turns)
      ? scenario.turns.map((turn) => turn.engineeringSpecification)
      : []),
  ].filter((value) => typeof value === "string" && value.trim().length > 0);
}

function validateDeclaredSectionProperties(specification, groundTruth, tolerance, prefix, errors) {
  const sections = Array.isArray(groundTruth?.model?.sections) ? groundTruth.model.sections : [];
  const lowerSpecification = specification.toLowerCase();
  for (const section of sections) {
    const sectionName = String(section?.name || "").trim();
    if (!sectionName) continue;
    const sectionIndex = lowerSpecification.indexOf(sectionName.toLowerCase());
    if (sectionIndex < 0) {
      errors.push(`${prefix}: engineering specification omits ground-truth section "${sectionName}"`);
      continue;
    }
    const nextSectionIndex = sections
      .map((candidate) => String(candidate?.name || "").trim())
      .filter((name) => name && name.toLowerCase() !== sectionName.toLowerCase())
      .map((name) => lowerSpecification.indexOf(name.toLowerCase(), sectionIndex + sectionName.length))
      .filter((index) => index > sectionIndex)
      .sort((left, right) => left - right)[0];
    const sectionText = specification.slice(
      sectionIndex,
      nextSectionIndex === undefined ? sectionIndex + 500 : nextSectionIndex,
    );
    for (const [property, expected] of Object.entries(section.properties || {})) {
      if (typeof expected !== "number" || !Number.isFinite(expected)) continue;
      const match = sectionText.match(new RegExp(`${property}\\s*=\\s*([0-9.eE+-]+)`, "i"));
      if (!match) {
        errors.push(`${prefix}: engineering specification omits ${sectionName}.${property}`);
        continue;
      }
      const actual = Number(match[1]);
      const difference = Math.abs(actual - expected);
      const allowed = Math.max(1e-12, Math.abs(expected) * tolerance);
      if (!Number.isFinite(actual) || difference > allowed) {
        errors.push(
          `${prefix}: engineering specification ${sectionName}.${property}=${match[1]} conflicts with `
          + `ground truth ${expected}`,
        );
      }
    }
  }
}

const MATERIAL_PROPERTY_LABELS = {
  E: ["E"],
  nu: ["nu", "ν", "泊松比"],
  rho: ["rho", "ρ", "density", "密度"],
  fy: ["fy", "f_y"],
  fc: ["fc", "f_c"],
};

function validateDeclaredMaterialProperties(specification, groundTruth, tolerance, prefix, errors) {
  const materials = Array.isArray(groundTruth?.model?.materials) ? groundTruth.model.materials : [];
  const lowerSpecification = specification.toLowerCase();
  for (const material of materials) {
    const materialName = String(material?.name || "").trim();
    if (materialName && !lowerSpecification.includes(materialName.toLowerCase())) {
      errors.push(`${prefix}: engineering specification omits ground-truth material "${materialName}"`);
    }
    for (const [property, labels] of Object.entries(MATERIAL_PROPERTY_LABELS)) {
      const expected = material?.[property];
      if (typeof expected !== "number" || !Number.isFinite(expected)) continue;
      const labelPattern = labels.map((label) => label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|");
      const match = specification.match(new RegExp(`(?:${labelPattern})\\s*=\\s*([0-9.eE+-]+)`, "i"));
      if (!match) {
        errors.push(`${prefix}: engineering specification omits ${materialName || "material"}.${property}`);
        continue;
      }
      const actual = Number(match[1]);
      const difference = Math.abs(actual - expected);
      const allowed = Math.max(1e-12, Math.abs(expected) * tolerance);
      if (!Number.isFinite(actual) || difference > allowed) {
        errors.push(
          `${prefix}: engineering specification ${materialName || "material"}.${property}=${match[1]} conflicts with `
          + `ground truth ${expected}`,
        );
      }
    }
  }
}

function validateDeclaredAnalysisSettings(specification, prefix, errors) {
  const requirements = [
    [/\bSI\b/i, "SI units"],
    [/(?:global[-\s]*z[-\s]*up|全局\s*Z\s*轴向上)/iu, "global-Z-up coordinates"],
    [/(?:self[-\s]*weight|自重)/iu, "member self-weight policy"],
    [/(?:load combination|荷载组合)/iu, "analysis load combination"],
  ];
  for (const [pattern, label] of requirements) {
    if (!pattern.test(specification)) {
      errors.push(`${prefix}: engineering specification omits ${label}`);
    }
  }
}

function hasExactly(values, expected) {
  return values.length === expected.length && expected.every((value) => values.includes(value));
}

function validateGroundTruthReferences(entry, errors) {
  const model = entry?.model || {};
  const prefix = `ground truth ${entry?.id || "(missing id)"}`;
  const collections = ["nodes", "elements", "materials", "sections", "load_cases", "stories"];
  for (const collection of collections) {
    const values = Array.isArray(model[collection]) ? model[collection] : [];
    const ids = values.map((item) => String(item?.id ?? ""));
    if (ids.some((id) => id.length === 0) || ids.length !== new Set(ids).size) {
      errors.push(`${prefix}: ${collection} must have unique non-empty ids`);
    }
  }
  const nodeIds = new Set((model.nodes || []).map((node) => String(node.id)));
  const elementIds = new Set((model.elements || []).map((element) => String(element.id)));
  const materialIds = new Set((model.materials || []).map((material) => String(material.id)));
  const sectionIds = new Set((model.sections || []).map((section) => String(section.id)));
  const storyIds = new Set((model.stories || []).map((story) => String(story.id)));
  for (const entity of [...(model.nodes || []), ...(model.elements || [])]) {
    if (entity?.story !== undefined && !storyIds.has(String(entity.story))) {
      errors.push(`${prefix}: '${entity.id}' references an unknown story`);
    }
  }
  for (const element of model.elements || []) {
    if (!Array.isArray(element.nodes) || element.nodes.length !== 2
      || element.nodes.some((id) => !nodeIds.has(String(id)))) {
      errors.push(`${prefix}: element '${element.id}' has invalid node references`);
    }
    if (!materialIds.has(String(element.material)) || !sectionIds.has(String(element.section))) {
      errors.push(`${prefix}: element '${element.id}' has invalid material/section references`);
    }
  }
  for (const loadCase of model.load_cases || []) {
    for (const load of loadCase.loads || []) {
      const node = load.node ?? load.nodeId ?? load.node_id;
      const element = load.element ?? load.elementId ?? load.element_id;
      if ((node === undefined) === (element === undefined)
        || (node !== undefined && !nodeIds.has(String(node)))
        || (element !== undefined && !elementIds.has(String(element)))) {
        errors.push(`${prefix}: load case '${loadCase.id}' has an invalid or ambiguous target`);
      }
    }
  }
}

function validateNumericalTruthPayload(payload, groundTruthList, pinnedVersion, errors) {
  if (payload.schemaVersion !== 1 || payload.sourceModelFileSha256 !== sha256(groundTruthList)) {
    errors.push("numerical ground truth: schema or source-model hash mismatch");
  }
  if (!pinnedVersion) errors.push("numerical ground truth: pinned OpenSeesPy version is unavailable");
  if (!Number.isInteger(payload.requiredIndependentRuns) || payload.requiredIndependentRuns < 2) {
    errors.push("numerical ground truth: requiredIndependentRuns must be >= 2");
  }
  const entries = Array.isArray(payload.models) ? payload.models : [];
  const byId = new Map(entries.map((entry) => [entry.modelId, entry]));
  if (entries.length !== byId.size || entries.length !== groundTruthList.length) {
    errors.push("numerical ground truth: model set must exactly match structural ground truth");
  }
  for (const model of groundTruthList) {
    const entry = byId.get(model.id);
    if (!entry) {
      errors.push(`numerical ground truth: missing '${model.id}'`);
      continue;
    }
    if (entry.inputSha256 !== sha256(model.model)) {
      errors.push(`numerical ground truth ${model.id}: input hash mismatch`);
    }
    if (entry.solver?.name !== "OpenSeesPy"
      || entry.solver?.packageVersion !== pinnedVersion
      || !entry.solver?.runtimePackage
      || !entry.solver?.runtimePackageVersion
      || !entry.solver?.version) {
      errors.push(`numerical ground truth ${model.id}: incomplete OpenSees identity`);
    }
    const combinations = model.model.load_combinations || [];
    if (combinations.length !== 1
      || entry.analysisSelection?.loadCombinationId !== combinations[0].id
      || canonicalJson(entry.analysisSelection?.factors) !== canonicalJson(combinations[0].factors)) {
      errors.push(`numerical ground truth ${model.id}: load-combination selection mismatch`);
    }
    if (entry.verification?.runCount < 2
      || entry.verification?.runCount !== payload.requiredIndependentRuns
      || entry.verification?.outputHashes?.length !== entry.verification.runCount) {
      errors.push(`numerical ground truth ${model.id}: fewer than two recorded independent runs`);
    }
    if (entry.verification?.outputHashes?.[0] !== sha256(entry.result)) {
      errors.push(`numerical ground truth ${model.id}: stored result hash mismatch`);
    }
    if (canonicalJson(entry.verification?.tolerances) !== canonicalJson(payload.numericTolerances)) {
      errors.push(`numerical ground truth ${model.id}: verification tolerance mismatch`);
    }
    if (entry.verification?.executionVariants?.length !== entry.verification?.runCount
      || new Set(entry.verification.executionVariants).size !== entry.verification.runCount) {
      errors.push(`numerical ground truth ${model.id}: execution variants are missing or duplicated`);
    }
    if (entry.verification?.solverConfigurations?.length !== entry.verification?.runCount
      || new Set(entry.verification.solverConfigurations.map(canonicalJson)).size < 2) {
      errors.push(`numerical ground truth ${model.id}: fewer than two distinct solver configurations`);
    }
    if (entry.verification?.equilibrium?.length !== entry.verification?.runCount
      || entry.verification.equilibrium.some((check) => check?.pass !== true)) {
      errors.push(`numerical ground truth ${model.id}: missing successful equilibrium checks`);
    }
    const recomputedEquilibrium = checkStaticEquilibrium(model.model, entry.result, entry.analysisSelection);
    if (!recomputedEquilibrium.pass) {
      errors.push(
        `numerical ground truth ${model.id}: recomputed equilibrium failed (${recomputedEquilibrium.failures.join("; ")})`,
      );
    }
    const recomputedAnalytical = checkAnalyticalOracle(model.id, model.model, entry.result);
    if (!recomputedAnalytical.pass) {
      errors.push(
        `numerical ground truth ${model.id}: analytical oracle failed (${recomputedAnalytical.failures.join("; ")})`,
      );
    }
    if (entry.verification?.analytical?.length !== entry.verification?.runCount
      || entry.verification.analytical.some((check) => check?.pass !== true)) {
      errors.push(`numerical ground truth ${model.id}: missing analytical-oracle records`);
    }
    if (model.model.coordinate_system?.dimension === "2d") {
      const independentRecord = entry.verification?.independentLinearSolver;
      if (independentRecord?.version !== INDEPENDENT_SOLVER_VERSION
        || independentRecord?.inputSha256 !== sha256(model.model)
        || !independentRecord?.outputSha256) {
        errors.push(`numerical ground truth ${model.id}: missing independent direct-stiffness verification`);
      } else {
        try {
          const independentResult = solveIndependentLinearModel(model.model);
          if (independentRecord.outputSha256 !== sha256(independentResult)) {
            errors.push(`numerical ground truth ${model.id}: independent solution hash mismatch`);
          }
          const comparison = compareAnalysisResults(
            independentResult,
            entry.result,
            {
              nodeMapping: Object.fromEntries(model.model.nodes.map((node) => [String(node.id), String(node.id)])),
              elementMapping: Object.fromEntries(
                model.model.elements.map((element) => [String(element.id), String(element.id)]),
              ),
              elementOrientation: Object.fromEntries(
                model.model.elements.map((element) => [String(element.id), "same"]),
              ),
            },
            { numericAbsolute: 1e-7, numeric: 1e-6 },
          );
          if (!comparison.pass) {
            errors.push(
              `numerical ground truth ${model.id}: independent solution disagrees (${comparison.failures.slice(0, 3).join("; ")})`,
            );
          }
        } catch (error) {
          errors.push(`numerical ground truth ${model.id}: independent solution failed (${error.message})`);
        }
      }
    } else if (entry.verification?.independentLinearSolver !== null) {
      errors.push(`numerical ground truth ${model.id}: unexpected 2-D independent-solver record`);
    }
    const resultKeys = ["displacements", "reactions", "forces"];
    if (entry.result?.status !== "success"
      || !String(entry.result?.analysisMode || "").startsWith("opensees_")
      || resultKeys.some((key) => !entry.result?.[key] || typeof entry.result[key] !== "object")) {
      errors.push(`numerical ground truth ${model.id}: incomplete OpenSees response tree`);
    }
  }
}

function validateNumericalTruth(groundTruthList, errors) {
  if (!fs.existsSync(NUMERICAL_GROUND_TRUTH_FILE)) return;
  let payload;
  try {
    payload = JSON.parse(fs.readFileSync(NUMERICAL_GROUND_TRUTH_FILE, "utf8"));
  } catch (error) {
    errors.push(`numerical ground truth: invalid JSON (${error.message})`);
    return;
  }
  let pinnedVersion;
  try {
    const requirements = fs.readFileSync(OPENSEES_REQUIREMENTS_FILE, "utf8");
    pinnedVersion = requirements.match(/^openseespy==([^\s]+)$/m)?.[1];
  } catch (error) {
    errors.push(`numerical ground truth: cannot read OpenSees requirements (${error.message})`);
  }
  validateNumericalTruthPayload(payload, groundTruthList, pinnedVersion, errors);
}

function validate() {
  const errors = [];
  const numericalTruthAvailable = fs.existsSync(NUMERICAL_GROUND_TRUTH_FILE);
  const crossEngineTruth = fs.existsSync(CROSS_ENGINE_GROUND_TRUTH_FILE)
    ? JSON.parse(fs.readFileSync(CROSS_ENGINE_GROUND_TRUTH_FILE, "utf-8"))
    : { cases: [] };
  const groundTruthList = JSON.parse(fs.readFileSync(GROUND_TRUTH_FILE, "utf-8"));
  if (groundTruthList.length !== new Set(groundTruthList.map((entry) => entry.id)).size) {
    errors.push("ground truth model ids must be unique");
  }
  for (const entry of groundTruthList) {
    validateGroundTruthCoordinateContract(entry, errors);
    validateGroundTruthReferences(entry, errors);
  }
  validateNumericalTruth(groundTruthList, errors);
  const groundTruthModels = new Map(
    groundTruthList.map((item) => [item.id, item]),
  );
  const files = collectJsonFiles(SCENARIOS_DIR);
  const ids = new Map();
  const promptSignatures = new Map();
  const attachmentNames = new Map();
  const familyCounts = Object.fromEntries(Object.keys(TASK_FAMILIES).map((family) => [family, 0]));
  const familyLocaleCounts = Object.fromEntries(
    Object.keys(TASK_FAMILIES).flatMap((family) => [[`${family}/zh`, 0], [`${family}/en`, 0]]),
  );
  const splitCounts = { core: 0, auxiliary: 0 };

  for (const file of files) {
    const relative = rel(file);
    const parts = relative.replace(/^scenarios\//, "").split("/");
    if (parts.length !== 2) {
      errors.push(`${relative}: scenarios must live directly under scenarios/<taskFamily>/<id>.json`);
      continue;
    }

    const [familyDir, fileName] = parts;
    if (!TASK_FAMILIES[familyDir]) {
      errors.push(`${relative}: unknown task family directory "${familyDir}"`);
      continue;
    }

    let parsed;
    try {
      parsed = JSON.parse(fs.readFileSync(file, "utf-8"));
    } catch (error) {
      errors.push(`${relative}: invalid JSON (${error.message})`);
      continue;
    }

    if (Array.isArray(parsed) || !parsed || typeof parsed !== "object") {
      errors.push(`${relative}: expected one scenario object, not an array or primitive`);
      continue;
    }

    const scenario = parsed;
    for (const field of REQUIRED_FIELDS) {
      if (scenario[field] === undefined || scenario[field] === null) {
        errors.push(`${relative}: missing required field "${field}"`);
      }
    }

    if (scenario.maxRetries !== SCENARIO_MAX_RETRIES) {
      errors.push(`${relative}: maxRetries must be ${SCENARIO_MAX_RETRIES}`);
    }

    const expectedFileName = `${scenario.id}.json`;
    if (fileName !== expectedFileName) {
      errors.push(`${relative}: file name must match id (${expectedFileName})`);
    }

    if (ids.has(scenario.id)) {
      errors.push(`${relative}: duplicate scenario id "${scenario.id}" also found in ${ids.get(scenario.id)}`);
    } else if (scenario.id) {
      ids.set(scenario.id, relative);
    }

    if (scenario.taskFamily !== familyDir) {
      errors.push(`${relative}: taskFamily "${scenario.taskFamily}" does not match directory "${familyDir}"`);
    }

    const expectedBenchmarkType = BENCHMARK_STRUCTURE_TYPE[scenario.structureType] || scenario.structureType;
    if (scenario.benchmarkStructureType !== expectedBenchmarkType) {
      errors.push(
        `${relative}: benchmarkStructureType must be "${expectedBenchmarkType}" for structureType "${scenario.structureType}"`,
      );
    }

    const expectedSplit = TASK_FAMILIES[familyDir].split;
    if (scenario.split !== expectedSplit) {
      errors.push(`${relative}: split must be "${expectedSplit}" for ${familyDir}`);
    }

    familyCounts[familyDir] += 1;
    if (scenario.locale === "zh" || scenario.locale === "en") {
      familyLocaleCounts[`${familyDir}/${scenario.locale}`] += 1;
    } else {
      errors.push(`${relative}: locale must be "zh" or "en"`);
    }
    if (scenario.split) splitCounts[scenario.split] = (splitCounts[scenario.split] || 0) + 1;

    if (scenario.locale === "en") {
      const userText = [
        scenario.description || "",
        scenario.message || "",
        ...(Array.isArray(scenario.turns) ? scenario.turns.map((turn) => turn.message || "") : []),
        ...engineeringSpecifications(scenario),
      ].join(" ");
      if (hasCjk(userText)) {
        errors.push(`${relative}: English-locale description/message must not contain CJK text`);
      }
      if (Array.isArray(scenario.tags)) {
        if (scenario.tags.includes("zh")) errors.push(`${relative}: English-locale scenario must not have a "zh" tag`);
        if (!scenario.tags.includes("en")) errors.push(`${relative}: English-locale scenario must have an "en" tag`);
      }
    }

    if (scenario.inputModality !== "image") {
      const promptSignature = [
        scenario.taskFamily,
        scenario.benchmarkStructureType,
        scenario.inputModality,
        normalizePromptSignature(scenarioPromptText(scenario)),
      ].join("::");
      if (promptSignatures.has(promptSignature)) {
        errors.push(
          `${relative}: duplicate normalized prompt signature also found in ${promptSignatures.get(promptSignature)}`,
        );
      } else {
        promptSignatures.set(promptSignature, relative);
      }
    }

    if (!Array.isArray(scenario.evaluationFocus) || scenario.evaluationFocus.length === 0) {
      errors.push(`${relative}: evaluationFocus must be a non-empty array`);
    } else {
      for (const focus of scenario.evaluationFocus) {
        if (!EVALUATION_FOCUS.has(focus)) {
          errors.push(`${relative}: unknown evaluationFocus "${focus}"`);
        }
      }
    }

    const hasMessage = typeof scenario.message === "string" && scenario.message.trim().length > 0;
    const hasTurns = Array.isArray(scenario.turns) && scenario.turns.length > 0;
    if (!hasMessage && !hasTurns) {
      errors.push(`${relative}: scenario must define message or turns`);
    }

    const assertions = [
      ...(Array.isArray(scenario.expect?.assertions) ? scenario.expect.assertions : []),
      ...(Array.isArray(scenario.turns)
        ? scenario.turns.flatMap((turn) => Array.isArray(turn.assertions) ? turn.assertions : [])
        : []),
    ];
    if (assertions.length === 0) {
      errors.push(`${relative}: scenario must define at least one assertion`);
    }

    const specificationGroups = [
      {
        assertions: scenario.expect?.assertions,
        specification: scenario.engineeringSpecification,
        label: "scenario",
      },
      ...(Array.isArray(scenario.turns)
        ? scenario.turns.map((turn, index) => ({
            assertions: turn.assertions,
            specification: turn.engineeringSpecification,
            label: `turn ${index + 1}`,
          }))
        : []),
    ];
    for (const group of specificationGroups) {
      const specification = group.specification ?? scenario.engineeringSpecification;
      if (typeof specification !== "string" || !Array.isArray(group.assertions)) continue;
      const modelAssertion = group.assertions.find((assertion) => assertion.type === "model_matches");
      const groundTruth = modelAssertion
        ? groundTruthModels.get(modelAssertion.groundTruthId)
        : null;
      if (!groundTruth) continue;
      validateDeclaredSectionProperties(
        specification,
        groundTruth,
        modelAssertion.tolerances?.property ?? 0.05,
        `${relative} ${group.label}`,
        errors,
      );
      if (["image", "dxf"].includes(scenario.inputModality)
        && scenario.inputContract?.completeness === "complete") {
        validateDeclaredMaterialProperties(
          specification,
          groundTruth,
          modelAssertion.tolerances?.property ?? 0.05,
          `${relative} ${group.label}`,
          errors,
        );
        validateDeclaredAnalysisSettings(specification, `${relative} ${group.label}`, errors);
      }
    }

    const assertionTypes = assertions.map((assertion) => assertion.type);
    const focus = new Set(Array.isArray(scenario.evaluationFocus) ? scenario.evaluationFocus : []);
    const expectedEngineId = scenario.analysisEngineTarget || (
      scenario.analysisSkillTarget ? ANALYSIS_SKILL_ENGINE_IDS[scenario.analysisSkillTarget] : undefined
    );

    if (scenario.taskFamily === "interactive_robustness"
      && ISSUE_SPECIFIC_INTERACTION_CATEGORIES.has(scenario.category)
      && !assertionTypes.includes("natural_language")) {
      errors.push(
        `${relative}: ${scenario.category} scenarios must semantically verify that the specific `
        + "invalid, ambiguous, or conflicting input was identified",
      );
    }

    if (scenario.taskFamily === "multimodal_reverse_engineering") {
      for (const attachment of collectAttachments(scenario)) {
        const originalName = String(attachment.originalName || "");
        if (!NEUTRAL_DRAWING_NAME.test(originalName)) {
          errors.push(`${relative}: attachment originalName must use a neutral drawing-NNN.png/dxf name`);
        } else if (attachmentNames.has(originalName)) {
          errors.push(
            `${relative}: attachment name ${originalName} is also used in ${attachmentNames.get(originalName)}`,
          );
        } else {
          attachmentNames.set(originalName, relative);
        }
      }
    }

    if (scenario.inputModality === "image") {
      const imageAttachments = collectAttachments(scenario).filter((attachment) => (
        String(attachment.mimeType || "").startsWith("image/")
      ));
      if (imageAttachments.length === 0) {
        errors.push(`${relative}: image scenario must provide an image attachment`);
      }

      const taskText = [
        scenario.message || "",
        ...(Array.isArray(scenario.turns) ? scenario.turns.map((turn) => turn.message || "") : []),
      ].join(" ");
      if (/\d/.test(taskText)) {
        errors.push(`${relative}: image task instructions must not duplicate numeric engineering parameters`);
      }

      const contract = scenario.inputContract;
      const imageProvides = Array.isArray(contract?.imageProvides) ? contract.imageProvides : [];
      const specificationProvides = Array.isArray(contract?.specificationProvides)
        ? contract.specificationProvides
        : [];
      const specifications = engineeringSpecifications(scenario);
      if (contract?.completeness === "complete") {
        if (!hasExactly(imageProvides, COMPLETE_IMAGE_FIELDS)) {
          errors.push(`${relative}: complete image input must provide only topology, dimensions, supports, and loads`);
        }
        if (!hasExactly(specificationProvides, COMPLETE_SPECIFICATION_FIELDS)) {
          errors.push(`${relative}: complete engineering specification must provide only materials, sections, and analysis settings`);
        }
        if (specifications.length !== 1) {
          errors.push(`${relative}: complete image input must provide exactly one engineering specification`);
        } else if (IMAGE_ONLY_SPECIFICATION_TERMS.test(specifications[0])) {
          errors.push(`${relative}: engineering specification duplicates image-only geometry, support, or load evidence`);
        }
      } else if (contract?.completeness === "intentionally-incomplete") {
        const safeAssertions = ["has_interaction_questions", "no_bad_model", "should_not_analyze"];
        if (specifications.length !== 0
          || safeAssertions.some((type) => !assertionTypes.includes(type))) {
          errors.push(`${relative}: intentionally incomplete image input must withhold the specification and require safe clarification`);
        }
      } else {
        errors.push(`${relative}: image scenario must declare complete or intentionally-incomplete inputContract`);
      }
    }

    if (scenario.inputModality === "dxf") {
      const dxfAttachments = collectAttachments(scenario).filter((attachment) => (
        String(attachment.mimeType || "").toLowerCase().includes("dxf")
      ));
      if (dxfAttachments.length !== 1) {
        errors.push(`${relative}: DXF scenario must provide exactly one DXF attachment`);
      }

      const taskText = [
        scenario.message || "",
        ...(Array.isArray(scenario.turns) ? scenario.turns.map((turn) => turn.message || "") : []),
      ].join(" ");
      if (/\d/.test(taskText)) {
        errors.push(`${relative}: DXF task instructions must not duplicate numeric drawing evidence`);
      }

      const contract = scenario.inputContract;
      const dxfProvides = Array.isArray(contract?.dxfProvides) ? contract.dxfProvides : [];
      const specificationProvides = Array.isArray(contract?.specificationProvides)
        ? contract.specificationProvides
        : [];
      const structuralDxf = hasExactly(dxfProvides, COMPLETE_IMAGE_FIELDS);
      const architecturalDxf = hasExactly(dxfProvides, ARCHITECTURAL_DXF_FIELDS);
      const architecturalSpecificationFields = scenario.tags?.includes("3d")
        ? ["vertical-geometry", ...ARCHITECTURAL_DXF_SPECIFICATION_FIELDS]
        : ARCHITECTURAL_DXF_SPECIFICATION_FIELDS;
      const specifications = engineeringSpecifications(scenario);

      if (contract?.completeness !== "complete") {
        errors.push(`${relative}: DXF scenario must declare a complete inputContract`);
      } else if (structuralDxf) {
        if (!hasExactly(specificationProvides, COMPLETE_SPECIFICATION_FIELDS)) {
          errors.push(
            `${relative}: complete structural DXF must provide topology, dimensions, supports, and loads, `
            + "while the engineering specification provides materials, sections, and analysis settings",
          );
        }
        for (const attachment of dxfAttachments) {
          const content = fs.readFileSync(resolveAttachment(attachment.relPath), "utf-8");
          if (!/\bSUPPORT\b/.test(content) || !/(?:FIXED|PIN|ROLLER FREE X)/.test(content)) {
            errors.push(`${relative}: structural DXF does not contain explicit support evidence`);
          }
          if (!/\bLOAD\b/.test(content) || !/(?:global [XYZ]|global F[XYZ]|global -Z)/.test(content)) {
            errors.push(`${relative}: structural DXF does not contain explicit signed load-direction evidence`);
          }
        }
      } else if (architecturalDxf) {
        if (!hasExactly(specificationProvides, architecturalSpecificationFields)) {
          errors.push(`${relative}: architectural DXF specification contract is incomplete`);
        }
        if (specifications.length !== 1) {
          errors.push(`${relative}: architectural DXF must provide exactly one explicit engineering specification`);
        }
      } else {
        errors.push(`${relative}: DXF inputContract does not declare a supported evidence split`);
      }
    }

    if (numericalTruthAvailable && assertionTypes.includes("has_analysis")) {
      const numericalEngine = normalizeEngineKey(scenario.analysisEngineTarget) || "opensees";
      for (const modelAssertion of assertions.filter((assertion) => assertion.type === "model_matches")) {
        const engineTruthAvailable = numericalEngine === "opensees"
          || Boolean(findEngineGroundTruth(crossEngineTruth, modelAssertion.groundTruthId, numericalEngine));
        const wired = assertions.some((assertion) => (
          assertion.type === "numerical_matches"
          && assertion.groundTruthId === modelAssertion.groundTruthId
        ));
        if (engineTruthAvailable && !wired) {
          errors.push(
            `${relative}: complete numerical truth exists but '${modelAssertion.groundTruthId}' is not scored`,
          );
        } else if (!engineTruthAvailable) {
          errors.push(
            `${relative}: analyzable model '${modelAssertion.groundTruthId}' has no lossless `
            + `${numericalEngine} numerical truth; reclassify unsupported adapter input as safe non-execution`,
          );
        }
      }
    }

    if (scenario.tags?.includes("unsupported-2d-commercial-adapter")) {
      const safeBoundaryAssertions = ["has_interaction_questions", "safe_non_execution"];
      if (!focus.has("interaction")
        || safeBoundaryAssertions.some((type) => !assertionTypes.includes(type))
        || assertionTypes.some((type) => ["model_matches", "has_analysis", "engine_match", "numerical_matches"].includes(type))) {
        errors.push(
          `${relative}: unsupported 2-D commercial-adapter scenarios must require clarification and safe non-execution`,
        );
      }
      if (!["builtin-pkpm", "builtin-yjk"].includes(scenario.analysisEngineTarget)) {
        errors.push(`${relative}: unsupported commercial-adapter tag requires PKPM or YJK target`);
      }
    }

    if (scenario.analysisSkillTarget !== undefined && !ANALYSIS_SKILL_ENGINE_IDS[scenario.analysisSkillTarget]) {
      errors.push(`${relative}: unknown analysisSkillTarget "${scenario.analysisSkillTarget}"`);
    }
    if (scenario.analysisEngineTarget !== undefined) {
      if (!Object.values(ANALYSIS_SKILL_ENGINE_IDS).includes(scenario.analysisEngineTarget)) {
        errors.push(`${relative}: unknown analysisEngineTarget "${scenario.analysisEngineTarget}"`);
      }
      if (scenario.analysisSkillTarget && scenario.analysisEngineTarget !== ANALYSIS_SKILL_ENGINE_IDS[scenario.analysisSkillTarget]) {
        errors.push(
          `${relative}: analysisEngineTarget "${scenario.analysisEngineTarget}" does not match ` +
          `analysisSkillTarget "${scenario.analysisSkillTarget}"`,
        );
      }
    }

    for (const assertion of assertions) {
      if (!ASSERTION_TYPES.has(assertion.type)) {
        errors.push(`${relative}: unknown assertion type "${assertion.type}"`);
        continue;
      }
      if (assertion.type === "skill_match" && assertion.primary !== scenario.skillTarget) {
        errors.push(
          `${relative}: skill_match primary "${assertion.primary}" must match skillTarget "${scenario.skillTarget}"`,
        );
      }
      if (assertion.type === "structural_type" && assertion.expected !== scenario.structureType) {
        const pair = `${scenario.structureType}/${assertion.expected}`;
        if (!ALLOWED_STRUCTURAL_TYPE_PAIRS.has(pair)) {
          errors.push(
            `${relative}: structural_type expected "${assertion.expected}" must match structureType "${scenario.structureType}"`,
          );
        }
      }
      if (assertion.type === "model_matches") {
        const groundTruth = groundTruthModels.get(assertion.groundTruthId);
        if (!groundTruth) {
          errors.push(`${relative}: unknown groundTruthId "${assertion.groundTruthId}"`);
        } else {
          const pair = `${scenario.structureType}/${groundTruth.inferredType}`;
          if (scenario.structureType !== groundTruth.inferredType && !ALLOWED_STRUCTURAL_TYPE_PAIRS.has(pair)) {
            errors.push(
              `${relative}: groundTruth "${assertion.groundTruthId}" type "${groundTruth.inferredType}" ` +
              `must match structureType "${scenario.structureType}"`,
            );
          }
        }
        if (assertion.loadAxes !== undefined) {
          const invalidAxes = Array.isArray(assertion.loadAxes)
            ? assertion.loadAxes.filter((axis) => !["x", "y", "z"].includes(String(axis).toLowerCase()))
            : ["(not an array)"];
          if (invalidAxes.length > 0) {
            errors.push(`${relative}: model_matches loadAxes must contain only x, y, or z`);
          }
        }
        if (assertion.matcherVersion !== undefined && assertion.matcherVersion !== "v1") {
          errors.push(`${relative}: model_matches matcherVersion may only be "v1" for archived-run reproduction`);
        }
        if (assertion.tolerances !== undefined) {
          const allowedToleranceKeys = new Set(["span", "coordinate", "load", "property"]);
          if (!assertion.tolerances || typeof assertion.tolerances !== "object" || Array.isArray(assertion.tolerances)) {
            errors.push(`${relative}: model_matches tolerances must be an object`);
          } else {
            for (const [key, value] of Object.entries(assertion.tolerances)) {
              if (!allowedToleranceKeys.has(key)) {
                errors.push(`${relative}: model_matches has unknown tolerance "${key}"`);
              } else if (typeof value !== "number" || !Number.isFinite(value) || value < 0) {
                errors.push(`${relative}: model_matches tolerance "${key}" must be a finite non-negative number`);
              } else if (["load", "property"].includes(key) && value > 1) {
                errors.push(`${relative}: model_matches tolerance "${key}" must be <= 1`);
              }
            }
          }
        }
        if (assertion.matcherVersion !== "v1") {
          for (const [key, expected] of Object.entries(STRICT_MODEL_TOLERANCES)) {
            if (assertion.tolerances?.[key] !== expected) {
              errors.push(`${relative}: strict model_matches tolerance "${key}" must be ${expected}`);
            }
          }
        }
      }
      if ((assertion.type === "has_model" || assertion.type === "model_matches") && !focus.has("modeling")) {
        errors.push(`${relative}: ${assertion.type} assertion requires "modeling" evaluationFocus`);
      }
      if (assertion.type === "model_matches" && !focus.has("model_match")) {
        errors.push(`${relative}: model_matches assertion requires "model_match" evaluationFocus`);
      }
      if (assertion.type === "has_analysis" && !focus.has("analysis")) {
        errors.push(`${relative}: has_analysis assertion requires "analysis" evaluationFocus`);
      }
      if (assertion.type === "numerical_matches") {
        if (!groundTruthModels.has(assertion.groundTruthId)) {
          errors.push(`${relative}: numerical_matches has unknown groundTruthId "${assertion.groundTruthId}"`);
        }
        if (!focus.has("analysis") || !focus.has("numerical_match")) {
          errors.push(`${relative}: numerical_matches requires "analysis" and "numerical_match" evaluationFocus`);
        }
        if (scenario.analysisEngineTarget && assertion.engineId !== scenario.analysisEngineTarget) {
          errors.push(
            `${relative}: numerical_matches engineId must match analysisEngineTarget `
            + `"${scenario.analysisEngineTarget}"`,
          );
        }
        const tolerances = assertion.tolerances || {};
        for (const key of ["numeric", "numericAbsolute"]) {
          if (tolerances[key] !== undefined
            && (typeof tolerances[key] !== "number" || !Number.isFinite(tolerances[key]) || tolerances[key] < 0)) {
            errors.push(`${relative}: numerical_matches tolerance "${key}" must be finite and non-negative`);
          }
        }
        for (const [key, expected] of Object.entries({
          ...STRICT_MODEL_TOLERANCES,
          ...STRICT_NUMERICAL_TOLERANCES,
        })) {
          if (tolerances[key] !== expected) {
            errors.push(`${relative}: numerical_matches tolerance "${key}" must be ${expected}`);
          }
        }
      }
      if (assertion.type === "engine_match") {
        if (!focus.has("engine_match")) {
          errors.push(`${relative}: engine_match assertion requires "engine_match" evaluationFocus`);
        }
        if (!focus.has("analysis")) {
          errors.push(`${relative}: engine_match assertion requires "analysis" evaluationFocus`);
        }
        if (expectedEngineId && assertion.expected !== expectedEngineId) {
          errors.push(
            `${relative}: engine_match expected "${assertion.expected}" must match analysis target "${expectedEngineId}"`,
          );
        }
        if (assertion.skillId && scenario.analysisSkillTarget && assertion.skillId !== scenario.analysisSkillTarget) {
          errors.push(
            `${relative}: engine_match skillId "${assertion.skillId}" must match analysisSkillTarget ` +
            `"${scenario.analysisSkillTarget}"`,
          );
        }
      }
      if (assertion.type === "has_interaction_questions" && !focus.has("interaction")) {
        errors.push(`${relative}: has_interaction_questions assertion requires "interaction" evaluationFocus`);
      }
      if (
        assertion.type === "analysis_or_interaction"
        && !focus.has("interaction")
        && !focus.has("analysis")
      ) {
        errors.push(`${relative}: analysis_or_interaction assertion requires "interaction" or "analysis" evaluationFocus`);
      }
      if (assertion.type === "safe_non_execution") {
        if (!focus.has("interaction")) {
          errors.push(`${relative}: safe_non_execution assertion requires "interaction" evaluationFocus`);
        }
        if (assertion.reasonIncludes !== undefined) {
          errors.push(`${relative}: safe_non_execution must not require implementation-specific rejection wording`);
        }
      }
      if (assertion.type === "has_report" && !focus.has("report")) {
        errors.push(`${relative}: has_report assertion requires "report" evaluationFocus`);
      }
      if (assertion.type === "report_numerical_consistency"
        && (!focus.has("report") || !focus.has("analysis"))) {
        errors.push(
          `${relative}: report_numerical_consistency requires "report" and "analysis" evaluationFocus`,
        );
      }
    }
    if (focus.has("model_match") && !assertionTypes.includes("model_matches")) {
      errors.push(`${relative}: "model_match" evaluationFocus requires a model_matches assertion`);
    }
    if (focus.has("numerical_match") && !assertionTypes.includes("numerical_matches")) {
      errors.push(`${relative}: "numerical_match" evaluationFocus requires a numerical_matches assertion`);
    }
    if (focus.has("report") && !assertionTypes.includes("has_report")) {
      errors.push(`${relative}: "report" evaluationFocus requires a has_report assertion`);
    }
    if (assertionTypes.includes("has_report")
      && assertionTypes.includes("numerical_matches")
      && !assertionTypes.includes("report_numerical_consistency")) {
      errors.push(`${relative}: numerical reports require a report_numerical_consistency assertion`);
    }
    if (focus.has("engine_match") && !assertionTypes.includes("engine_match")) {
      errors.push(`${relative}: "engine_match" evaluationFocus requires an engine_match assertion`);
    }

    for (const attachment of collectAttachments(scenario)) {
      if (!attachment.relPath) {
        errors.push(`${relative}: attachment is missing relPath`);
        continue;
      }
      const attachmentPath = resolveAttachment(attachment.relPath);
      if (!fs.existsSync(attachmentPath)) {
        errors.push(`${relative}: attachment does not exist (${attachment.relPath})`);
      }
    }
  }

  for (const [family, spec] of Object.entries(TASK_FAMILIES)) {
    if (familyCounts[family] !== spec.count) {
      errors.push(`${family}: expected ${spec.count} scenarios, found ${familyCounts[family]}`);
    }
    for (const locale of ["zh", "en"]) {
      const actual = familyLocaleCounts[`${family}/${locale}`];
      if (actual !== spec.count / 2) {
        errors.push(`${family}/${locale}: expected ${spec.count / 2} scenarios, found ${actual}`);
      }
    }
  }

  if (splitCounts.core !== 100) {
    errors.push(`core split: expected 100 scenarios, found ${splitCounts.core}`);
  }
  if (splitCounts.auxiliary !== 50) {
    errors.push(`auxiliary split: expected 50 scenarios, found ${splitCounts.auxiliary}`);
  }

  if (errors.length > 0) {
    process.stderr.write(`Scenario validation failed with ${errors.length} issue(s):\n`);
    for (const error of errors) {
      process.stderr.write(`- ${error}\n`);
    }
    process.exitCode = 1;
    return;
  }

  process.stdout.write(
    `Scenario validation passed: ${files.length} files, ${ids.size} unique scenarios, ` +
    `${familyCounts.standard_workflow}/${familyCounts.interactive_robustness}/` +
    `${familyCounts.multimodal_reverse_engineering} by task family.\n`,
  );
}

if (require.main === module) validate();

module.exports = {
  validateDeclaredAnalysisSettings,
  validateDeclaredMaterialProperties,
  validateDeclaredSectionProperties,
  validateNumericalTruthPayload,
};
