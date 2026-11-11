import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import ts from 'typescript';
import { createRequire } from 'node:module';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';

const source = new URL('../src/scene-loads.ts', import.meta.url);
const exists = fs.existsSync(source);
const api = exists
  ? await import(
      `data:text/javascript;base64,${Buffer.from(ts.transpileModule(fs.readFileSync(source, 'utf8'), { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ES2022 } }).outputText).toString('base64')}`
    )
  : {};
const dofs = ['ux', 'uy', 'uz', 'rx', 'ry', 'rz'];
const model = {
  unit_system: 'SI',
  coordinate_system: { dimension: '3d', semantics: 'global-z-up', dof_order: dofs },
  nodes: [
    { id: 'A', x: 1, y: 2, z: 3 },
    { id: 'B', x: 4, y: 6, z: 3 },
  ],
  elements: [{ id: 'beam', nodes: ['A', 'B'], type: 'beam' }],
  load_cases: [{ id: 'D', loads: [] }],
};
const near = (actual, expected) =>
  assert.ok(Math.abs(actual - expected) < 1e-12, `${actual} != ${expected}`);
const vectorNear = (actual, expected) => actual.forEach((value, i) => near(value, expected[i]));
const cross = (a, b) => [
  a[1] * b[2] - a[2] * b[1],
  a[2] * b[0] - a[0] * b[2],
  a[0] * b[1] - a[1] * b[0],
];
const dot = (a, b) => a.reduce((sum, value, i) => sum + value * b[i], 0);

test('scene load and physical-support helpers exist', () => {
  for (const name of [
    'nodalMomentGlyphs',
    'forceLoadPoints',
    'visibleSupportRestraints',
    'supportKind',
  ])
    assert.equal(typeof api[name], 'function', name);
});

test(
  'curved moment arrows follow the signed right-hand axis for all six axis directions',
  { skip: !exists },
  () => {
    for (const [axis, component] of ['mx', 'my', 'mz'].entries())
      for (const sign of [-1, 1]) {
        const input = structuredClone(model);
        input.load_cases[0].loads = [
          {
            id: 'couple',
            type: 'nodal',
            reference_frame: 'global',
            node: 'A',
            [component]: sign * 3,
          },
        ];
        const glyphs = api.nodalMomentGlyphs(input, 'D', 0.5);
        assert.equal(glyphs.length, 1);
        const glyph = glyphs[0];
        const wantedAxis = [0, 0, 0];
        wantedAxis[axis] = sign;
        vectorNear(glyph.axis, wantedAxis);
        assert.match(glyph.label, new RegExp(`${component}=${sign > 0 ? '\\+' : '-'}3 kN\\.m`));
        assert.ok(glyph.label.includes(`${sign > 0 ? '+' : '-'}${'XYZ'[axis]}`));
        for (let i = 1; i < glyph.points.length; i++) {
          const radial = glyph.points[i].map((value, index) => value - glyph.center[index]);
          const previous = glyph.points[i - 1].map((value, index) => value - glyph.center[index]);
          near(Math.hypot(...radial), 0.5);
          near(radial[axis], 0);
          assert.ok(
            dot(cross(previous, radial), wantedAxis) > 0,
            `${component} ${sign}: curve winding`,
          );
        }
        const end = glyph.points.at(-1).map((value, index) => value - glyph.center[index]);
        near(dot(end, glyph.tangent), 0);
        near(Math.hypot(...glyph.tangent), 1);
        assert.ok(
          dot(cross(end, glyph.tangent), wantedAxis) > 0,
          'arrowhead points along the same winding',
        );
      }
  },
);

