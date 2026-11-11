import type { Geometry, Load, Model, Node } from './types';

type SupportGeometry = Geometry & { metadata?: Model['metadata'] };

export type LoadPoint = [number, number, number];
export type MomentGlyph = {
  nodeId: string;
  loadId?: string;
  component: 'mx' | 'my' | 'mz';
  value: number;
  center: LoadPoint;
  axis: LoadPoint;
  points: LoadPoint[];
  tangent: LoadPoint;
  labelPosition: LoadPoint;
  label: string;
};
const xyz = (node: Node): LoadPoint => [node.x, node.y, node.z];

/** The authored start/end distances are metres along the directed member. */
export function forceLoadPoints(model: Model, load: Load): LoadPoint[] {
  if (load.reference_frame !== 'global') return [];
  if (load.type === 'nodal') {
    const node = model.nodes.find((item) => item.id === load.node);
    return node && xyz(node).every(Number.isFinite) ? [xyz(node)] : [];
  }
  if (load.type !== 'distributed') return [];
  const member = model.elements.find((item) => item.id === load.element);
  if (!member || member.nodes.length !== 2) return [];
  const [a, b] = member.nodes.map((id) => model.nodes.find((node) => node.id === id));
  if (!a || !b || ![...xyz(a), ...xyz(b)].every(Number.isFinite)) return [];
  const length = Math.hypot(b.x - a.x, b.y - a.y, b.z - a.z);
  const start = load.start ?? 0,
    end = load.end ?? length;
  if (
    !Number.isFinite(start) ||
    !Number.isFinite(end) ||
    length === 0 ||
    start < 0 ||
    end <= start ||
    end > length + 1e-12 * Math.max(1, length)
  )
    return [];
  return [0, 0.25, 0.5, 0.75, 1].map((fraction) => {
    const position = (start + fraction * (end - start)) / length;
    return [
      a.x + (b.x - a.x) * position,
      a.y + (b.y - a.y) * position,
      a.z + (b.z - a.z) * position,
    ];
  });
}

/** Positive rotation winds from u toward v, where u × v is the positive axis. */
export function nodalMomentGlyphs(model: Model, loadCase: string, radius: number): MomentGlyph[] {
  if (!Number.isFinite(radius) || radius <= 0) return [];
  const result: MomentGlyph[] = [];
  for (const load of model.load_cases.find((item) => item.id === loadCase)?.loads || []) {
    if (load.type !== 'nodal' || load.reference_frame !== 'global') continue;
    const node = model.nodes.find((item) => item.id === load.node);
    if (!node || !xyz(node).every(Number.isFinite)) continue;
    const center = xyz(node);
    for (const [axisIndex, component] of (['mx', 'my', 'mz'] as const).entries()) {
      const value = load[component];
      if (value === undefined || !Number.isFinite(value) || value === 0) continue;
      const sign = Math.sign(value);
      const u = (axisIndex + 1) % 3,
        v = (axisIndex + 2) % 3;
      const axis: LoadPoint = [0, 0, 0];
      axis[axisIndex] = sign;
      const at = (angle: number, scale = 1): LoadPoint => {
        const point = [...center] as LoadPoint;
        point[u] += radius * scale * Math.cos(angle);
        point[v] += radius * scale * Math.sin(angle);
        return point;
      };
      const end = sign * Math.PI * 1.5;
      const tangent: LoadPoint = [0, 0, 0];
      tangent[u] = -sign * Math.sin(end);
      tangent[v] = sign * Math.cos(end);
      result.push({
        nodeId: node.id,
        loadId: load.id,
        component,
        value,
        center,
        axis,
        points: Array.from({ length: 33 }, (_, index) => at((end * index) / 32)),
        tangent,
        labelPosition: at(Math.PI / 4, 1.65),
        label: `${node.id} · ${component}=${value > 0 ? '+' : ''}${value}${model.unit_system === 'SI' ? ' kN.m' : ''} (${sign > 0 ? '+' : '-'}${'XYZ'[axisIndex]})`,
      });
    }
  }
  return result;
}

function activeSupportDofs(model: SupportGeometry, node: Node): boolean[] {
  const planar = model.coordinate_system.dimension.toLowerCase() === '2d';
  const plane = model.coordinate_system.plane || 'xz';
  const planarDofs =
    plane === 'xy' ? ['ux', 'uy', 'rz'] : plane === 'yz' ? ['uy', 'uz', 'rx'] : ['ux', 'uz', 'ry'];
  const incident = model.elements.filter((element) => element.nodes.includes(node.id));
  const trussOnly = incident.length > 0 && incident.every((element) => element.type === 'truss');
  const declaredInactive = Array.isArray(model.metadata?.inactiveDofs)
    ? model.metadata.inactiveDofs
    : [];
  return model.coordinate_system.dof_order.map(
    (dof) =>
      (!planar || planarDofs.includes(dof)) &&
      !(trussOnly && dof.startsWith('r')) &&
      !declaredInactive.includes(dof),
  );
}

/** Keep the original DOF index order while removing analysis-only suppression. */
export function visibleSupportRestraints(model: SupportGeometry, node: Node): boolean[] {
  return activeSupportDofs(model, node).map(
    (active, index) => active && node.restraints?.[index] === true,
  );
}

export function supportKind(
  model: SupportGeometry,
  node: Node,
): 'fixed' | 'pin' | 'roller' | 'rotation' | 'partial' | null {
  const active = activeSupportDofs(model, node),
    constrained = visibleSupportRestraints(model, node);
  if (!constrained.some(Boolean)) return null;
  const translations = model.coordinate_system.dof_order.flatMap((dof, index) =>
    active[index] && dof.startsWith('u') ? [constrained[index]] : [],
  );
  const rotations = model.coordinate_system.dof_order.flatMap((dof, index) =>
    active[index] && dof.startsWith('r') ? [constrained[index]] : [],
  );
  if (!translations.some(Boolean)) return 'rotation';
  if (rotations.length && rotations.every(Boolean) && translations.every(Boolean)) return 'fixed';
  if (rotations.some(Boolean)) return 'partial';
  return translations.every(Boolean) ? 'pin' : 'roller';
}
