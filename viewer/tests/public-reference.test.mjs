import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import ts from 'typescript';
import { createRequire } from 'node:module';
import path from 'node:path';
const require = createRequire(import.meta.url);
const { comparePhysicalModels } = require('../../lib/physical-model-fidelity.cjs');

const file = new URL('../src/public-reference.ts', import.meta.url);
const api = fs.existsSync(file)
  ? await import(
      `data:text/javascript;base64,${Buffer.from(
        ts.transpileModule(fs.readFileSync(file, 'utf8'), {
          compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ES2022 },
        }).outputText,
      ).toString('base64')}`
    )
  : {};

test('normal result downloads keep exact signed values, units, locations and deformation without audit records', () => {
  assert.equal(typeof api.publicReferenceForDownload, 'function');
  const q = {
    id: 'q1',
    selection: { kind: 'case', id: 'D' },
    location: { kind: 'node', id: 'A' },
    component: 'uz',
    value: -0,
    unit: 'mm',
    tolerance: { absolute: 0.01, relative: 0.1 },
    rawTrace: { source: '/private/results.json' },
    engineeringPrecision: { allowance: 0.4 },
  };
  const input = {
    caseId: 'STD-001',
    turnId: 't1',
    state: 1,
    targetEngine: 'OpenSees',
    selection: { kind: 'case', id: 'D' },
    component: 'uz',
    unit: 'mm',
    projection: 'xz',
    sourceHash: 'a'.repeat(64),
    referenceSource: { sha256: 'b'.repeat(64) },
    quantities: [q],
    derived: [
      {
        id: 'd1',
        operation: 'max-absolute',
        value: -1.23456789012345,
        unit: 'mm',
        governingOperand: 'q1',
        tolerance: { absolute: 0.01 },
      },
    ],
    deformation: {
      scale: 200,
      nodes: [
        {
          id: 'A',
          original: [0, 0, 0],
          translationM: [0, 0, -0.001],
          deformed: [0, 0, -0.2],
          quantityIds: ['q1'],
        },
      ],
      elements: [],
      missingNodeIds: [],
      quantities: [q],
      field: { sourceHash: 'c'.repeat(64), receipt: { runId: 'private-run' } },
    },
  };
  const output = api.publicReferenceForDownload(input);
  assert.deepEqual(output, {
    caseId: 'STD-001',
    turnId: 't1',
    state: 1,
    engine: 'OpenSees',
    selection: { kind: 'case', id: 'D' },
    component: 'uz',
    unit: 'mm',
    projection: 'xz',
    quantities: [
      {
        id: 'q1',
        selection: { kind: 'case', id: 'D' },
        location: { kind: 'node', id: 'A' },
        component: 'uz',
        value: -0,
        unit: 'mm',
      },
    ],
    derived: [
      {
        id: 'd1',
        operation: 'max-absolute',
        value: -1.23456789012345,
        unit: 'mm',
        governingOperand: 'q1',
      },
    ],
    deformation: {
      scale: 200,
      nodes: [
        {
          id: 'A',
          original: [0, 0, 0],
          translationM: [0, 0, -0.001],
          deformed: [0, 0, -0.2],
          quantityIds: ['q1'],
        },
      ],
      elements: [],
      missingNodeIds: [],
      quantities: [
        {
          id: 'q1',
          selection: { kind: 'case', id: 'D' },
          location: { kind: 'node', id: 'A' },
          component: 'uz',
          value: -0,
          unit: 'mm',
        },
      ],
    },
  });
  assert.ok(Object.is(output.quantities[0].value, -0));
});

test('normal model download contains engineering model data without repository metadata', () => {
  assert.equal(typeof api.publicModelForDownload, 'function');
  assert.deepEqual(
    api.publicModelForDownload('STD-001', 't1', 'OpenSees', {
      nodes: [
        {
          id: 'A',
          x: 0,
          y: 0,
          z: -0,
          restraints: [true, true, true],
          rawTrace: '/private/node.json',
        },
      ],
      elements: [{ id: 'e1', nodes: ['A', 'B'], type: 'beam', material: 'M1', section: 'S1' }],
      unit_system: 'kN-m',
      coordinate_system: { dimension: '2d', plane: 'xz' },
      materials: [],
      sections: [],
      load_cases: [],
      load_combinations: [],
      metadata: { sourceHash: 'a'.repeat(64), source: '/private/model.json' },
    }),
    {
      caseId: 'STD-001',
      turnId: 't1',
      engine: 'OpenSees',
      model: {
        nodes: [{ id: 'A', x: 0, y: 0, z: -0, restraints: [true, true, true] }],
        elements: [{ id: 'e1', nodes: ['A', 'B'], type: 'beam', material: 'M1', section: 'S1' }],
        unit_system: 'kN-m',
        coordinate_system: { dimension: '2d', plane: 'xz' },
        materials: [],
        sections: [],
        load_cases: [],
        load_combinations: [],
      },
    },
  );
});

test('normal model downloads preserve the physical and analysis semantics of every frozen state', () => {
  const root = path.resolve(new URL('../../corpora/research-300/cases/', import.meta.url).pathname);
  let states = 0;
  for (const id of fs.readdirSync(root).filter((id) => /^(STD|INT|MM)-\d{3}$/.test(id))) {
    const folder = path.join(root, id);
    const contract = JSON.parse(fs.readFileSync(path.join(folder, 'contract.json')));
    for (const filename of contract.modelStates) {
      const model = JSON.parse(fs.readFileSync(path.join(folder, filename)));
      const downloaded = api.publicModelForDownload(id, 't1', contract.plannedEngine, model).model;
      const comparison = comparePhysicalModels(downloaded, model, {
        coordinate: 1e-8,
        property: 1e-6,
        load: 1e-6,
      });
      assert.equal(comparison.pass, true, `${id}/${filename}: ${comparison.failures.join('; ')}`);
      assert.deepEqual(downloaded.analysis_control, model.analysis_control);
      assert.equal(downloaded.schema_version, model.schema_version);
      states++;
    }
  }
  assert.equal(states, 364);
});
