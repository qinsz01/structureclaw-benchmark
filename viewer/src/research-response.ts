import type { Geometry, Model } from './types';
import type {
  ResearchQuantity,
  ResearchSelection,
  ResearchDisplacementSample,
  ResearchDeformationField,
} from './research-types';

export const selectionKey = (selection: ResearchSelection) => `${selection.kind}:${selection.id}`;
export const sameSelection = (a: ResearchSelection, b: ResearchSelection) =>
  a.kind === b.kind && a.id === b.id;
const finite = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v);
export function canonicalValue(
  q: Pick<ResearchQuantity, 'component' | 'value' | 'unit'>,
): { value: number; unit: string } | null {
  const unit = q.unit.replace(/[·*]/g, '.');
  let units: Record<string, number>, target: string;
  if (/^u[xyz]$/.test(q.component)) {
    units = { m: 1, mm: 0.001 };
    target = 'm';
  } else if (/^r[xyz]$/.test(q.component)) {
    units = { rad: 1 };
    target = 'rad';
  } else if (/^(F[xyz]|N|V[23])$/.test(q.component)) {
    units = { kN: 1, N: 0.001 };
    target = 'kN';
  } else if (/^(M[xyz23]|T)$/.test(q.component)) {
    units = { 'kN.m': 1, 'N.m': 0.001 };
    target = 'kN·m';
  } else return null;
  if (!finite(q.value) || !Object.hasOwn(units, unit)) return null;
  const value = q.value * units[unit];
  return finite(value) ? { value, unit: target } : null;
}
export type ResponsePoint = {
  quantity: ResearchQuantity;
  xyz: [number, number, number];
  value: number;
  unit: string;
};
function coordinates(model: Geometry, q: ResearchQuantity): [number, number, number] | null {
  const nodes = new Map(model.nodes.map((n) => [n.id, n]));
  const position = (id: string): [number, number, number] | null => {
    const n = nodes.get(id);
    return n && [n.x, n.y, n.z].every(finite) ? [n.x, n.y, n.z] : null;
  };
  if (q.location.kind === 'node') return position(q.location.id);
  const member = model.elements.find((e) => e.id === q.location.id);
  if (
    !member ||
    member.nodes.length !== 2 ||
    !finite(q.location.positionM) ||
    !['left', 'right'].includes(q.location.side || '')
  )
    return null;
  const a = position(member.nodes[0]),
    b = position(member.nodes[1]);
  if (!a || !b) return null;
  const length = Math.hypot(...a.map((v, i) => b[i] - v));
  if (!length || q.location.positionM < 0 || q.location.positionM > length + 1e-8) return null;
  const f = Math.min(q.location.positionM / length, 1);
  return a.map((v, i) => v + f * (b[i] - v)) as [number, number, number];
}
export function responseSeries(
  model: Geometry,
  quantities: ResearchQuantity[],
  selection: ResearchSelection,
  component: string,
  preferRequestedUnits = false,
) {
  const points: ResponsePoint[] = [],
    unavailable: string[] = [];
  for (const quantity of quantities.filter(
    (q) => sameSelection(q.selection, selection) && q.component === component,
  )) {
    const normalized = canonicalValue(quantity),
      xyz = coordinates(model, quantity);
    if (!normalized || !xyz) {
      unavailable.push(quantity.id);
      continue;
    }
    points.push({ quantity, xyz, ...normalized });
  }
  if (preferRequestedUnits && new Set(points.map((p) => p.quantity.unit)).size === 1) {
    for (const point of points) {
      point.value = point.quantity.value;
      point.unit = point.quantity.unit;
    }
  }
  return {
    points,
    unavailable,
    unit: points[0]?.unit || '',
    maxAbsolute: Math.max(0, ...points.map((p) => Math.abs(p.value))),
  };
}
export function discreteDeformation(
  model: Geometry,
  quantities: ResearchDisplacementSample[],
  selection: ResearchSelection,
  scale: number,
) {
  if (!finite(scale) || scale < 0) throw Error('Deformation scale must be finite and nonnegative');
  const values = new Map<string, Map<string, number>>();
  for (const q of quantities.filter(
    (q) =>
      q.location.kind === 'node' &&
      /^u[xyz]$/.test(q.component) &&
      sameSelection(q.selection, selection),
  )) {
    const row = values.get(q.location.id) || new Map<string, number>();
    const v = canonicalValue(q)?.value;
    row.set(
      q.component,
      v === undefined || (row.has(q.component) && row.get(q.component) !== v) ? NaN : v,
    );
    values.set(q.location.id, row);
  }
  const nodes = model.nodes.flatMap((n) => {
    const row = values.get(n.id),
      u = ['ux', 'uy', 'uz'].map((k) => row?.get(k));
    if (!u.every(finite)) return [];
    const xyz = [n.x + u[0]! * scale, n.y + u[1]! * scale, n.z + u[2]! * scale];
    return xyz.every(finite) ? [{ ...n, x: xyz[0], y: xyz[1], z: xyz[2] }] : [];
  });
  const included = new Set(nodes.map((n) => n.id));
  return {
    nodes,
    elements: model.elements.filter((e) => e.nodes.every((id) => included.has(id))),
    missingNodeIds: model.nodes.filter((n) => !included.has(n.id)).map((n) => n.id),
  };
}
export function responseColor(value: number, maximum: number) {
  if (!finite(value) || !finite(maximum) || maximum <= 0 || value === 0) return '#edf1f7';
  const ratio = Math.min(Math.abs(value) / maximum, 1);
  const base = [237, 241, 247],
    end = value < 0 ? [40, 97, 190] : [200, 61, 67];
  return `rgb(${base.map((v, i) => Math.round(v + (end[i] - v) * ratio)).join(',')})`;
}
export type ProjectionView = 'xy' | 'xz' | 'yz' | 'iso';
export function projectPoint(
  xyz: [number, number, number],
  view: ProjectionView,
): [number, number] {
  const [x, y, z] = xyz;
  if (view === 'iso') return [x * 0.83 - y * 0.62, -z + x * 0.28 + y * 0.38];
  return view === 'xy' ? [x, -y] : view === 'yz' ? [y, -z] : [x, -z];
}

