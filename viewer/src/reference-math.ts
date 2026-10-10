import type { Assertion, Reference, Result } from './types';

export type Pick = {
  entity: string;
  kind: 'node' | 'member';
  component: string;
  value: number;
  unit: string;
};
export function referenceResult(reference: Reference, assertions: Assertion[], target?: string) {
  const assertion = assertions.find(
    (a) => a.type === 'numerical_matches' && a.groundTruthId === reference.id,
  );
  const engine = (assertion?.engineId || target || 'builtin-opensees').replace('builtin-', '');
  const commercial = reference.commercial?.engines[engine];
  return {
    engine,
    result: !assertion
      ? undefined
      : engine === 'opensees'
        ? reference.numerical?.result
        : commercial?.response,
    caseName:
      engine === 'opensees'
        ? reference.numerical?.analysisSelection.loadCombinationId
        : commercial?.response?.caseKey,
  };
}
export function resultUnit(result: Result, kind: string, component: string) {
  const units = result.meta?.units || result.units || {};
  const key =
    kind === 'displacements'
      ? component.startsWith('r')
        ? 'rotation'
        : 'displacement'
      : /^(m|M|T)/.test(component.split('.').pop() || '')
        ? 'moment'
        : 'force';
  return units[key] || '—';
}
export function memberMoment(value: unknown): number | undefined {
  if (!value || typeof value !== 'object') return undefined;
  const row = value as Record<string, unknown>;
  const ends = [row.n1, row.n2].flatMap((v) =>
    v && typeof v === 'object' && typeof (v as Record<string, unknown>).M === 'number'
      ? [Math.abs((v as Record<string, number>).M)]
      : [],
  );
  // Only the explicitly named 2-D end moment component is comparable here.
  return ends.length === 2 ? Math.max(...ends) : undefined;
}
export type BeamCheck = {
  family: 'uniform' | 'cantilever';
  L: number;
  E: number;
  I: number;
  load: number;
  checks: {
    label: 'deflection' | 'left' | 'right';
    formula: string;
    substitution?: string;
    expected: number;
    actual?: number;
    unit: string;
    node: string;
  }[];
  samples: { x: number; displacement: number; moment: number; shear: number }[];
  forceResidual?: number;
  momentResidual?: number;
};
export function beamCheck(reference: Reference): BeamCheck | null {
  const m = reference.model,
    numerical = reference.numerical;
  if (
    !numerical ||
    m.unit_system !== 'SI' ||
    m.coordinate_system.dimension !== '2d' ||
    m.coordinate_system.plane !== 'xz' ||
    m.stories?.some((s) => s.floor_loads?.length)
  )
    return null;
  const nodes = [...m.nodes].sort((a, b) => a.x - b.x),
    first = nodes[0],
    last = nodes.at(-1);
  if (
    !first ||
    !last ||
    nodes.length < 2 ||
    m.elements.length !== nodes.length - 1 ||
    nodes.some((n) => n.y !== first.y || n.z !== first.z)
  )
    return null;
  const L = last.x - first.x;
  if (!(L > 0) || nodes.some((n, i) => i > 0 && n.x <= nodes[i - 1].x)) return null;
  const firstElement = m.elements[0];
  if (
    m.elements.some(
      (e) =>
        e.type !== 'beam' ||
        e.material !== firstElement.material ||
        e.section !== firstElement.section ||
        Object.keys(e).some((k) => /release|offset/i.test(k)),
    )
  )
    return null;
  if (
    nodes
      .slice(1)
      .some(
        (n, i) =>
          m.elements.filter(
            (e) => e.nodes.length === 2 && e.nodes.includes(n.id) && e.nodes.includes(nodes[i].id),
          ).length !== 1,
      )
  )
    return null;
  if (nodes.slice(1, -1).some((n) => [0, 2, 4].some((i) => n.restraints?.[i]))) return null;
  const E = Number(m.materials.find((x) => x.id === firstElement.material)?.E) * 1000;
  const props = m.sections.find((x) => x.id === firstElement.section)?.properties as
    Record<string, number> | undefined;
  const I = props?.Iy;
  if (!(E > 0) || !I || !(I > 0) || !Number.isFinite(E * I)) return null;
  const factors = numerical.analysisSelection.factors;
  if (
    !factors ||
    Object.entries(factors).some(
      ([id, f]) => !Number.isFinite(f) || !m.load_cases.some((c) => c.id === id),
    )
  )
    return null;
  const loads = m.load_cases.flatMap((c) =>
    (factors[c.id] || 0) === 0 ? [] : c.loads.map((l) => ({ ...l, factor: factors[c.id] })),
  );
  if (
    !loads.length ||
    loads.some(
      (l) =>
        l.reference_frame !== 'global' ||
        Object.entries(l).some(
          ([k, v]) => typeof v === 'number' && !['fz', 'wz', 'factor'].includes(k) && v !== 0,
        ),
    )
  )
    return null;
  let family: BeamCheck['family'], load: number;
  if (
    first.restraints?.[0] &&
    first.restraints?.[2] &&
    !first.restraints?.[4] &&
    !last.restraints?.[0] &&
    last.restraints?.[2] &&
    !last.restraints?.[4] &&
    loads.every((l) => l.type === 'distributed' && m.elements.some((e) => e.id === l.element))
  ) {
    const q = m.elements.map(
      (e) =>
        -loads.filter((l) => l.element === e.id).reduce((v, l) => v + (l.wz || 0) * l.factor, 0),
    );
    if (q.some((v) => !Number.isFinite(v) || Math.abs(v - q[0]) > 1e-10) || q[0] === 0) return null;
    family = 'uniform';
    load = q[0];
  } else if (
    [0, 2, 4].every((i) => first.restraints?.[i]) &&
    [0, 2, 4].every((i) => !last.restraints?.[i]) &&
    loads.every(
      (l) => (l.type === 'nodal' || l.type === undefined) && l.node === last.id && !l.element,
    )
  ) {
    family = 'cantilever';
    load = -loads.reduce((v, l) => v + (l.fz || 0) * l.factor, 0);
    if (!Number.isFinite(load) || load === 0) return null;
  } else return null;
  const samples = Array.from({ length: 81 }, (_, i) => {
    const x = (i * L) / 80;
    return {
      x,
      displacement:
        family === 'uniform'
          ? (-load * x * (L ** 3 - 2 * L * x * x + x ** 3)) / (24 * E * I)
          : (-load * x * x * (3 * L - x)) / (6 * E * I),
      moment: family === 'uniform' ? (load * x * (L - x)) / 2 : -load * (L - x),
      shear: family === 'uniform' ? load * (L / 2 - x) : load,
    };
  });
  const control =
    family === 'uniform' ? nodes.find((n) => Math.abs(n.x - first.x - L / 2) < 1e-9) : last;
  const checks: BeamCheck['checks'] = [
    {
      label: 'deflection',
      formula: family === 'uniform' ? 'u_z(L/2) = −5qL⁴/(384EI)' : 'u_z(L) = −PL³/(3EI)',
      expected:
        family === 'uniform'
          ? (-5 * load * L ** 4) / (384 * E * I)
          : (-load * L ** 3) / (3 * E * I),
      actual: control ? numerical.result.displacements?.[control.id]?.uz : undefined,
      node: control?.id || '—',
      unit: 'm',
    },
    {
      label: 'left',
      formula: family === 'uniform' ? 'R_z(0) = qL/2' : 'R_z(0) = P',
      expected: family === 'uniform' ? (load * L) / 2 : load,
      actual: numerical.result.reactions?.[first.id]?.fz,
      node: first.id,
      unit: 'kN',
    },
  ];
  if (family === 'uniform')
    checks.push({
      label: 'right',
      formula: 'R_z(L) = qL/2',
      expected: (load * L) / 2,
      actual: numerical.result.reactions?.[last.id]?.fz,
      node: last.id,
      unit: 'kN',
    });
  const supports = family === 'uniform' ? [first, last] : [first];
  const reactions = supports.map((n) => numerical.result.reactions?.[n.id]?.fz);
  checks[0].substitution =
    family === 'uniform'
      ? `−5 × ${load} × ${L}⁴ / (384 × ${E} × ${I})`
      : `−${load} × ${L}³ / (3 × ${E} × ${I})`;
  for (const c of checks.slice(1))
    c.substitution = family === 'uniform' ? `${load} × ${L} / 2` : String(load);
  const momentResidual =
    family === 'uniform'
      ? typeof reactions[1] === 'number'
        ? -L * reactions[1] + (load * L * L) / 2
        : undefined
      : typeof numerical.result.reactions?.[first.id]?.my === 'number'
        ? numerical.result.reactions[first.id].my + load * L
        : undefined;
  return {
    family,
    L,
    E,
    I,
    load,
    checks,
    samples,
    momentResidual,
    forceResidual: reactions.every((v) => typeof v === 'number')
      ? reactions.reduce<number>((a, b) => a + b!, 0) - load * (family === 'uniform' ? L : 1)
      : undefined,
  };
}
