export type Locale = 'zh' | 'en';
export type Raw = Record<string, unknown>;
export type Node = { id: string; x: number; y: number; z: number; restraints?: boolean[] };
export type Element = {
  id: string;
  nodes: string[];
  type: string;
  material?: string;
  section?: string;
};
export type Load = {
  type?: string;
  node?: string;
  element?: string;
  fx?: number;
  fy?: number;
  fz?: number;
  wx?: number;
  wy?: number;
  wz?: number;
  reference_frame?: string;
};
export type Geometry = {
  nodes: Node[];
  elements: Element[];
  coordinate_system: { dimension: string; plane?: string; semantics: string; dof_order: string[] };
};
export type Model = Geometry & {
  unit_system: string;
  materials: Raw[];
  sections: Raw[];
  load_cases: { id: string; type?: string; loads: Load[] }[];
  stories?: {
    id: string;
    height: number;
    elevation?: number;
    floor_loads?: { type: string; value: number }[];
    [key: string]: unknown;
  }[];
  load_combinations: Raw[];
  metadata?: Raw;
};
export type Assertion = {
  type: string;
  groundTruthId?: string;
  description?: string;
  engineId?: string;
  [key: string]: unknown;
};
export type Attachment = { originalName: string; relPath: string; mimeType: string };
export type Turn = { message: string; engineeringSpecification?: string; assertions: Assertion[] };
export type CaseSummary = {
  id: string;
  description: string;
  family: string;
  locale: Locale;
  structure: string;
  modality: string;
  difficulty: string;
  turnCount: number;
  referenceIds: string[];
  source: string;
  search: string;
};
export type CaseDetail = {
  source: string;
  sourceSha256: string;
  references: string[][];
  turns: Turn[];
  scenario: {
    id: string;
    description: string;
    attachments?: Attachment[];
    engineeringSpecification?: string;
    analysisEngineTarget?: string;
    inputContract?: Raw;
    [key: string]: unknown;
  };
};
export type Result = {
  displacements?: Record<string, Record<string, number>>;
  reactions?: Record<string, Record<string, number>>;
  forces?: Record<string, unknown>;
  meta?: { units?: Record<string, string> };
  units?: Record<string, string>;
  caseKey?: string;
  unavailable?: string[];
  [key: string]: unknown;
};
export type Reference = {
  derivedMemberResponses?: {
    inputSha256: string;
    sourceSnapshot: string;
    responses: import('./member-response').MemberResponse[];
    algorithm: { name: string; version: number; source: string; sha256: string };
  };
  id: string;
  description: string;
  model: Model;
  numerical: {
    solver: { name: string; version: string };
    analysisSelection: { loadCombinationId?: string; factors?: Record<string, number> };
    result: Result;
  } | null;
  commercial: {
    engines: Record<
      string,
      { identity: { name: string; configuredVersion: string }; metrics: Raw; response?: Result }
    >;
  } | null;
};
export type Index = {
  corpus: { benchmarkVersion: string; taskFamilies: Record<string, { total: number }> };
  cases: CaseSummary[];
  modelCount: number;
  sources: { source: string; sha256: string }[];
};