/** Separate samples in screen space without changing their physical station. */
export function layoutResponseMarkers(
  points: ResponsePoint[],
  project: (xyz: [number, number, number]) => number[],
  gap = 16,
  bounds: [number, number, number, number] = [32, 72, 840, 448],
) {
  const occupied: [number, number][] = [];
  return points.map((point) => {
    const anchor = project(point.xyz) as [number, number];
    let position: [number, number] = [...anchor];
    for (let ring = 0; ; ring++) {
      const count = ring ? Math.ceil(2 * Math.PI * ring) : 1;
      let found = false;
      for (let i = 0; i < count; i++) {
        const angle = -Math.PI / 2 + (i * 2 * Math.PI) / count;
        const candidate: [number, number] = [
          anchor[0] + ring * gap * Math.cos(angle),
          anchor[1] + ring * gap * Math.sin(angle),
        ];
        if (
          candidate[0] >= bounds[0] &&
          candidate[0] <= bounds[2] &&
          candidate[1] >= bounds[1] &&
          candidate[1] <= bounds[3] &&
          occupied.every((p) => Math.hypot(p[0] - candidate[0], p[1] - candidate[1]) >= gap - 1e-8)
        ) {
          position = candidate;
          found = true;
          break;
        }
      }
      if (found) break;
    }
    occupied.push(position);
    return { point, anchor, position };
  });
}

/** Enough source data to reconstruct the displayed deformation independently. */
export function deformationEvidence(
  model: Geometry,
  quantities: ResearchDisplacementSample[],
  selection: ResearchSelection,
  scale: number,
) {
  const result = discreteDeformation(model, quantities, selection, scale);
  const ids = new Set(result.nodes.map((n) => n.id));
  const supporting = quantities.filter(
    (q) =>
      q.location.kind === 'node' &&
      ids.has(q.location.id) &&
      /^u[xyz]$/.test(q.component) &&
      sameSelection(q.selection, selection),
  );
  const nodes = result.nodes.map((n) => {
    const original = model.nodes.find((v) => v.id === n.id)!;
    const rows = supporting.filter((q) => q.location.id === n.id);
    return {
      id: n.id,
      original: [original.x, original.y, original.z],
      translationM: ['ux', 'uy', 'uz'].map(
        (component) => canonicalValue(rows.find((q) => q.component === component)!)!.value,
      ),
      deformed: [n.x, n.y, n.z],
      quantityIds: rows.map((q) => q.id),
    };
  });
  return {
    scale,
    kind: 'complete-recorded-node-vectors-only',
    nodes,
    elements: result.elements,
    missingNodeIds: result.missingNodeIds,
    quantities: supporting,
  };
}

/** Local-to-global basis follows the frozen research-300 coordinate contract. */
export function memberAxisEvidence(model: Geometry & { metadata?: Model['metadata'] }, id: string) {
  const element = model.elements.find((e) => e.id === id);
  if (!element || element.nodes.length !== 2) return null;
  const endpoints = element.nodes
    .map((nodeId) => model.nodes.find((n) => n.id === nodeId))
    .map((n) => (n ? [n.x, n.y, n.z] : null));
  if (endpoints.some((p) => !p || !p.every(finite))) return null;
  const [a, b] = endpoints as number[][];
  const normalize = (p: number[]) => {
    const length = Math.hypot(...p);
    return length > 1e-12 && finite(length) ? p.map((v) => v / length) : null;
  };
  const cross = (u: number[], v: number[]) => [
    u[1] * v[2] - u[2] * v[1],
    u[2] * v[0] - u[0] * v[2],
    u[0] * v[1] - u[1] * v[0],
  ];
  const x = normalize(b.map((v, i) => v - a[i]));
  const references = model.metadata?.elementReferenceVectors as
    Record<string, number[]> | undefined;
  const referenceVector = references?.[id] || null;
  const rotationDegrees = element.rotation_angle || 0;
  let y =
    model.coordinate_system.dimension === '2d'
      ? [0, 1, 0]
      : x && referenceVector?.length === 3 && referenceVector.every(finite)
        ? normalize(cross(referenceVector, x))
        : null;
  let basisGlobal: number[][] | null = null;
  if (x && y) {
    const z = cross(x, y),
      angle = (rotationDegrees * Math.PI) / 180,
      c = Math.cos(angle),
      s = Math.sin(angle);
    basisGlobal = [x, y.map((v, i) => c * v + s * z[i]), z.map((v, i) => c * v - s * y![i])];
  }
  return {
    id,
    nodeIds: element.nodes,
    endpoints,
    local1Global: x,
    basisGlobal,
    referenceVector,
    rotationDegrees,
    basisSource: 'frozen-model-coordinate-contract',
  };
}

