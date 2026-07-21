const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const {
  buildValidationEntry,
  compareCommercialEngineResponses,
  compareEngineMetrics,
  extractEngineMetrics,
  normalizeCommercialEngineResponse,
} = require("../lib/cross-engine-ground-truth.cjs");
const { canonicalJson, sha256 } = require("../lib/numerical-ground-truth.cjs");

const BENCH_ROOT = path.resolve(__dirname, "..");
const SCLAW_ROOT = path.resolve(BENCH_ROOT, "../..");
const CASES_FILE = path.join(BENCH_ROOT, "fixtures", "cross-engine-ground-truth-cases.json");
const MODELS_FILE = path.join(BENCH_ROOT, "fixtures", "ground-truth-models.json");
const DEFAULT_OUTPUT = path.join(BENCH_ROOT, "fixtures", "cross-engine-ground-truth-validation.json");
const WORKER = path.join(__dirname, "cross-engine-ground-truth-worker.py");
const ENGINES = ["opensees", "pkpm", "yjk"];

function parseArgs(argv) {
  const options = { output: DEFAULT_OUTPUT, python: null, caseIds: [], verify: false };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--output") options.output = path.resolve(argv[++index]);
    else if (arg === "--python") options.python = argv[++index];
    else if (arg === "--case") options.caseIds.push(argv[++index]);
    else if (arg === "--verify") options.verify = true;
    else throw new Error(`Unknown argument: ${arg}`);
  }
  if (options.verify && options.caseIds.length > 0) {
    throw new Error("--verify covers the full validation set and cannot be combined with --case");
  }
  return options;
}

function pythonCandidates(explicit) {
  if (explicit) return [explicit];
  const executable = process.platform === "win32" ? "python.exe" : "python";
  return [
    process.env.SCLAW_ANALYSIS_PYTHON,
    path.join(SCLAW_ROOT, "backend", ".venv", process.platform === "win32" ? "Scripts" : "bin", executable),
    process.env.USERPROFILE
      ? path.join(process.env.USERPROFILE, ".structureclaw", ".venv", process.platform === "win32" ? "Scripts" : "bin", executable)
      : null,
    "python3",
    "python",
  ].filter(Boolean);
}

function resolvePython(explicit) {
  for (const candidate of pythonCandidates(explicit)) {
    const probe = spawnSync(candidate, ["-c", "import openseespy, pydantic"], {
      encoding: "utf8", windowsHide: true, timeout: 30_000,
    });
    if (probe.status === 0) return candidate;
  }
  throw new Error("No Python with OpenSeesPy and Pydantic was found; pass --python");
}

function geometricArea(section) {
  const shape = section?.shape || {};
  const kind = String(shape.kind || section?.type || "").toLowerCase();
  if (["rect", "rectangle", "rectangular"].includes(kind)) {
    return Number(shape.B) * Number(shape.H) / 1e6;
  }
  if (["h", "i", "i-section", "h-section"].includes(kind)) {
    const height = Number(shape.H);
    const width = Number(shape.B);
    const web = Number(shape.tw);
    const flange = Number(shape.tf);
    return (2 * width * flange + Math.max(0, height - 2 * flange) * web) / 1e6;
  }
  const area = Number(section?.properties?.A);
  if (!Number.isFinite(area) || area <= 0) {
    throw new Error(`Section '${section?.id}' has no usable geometric area`);
  }
  return area;
}

function modelDimension(model) {
  return String(
    model?.coordinate_system?.dimension
      || model?.metadata?.frameDimension
      || "",
  ).toLowerCase();
}

function hasGeometricSection(section) {
  const shape = section?.shape || {};
  const kind = String(shape.kind || "").toLowerCase();
  if (["rect", "rectangle", "rectangular"].includes(kind)) {
    return Number.isFinite(Number(shape.B)) && Number(shape.B) > 0
      && Number.isFinite(Number(shape.H)) && Number(shape.H) > 0;
  }
  if (["h", "i", "i-section", "h-section"].includes(kind)) {
    return ["H", "B", "tw", "tf"].every((key) => Number.isFinite(Number(shape[key])) && Number(shape[key]) > 0);
  }
  return false;
}

