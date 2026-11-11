'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const file = path.join(__dirname, 'research300-catalogue.cjs');
const api = fs.existsSync(file) ? require(file) : {};
const build = (...args) => api.buildResearchCatalogue?.(...args);

function fixture() {
  const ids = ['STD-001', 'INT-001', 'MM-001', 'MM-002'];
  const families = ['standard_workflow', 'interactive_robustness', 'multimodal_reverse_engineering', 'multimodal_reverse_engineering'];
  const categories = ['std_boundary', 'int_update', 'mm_image', 'mm_cad'];
  const planCases = ids.map((id, i) => ({ id, title: `题目 ${id}`, family: families[i], language: i % 2 ? '英文' : '中文', plannedEngine: ['OpenSees', 'OpenSees', 'YJK', 'PKPM'][i], structure: i === 3 ? '空间框架' : '梁', dimension: i === 3 ? '3D' : '2D', difficulty: ['L1', 'L2', 'L3', 'L3'][i], sourceRequirements: { 'task.modelingFocus': `侧重 ${id}` } }));
  const sourceTasks = planCases.map((p) => ({ id: p.id, difficultyReason: `预设依据 ${p.id}` }));
  const attachment = (name) => ({ name, path: `attachments/${name}`, sha256: 'private-value-must-not-be-exported' });
  const turns = [
    [{ id: 't1', inputEdition: 'current', attachments: [attachment('input.md')] }],
    [{ id: 't1', inputEdition: 'current', attachments: [attachment('input.md')] }, { id: 't2', inputEdition: 'current', attachments: [] }, { id: 't3', inputEdition: 'current', attachments: [attachment('input.md')] }],
    [{ id: 't1', inputEdition: 'current', attachments: [attachment('question.png')] }, { id: 't2', inputEdition: 'current', attachments: [attachment('clarified.png')] }],
    [{ id: 't1', inputEdition: 'current', attachments: [attachment('drawing.dxf')] }],
  ];
  const cases = planCases.map((p, i) => {
    const status = { authored: true, referenceReady: true, nativeVerified: true, inputReviewed: false, accepted: false, agentNotRun: true };
    const states = Array.from({ length: i === 1 ? 2 : 1 }, (_, j) => ({ state: j + 1 }));
    return {
      summary: { id: p.id, description: p.title, family: p.family, locale: i % 2 ? 'en' : 'zh', engine: p.plannedEngine, structure: p.structure, modality: i === 2 ? 'image' : i === 3 ? 'dxf' : 'text', turnCount: turns[i].length, stateCount: states.length, sourceHash: 'must-not-leak', status },
      detail: { id: p.id, turns: turns[i], states, publicInputReview: { status: 'pending', verified: false }, status },
      models: states.map(() => ({ model: { coordinate_system: { dimension: p.dimension.toLowerCase() } } })),
    };
  });
  const taxonomy = { schemaVersion: 1, categories: categories.map((key, i) => ({ key, family: families[i], zh: `分类${i}`, en: `Category ${i}`, description: `分类说明${i}` })), cases: ids.map((id, i) => ({ id, category: categories[i], rationale: `归类依据 ${id}` })) };
  return { planCases, sourceTasks, cases, taxonomy };
}

// A repeated file in a later turn must not become another physical input file.
test('counts tasks, turns, model states and unique public files separately', () => {
  const result = build(fixture());
  assert.deepEqual(result?.totals, { cases: 4, turns: 7, states: 5, attachmentFiles: 5, attachmentUses: 6, markdownFiles: 2, pngFiles: 2, dxfFiles: 1 });
  const interactive = result.cases.find((row) => row.id === 'INT-001');
  assert.equal(interactive.attachmentFiles, 1);
  assert.equal(interactive.attachmentUses, 2);
  assert.equal(interactive.turns, 3);
  assert.equal(interactive.states, 2);
  const image = result.breakdowns.modality.find((row) => row.key === 'image');
  assert.equal(image.cases, 1);
  assert.equal(image.pngFiles, 2);
  assert.equal(result.breakdowns.family.find((row) => row.key === 'multimodal_reverse_engineering').cases, 2);
  assert.equal(result.breakdowns.dimension.find((row) => row.key === '3D').cases, 1);
});

test('uses current input-review status and exports classifications without answer or provenance payloads', { skip: !api.buildResearchCatalogue }, () => {
  const input = fixture();
  input.cases[0].detail.publicInputReview = { status: 'passed', verified: true };
  input.cases[1].detail.publicInputReview = { status: 'passed', verified: false };
  const before = JSON.stringify(input);
  const result = build(input);
  assert.equal(result.cases[0].inputReviewStatus, 'passed');
  assert.equal(result.cases[1].inputReviewStatus, 'invalid');
  assert.ok(result.cases.every((row) => !row.accepted && row.nativeVerified && row.modelTrialStatus === 'not-run'));
  assert.equal(result.cases[0].difficultyReason, '预设依据 STD-001');
  assert.equal(result.cases[0].focus, '侧重 STD-001');
  assert.equal(result.definitions.category[0].zh, '分类0');
  assert.doesNotMatch(JSON.stringify(result), /sourceHash|sha256|private-value|must-not-leak|quantities|tolerance|rawTrace/);
  assert.equal(JSON.stringify(input), before);
  assert.deepEqual(build({ ...input, cases: [...input.cases].reverse() }), result, 'stable order must not depend on filesystem enumeration');
});

test('refuses incomplete, duplicate, cross-family or unknown primary classifications', { skip: !api.buildResearchCatalogue }, () => {
  for (const mutate of [
    (x) => x.taxonomy.cases.pop(),
    (x) => x.taxonomy.cases.push(x.taxonomy.cases[0]),
    (x) => { x.taxonomy.cases[0].category = 'unknown'; },
    (x) => { x.taxonomy.cases[0].category = 'int_update'; },
    (x) => x.taxonomy.cases.push({ id: 'STD-999', category: 'std_boundary' }),
  ]) {
    const input = fixture(); mutate(input);
    assert.throws(() => build(input), /classification|taxonomy|category/i);
  }
});

test('refuses metadata drift and unsupported or conflicting public attachment identities', { skip: !api.buildResearchCatalogue }, () => {
  for (const mutate of [
    (x) => { x.planCases[0].title = 'different title'; },
    (x) => { x.cases[0].summary.turnCount = 99; },
    (x) => { x.cases[0].models[0].model.coordinate_system.dimension = '3d'; },
    (x) => { x.cases[0].detail.turns[0].attachments[0].name = 'private.json'; },
    (x) => { x.cases[0].detail.turns[0].inputEdition = 'old-edition'; },
    (x) => { x.cases[1].detail.turns[2].attachments[0].sha256 = 'changed'; },
  ]) {
    const input = fixture(); mutate(input);
    assert.throws(() => build(input), /differs|attachment|edition|public input|dimension|title/i);
  }
});
