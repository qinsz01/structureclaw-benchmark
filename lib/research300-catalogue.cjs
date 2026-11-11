'use strict';
const path = require('node:path');

const choice = (key, zh, en, description) => ({ key, zh, en, ...(description ? { description } : {}) });
const baseDefinitions = {
  family: [
    choice('standard_workflow', '标准工作流', 'Standard workflow'),
    choice('interactive_robustness', '交互鲁棒性', 'Interactive robustness'),
    choice('multimodal_reverse_engineering', '多模态逆向建模', 'Multimodal reconstruction'),
  ],
  structure: [
    choice('梁', '梁', 'Beam'), choice('连续梁', '连续梁', 'Continuous beam'),
    choice('桁架', '桁架', 'Truss'), choice('门式刚架', '门式刚架', 'Portal frame'),
    choice('平面钢框架', '平面钢框架', 'Planar steel frame'),
    choice('平面混凝土框架', '平面混凝土框架', 'Planar concrete frame'),
    choice('空间框架', '空间框架', 'Spatial frame'), choice('柱', '柱', 'Column'),
  ],
  dimension: [choice('2D', '二维', '2D'), choice('3D', '三维', '3D')],
  difficulty: [
    choice('L1', 'L1 · 基本映射', 'L1 · Basic mapping', '信息直接、边界清楚，主要映射单一；预设难度，尚未按模型实测校准。'),
    choice('L2', 'L2 · 单项非直接映射', 'L2 · One nontrivial mapping', '涉及分段、换算、分组、非均匀荷载或关键澄清；预设难度，尚未按模型实测校准。'),
    choice('L3', 'L3 · 多约束联合处理', 'L3 · Coupled constraints', '需要联合处理多种映射或多轮依赖；规模、三维和英文不单独决定难度。尚未按模型实测校准。'),
  ],
  modality: [choice('text', '文字与输入表', 'Text and input table'), choice('image', '图片', 'Image'), choice('dxf', 'DXF', 'DXF')],
  engine: [choice('OpenSees', 'OpenSees', 'OpenSees'), choice('PKPM', 'PKPM', 'PKPM'), choice('YJK', 'YJK', 'YJK')],
  language: [choice('zh', '中文', 'Chinese'), choice('en', '英文', 'English')],
};
const numericFields = ['turns', 'states', 'attachmentFiles', 'attachmentUses', 'markdownFiles', 'pngFiles', 'dxfFiles'];
const assert = (condition, message) => { if (!condition) throw new Error(`Research catalogue: ${message}`); };

function keyed(rows, label) {
  assert(Array.isArray(rows), `${label} must be an array`);
  const result = new Map();
  for (const row of rows) {
    assert(row && typeof row.id === 'string' && !result.has(row.id), `duplicate or invalid ${label} identity`);
    result.set(row.id, row);
  }
  return result;
}

function sameInventory(actual, expected, label) {
  assert(actual.size === expected.size && [...expected.keys()].every((id) => actual.has(id)), `${label} inventory differs`);
}

function inputCounts(detail, family) {
  const files = new Map();
  let attachmentUses = 0;
  for (const turn of detail.turns) {
    assert(turn.inputEdition === 'current', `${detail.id}/${turn.id}: current public input is required`);
    assert(Array.isArray(turn.attachments), `${detail.id}: public attachments missing`);
    assert(turn.attachments.length <= 1 && (family !== 'multimodal_reverse_engineering' || turn.attachments.length === 1), `${detail.id}/${turn.id}: clean attachment count differs`);
    for (const attachment of turn.attachments) {
      const extension = path.posix.extname(attachment.name).toLowerCase();
      assert(['.md', '.png', '.dxf'].includes(extension), `${detail.id}: unsupported public attachment ${attachment.name}`);
      assert(typeof attachment.path === 'string' && attachment.path.length, `${detail.id}: attachment identity missing`);
      const previous = files.get(attachment.path);
      assert(!previous || (previous.sha256 === attachment.sha256 && previous.extension === extension), `${detail.id}: attachment identity differs between turns`);
      files.set(attachment.path, { extension, sha256: attachment.sha256 });
      attachmentUses++;
    }
  }
  const markdownFiles = [...files.values()].filter((f) => f.extension === '.md').length;
  const pngFiles = [...files.values()].filter((f) => f.extension === '.png').length;
  const dxfFiles = [...files.values()].filter((f) => f.extension === '.dxf').length;
  if (family === 'multimodal_reverse_engineering')
    assert(markdownFiles === 0 && !(pngFiles && dxfFiles), `${detail.id}: multimodal attachment formats differ`);
  else assert(pngFiles === 0 && dxfFiles === 0, `${detail.id}: text attachment formats differ`);
  return { attachmentFiles: files.size, attachmentUses, markdownFiles, pngFiles, dxfFiles };
}