test(
  'pure moments and force-plus-moment loads both survive current-case selection without mutation',
  { skip: !exists },
  () => {
    const input = structuredClone(model);
    input.load_cases = [
      {
        id: 'D',
        loads: [
          { type: 'nodal', reference_frame: 'global', node: 'A', my: -8 },
          { type: 'nodal', reference_frame: 'global', node: 'B', fx: 25, mz: 6 },
        ],
      },
      { id: 'L', loads: [{ type: 'nodal', reference_frame: 'global', node: 'A', mx: 100 }] },
    ];
    const before = structuredClone(input);
    const glyphs = api.nodalMomentGlyphs(input, 'D', 0.2);
    assert.deepEqual(
      glyphs.map((g) => [g.nodeId, g.component, g.value]),
      [
        ['A', 'my', -8],
        ['B', 'mz', 6],
      ],
    );
    assert.deepEqual(input, before);
    assert.deepEqual(api.nodalMomentGlyphs(input, 'missing', 0.2), []);
    assert.deepEqual(api.nodalMomentGlyphs(input, 'D', 0), []);
  },
);

test(
  'partial distributed arrows use physical start/end distances along the directed member',
  { skip: !exists },
  () => {
    const partial = {
      type: 'distributed',
      reference_frame: 'global',
      element: 'beam',
      start: 1,
      end: 4,
      wz: -9,
    };
    const points = api.forceLoadPoints(model, partial);
    assert.equal(points.length, 5);
    vectorNear(points[0], [1.6, 2.8, 3]);
    vectorNear(points[2], [2.5, 4, 3]);
    vectorNear(points.at(-1), [3.4, 5.2, 3]);
    const full = api.forceLoadPoints(model, { ...partial, start: undefined, end: undefined });
    vectorNear(full[0], [1, 2, 3]);
    vectorNear(full.at(-1), [4, 6, 3]);
    assert.deepEqual(
      api.forceLoadPoints(model, { type: 'nodal', node: 'B', reference_frame: 'global', fx: 10 }),
      [[4, 6, 3]],
    );
  },
);

test(
  'unknown frames, missing nodes, nonfinite moments and invalid extents never get fabricated symbols',
  { skip: !exists },
  () => {
    const input = structuredClone(model);
    input.load_cases[0].loads = [
      { type: 'nodal', reference_frame: 'local', node: 'A', my: 3 },
      { type: 'nodal', reference_frame: 'global', node: 'absent', my: 3 },
      { type: 'nodal', reference_frame: 'global', node: 'A', my: NaN },
      { type: 'nodal', reference_frame: 'global', node: 'A', my: 0 },
    ];
    assert.deepEqual(api.nodalMomentGlyphs(input, 'D', 0.5), []);
    for (const [start, end] of [
      [-1, 2],
      [2, 1],
      [2, 2],
      [0, 6],
      [0, Infinity],
    ])
      assert.deepEqual(
        api.forceLoadPoints(model, {
          type: 'distributed',
          reference_frame: 'global',
          element: 'beam',
          wz: -1,
          start,
          end,
        }),
        [],
      );
    assert.deepEqual(
      api.forceLoadPoints(model, {
        type: 'nodal',
        reference_frame: 'element-local',
        node: 'A',
        fx: 1,
      }),
      [],
    );
  },
);

test(
  'physical support flags remove planar suppression while retaining fixed, roller and rotational restraints',
  { skip: !exists },
  () => {
    const input = {
      ...model,
      coordinate_system: { ...model.coordinate_system, dimension: '2d', plane: 'xz' },
    };
    const interior = { ...input.nodes[0], restraints: [false, true, false, true, false, true] };
    assert.deepEqual(api.visibleSupportRestraints(input, interior), [
      false,
      false,
      false,
      false,
      false,
      false,
    ]);
    assert.equal(api.supportKind(input, interior), null);
    assert.equal(
      api.supportKind(input, { ...interior, restraints: [true, true, true, true, true, true] }),
      'fixed',
    );
    assert.equal(
      api.supportKind(input, { ...interior, restraints: [false, true, true, true, false, true] }),
      'roller',
    );
    assert.equal(
      api.supportKind(input, { ...interior, restraints: [false, true, false, true, true, true] }),
      'rotation',
    );
    const spatial = { ...model, elements: [{ ...model.elements[0], type: 'truss' }] };
    const rotationsOnly = {
      ...model.nodes[0],
      restraints: [false, false, false, true, true, true],
    };
    assert.deepEqual(api.visibleSupportRestraints(spatial, rotationsOnly), [
      false,
      false,
      false,
      false,
      false,
      false,
    ]);
    assert.equal(api.supportKind(spatial, rotationsOnly), null);
    assert.equal(
      api.supportKind(spatial, {
        ...rotationsOnly,
        restraints: [true, true, true, true, true, true],
      }),
      'pin',
    );
    assert.equal(
      api.supportKind(model, rotationsOnly),
      'rotation',
      'rotations remain physical when a beam is connected',
    );
  },
);

