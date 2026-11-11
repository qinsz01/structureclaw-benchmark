import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import ts from 'typescript';

const file = new URL('../src/research-response.ts', import.meta.url);
const exists = fs.existsSync(file);
const api = exists
  ? await import(
      `data:text/javascript;base64,${Buffer.from(ts.transpileModule(fs.readFileSync(file, 'utf8'), { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ES2022 } }).outputText).toString('base64')}`
    )
  : {};
const model = {
  nodes: [
    { id: 'A', x: 0, y: 0, z: 0 },
    { id: 'B', x: 4, y: 0, z: 3 },
  ],
  elements: [{ id: 'beam', nodes: ['A', 'B'], type: 'beam' }],
  coordinate_system: { dimension: '3d', semantics: 'right-handed', dof_order: [] },
};
const q = (
  id,
  component,
  value,
  unit,
  location = { kind: 'node', id: 'A' },
  selection = { kind: 'case', id: 'D' },
) => ({
  id,
  component,
  value,
  unit,
  location,
  selection,
  tolerance: { absolute: 1e-8, relative: 1e-6 },
});

test('research result adapter is available without legacy response data', () => {
  assert.equal(typeof api.responseSeries, 'function');
  assert.equal(typeof api.discreteDeformation, 'function');
});
test(
  'signed values use dimension-compatible canonical units and exact selection kind',
  { skip: !exists },
  () => {
    const rows = [
      q('x', 'ux', -2, 'mm'),
      q('other', 'ux', 70, 'm', undefined, { kind: 'combination', id: 'D' }),
    ];
    const snapshot = JSON.stringify(rows);
    const result = api.responseSeries(model, rows, { kind: 'case', id: 'D' }, 'ux');
    assert.equal(result.points.length, 1);
    assert.equal(result.points[0].value, -0.002);
    assert.equal(result.unit, 'm');
    assert.equal(result.points[0].quantity.value, -2);
    assert.equal(JSON.stringify(rows), snapshot);
  },
);
test(
  'physical member stations retain left and right discontinuity values',
  { skip: !exists },
  () => {
    const rows = [
      q('left', 'M3', -2500, 'N*m', { kind: 'member', id: 'beam', positionM: 2.5, side: 'left' }),
      q('right', 'M3', 3, 'kN.m', { kind: 'member', id: 'beam', positionM: 2.5, side: 'right' }),
    ];
    const result = api.responseSeries(model, rows, { kind: 'case', id: 'D' }, 'M3');
    assert.deepEqual(
      result.points.map((p) => p.xyz),
      [
        [2, 0, 1.5],
        [2, 0, 1.5],
      ],
    );
    assert.deepEqual(
      result.points.map((p) => p.value),
      [-2.5, 3],
    );
    assert.deepEqual(
      result.points.map((p) => p.quantity.location.side),
      ['left', 'right'],
    );
  },
);
test(
  'missing objects, incompatible units, nonfinite values and out-of-span stations never become zero',
  { skip: !exists },
  () => {
    const rows = [
      q('missing', 'ux', 1, 'm', { kind: 'node', id: 'absent' }),
      q('wrong', 'ux', 1, 'kN'),
      q('infinite', 'ux', Infinity, 'm'),
    ];
    const result = api.responseSeries(model, rows, { kind: 'case', id: 'D' }, 'ux');
    assert.equal(result.points.length, 0);
    assert.equal(result.unavailable.length, 3);
    assert.equal(
      api.responseSeries(
        model,
        [
          q('outside', 'M3', 3, 'kN.m', {
            kind: 'member',
            id: 'beam',
            positionM: 6,
            side: 'right',
          }),
        ],
        { kind: 'case', id: 'D' },
        'M3',
      ).points.length,
      0,
    );
  },
);
test(
  'deformation requires all three recorded translations, preserving missing nodes and edges',
  { skip: !exists },
  () => {
    const rows = [
      q('ax', 'ux', 1, 'mm'),
      q('ay', 'uy', 0, 'm'),
      q('az', 'uz', -2, 'mm'),
      q('bz', 'uz', 3, 'mm', { kind: 'node', id: 'B' }),
    ];
    const r = api.discreteDeformation(model, rows, { kind: 'case', id: 'D' }, 100);
    assert.deepEqual(
      r.nodes.map((n) => [n.id, n.x, n.y, n.z]),
      [['A', 0.1, 0, -0.2]],
    );
    assert.equal(r.elements.length, 0);
    assert.deepEqual(r.missingNodeIds, ['B']);
    rows.push(
      q('bx', 'ux', 0, 'm', { kind: 'node', id: 'B' }),
      q('by', 'uy', 0, 'm', { kind: 'node', id: 'B' }),
    );
    assert.equal(
      api.discreteDeformation(model, rows, { kind: 'case', id: 'D' }, 100).elements.length,
      1,
    );
  },
);
test(
  'conflicting duplicate components withhold deformation instead of selecting one',
  { skip: !exists },
  () => {
    const rows = [
      q('a', 'ux', 1, 'm'),
      q('b', 'ux', 2, 'm'),
      q('c', 'uy', 0, 'm'),
      q('d', 'uz', 0, 'm'),
    ];
    assert.equal(
      api.discreteDeformation(model, rows, { kind: 'case', id: 'D' }, 1).nodes.length,
      0,
    );
  },
);
test(
  'quantity component groups and color scaling retain zeros and signs',
  { skip: !exists },
  () => {
    assert.equal(api.responseColor(0, 0), '#edf1f7');
    assert.notEqual(api.responseColor(-2, 2), api.responseColor(2, 2));
    assert.equal(api.canonicalValue(q('zero', 'M2', 0, 'kN·m')).value, 0);
  },
);