function storyFloorLoads(story) {
  if (Array.isArray(story?.floor_loads) && story.floor_loads.length > 0) {
    return story.floor_loads.map((load) => ({ type: load.type, value: Number(load.value) }));
  }
  const declared = [];
  if (Number.isFinite(Number(story?.dead_load))) {
    declared.push({ type: "dead", value: Number(story.dead_load) });
  }
  if (Number.isFinite(Number(story?.live_load))) {
    declared.push({ type: "live", value: Number(story.live_load) });
  }
  if (declared.length > 0) return declared;
  if (Number.isFinite(Number(story?.floorLoad))) {
    return [{ type: "dead", value: Number(story.floorLoad) }];
  }
  return [];
}

function classifyCrossEngineSupport(entry) {
  const model = entry?.model || {};
  if (modelDimension(model) !== "3d") {
    return {
      supported: false,
      reasonCode: "commercial_adapters_require_3d_story_model",
      reason: "PKPM and YJK require a 3-D standard-floor model; a 2-D model cannot be extruded without inventing geometry.",
    };
  }
  if (!Array.isArray(model.stories) || model.stories.length === 0
    || model.stories.some((story) => !Number.isFinite(Number(story?.height)) || Number(story.height) <= 0)) {
    return {
      supported: false,
      reasonCode: "missing_story_geometry",
      reason: "The commercial adapters require explicit positive story heights.",
    };
  }
  if (model.stories.some((story) => storyFloorLoads(story).length === 0)) {
    return {
      supported: false,
      reasonCode: "missing_story_floor_load",
      reason: "No declared story floor load is available for a common three-engine gravity case.",
    };
  }
  const unsupportedSection = (model.sections || []).find((section) => !hasGeometricSection(section));
  if (unsupportedSection) {
    return {
      supported: false,
      reasonCode: "missing_physical_section_geometry",
      reason: `Section '${unsupportedSection.id}' has stiffness properties but no complete physical dimensions; mapping it to a commercial section would not be lossless.`,
    };
  }
  const unsupportedElement = (model.elements || []).find((element) => !["beam", "column"].includes(element.type));
  if (unsupportedElement) {
    return {
      supported: false,
      reasonCode: "unsupported_commercial_element_type",
      reason: `Element '${unsupportedElement.id}' has unsupported type '${unsupportedElement.type}'.`,
    };
  }
  return {
    supported: true,
    reasonCode: "supported_common_3d_story_model",
    reason: "The 3-D story geometry, physical sections, and story floor loads can be represented by all three engines.",
  };
}

function memberSelfWeightLoads(model) {
  const materials = new Map((model.materials || []).map((item) => [String(item.id), item]));
  const sections = new Map((model.sections || []).map((item) => [String(item.id), item]));
  return (model.elements || []).map((element) => {
    const material = materials.get(String(element.material));
    const section = sections.get(String(element.section));
    const density = Number(material?.rho);
    if (!Number.isFinite(density) || density <= 0) {
      throw new Error(`Element '${element.id}' has no positive material density`);
    }
    return {
      type: "distributed",
      element: element.id,
      reference_frame: "global",
      wx: 0,
      wy: 0,
      wz: -(density * geometricArea(section) * 9.80665 / 1000),
      source: "cross_engine_geometric_member_self_weight",
    };
  });
}

function deriveCommonModel(source, caseId) {
  const model = structuredClone(source);
  let elevation = 0;
  model.project = { ...(model.project || {}), name: caseId };
  model.stories = (model.stories || []).map((story) => {
    const floorLoads = storyFloorLoads(story);
    const deadLoad = floorLoads
      .filter((load) => String(load.type).toLowerCase() === "dead")
      .reduce((sum, load) => sum + Number(load.value), 0);
    const liveLoad = floorLoads
      .filter((load) => String(load.type).toLowerCase() === "live")
      .reduce((sum, load) => sum + Number(load.value), 0);
    const next = {
      ...story,
      elevation,
      floor_loads: floorLoads,
      dead_load: deadLoad,
      live_load: liveLoad,
    };
    delete next.floorLoad;
    delete next.floorLoadUnit;
    elevation += Number(story.height);
    return next;
  });
  model.load_cases = [];
  model.load_combinations = [];
  return model;
}