test(
  'static thumbnail only labels physical supports, including a real rotational restraint',
  { skip: !exists },
  () => {
    const thumbnail = new URL('../src/thumbnail.tsx', import.meta.url);
    const code = ts.transpileModule(fs.readFileSync(thumbnail, 'utf8'), {
      compilerOptions: {
        target: ts.ScriptTarget.ES2022,
        module: ts.ModuleKind.CommonJS,
        jsx: ts.JsxEmit.ReactJSX,
      },
    }).outputText;
    const require = createRequire(import.meta.url);
    const module = { exports: {} };
    new Function('module', 'exports', 'require', code)(module, module.exports, (name) =>
      name === './scene-loads' ? api : require(name),
    );
    const geometry = {
      coordinate_system: {
        dimension: '2d',
        plane: 'xz',
        semantics: 'global-z-up',
        dof_order: dofs,
      },
      nodes: [
        { id: 'A', x: 0, y: 0, z: 0, restraints: [true, true, true, true, false, true] },
        { id: 'B', x: 3, y: 0, z: 0, restraints: [false, true, false, true, false, true] },
        { id: 'C', x: 6, y: 0, z: 0, restraints: [false, true, false, true, true, true] },
      ],
      elements: [
        { id: 'AB', nodes: ['A', 'B'], type: 'beam' },
        { id: 'BC', nodes: ['B', 'C'], type: 'beam' },
      ],
    };
    const svg = renderToStaticMarkup(
      createElement(module.exports.Thumbnail, { model: geometry, decorative: false }),
    );
    assert.match(svg, /A · pin support/);
    assert.doesNotMatch(svg, /B · .* support/);
    assert.match(svg, /C · rotation support/);
  },
);

test(
  'every exported nonzero nodal moment has a glyph and all four partial intervals keep their actual endpoints',
  { skip: !exists },
  () => {
    const directory = new URL('../public/data/models/', import.meta.url);
    let moments = 0,
      partial = 0;
    for (const file of fs.readdirSync(directory)) {
      const { model: input } = JSON.parse(fs.readFileSync(new URL(file, directory), 'utf8'));
      for (const lc of input.load_cases) {
        const glyphs = api.nodalMomentGlyphs(input, lc.id, 0.1);
        const wanted = lc.loads.flatMap((load) =>
          ['mx', 'my', 'mz'].filter(
            (component) => Number.isFinite(load[component]) && load[component] !== 0,
          ),
        );
        assert.equal(glyphs.length, wanted.length, file);
        moments += glyphs.length;
        for (const load of lc.loads.filter((load) => load.type === 'distributed')) {
          const element = input.elements.find((e) => e.id === load.element);
          const [a, b] = element.nodes.map((id) => input.nodes.find((n) => n.id === id));
          const length = Math.hypot(b.x - a.x, b.y - a.y, b.z - a.z);
          const start = load.start ?? 0,
            end = load.end ?? length;
          const points = api.forceLoadPoints(input, load);
          assert.equal(points.length, 5, `${file}/${load.id}`);
          vectorNear(
            points[0],
            ['x', 'y', 'z'].map((axis) => a[axis] + ((b[axis] - a[axis]) * start) / length),
          );
          vectorNear(
            points.at(-1),
            ['x', 'y', 'z'].map((axis) => a[axis] + ((b[axis] - a[axis]) * end) / length),
          );
          if (start > 1e-12 || Math.abs(end - length) > 1e-12) partial++;
        }
      }
    }
    assert.equal(moments, 20);
    assert.equal(partial, 4);
  },
);