test('coincident member samples retain individually clickable markers with exact anchors', () => {
  const rows = Array.from({ length: 20 }, (_, i) =>
    q(`q${i}`, 'M2', i - 10, 'kN.m', {
      kind: 'member',
      id: 'beam',
      positionM: 2.5,
      side: i % 2 ? 'left' : 'right',
    }),
  );
  const points = api.responseSeries(model, rows, { kind: 'case', id: 'D' }, 'M2').points;
  const markers = api.layoutResponseMarkers(points, () => [100, 100]);
  assert.equal(markers.length, 20);
  assert.deepEqual(
    markers.map((m) => m.point.quantity),
    rows,
  );
  assert.ok(markers.every((m) => m.anchor[0] === 100 && m.anchor[1] === 100));
  for (let i = 0; i < markers.length; i++)
    for (let j = 0; j < i; j++)
      assert.ok(
        Math.hypot(...markers[i].position.map((x, k) => x - markers[j].position[k])) >= 14 - 1e-8,
      );
  assert.deepEqual(
    api.layoutResponseMarkers(points, () => [100, 100]),
    markers,
  );
});
test('standalone deformation data includes complete supporting translations and coordinates', () => {
  const rows = [
    q('ax', 'ux', 1, 'mm'),
    q('ay', 'uy', 0, 'm'),
    q('az', 'uz', -2, 'mm'),
    q('bx', 'ux', 3, 'mm', { kind: 'node', id: 'B' }),
  ];
  const result = api.deformationEvidence(model, rows, { kind: 'case', id: 'D' }, 100);
  assert.equal(result.nodes.length, 1);
  assert.deepEqual(result.nodes[0], {
    id: 'A',
    original: [0, 0, 0],
    translationM: [0.001, 0, -0.002],
    deformed: [0.1, 0, -0.2],
    quantityIds: ['ax', 'ay', 'az'],
  });
  assert.deepEqual(
    result.quantities.map((q) => q.id),
    ['ax', 'ay', 'az'],
  );
  assert.equal(
    api.discreteDeformation(model, result.quantities, { kind: 'case', id: 'D' }, 100).nodes.length,
    1,
  );
});
test('member axes preserve directed endpoints, planar convention, section roll and explicit 3D reference vectors', () => {
  const planar = {
    ...model,
    coordinate_system: { ...model.coordinate_system, dimension: '2d', plane: 'xz' },
    elements: [{ ...model.elements[0], rotation_angle: 90 }],
  };
  const axes = api.memberAxisEvidence(planar, 'beam');
  assert.deepEqual(axes.nodeIds, ['A', 'B']);
  assert.deepEqual(axes.endpoints, [
    [0, 0, 0],
    [4, 0, 3],
  ]);
  const expected = [
    [0.8, 0, 0.6],
    [-0.6, 0, 0.8],
    [0, -1, 0],
  ];
  axes.basisGlobal.forEach((r, i) =>
    r.forEach((v, j) => assert.ok(Math.abs(v - expected[i][j]) < 1e-12)),
  );
  const spatial = { ...model, metadata: { elementReferenceVectors: { beam: [0, 0, 1] } } };
  const spatialAxes = api.memberAxisEvidence(spatial, 'beam');
  assert.deepEqual(spatialAxes.basisGlobal, [
    [0.8, 0, 0.6],
    [0, 1, 0],
    [-0.6, 0, 0.8],
  ]);
  assert.equal(api.memberAxisEvidence({ ...model, metadata: {} }, 'beam').basisGlobal, null);
});
test('exact reference JSON and labels preserve negative zero', () => {
  const result = api.exactJson({ value: -0, label: '-0', nested: [0, -0] }, 2);
  assert.ok(Object.is(JSON.parse(result).value, -0));
  assert.ok(Object.is(JSON.parse(result).nested[1], -0));
  assert.equal(JSON.parse(result).label, '-0');
  assert.equal(api.exactNumber(-0), '-0');
});