function openSeesModel(commonModel) {
  const model = structuredClone(commonModel);
  model.load_cases = [
    { id: "DL", type: "dead", loads: [] },
    { id: "SELF_WEIGHT", type: "dead", loads: memberSelfWeightLoads(model) },
  ];
  model.load_combinations = [{
    id: "CROSS_ENGINE_DL",
    name: "Cross-engine dead load",
    factors: { DL: 1, SELF_WEIGHT: 1 },
  }];
  return model;
}

function engineEnvironment(engine, tempRoot, caseId) {
  const env = { ...process.env };
  if (engine === "pkpm") {
    if (!env.PKPM_CYCLE_PATH) throw new Error("PKPM_CYCLE_PATH is required for three-engine validation");
    env.PKPM_WORK_DIR = path.join(tempRoot, caseId, "pkpm-work");
  }
  if (engine === "yjk") {
    if (!env.YJKS_ROOT && !env.YJK_PATH) {
      throw new Error("YJKS_ROOT or YJK_PATH is required for three-engine validation");
    }
    env.YJK_WORK_DIR = path.join(tempRoot, caseId, "yjk-work");
    env.YJK_CLOSE_AFTER_RUN = "1";
  }
  return env;
}

function runEngine(engine, model, definition, options, tempRoot, runNumber) {
  const runId = `${definition.id}-run-${runNumber}`;
  const caseDir = path.join(tempRoot, definition.id, `run-${runNumber}`);
  fs.mkdirSync(caseDir, { recursive: true });
  const input = path.join(caseDir, `${engine}-input.json`);
  const output = path.join(caseDir, `${engine}-output.json`);
  const parameters = engine === "opensees"
    ? { loadCombinationId: "CROSS_ENGINE_DL", floorLoadTransferMode: "auto_code_cn" }
    : { timeout: 600, traceId: runId };
  fs.writeFileSync(input, canonicalJson({ model, parameters }), "utf8");
  const child = spawnSync(options.python, [
    WORKER,
    "--sclaw-root", SCLAW_ROOT,
    "--engine", engine,
    "--input", input,
    "--output", output,
  ], {
    cwd: BENCH_ROOT,
    env: engineEnvironment(engine, tempRoot, runId),
    encoding: "utf8",
    windowsHide: true,
    timeout: 15 * 60 * 1000,
    maxBuffer: 20 * 1024 * 1024,
  });
  if (child.error) throw child.error;
  if (child.status !== 0) {
    const detail = [child.stderr, child.stdout].filter(Boolean).join("\n").trim();
    throw new Error(`${engine} worker failed (${child.status}): ${detail}`);
  }
  if (!fs.existsSync(output)) throw new Error(`${engine} worker produced no output`);
  return {
    ...JSON.parse(fs.readFileSync(output, "utf8")),
    inputSha256: sha256(model),
  };
}

function identityMappings(model) {
  return {
    nodeMapping: Object.fromEntries((model.nodes || []).map((node) => [String(node.id), String(node.id)])),
    elementMapping: Object.fromEntries((model.elements || []).map((element) => [String(element.id), String(element.id)])),
    elementOrientation: Object.fromEntries((model.elements || []).map((element) => [String(element.id), "same"])),
  };
}

function verifyRepeatedEngineRun(engine, model, firstRun, secondRun) {
  const tolerances = { numeric: 1e-4, numericAbsolute: 1e-8 };
  if (canonicalJson(firstRun.identity) !== canonicalJson(secondRun.identity)) {
    throw new Error(`${engine}: solver identity changed between repeated runs`);
  }
  if (engine === "opensees") {
    const first = extractEngineMetrics(engine, model, firstRun.result);
    const second = extractEngineMetrics(engine, model, secondRun.result);
    const comparison = compareEngineMetrics(second, first, tolerances);
    if (!comparison.pass) {
      throw new Error(`${engine}: repeated metrics disagree: ${comparison.failures.slice(0, 5).join("; ")}`);
    }
    return {
      runCount: 2,
      normalizedOutputHashes: [sha256(first), sha256(second)],
      ...comparison,
    };
  }
  const first = normalizeCommercialEngineResponse(engine, model, firstRun.result);
  const second = normalizeCommercialEngineResponse(engine, model, secondRun.result);
  const comparison = compareCommercialEngineResponses(
    second,
    first,
    identityMappings(model),
    tolerances,
  );
  if (!comparison.pass) {
    throw new Error(`${engine}: repeated responses disagree: ${comparison.failures.slice(0, 5).join("; ")}`);
  }
  return {
    runCount: 2,
    normalizedOutputHashes: [sha256(first), sha256(second)],
    ...comparison,
  };
}