function currentReviewStatus(review) {
  if (!review || review.status === 'pending') return 'pending';
  return review.verified && ['passed', 'failed', 'partial'].includes(review.status) ? review.status : 'invalid';
}

function count(rows) {
  return Object.fromEntries([['cases', rows.length], ...numericFields.map((field) => [field, rows.reduce((sum, row) => sum + row[field], 0)])]);
}

/** One read-only projection drives the site, JSON download and current workbook. */
function buildResearchCatalogue({ planCases, sourceTasks, cases, taxonomy }) {
  const plans = keyed(planCases, 'source plan'), sources = keyed(sourceTasks, 'task source');
  const records = keyed(cases.map((record) => ({ id: record.summary.id, record })), 'current case');
  assert(taxonomy?.schemaVersion === 1 && Array.isArray(taxonomy.categories), 'taxonomy schema missing');
  const assignments = keyed(taxonomy.cases, 'taxonomy classification');
  sameInventory(records, plans, 'current case');
  sameInventory(sources, plans, 'task source');
  sameInventory(assignments, plans, 'taxonomy classification');
  const definitions = { ...structuredClone(baseDefinitions), category: [] };
  const categoryKeys = new Set();
  for (const item of taxonomy.categories) {
    assert(item && typeof item.key === 'string' && !categoryKeys.has(item.key) && definitions.family.some((f) => f.key === item.family), 'invalid or duplicate taxonomy category');
    assert(['zh', 'en', 'description'].every((field) => typeof item[field] === 'string' && item[field].trim()), `category ${item.key}: labels and definition required`);
    categoryKeys.add(item.key);
    definitions.category.push({ key: item.key, family: item.family, zh: item.zh, en: item.en, description: item.description });
  }
  const familyOrder = new Map(definitions.family.map((f, i) => [f.key, i]));
  const rows = [...plans.values()].sort((a, b) => (familyOrder.get(a.family) - familyOrder.get(b.family)) || a.id.localeCompare(b.id, 'en')).map((plan) => {
    const { summary, detail, models } = records.get(plan.id).record;
    assert(summary.description === plan.title, `${plan.id}: title differs`);
    for (const [field, target] of [['family', 'family'], ['engine', 'plannedEngine'], ['structure', 'structure']])
      assert(summary[field] === plan[target], `${plan.id}: ${field} differs from plan`);
    assert(detail.id === plan.id && summary.turnCount === detail.turns.length && summary.stateCount === detail.states.length, `${plan.id}: turn/state count differs`);
    assert(Array.isArray(models) && models.length === detail.states.length && models.every((model) => model.model.coordinate_system.dimension.toUpperCase() === plan.dimension), `${plan.id}: physical model dimension differs`);
    const language = { 中文: 'zh', 英文: 'en' }[plan.language];
    assert(language && summary.locale === language, `${plan.id}: language differs`);
    const category = definitions.category.find((c) => c.key === assignments.get(plan.id).category);
    assert(category && category.family === plan.family, `${plan.id}: unknown or cross-family classification category`);
    const input = inputCounts(detail, plan.family);
    const modality = input.dxfFiles ? 'dxf' : input.pngFiles ? 'image' : 'text';
    assert(modality === summary.modality, `${plan.id}: attachment modality differs`);
    const status = summary.status;
    const row = {
      id: plan.id, title: plan.title, family: plan.family, category: category.key,
      focus: plan.sourceRequirements['task.modelingFocus'], structure: plan.structure,
      dimension: plan.dimension, difficulty: plan.difficulty,
      difficultyReason: sources.get(plan.id).difficultyReason,
      engine: plan.plannedEngine, language, modality,
      turns: detail.turns.length, states: detail.states.length, ...input,
      authored: status.authored, referenceReady: status.referenceReady,
      nativeVerified: status.nativeVerified, inputReviewStatus: currentReviewStatus(detail.publicInputReview),
      accepted: status.accepted, modelTrialStatus: status.agentNotRun ? 'not-run' : 'run',
    };
    for (const [dimension, choices] of Object.entries(definitions))
      assert(choices.some((item) => item.key === row[dimension]), `${plan.id}: unknown ${dimension} classification`);
    assert(typeof row.focus === 'string' && typeof row.difficultyReason === 'string' && row.difficultyReason.trim(), `${plan.id}: classification description missing`);
    for (const field of ['authored', 'referenceReady', 'nativeVerified', 'accepted']) assert(typeof row[field] === 'boolean', `${plan.id}: ${field} status missing`);
    return row;
  });
  const breakdowns = Object.fromEntries(Object.entries(definitions).map(([dimension, choices]) => [dimension,
    choices.map(({ key, zh, en, family }) => ({ key, zh, en, ...(family ? { family } : {}), ...count(rows.filter((row) => row[dimension] === key)) })),
  ]));
  return { schemaVersion: 1, edition: 'current', totals: count(rows), definitions, breakdowns, cases: rows };
}

module.exports = { buildResearchCatalogue };