test('dense projection markers stay clear of figure titles and captions', () => {
  const rows = Array.from({ length: 40 }, (_, i) => q(`q${i}`, 'ux', i, 'm'));
  const points = api.responseSeries(model, rows, { kind: 'case', id: 'D' }, 'ux').points;
  for (const anchor of [
    [430, 77],
    [430, 427],
  ]) {
    const markers = api.layoutResponseMarkers(points, () => anchor);
    assert.ok(
      markers.every(
        (m) =>
          m.position[0] >= 32 &&
          m.position[0] <= 840 &&
          m.position[1] >= 72 &&
          m.position[1] <= 448,
      ),
    );
  }
});

test('display series uses the current turn unit when uniform and canonical units for mixed rows', () => {
  const rows = [q('a', 'ux', -2, 'mm'), q('b', 'ux', 4, 'mm', { kind: 'node', id: 'B' })];
  const display = api.responseSeries(model, rows, { kind: 'case', id: 'D' }, 'ux', true);
  assert.equal(display.unit, 'mm');
  assert.deepEqual(
    display.points.map((p) => p.value),
    [-2, 4],
  );
  assert.equal(display.maxAbsolute, 4);
  rows[1] = { ...rows[1], value: 0.004, unit: 'm' };
  const mixed = api.responseSeries(model, rows, { kind: 'case', id: 'D' }, 'ux', true);
  assert.equal(mixed.unit, 'm');
  assert.deepEqual(
    mixed.points.map((p) => p.value),
    [-0.002, 0.004],
  );
});

test('automatic deformation magnification uses projected extent and handles zero or hidden responses', () => {
  assert.equal(typeof api.automaticDeformationScale, 'function');
  const rows = [q('x', 'ux', 1, 'mm'), q('y', 'uy', 0, 'm'), q('z', 'uz', -2, 'mm')];
  const s = { kind: 'case', id: 'D' };
  const auto = api.automaticDeformationScale(model, rows, s, 'xy');
  assert.equal(auto.scale, 480);
  assert.equal(auto.allZero, false);
  const zero = api.automaticDeformationScale(
    model,
    rows.map((r) => ({ ...r, value: 0 })),
    s,
    'xz',
  );
  assert.equal(zero.scale, 1);
  assert.equal(zero.allZero, true);
  const hidden = api.automaticDeformationScale(
    model,
    rows.map((r) => ({ ...r, value: r.component === 'uz' ? 1 : 0 })),
    s,
    'xy',
  );
  assert.equal(hidden.projectionHidden, true);
  assert.ok(Number.isFinite(hidden.scale));
  for (const scale of [-1, Infinity, NaN])
    assert.throws(() => api.discreteDeformation(model, rows, s, scale), /finite/);
});
test('native deformation field selection refuses other states, engines, selections and model hashes', () => {
  assert.equal(typeof api.selectDeformationField, 'function');
  const binding = {
    caseId: 'STD-001',
    state: 1,
    engine: 'OpenSees',
    sourceHash: 'source',
    modelSha256: 'model',
    selection: { kind: 'case', id: 'D' },
  };
  const field = { ...binding, purpose: 'native-node-deformation-only', quantities: [] };
  assert.equal(api.selectDeformationField([field], binding), field);
  for (const wrong of [
    { state: 2 },
    { engine: 'PKPM' },
    { modelSha256: 'other' },
    { sourceHash: 'other' },
    { caseId: 'MM-001' },
    { selection: { kind: 'combination', id: 'D' } },
  ])
    assert.equal(api.selectDeformationField([field], { ...binding, ...wrong }), undefined);
  assert.equal(api.selectDeformationField([field, field], binding), undefined);
});
test('PNG exports embed reconstructable exact supporting metadata, including negative zero', () => {
  assert.equal(typeof api.embedPngMetadata, 'function');
  const png = Buffer.from(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aB1cAAAAASUVORK5CYII=',
    'base64',
  );
  const result = Buffer.from(
    api.embedPngMetadata(png, { deformation: { value: -0, source: '原生' } }),
  );
  assert.deepEqual(result.subarray(0, 8), png.subarray(0, 8));
  let found = false;
  for (let offset = 8; offset < result.length;) {
    const size = result.readUInt32BE(offset),
      type = result.toString('ascii', offset + 4, offset + 8);
    if (type === 'iTXt') {
      const payload = result.subarray(offset + 8, offset + 8 + size);
      const json = payload.subarray(Buffer.byteLength('research300') + 5).toString('utf8');
      const parsed = JSON.parse(json);
      assert.ok(Object.is(parsed.deformation.value, -0));
      assert.equal(parsed.deformation.source, '原生');
      found = true;
    }
    offset += size + 12;
  }
  assert.equal(found, true);
});
