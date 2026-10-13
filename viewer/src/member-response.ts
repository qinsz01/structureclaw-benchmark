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
/** Display-only adapter; mechanics are derived offline by StructureClaw's shared library. */
export function memberResponses(
  reference: Reference,
  result: Result,
  engine: string,
): MemberResponse[] {
  const derived = reference.derivedMemberResponses;
  const sourceSnapshot = JSON.stringify({
    model: reference.model,
    result,
    factors: reference.numerical?.analysisSelection.factors,
  });
  if (engine === 'opensees' && derived?.sourceSnapshot === sourceSnapshot) return derived.responses;
  return reference.model.elements.map((element) => ({
    id: element.id,
    length: 0,
    state: 'unavailable',
    reason: engine === 'opensees' ? 'derived-data' : 'engine',
    samples: [],
  }));
}
