import type { Reference, Result } from './types';

export type Vec = [number, number, number];
export type Sample = {
  x: number;
  position: Vec;
  displacement: Vec;
  N?: number;
  V2?: number;
  V3?: number;
  M2?: number;
  M3?: number;
  T?: number;
};
export type MemberResponse = {
  id: string;
  length: number;
  state: 'recovered' | 'interpolated' | 'truss' | 'unavailable';
  reason: string;
  samples: Sample[];
  axes?: Vec[];
  endError?: number;
};
const dot = (a: Vec, b: Vec) => a.reduce((v, n, i) => v + n * b[i], 0);
const add = (a: Vec, b: Vec): Vec => a.map((v, i) => v + b[i]) as Vec;
const mul = (a: Vec, s: number): Vec => a.map((v) => v * s) as Vec;
const finite = (a: unknown[]): a is number[] =>
  a.every((v) => typeof v === 'number' && Number.isFinite(v));
function hermite(a: number, b: number, ra: number, rb: number, L: number, t: number) {
  return (
    (1 - 3 * t * t + 2 * t ** 3) * a +
    (t - 2 * t * t + t ** 3) * L * ra +
    (3 * t * t - 2 * t ** 3) * b +
    (-t * t + t ** 3) * L * rb
  );
}

// Frozen results only. No solver, mesh mutation, or benchmark tolerances are involved.
export function memberResponses(
  reference: Reference,
  result: Result,
  engine: string,
): MemberResponse[] {
  const m = reference.model,
    planar = m.coordinate_system.dimension === '2d',
    numerical = reference.numerical;
  const units = result.meta?.units || result.units;
  const factors = numerical?.analysisSelection.factors;
  const transfer = result.floorLoadTransfer as { effectiveMode?: string } | undefined;
  const hiddenLoads =
    !!m.stories?.some((s) => s.floor_loads?.length) && transfer?.effectiveMode !== 'node_tributary';
  const validFactors =
    !!factors &&
    Object.entries(factors).every(
      ([id, f]) => Number.isFinite(f) && m.load_cases.some((c) => c.id === id),
    );
  const activeLoads = m.load_cases.flatMap((c) =>
    (factors?.[c.id] || 0) === 0 ? [] : c.loads.map((l) => ({ ...l, factor: factors![c.id] })),
  );
  return m.elements.map((e) => {
    const fail = (reason: string): MemberResponse => ({
      id: e.id,
      length: 0,
      state: 'unavailable',
      reason,
      samples: [],
    });
    const a = m.nodes.find((n) => n.id === e.nodes[0]),
      b = m.nodes.find((n) => n.id === e.nodes[1]);
    if (!a || !b || e.nodes.length !== 2) return fail('geometry');
    const legacyTruss =
      engine === 'opensees' && result.analysisMode === 'opensees_2d_truss' && !units;
    if (m.unit_system !== 'SI' || (units?.displacement !== 'm' && !legacyTruss))
      return fail('units');
    const start: Vec = [a.x, a.y, a.z],
      end: Vec = [b.x, b.y, b.z],
      dx = end.map((v, i) => v - start[i]) as Vec,
      L = Math.hypot(...dx);
    if (!L) return fail('geometry');
    const da = result.displacements?.[a.id],
      db = result.displacements?.[b.id];
    if (!da || !db || !finite([da.ux, da.uy, da.uz, db.ux, db.uy, db.uz]))
      return fail('displacements');
    const ua: Vec = [da.ux, da.uy, da.uz],
      ub: Vec = [db.ux, db.uy, db.uz];
    const force = result.forces?.[e.id] as
      | {
          axial?: number;
          referenceFrame?: string;
          localAxes?: { x: Vec; y: Vec; z: Vec };
          n1?: Record<string, number>;
          n2?: Record<string, number>;
        }
      | undefined;
    if (e.type === 'truss')
      return {
        id: e.id,
        length: L,
        state: 'truss',
        reason: 'axial',
        samples: Array.from({ length: 41 }, (_, i) => {
          const t = i / 40;
          return {
            x: t * L,
            position: add(start, mul(dx, t)),
            displacement: add(mul(ua, 1 - t), mul(ub, t)),
            N: typeof force?.axial === 'number' ? force.axial : undefined,
          };
        }),
      };
    if (!['beam', 'column'].includes(e.type)) return fail('element');
    if (engine !== 'opensees') return fail('engine');
    if (planar && (m.coordinate_system.plane !== 'xz' || Math.abs(dx[1]) > 1e-9))
      return fail('axes');
    const ex = mul(dx, 1 / L),
      axes: Vec[] = planar
        ? [ex, [-ex[2], 0, ex[0]], [0, -1, 0]]
        : force?.localAxes
          ? [force.localAxes.x, force.localAxes.y, force.localAxes.z]
          : [];
    if (
      axes.length !== 3 ||
      axes.some(
        (v) => !Array.isArray(v) || v.length !== 3 || !finite(v) || Math.abs(dot(v, v) - 1) > 1e-6,
      ) ||
      axes.some((v, i) => axes.some((w, j) => i !== j && Math.abs(dot(v, w)) > 1e-6)) ||
      dot(ex, axes[0]) < 1 - 1e-6
    )
      return fail('axes');
    if (!finite([da.rx, da.ry, da.rz, db.rx, db.ry, db.rz])) return fail('rotations');
    const va = axes.map((v) => dot(v, ua)),
      vb = axes.map((v) => dot(v, ub));
    const ra = planar ? [0, 0, -da.ry] : axes.map((v) => dot(v, [da.rx, da.ry, da.rz]));
    const rb = planar ? [0, 0, -db.ry] : axes.map((v) => dot(v, [db.rx, db.ry, db.rz]));
    const E = Number(m.materials.find((v) => v.id === e.material)?.E) * 1000;
    const p = m.sections.find((v) => v.id === e.section)?.properties as
      Record<string, number> | undefined;
    const n1 = force?.n1,
      n2 = force?.n2;
    const q: Vec = [0, 0, 0];
    const memberLoads = activeLoads.filter((l) => l.element === e.id);
    const loadsKnown =
      validFactors &&
      !hiddenLoads &&
      memberLoads.every(
        (l) =>
          l.type === 'distributed' &&
          l.reference_frame === 'global' &&
          Object.keys(l).every((k) =>
            ['type', 'element', 'wx', 'wy', 'wz', 'reference_frame', 'factor'].includes(k),
          ),
      );
    if (loadsKnown)
      for (const l of memberLoads) {
        const global: Vec = [l.wx || 0, l.wy || 0, l.wz || 0];
        axes.forEach((v, i) => (q[i] += dot(v, global) * l.factor));
      }
    const Iy = planar ? p?.Iy : p?.Iz,
      Iz = p?.Iy;
    const stiffness = !!p && finite([E, p.A, Iy, Iz]) && E > 0 && p.A > 0 && Iy! > 0 && Iz! > 0;
    const required = planar ? ['N', 'V', 'M'] : ['N', 'V2', 'V3', 'M2', 'M3', 'T'];
    const ends = !!n1 && !!n2 && required.every((k) => finite([n1[k], n2[k]]));
    let eligible =
      loadsKnown &&
      stiffness &&
      ends &&
      force?.referenceFrame === 'element-local' &&
      units?.force === 'kN' &&
      units?.moment === 'kN.m' &&
      !Object.keys(e).some((k) => /release|offset/i.test(k));
    const V = n1?.[planar ? 'V' : 'V2'] || 0,
      M = n1?.[planar ? 'M' : 'M3'] || 0;
    const moment = (x: number) => -M + V * x + (q[1] * x * x) / 2;
    const moment2 = (x: number) => -(n1?.M2 || 0) - (n1?.V3 || 0) * x - (q[2] * x * x) / 2;
    const poly = (x: number) =>
      ((-M * x * x) / 2 + (V * x ** 3) / 6 + (q[1] * x ** 4) / 24) / (E * Iy!);
    const polyZ = (x: number) =>
      (((n1?.M2 || 0) * x * x) / 2 + ((n1?.V3 || 0) * x ** 3) / 6 + (q[2] * x ** 4) / 24) /
      (E * Iz!);
    const sy = (vb[1] - va[1] - poly(L)) / L,
      sz = (vb[2] - va[2] - polyZ(L)) / L;
    const slopeY = sy + (-M * L + (V * L * L) / 2 + (q[1] * L ** 3) / 6) / (E * Iy!);
    const slopeZ =
      sz + ((n1?.M2 || 0) * L + ((n1?.V3 || 0) * L * L) / 2 + (q[2] * L ** 3) / 6) / (E * Iz!);
    let error = 0;
    if (eligible) {
      const pairs = [
        [moment(L), n2![planar ? 'M' : 'M3']],
        [V + q[1] * L, -n2![planar ? 'V' : 'V2']],
        [-n1!.N - q[0] * L, n2!.N],
        [(E * p!.A * (vb[0] - va[0])) / L, (-n1!.N + n2!.N) / 2],
        [sy, ra[2]],
        [slopeY, rb[2]],
      ];
      if (!planar)
        pairs.push(
          [-n1!.T, n2!.T],
          [moment2(L), n2!.M2],
          [(n1!.V3 || 0) + q[2] * L, -n2!.V3],
          [sz, -ra[1]],
          [slopeZ, -rb[1]],
        );
      error = Math.max(
        ...pairs.map(
          ([v, w]) => Math.abs(v - w) / (1e-8 + 1e-5 * Math.max(Math.abs(v), Math.abs(w))),
        ),
      );
      eligible = error <= 1;
    }
    const reason = eligible
      ? 'checked'
      : hiddenLoads
        ? 'floor'
        : !loadsKnown
          ? 'loads'
          : !stiffness
            ? 'stiffness'
            : !ends
              ? 'forces'
              : 'consistency';
    return {
      id: e.id,
      length: L,
      state: eligible ? 'recovered' : 'interpolated',
      reason,
      axes,
      endError: eligible ? error : undefined,
      samples: Array.from({ length: 81 }, (_, i) => {
        const t = i / 80,
          x = L * t;
        const local: Vec = [
          va[0] * (1 - t) + vb[0] * t + (eligible ? (q[0] * x * (L - x)) / (2 * E * p!.A) : 0),
          eligible ? va[1] + sy * x + poly(x) : hermite(va[1], vb[1], ra[2], rb[2], L, t),
          planar
            ? 0
            : eligible
              ? va[2] + sz * x + polyZ(x)
              : hermite(va[2], vb[2], -ra[1], -rb[1], L, t),
        ];
        return {
          x,
          position: add(start, mul(dx, t)),
          displacement: axes.reduce<Vec>((v, axis, j) => add(v, mul(axis, local[j])), [0, 0, 0]),
          ...(eligible
            ? {
                N: -n1!.N - q[0] * x,
                V2: V + q[1] * x,
                M3: moment(x),
                ...(!planar ? { V3: n1!.V3 + q[2] * x, M2: moment2(x), T: -n1!.T } : {}),
              }
            : {}),
        };
      }),
    };
  });
}
