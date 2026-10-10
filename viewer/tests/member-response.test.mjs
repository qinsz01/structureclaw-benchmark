import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import ts from 'typescript';
const js = ts.transpileModule(
  fs.readFileSync(new URL('../src/member-response.ts', import.meta.url), 'utf8'),
  { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ES2022 } },
).outputText;
const { memberResponses } = await import(
  `data:text/javascript;base64,${Buffer.from(js).toString('base64')}`
);
const read = (id) =>
  JSON.parse(fs.readFileSync(new URL(`../public/data/models/${id}.json`, import.meta.url)));
const near = (a, b) => assert.ok(Math.abs(a - b) < 1e-9, `${a} != ${b}`);
test('interior UDL correction reproduces quartic beam deflection, not only nodal interpolation', () => {
  const r = read('beam-simple-6m'),
    rows = memberResponses(r, r.numerical.result, 'opensees');
  assert.ok(rows.every((r) => r.state === 'recovered'));
  for (const row of rows)
    for (const p of row.samples) {
      const x = p.position[0];
      near(
        p.displacement[2],
        (-20 * x * (6 ** 3 - 2 * 6 * x * x + x ** 3)) / (24 * 205000000 * 0.0001),
      );
      near(p.M3, (20 * x * (6 - x)) / 2);
      near(p.V2, 60 - 20 * x);
    }
});
test('UDL plus midpoint force preserves both one-sided shear values and interior deflection', () => {
  const r = read('beam-simple-6m-udl20-point30'),
    rows = memberResponses(r, r.numerical.result, 'opensees');
  for (const row of rows)
    for (const p of row.samples) {
      const x = p.position[0],
        s = Math.min(x, 6 - x);
      near(
        p.displacement[2],
        (-20 * x * (6 ** 3 - 12 * x * x + x ** 3)) / (24 * 205000000 * 0.0001) -
          (30 * s * (3 * 36 - 4 * s * s)) / (48 * 205000000 * 0.0001),
      );
    }
  near(rows[0].samples.at(-1).V2, 15);
  near(rows[1].samples[0].V2, -15);
});
test('spatial local axes reproduce the same beam in the XZ plane', () => {
  const r = read('beam-simple-6m');
  r.model.coordinate_system.dimension = '3d';
  r.numerical.result.analysisMode = 'opensees_3d_frame';
  for (const force of Object.values(r.numerical.result.forces)) {
    force.localAxes = { x: [1, 0, 0], y: [0, 1, 0], z: [0, 0, 1] };
    for (const end of [force.n1, force.n2])
      Object.assign(end, { V2: 0, V3: end.V, M2: -end.M, M3: 0, T: 0 });
  }
  const rows = memberResponses(r, r.numerical.result, 'opensees');
  assert.ok(rows.every((v) => v.state === 'recovered'));
  for (const row of rows)
    for (const p of row.samples) {
      const x = p.position[0];
      near(p.displacement[2], (-20 * x * (216 - 12 * x * x + x ** 3)) / (24 * 205000000 * 0.0001));
      near(p.M2, (-20 * x * (6 - x)) / 2);
    }
});
test('all frozen structural references have explicit coverage, endpoints and immutable inputs', () => {
  const counts = {};
  for (const file of fs.readdirSync(new URL('../public/data/models/', import.meta.url))) {
    const r = read(file.slice(0, -5)),
      before = JSON.stringify(r),
      rows = memberResponses(r, r.numerical.result, 'opensees');
    assert.equal(rows.length, r.model.elements.length);
    for (const row of rows) {
      counts[row.state] = (counts[row.state] || 0) + 1;
      assert.notEqual(row.state, 'unavailable', `${r.id}/${row.id}`);
      const e = r.model.elements.find((e) => e.id === row.id);
      for (const [sample, id] of [
        [row.samples[0], e.nodes[0]],
        [row.samples.at(-1), e.nodes[1]],
      ])
        ['ux', 'uy', 'uz'].forEach((k, i) =>
          near(sample.displacement[i], r.numerical.result.displacements[id][k]),
        );
      if (row.state === 'interpolated') assert.ok(row.samples.every((p) => p.M3 === undefined));
    }
    assert.equal(JSON.stringify(r), before);
  }
  assert.ok(counts.recovered > 100);
  assert.ok(counts.truss > 100);
  assert.ok(counts.interpolated > 100);
});
test('unknown loads, altered end forces, missing axes and commercial engines fail closed', () => {
  let r = read('beam-simple-6m');
  r.numerical.result.forces['1'].n2.M += 5;
  assert.equal(memberResponses(r, r.numerical.result, 'opensees')[0].state, 'interpolated');
  r = read('frame3d-simple');
  delete r.numerical.result.forces[r.model.elements[0].id].localAxes;
  assert.equal(memberResponses(r, r.numerical.result, 'opensees')[0].state, 'unavailable');
  r = read('beam-simple-6m');
  assert.equal(memberResponses(r, r.numerical.result, 'pkpm')[0].state, 'unavailable');
});