export const exactNumber = (value: number) => (Object.is(value, -0) ? '-0' : String(value));
export function exactJson(value: unknown, space = 0): string {
  const ordinary = JSON.stringify(value, null, space);
  if (ordinary === undefined) return 'null';
  let marker = '__research_negative_zero__';
  while (ordinary.includes(marker)) marker += '_';
  return JSON.stringify(value, (_key, item) => (Object.is(item, -0) ? marker : item), space)
    .split(JSON.stringify(marker))
    .join('-0');
}

/** Exact binding also prevents a same-named combination from borrowing a basic case. */
export function selectDeformationField(
  fields: ResearchDeformationField[],
  binding: {
    caseId: string;
    state: number;
    engine: string;
    sourceHash?: string;
    modelSha256: string;
    selection: ResearchSelection;
  },
) {
  const found = fields.filter(
    (field) =>
      field.purpose === 'native-node-deformation-only' &&
      field.caseId === binding.caseId &&
      field.state === binding.state &&
      field.engine === binding.engine &&
      field.sourceHash === binding.sourceHash &&
      field.modelSha256 === binding.modelSha256 &&
      sameSelection(field.selection, binding.selection),
  );
  return found.length === 1 ? found[0] : undefined;
}

/** Target a visible 12% projected displacement without amplifying projection roundoff. */
export function automaticDeformationScale(
  model: Geometry,
  quantities: ResearchDisplacementSample[],
  selection: ResearchSelection,
  view: ProjectionView,
) {
  const evidence = deformationEvidence(model, quantities, selection, 1);
  const projected = model.nodes.map((n) => projectPoint([n.x, n.y, n.z], view));
  const extent = Math.max(
    0.1,
    ...[0, 1].map(
      (j) => Math.max(...projected.map((p) => p[j])) - Math.min(...projected.map((p) => p[j])),
    ),
  );
  const maxTranslationM = Math.max(0, ...evidence.nodes.map((n) => Math.hypot(...n.translationM)));
  const maxProjectedTranslationM = Math.max(
    0,
    ...evidence.nodes.map((n) =>
      Math.hypot(...projectPoint(n.translationM as [number, number, number], view)),
    ),
  );
  const projectionHidden =
    maxTranslationM > 0 && maxProjectedTranslationM <= maxTranslationM * 1e-12;
  const maximum = projectionHidden ? maxTranslationM : maxProjectedTranslationM;
  const raw = maximum > 0 ? (0.12 * extent) / maximum : 1;
  return {
    scale: Number.isFinite(raw) ? raw : Number.MAX_VALUE,
    maxTranslationM,
    maxProjectedTranslationM,
    allZero: maxTranslationM === 0,
    projectionHidden,
  };
}

/** PNG iTXt preserves the same UTF-8 evidence JSON as SVG metadata and JSON downloads. */
export function embedPngMetadata(png: Uint8Array, metadata: unknown): Uint8Array<ArrayBuffer> {
  const encoder = new TextEncoder(),
    data = encoder.encode('research300\0\0\0\0\0' + exactJson(metadata));
  const chunk = new Uint8Array(data.length + 12),
    view = new DataView(chunk.buffer);
  view.setUint32(0, data.length);
  chunk.set(encoder.encode('iTXt'), 4);
  chunk.set(data, 8);
  let crc = 0xffffffff;
  for (const byte of chunk.subarray(4, -4)) {
    crc ^= byte;
    for (let bit = 0; bit < 8; bit++) crc = (crc >>> 1) ^ (crc & 1 ? 0xedb88320 : 0);
  }
  view.setUint32(chunk.length - 4, (crc ^ 0xffffffff) >>> 0);
  if (
    png.length < 20 ||
    png[0] !== 137 ||
    encoder.encode('IEND').some((b, i) => png[png.length - 8 + i] !== b)
  )
    throw Error('Invalid PNG export');
  const result = new Uint8Array(png.length + chunk.length);
  result.set(png.subarray(0, -12));
  result.set(chunk, png.length - 12);
  result.set(png.subarray(-12), png.length - 12 + chunk.length);
  return result;
}
