const fs = require("node:fs");
const path = require("node:path");

const BENCH_ROOT = path.resolve(__dirname, "..");
const GROUND_TRUTH_MODELS = JSON.parse(fs.readFileSync(
  path.join(BENCH_ROOT, "fixtures", "ground-truth-models.json"),
  "utf8",
));
const GROUND_TRUTH_BY_ID = new Map(
  GROUND_TRUTH_MODELS.map((entry) => [entry.id, entry.model]),
);
const GENERATED_INSTRUCTIONS = {
  en: "Use these complete analysis-property records exactly in every mode; they are not placeholders and need no clarification. Use only the user task to classify the structure, but include these properties in parameter extraction. Do not create an explicit self-weight load or duplicate a converted load; an analysis provider may apply its configured member self-weight internally. Reconstruct geometry, topology, supports, and load placement from the task.",
  zh: "所有模式均须严格使用以下完整分析属性；这些记录不是占位符，无需要求补充。结构分类只使用用户任务，参数提取须同时包含这些属性。不得显式创建构件自重荷载或重复施加折算荷载；分析后端可按自身配置在内部计入构件自重。几何、拓扑、支座和荷载位置仍由用户任务确定。",
};

function isGeneratedEngineeringSpecification(value) {
  return typeof value === "string"
    && Object.values(GENERATED_INSTRUCTIONS).some((instruction) => value.startsWith(instruction));
}

function engineeringSpecificationForAssertions(assertions, locale) {
  const assertion = (assertions || []).find((item) => (
    (item?.type === "model_matches" || item?.type === "numerical_matches")
    && typeof item.groundTruthId === "string"
  ));
  const model = assertion ? GROUND_TRUTH_BY_ID.get(assertion.groundTruthId) : null;
  if (!model) return "";

  const unitSystem = model.unit_system ?? model.unitSystem ?? "";
  const coordinateSystem = model.coordinate_system || {};
  const valueText = (value) => (value === undefined ? null : String(value));
  const recordText = (record, keys) => keys
    .map((key) => {
      const value = record?.[key];
      return value === undefined ? null : `${key}=${valueText(value)}`;
    })
    .filter(Boolean)
    .join(", ");
  const coordinateText = recordText(
    coordinateSystem,
    ["semantics", "version", "dimension", "plane", "dof_order"],
  );
  const materialsText = (model.materials || []).map((material) => (
    recordText(material, ["id", "name", "grade", "category", "E", "nu", "rho", "fy", "fc"])
  )).join("; ");
  const sectionsText = (model.sections || []).map((section) => {
    const identity = recordText(
      section,
      ["id", "name", "type", "purpose", "standard_steel_name"],
    );
    const shape = recordText(section.shape, ["kind", "H", "B", "tw", "tf", "D", "t"]);
    const properties = recordText(section.properties, ["A", "Iy", "Iz", "J", "G"]);
    const portalMember = model.metadata?.inferredType === "portal-frame"
      && section.shape?.kind === "H"
      && [section.shape.H, section.shape.B, section.shape.tw, section.shape.tf].every(Number.isFinite)
      ? `member=H${section.shape.H}x${section.shape.B}x${section.shape.tw}x${section.shape.tf}`
      : "";
    return [portalMember, identity, shape && `shape(${shape})`, properties && `properties(${properties})`]
      .filter(Boolean)
      .join(", ");
  }).join("; ");
  const combinationsText = (model.load_combinations || []).map((combination) => {
    const factors = Object.entries(combination.factors || {})
      .map(([caseId, factor]) => `${caseId}=${factor}`)
      .join(", ");
    return `id=${combination.id}, factors={${factors}}`;
  }).join("; ");
  const instruction = locale === "en" ? GENERATED_INSTRUCTIONS.en : GENERATED_INSTRUCTIONS.zh;
  const labels = locale === "en"
    ? ["Unit system", "Coordinate system", "Materials", "Sections", "Analysis load combinations"]
    : ["单位制", "坐标系", "材料", "截面", "分析荷载组合"];
  return [
    instruction,
    `${labels[0]}: ${unitSystem}`,
    `${labels[1]}: ${coordinateText}`,
    `${labels[2]}: ${materialsText}`,
    `${labels[3]}: ${sectionsText}`,
    `${labels[4]}: ${combinationsText}`,
  ].join("\n");
}

module.exports = {
  engineeringSpecificationForAssertions,
  isGeneratedEngineeringSpecification,
};
