import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import ts from 'typescript';

const file = new URL('../src/research-catalogue.ts', import.meta.url);
const exists = fs.existsSync(file);
const api = exists
  ? await import(
      `data:text/javascript;base64,${Buffer.from(ts.transpileModule(fs.readFileSync(file, 'utf8'), { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ES2022 } }).outputText).toString('base64')}`
    )
  : {};

const empty = {
  query: '',
  family: '',
  language: '',
  engine: '',
  category: '',
  structure: '',
  dimension: '',
  difficulty: '',
  modality: '',
};
const cases = [
  {
    id: 'STD-001',
    description: 'Steel frame',
    family: 'standard_workflow',
    locale: 'en',
    engine: 'OpenSees',
    structure: '框架',
    modality: 'text',
  },
  {
    id: 'STD-002',
    description: 'RC frame',
    family: 'standard_workflow',
    locale: 'zh',
    engine: 'YJK',
    structure: '框架',
    modality: 'text',
  },
  {
    id: 'MM-001',
    description: 'Steel frame image',
    family: 'multimodal_reverse_engineering',
    locale: 'en',
    engine: 'OpenSees',
    structure: '框架',
    modality: 'image',
  },
];
const catalogue = {
  definitions: {
    category: [
      { key: 'analysis', family: 'standard_workflow', zh: '静力分析', en: 'Static analysis' },
      {
        key: 'image-rebuild',
        family: 'multimodal_reverse_engineering',
        zh: '图像重建',
        en: 'Image reconstruction',
      },
    ],
    difficulty: [{ key: 'L2', zh: 'L2 · 中等', en: 'L2 · Intermediate' }],
  },
  cases: [
    {
      id: 'STD-001',
      category: 'analysis',
      focus: 'elastic bending',
      dimension: '2D',
      difficulty: 'L2',
      modality: 'text',
    },
    { id: 'STD-002', category: 'analysis', dimension: '3D', difficulty: 'L2', modality: 'text' },
    {
      id: 'MM-001',
      category: 'image-rebuild',
      dimension: '2D',
      difficulty: 'L2',
      modality: 'image',
    },
  ],
};

test('Codex result filters preserve original failures and keep repair checks separate in shared URLs', () => {
  const index = {
    cases: cases.map((c, i) => ({
      ...c,
      codexTrial: { status: i === 0 ? 'passed' : 'agent_failure', repaired: i === 1 },
    })),
  };
  assert.deepEqual(
    api.filterResearchCases(index, { ...empty, trial: 'passed' }, 'en').map((c) => c.id),
    ['STD-001'],
  );
  assert.deepEqual(
    api.filterResearchCases(index, { ...empty, trial: 'not-passed' }, 'en').map((c) => c.id),
    ['STD-002', 'MM-001'],
  );
  assert.deepEqual(
    api.filterResearchCases(index, { ...empty, trial: 'repaired' }, 'en').map((c) => c.id),
    ['STD-002'],
  );
  const hash = api.catalogueHash({ ...empty, engine: 'YJK', trial: 'not-passed' }, 2);
  assert.equal(api.readCatalogueLocation(hash).filters.trial, 'not-passed');
  assert.equal(api.readCatalogueLocation(hash).filters.engine, 'YJK');
  assert.equal(api.readCatalogueLocation(hash).page, 2);
});

test('catalogue filtering and shareable locations are available', () => {
  assert.equal(typeof api.filterResearchCases, 'function');
  assert.equal(typeof api.readCatalogueLocation, 'function');
  assert.equal(typeof api.catalogueHash, 'function');
});

test('all selected filters and Unicode search survive a shareable URL', { skip: !exists }, () => {
  const filters = {
    query: '空间 框架',
    family: 'standard_workflow',
    language: 'zh',
    engine: 'YJK',
    category: 'analysis',
    structure: '框架',
    dimension: '3D',
    difficulty: 'L2',
    modality: 'text',
  };
  const hash = api.catalogueHash(filters, 3);
  assert.equal(
    hash,
    '#/?q=%E7%A9%BA%E9%97%B4+%E6%A1%86%E6%9E%B6&family=standard_workflow&lang=zh&engine=YJK&category=analysis&structure=%E6%A1%86%E6%9E%B6&dimension=3D&difficulty=L2&modality=text&page=3',
  );
  assert.deepEqual(api.readCatalogueLocation(hash), { filters, page: 3 });
  assert.deepEqual(api.readCatalogueLocation(api.catalogueHash(empty, 1)), {
    filters: empty,
    page: 1,
  });
});

test(
  'invalid page links return to the first page and unrelated parameters are ignored',
  { skip: !exists },
  () => {
    for (const page of ['-8', 'Infinity', 'not-a-page']) {
      assert.deepEqual(api.readCatalogueLocation(`#/?page=${page}&maintainer=true`), {
        filters: empty,
        page: 1,
      });
    }
  },
);

test(
  'category, structure, dimension, difficulty and modality combine with existing filters',
  { skip: !exists },
  () => {
    const index = { cases, catalogue };
    const selected = {
      ...empty,
      query: 'elastic bending',
      family: 'standard_workflow',
      language: 'en',
      engine: 'OpenSees',
      category: 'analysis',
      structure: '框架',
      dimension: '2D',
      difficulty: 'L2',
      modality: 'text',
    };
    assert.deepEqual(
      api.filterResearchCases(index, selected, 'en').map((item) => item.id),
      ['STD-001'],
    );
    assert.deepEqual(api.filterResearchCases(index, { ...selected, dimension: '3D' }, 'en'), []);
    assert.deepEqual(api.filterResearchCases(index, { ...selected, difficulty: 'L3' }, 'en'), []);
    assert.deepEqual(
      api
        .filterResearchCases(index, { ...empty, category: 'image-rebuild' }, 'en')
        .map((item) => item.id),
      ['MM-001'],
    );
  },
);

test(
  'search uses localized catalogue classification and clearing restores every case',
  { skip: !exists },
  () => {
    const index = { cases, catalogue };
    assert.deepEqual(
      api.filterResearchCases(index, { ...empty, query: '图像重建' }, 'zh').map((item) => item.id),
      ['MM-001'],
    );
    assert.deepEqual(
      api.filterResearchCases(index, empty, 'en').map((item) => item.id),
      ['STD-001', 'STD-002', 'MM-001'],
    );
    assert.equal(index.cases.length, 3);
    assert.equal(index.catalogue.cases.length, 3);
  },
);

test(
  'older indexes retain family, language, engine and text search without a catalogue',
  { skip: !exists },
  () => {
    const result = api.filterResearchCases(
      { cases },
      { ...empty, family: 'standard_workflow', query: 'frame', language: 'zh', engine: 'YJK' },
      'en',
    );
    assert.deepEqual(
      result.map((item) => item.id),
      ['STD-002'],
    );
  },
);