function verifyCommitted(committed, generated, sourceById) {
  for (const field of ["sourceModelFileSha256", "caseDefinitionFileSha256"]) {
    if (committed[field] !== generated[field]) throw new Error(`${field} changed`);
  }
  const expected = new Map(committed.cases.map((entry) => [entry.caseId, entry]));
  if (expected.size !== generated.cases.length) throw new Error("Cross-engine validation case set changed");
  if (canonicalJson(committed.supportAudit) !== canonicalJson(generated.supportAudit)) {
    throw new Error("Cross-engine support audit changed");
  }
  for (const actual of generated.cases) {
    const prior = expected.get(actual.caseId);
    if (!prior) throw new Error(`Committed validation is missing '${actual.caseId}'`);
    if (prior.inputSha256 !== actual.inputSha256) throw new Error(`${actual.caseId}: input changed`);
    if (prior.validation.pass !== actual.validation.pass) throw new Error(`${actual.caseId}: validation status changed`);
    for (const engine of ENGINES) {
      if (canonicalJson(prior.engines[engine].identity) !== canonicalJson(actual.engines[engine].identity)) {
        throw new Error(`${actual.caseId}: ${engine} identity changed`);
      }
      if (prior.engines[engine].inputSha256 !== actual.engines[engine].inputSha256) {
        throw new Error(`${actual.caseId}: ${engine} input changed`);
      }
      if (prior.engines[engine].repeatability?.runCount !== 2
        || actual.engines[engine].repeatability?.runCount !== 2) {
        throw new Error(`${actual.caseId}: ${engine} is missing two-run repeatability evidence`);
      }
      if (engine !== "opensees") {
        const comparison = compareCommercialEngineResponses(
          actual.engines[engine].response,
          prior.engines[engine].response,
          identityMappings(sourceById.get(actual.provenance.sourceModelId)),
          { numeric: 1e-4, numericAbsolute: 1e-8 },
        );
        if (!comparison.pass) {
          throw new Error(`${actual.caseId}: ${engine} response changed: ${comparison.failures.slice(0, 5).join("; ")}`);
        }
      }
      for (const metric of Object.keys(generated.comparisonPolicy)) {
        const expectedValue = Number(prior.engines[engine].metrics[metric]);
        const actualValue = Number(actual.engines[engine].metrics[metric]);
        const scale = Math.max(Math.abs(expectedValue), Math.abs(actualValue), 1e-12);
        if (!Number.isFinite(expectedValue) || !Number.isFinite(actualValue)
          || Math.abs(expectedValue - actualValue) / scale > 1e-4) {
          throw new Error(`${actual.caseId}: ${engine} metric '${metric}' changed beyond repeatability tolerance`);
        }
      }
    }
  }
}

