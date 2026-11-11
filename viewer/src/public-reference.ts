import type { Model } from './types';
import type {
  ResearchDerived,
  ResearchDisplacementSample,
  ResearchQuantity,
  ResearchSelection,
} from './research-types';

function pick<T extends object, K extends keyof T>(value: T, keys: K[]): Pick<T, K> {
  return Object.fromEntries(
    keys.filter((key) => value[key] !== undefined).map((key) => [key, value[key]]),
  ) as Pick<T, K>;
}

function publicQuantity(q: ResearchQuantity | ResearchDisplacementSample) {
  return {
    ...pick(q, ['id', 'component', 'value', 'unit']),
    selection: pick(q.selection, ['kind', 'id']),
    location: pick(q.location, ['kind', 'id', 'positionM', 'side']),
  };
}

type ReferenceDownload = {
  caseId: string;
  turnId?: string;
  state: number;
  targetEngine: string;
  selection?: ResearchSelection;
  component?: string;
  unit?: string;
  projection?: string;
  quantities: (ResearchQuantity | ResearchDisplacementSample)[];
  derived?: ResearchDerived[];
  axes?: unknown;
  deformation?: {
    scale: number;
    nodes: object[];
    elements: object[];
    missingNodeIds: string[];
    quantities: ResearchDisplacementSample[];
  } | null;
};

export function publicReferenceForDownload(input: ReferenceDownload) {
  return {
    ...pick(input, [
      'caseId',
      'turnId',
      'state',
      'selection',
      'component',
      'unit',
      'projection',
      'axes',
    ]),
    engine: input.targetEngine,
    quantities: input.quantities.map(publicQuantity),
    ...(input.derived
      ? {
          derived: input.derived.map((d) =>
            pick(d, [
              'id',
              'operation',
              'value',
              'unit',
              'operands',
              'governingOperand',
              'governingSelection',
            ]),
          ),
        }
      : {}),
    ...(input.deformation
      ? {
          deformation: {
            ...pick(input.deformation, ['scale', 'nodes', 'elements', 'missingNodeIds']),
            quantities: input.deformation.quantities.map(publicQuantity),
          },
        }
      : {}),
  };
}

function engineeringProperties(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(engineeringProperties);
  if (value && typeof value === 'object')
    return Object.fromEntries(
      Object.entries(value)
        .filter(
          ([key]) =>
            !/(?:sha256|hash|receipt|rawTrace|tolerance|audit|provenance|source|path)/i.test(key),
        )
        .map(([key, item]) => [key, engineeringProperties(item)]),
    );
  return value;
}

export function publicModelForDownload(
  caseId: string,
  turnId: string,
  engine: string,
  model: Model,
) {
  const metadata = engineeringProperties(
    Object.fromEntries(
      Object.entries(model.metadata || {}).filter(
        ([key]) => !['authoringStatus', 'sectionAppendixOrigin'].includes(key),
      ),
    ),
  ) as Record<string, unknown>;
  return {
    caseId,
    turnId,
    engine,
    model: {
      ...(model.schema_version ? { schema_version: model.schema_version } : {}),
      unit_system: model.unit_system,
      coordinate_system: pick(model.coordinate_system, [
        'version',
        'dimension',
        'plane',
        'semantics',
        'dof_order',
      ]),
      nodes: model.nodes.map((node) => pick(node, ['id', 'x', 'y', 'z', 'restraints'])),
      elements: model.elements.map((element) =>
        pick(element, ['id', 'nodes', 'type', 'material', 'section', 'rotation_angle']),
      ),
      materials: engineeringProperties(model.materials),
      sections: engineeringProperties(model.sections),
      load_cases: engineeringProperties(model.load_cases),
      load_combinations: engineeringProperties(model.load_combinations),
      ...(model.analysis_control
        ? { analysis_control: engineeringProperties(model.analysis_control) }
        : {}),
      ...(model.stories ? { stories: engineeringProperties(model.stories) } : {}),
      ...(Object.keys(metadata).length ? { metadata } : {}),
    },
  };
}
