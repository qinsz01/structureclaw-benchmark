const { createHash } = require("node:crypto");

const { commonCorePass } = require("./report.cjs");

const INFORMATIONAL_METRICS = new Set([
  "duration",
  "toolCalls",
  "inputTokens",
  "outputTokens",
  "totalTokens",
  "visionInputTokens",
  "visionOutputTokens",
  "visionTotalTokens",
]);

const FAILURE_STAGE_BY_METRIC = {
  structural_type: "routing",
  skill_match: "routing",
  has_interaction_questions: "interaction",
  safe_non_execution: "interaction",
  should_not_analyze: "interaction",
  analysis_or_interaction: "interaction",
  no_bad_model: "artifact",
  has_model: "artifact",
  model_matches: "structural-correctness",
  engine_match: "backend",
  has_analysis: "backend",
  numerical_matches: "numerical-response",
  has_report: "report",
  report_numerical_consistency: "report",
  natural_language: "semantic",
  execution: "execution",
};

function numericMetric(result, name) {
  const values = (result.metrics || [])
    .filter((metric) => metric.metric === name)
    .map((metric) => Number(metric.actual))
    .filter(Number.isFinite);
  if (values.length === 0) return null;
  return values.reduce((sum, value) => sum + value, 0);
}

function requiredMetricPass(result, name) {
  const metrics = (result.metrics || []).filter((metric) => metric.metric === name);
  if (metrics.length === 0) return null;
  return metrics.every((metric) => metric.pass === true);
}