function main() {
  const options = parseArgs(process.argv.slice(2));
  options.python = resolvePython(options.python);
  const definitions = JSON.parse(fs.readFileSync(CASES_FILE, "utf8"));
  if (definitions.schemaVersion !== 2) throw new Error("Unsupported cross-engine case schema");
  const sources = JSON.parse(fs.readFileSync(MODELS_FILE, "utf8"));
  const supportAudit = sources.map((entry) => ({
    sourceModelId: entry.id,
    ...classifyCrossEngineSupport(entry),
  }));
  const eligible = supportAudit
    .filter((entry) => entry.supported)
    .map((entry) => ({ id: `cross-${entry.sourceModelId}`, sourceModelId: entry.sourceModelId }));
  const sourceById = new Map(sources.map((entry) => [entry.id, entry.model]));
  const requested = new Set(options.caseIds);
  const selected = requested.size > 0
    ? eligible.filter((entry) => requested.has(entry.id) || requested.has(entry.sourceModelId))
    : eligible;
  if (selected.length !== (requested.size || eligible.length)) {
    throw new Error("One or more requested cross-engine cases are unknown");
  }
  const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), "structureclaw-cross-engine-truth-"));
  try {
    const cases = [];
    for (const definition of selected) {
      const source = sourceById.get(definition.sourceModelId);
      if (!source) throw new Error(`${definition.id}: unknown source model '${definition.sourceModelId}'`);
      const commonModel = deriveCommonModel(source, definition.id);
      const engineRuns = {};
      const repeatability = {};
      for (const engine of ENGINES) {
        const engineModel = engine === "opensees" ? openSeesModel(commonModel) : commonModel;
        process.stdout.write(`[Cross-engine truth] ${definition.id}: ${engine} run 1/2\n`);
        engineRuns[engine] = runEngine(
          engine,
          engineModel,
          definition,
          options,
          tempRoot,
          1,
        );
        process.stdout.write(`[Cross-engine truth] ${definition.id}: ${engine} run 2/2\n`);
        const secondRun = runEngine(
          engine,
          engineModel,
          definition,
          options,
          tempRoot,
          2,
        );
        repeatability[engine] = verifyRepeatedEngineRun(engine, commonModel, engineRuns[engine], secondRun);
      }
      const validationEntry = buildValidationEntry({
        caseId: definition.id,
        model: commonModel,
        engineRuns,
        policy: definitions.comparisonPolicy,
        provenance: {
          sourceModelId: definition.sourceModelId,
          sourceModelSha256: sha256(source),
          loading: {
            stories: commonModel.stories.map((story) => ({
              id: story.id,
              elevation: story.elevation,
              floorLoads: story.floor_loads,
            })),
            memberSelfWeight: true,
            openSeesSelfWeightArea: "section geometric dimensions",
          },
          diagnosticExclusions: {
            maxBeamMoment: "OpenSees exposes member-end moments while the current PKPM/YJK result adapters expose the maximum across member stations.",
          },
        },
      });
      for (const engine of ENGINES) {
        validationEntry.engines[engine].repeatability = repeatability[engine];
      }
      cases.push(validationEntry);
    }
    const generated = {
      schemaVersion: 2,
      role: "external three-engine validation of canonical numerical ground truth",
      sourceModelFileSha256: sha256(sources),
      caseDefinitionFileSha256: sha256(definitions),
      comparisonPolicy: definitions.comparisonPolicy,
      repeatabilityRelativeTolerance: 1e-4,
      supportAudit: {
        totalGroundTruthModels: supportAudit.length,
        eligible: eligible.length,
        excluded: supportAudit.length - eligible.length,
        models: supportAudit,
      },
      cases,
      summary: {
        total: cases.length,
        fullyValidated: cases.filter((entry) => entry.validation.status === "fully_validated").length,
        equilibriumValidated: cases.filter((entry) => entry.validation.tiers.equilibrium?.pass).length,
        responseValidated: cases.filter((entry) => entry.validation.tiers.response?.pass).length,
        divergent: cases.filter((entry) => entry.validation.status === "divergent").length,
      },
    };
    if (requested.size > 0) {
      process.stdout.write(`${JSON.stringify(generated, null, 2)}\n`);
      return;
    }
    if (options.verify) {
      if (!fs.existsSync(options.output)) throw new Error(`No committed validation file at ${options.output}`);
      verifyCommitted(JSON.parse(fs.readFileSync(options.output, "utf8")), generated, sourceById);
      process.stdout.write(`Verified ${cases.length} cross-engine validation cases\n`);
      return;
    }
    fs.writeFileSync(options.output, `${JSON.stringify(generated, null, 2)}\n`, "utf8");
    process.stdout.write(`Wrote ${cases.length} cross-engine validation cases to ${options.output}\n`);
  } finally {
    try {
      fs.rmSync(tempRoot, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 });
    } catch (error) {
      process.stderr.write(
        `[Cross-engine truth] warning: temporary directory could not be removed: ${error.message}\n`,
      );
    }
  }
}

if (require.main === module) {
  try {
    main();
  } catch (error) {
    process.stderr.write(`${error.stack || error.message || String(error)}\n`);
    process.exitCode = 1;
  }
}

module.exports = {
  classifyCrossEngineSupport,
  deriveCommonModel,
  geometricArea,
  hasGeometricSection,
  memberSelfWeightLoads,
  openSeesModel,
  storyFloorLoads,
};