function mean(values) {
  if (values.length === 0) return null;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function quantile(values, probability) {
  if (values.length === 0) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const position = (sorted.length - 1) * probability;
  const lower = Math.floor(position);
  const upper = Math.ceil(position);
  if (lower === upper) return sorted[lower];
  const weight = position - lower;
  return sorted[lower] * (1 - weight) + sorted[upper] * weight;
}

function seedFromText(value) {
  return createHash("sha256").update(String(value)).digest().readUInt32BE(0);
}

function mulberry32(seed) {
  let state = seed >>> 0;
  return () => {
    state += 0x6D2B79F5;
    let value = state;
    value = Math.imul(value ^ value >>> 15, value | 1);
    value ^= value + Math.imul(value ^ value >>> 7, value | 61);
    return ((value ^ value >>> 14) >>> 0) / 4294967296;
  };
}

function bootstrapMean(values, options = {}) {
  if (values.length === 0) return { mean: null, lower: null, upper: null, samples: 0 };
  const iterations = options.iterations || 10_000;
  const random = mulberry32(seedFromText(options.seed || "structureclaw-bootstrap"));
  const estimates = [];
  for (let iteration = 0; iteration < iterations; iteration += 1) {
    let total = 0;
    for (let index = 0; index < values.length; index += 1) {
      total += values[Math.floor(random() * values.length)];
    }
    estimates.push(total / values.length);
  }
  return {
    mean: mean(values),
    lower: quantile(estimates, 0.025),
    upper: quantile(estimates, 0.975),
    samples: values.length,
  };
}

function pairedSignFlipPValue(differences, options = {}) {
  if (differences.length === 0) return null;
  const iterations = options.iterations || 10_000;
  const observed = Math.abs(mean(differences));
  const random = mulberry32(seedFromText(options.seed || "structureclaw-sign-flip"));
  let extreme = 0;
  for (let iteration = 0; iteration < iterations; iteration += 1) {
    const estimate = Math.abs(
      differences.reduce(
        (total, difference) => total + difference * (random() < 0.5 ? -1 : 1),
        0,
      ) / differences.length,
    );
    if (estimate >= observed - Number.EPSILON) extreme += 1;
  }
  return (extreme + 1) / (iterations + 1);
}

function holmAdjust(entries) {
  const ordered = [...entries].sort((left, right) => left.pValue - right.pValue);
  let previous = 0;
  const adjusted = new Map();
  for (let index = 0; index < ordered.length; index += 1) {
    const value = Math.min(1, ordered[index].pValue * (ordered.length - index));
    previous = Math.max(previous, value);
    adjusted.set(ordered[index].id, previous);
  }
  return entries.map((entry) => ({ ...entry, holmAdjustedPValue: adjusted.get(entry.id) }));
}

function groupBy(values, keyFunction) {
  const groups = new Map();
  for (const value of values) {
    const key = keyFunction(value);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(value);
  }
  return groups;
}

function scenarioMeanValues(rows, successFunction) {
  return [...groupBy(rows, (row) => row.baseScenarioId || row.scenarioId).values()]
    .map((scenarioRows) => mean(scenarioRows.map((row) => successFunction(row) ? 1 : 0)));
}

function summarizeCondition(rows, options = {}) {
  const successFunction = options.successFunction || ((row) => row.allPassed === true);
  const scenarioMeans = scenarioMeanValues(rows, successFunction);
  const stableGroups = [...groupBy(rows, (row) => row.baseScenarioId || row.scenarioId).values()];
  const stableSuccess = stableGroups.filter((group) => group.every(successFunction)).length;
  const stableFailure = stableGroups.filter((group) => group.every((row) => !successFunction(row))).length;
  const unstable = stableGroups.length - stableSuccess - stableFailure;
  return {
    atomicRuns: rows.length,
    scenarios: scenarioMeans.length,
    ...bootstrapMean(scenarioMeans, { seed: options.seed }),
    stableSuccess,
    unstable,
    stableFailure,
  };
}

function standardAutoLift(rows, modelId) {
  const relevant = rows.filter(
    (row) => row.modelId === modelId && row.taskFamily === "standard_workflow",
  );
  const grouped = groupBy(
    relevant,
    (row) => `${row.baseScenarioId || row.scenarioId}\0${row.repeatId}`,
  );
  const perScenario = new Map();
  for (const group of grouped.values()) {
    const auto = group.find((row) => row.mode === "auto");
    const generic = group.find((row) => row.mode === "generic-only");
    if (!auto || !generic) continue;
    const scenarioId = auto.baseScenarioId || auto.scenarioId;
    if (!perScenario.has(scenarioId)) perScenario.set(scenarioId, []);
    perScenario.get(scenarioId).push(
      Number(commonCorePass(auto)) - Number(commonCorePass(generic)),
    );
  }
  const differences = [...perScenario.values()].map(mean);
  const interval = bootstrapMean(differences, { seed: `auto-lift-${modelId}` });
  return {
    modelId,
    effect: interval.mean,
    lower: interval.lower,
    upper: interval.upper,
    scenarios: interval.samples,
    pValue: pairedSignFlipPValue(differences, { seed: `auto-lift-p-${modelId}` }),
  };
}

function evidenceLadder(rows) {
  const eligible = rows.filter((row) => requiredMetricPass(row, "numerical_matches") !== null);
  const steps = [
    ["modelArtifact", ["has_model"]],
    ["executable", ["has_model", "has_analysis"]],
    ["structurallyCorrect", ["has_model", "has_analysis", "model_matches"]],
    [
      "numericallyCorrect",
      ["has_model", "has_analysis", "model_matches", "numerical_matches"],
    ],
  ];
  const output = {};
  for (const [label, metrics] of steps) {
    const applicable = eligible.filter(
      (row) => metrics.every((metric) => requiredMetricPass(row, metric) !== null),
    );
    const passed = applicable.filter(
      (row) => metrics.every((metric) => requiredMetricPass(row, metric) === true),
    ).length;
    output[label] = {
      passed,
      total: applicable.length,
      rate: applicable.length > 0 ? passed / applicable.length : null,
    };
  }
  const endToEndPassed = eligible.filter((row) => row.allPassed === true).length;
  output.endToEndCorrect = {
    passed: endToEndPassed,
    total: eligible.length,
    rate: eligible.length > 0 ? endToEndPassed / eligible.length : null,
  };
  const executable = output.executable.passed;
  const numerical = eligible.filter(
    (row) => requiredMetricPass(row, "has_analysis") === true
      && requiredMetricPass(row, "model_matches") === true
      && requiredMetricPass(row, "numerical_matches") === true,
  ).length;
  output.executableButWrongRate = executable > 0 ? (executable - numerical) / executable : null;
  output.executionOverestimation = output.executable.rate === null
    || output.numericallyCorrect.rate === null
    ? null
    : output.executable.rate - output.numericallyCorrect.rate;
  return output;
}

function failureStage(result) {
  for (const metric of result.metrics || []) {
    if (metric.pass === true || INFORMATIONAL_METRICS.has(metric.metric)) continue;
    return FAILURE_STAGE_BY_METRIC[metric.metric] || "other";
  }
  return result.allPassed ? "success" : "other";
}

function failureBreakdown(rows) {
  return Object.fromEntries(
    [...groupBy(rows, failureStage).entries()]
      .map(([stage, group]) => [stage, group.length])
      .sort(([left], [right]) => left.localeCompare(right)),
  );
}

function describeNumeric(values) {
  const finite = values.filter(Number.isFinite);
  return {
    count: finite.length,
    mean: mean(finite),
    median: quantile(finite, 0.5),
    p95: quantile(finite, 0.95),
    total: finite.reduce((sum, value) => sum + value, 0),
  };
}

function efficiencySummary(rows) {
  const queueWait = rows.map(
    (row) => Number(row.executionProfile?.solverGate?.solverQueueWaitMs || 0),
  );
  const wall = rows.map((row) => Number(row.durationMs)).filter(Number.isFinite);
  const cooldown = rows.map(
    (row) => Number(row.executionProfile?.solverGate?.cooldownMs || 0),
  );
  const effective = rows.map((row) => {
    const explicit = Number(row.executionProfile?.effectiveDurationMs);
    return Number.isFinite(explicit)
      ? explicit
      : Math.max(0, Number(row.durationMs || 0) - Number(
        row.executionProfile?.solverGate?.solverQueueWaitMs || 0,
      ) - Number(row.executionProfile?.solverGate?.cooldownMs || 0));
  });
  return {
    toolCalls: describeNumeric(rows.map((row) => numericMetric(row, "toolCalls")).filter(Number.isFinite)),
    primaryTokens: describeNumeric(rows.map((row) => numericMetric(row, "totalTokens")).filter(Number.isFinite)),
    visionTokens: describeNumeric(rows.map((row) => numericMetric(row, "visionTotalTokens")).filter(Number.isFinite)),
    wallDurationMs: describeNumeric(wall),
    solverQueueWaitMs: describeNumeric(queueWait),
    solverCooldownMs: describeNumeric(cooldown),
    effectiveDurationMs: describeNumeric(effective),
  };
}

function aggregateFormalRows(rows) {
  const conditionGroups = groupBy(
    rows,
    (row) => [
      row.taskFamily,
      row.modelId,
      row.visionModelId || "",
      row.mode,
    ].join("\0"),
  );
  const conditions = [];
  for (const [key, group] of conditionGroups) {
    const [taskFamily, modelId, visionModelId, mode] = key.split("\0");
    conditions.push({
      taskFamily,
      modelId,
      visionModelId: visionModelId || null,
      mode,
      endToEnd: summarizeCondition(group, { seed: `e2e-${key}` }),
      commonCore: summarizeCondition(group, {
        seed: `common-${key}`,
        successFunction: commonCorePass,
      }),
      failures: failureBreakdown(group),
      efficiency: efficiencySummary(group),
    });
  }
  const modelIds = [...new Set(
    rows
      .filter((row) => row.taskFamily === "standard_workflow")
      .map((row) => row.modelId),
  )].sort();
  const autoLift = holmAdjust(modelIds.map((modelId) => standardAutoLift(rows, modelId)));
  return {
    atomicRuns: rows.length,
    conditions,
    standardAutoLift: autoLift,
    evidenceLadder: evidenceLadder(rows),
    overallFailures: failureBreakdown(rows),
    overallEfficiency: efficiencySummary(rows),
  };
}

module.exports = {
  aggregateFormalRows,
  bootstrapMean,
  evidenceLadder,
  failureStage,
  holmAdjust,
  pairedSignFlipPValue,
  requiredMetricPass,
  standardAutoLift,
  summarizeCondition,
};
