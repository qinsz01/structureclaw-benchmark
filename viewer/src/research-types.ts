import type { Locale, Model, Raw } from './types';
import type { TrialIndex } from './trial-types';

export type ResearchEngine = 'OpenSees' | 'PKPM' | 'YJK';
export type ResearchStatus = {
  authored: boolean;
  referenceReady: boolean;
  nativeVerified: boolean;
  inputReviewed: boolean;
  accepted: boolean;
  agentNotRun: boolean;
};
export type SourceFile = { source: string; sha256: string; path?: string; role?: string };
export type ResearchSelection = { kind: 'case' | 'combination'; id: string };
export type ResearchLocation = {
  kind: 'node' | 'member';
  id: string;
  positionM?: number;
  side?: 'left' | 'right';
};
export type ResearchQuantity = {
  id: string;
  selection: ResearchSelection;
  location: ResearchLocation;
  component: string;
  value: number;
  unit: string;
  tolerance: { absolute: number; relative: number };
  sourceValue?: number;
  sourceUnit?: string;
  rawTrace?: unknown;
  engineeringPrecision?: Raw;
  [key: string]: unknown;
};
export type ResearchDisplacementSample = Pick<
  ResearchQuantity,
  'id' | 'selection' | 'location' | 'component' | 'value' | 'unit'
> & {
  origin?: 'native-recorded' | 'explicit-constraint-zero';
  rawTrace?: unknown;
};
export type ResearchDeformationField = {
  schemaVersion: 1;
  purpose: 'native-node-deformation-only';
  caseId: string;
  engine: ResearchEngine;
  state: number;
  selection: ResearchSelection;
  sourceHash: string;
  modelSha256: string;
  receipt: SourceFile & { runId: string; engineVersion: string };
  sources: SourceFile[];
  quantities: ResearchDisplacementSample[];
  coverage: {
    totalNodes: number;
    completeNodes: number;
    totalElements: number;
    completeElements: number;
    missingNodeIds: string[];
    missingComponents: { nodeId: string; component: string; reason: string }[];
    nativeComponents: number;
    constraintComponents: number;
  };
};
export type ResearchDerived = {
  id: string;
  value: number;
  unit: string;
  operation: string;
  operands?: string[];
  tolerance?: { absolute: number; relative: number };
  governingOperand?: string | null;
  governingSelection?: ResearchSelection | null;
  sourceValue?: number;
  sourceUnit?: string;
  [key: string]: unknown;
};
export type ResearchAttachment = {
  name: string;
  path: string;
  source: string;
  sha256: string;
  bytes: number;
  mimeType: string;
};
export type ResearchTurn = {
  id: string;
  state: number | null;
  expectation: string;
  instruction: string;
  inputEdition?: string;
  publicInputSha256?: string;
  inputBinding?: Raw;
  attachments: ResearchAttachment[];
  responseContract: Raw;
  quantities: ResearchQuantity[];
  derived: ResearchDerived[];
  requiredOutputs: Raw[];
  unresolvedFields: unknown[];
};
export type ResearchReference = SourceFile & {
  kind: string;
  solver: Raw | null;
  role?: string;
  metadata?: Raw;
};
export type ResearchState = {
  deformationFields: ResearchDeformationField[];
  state: number;
  modelPath: string;
  modelSha256: string;
  reference: ResearchReference;
  quantities: ResearchQuantity[];
  derived: ResearchDerived[];
  selections: ResearchSelection[];
  receipts: Raw[];
  nativeReference: ResearchReference | null;
};
export type ResearchCaseSummary = {
  codexTrial?: { status: string; repaired: boolean };
  id: string;
  description: string;
  family: string;
  locale: Locale;
  engine: ResearchEngine;
  structure: string;
  modality: string;
  turnCount: number;
  stateCount: number;
  sourceHash: string;
  status: ResearchStatus;
  strictComparison: 'pass' | 'difference' | 'not-available';
};
export type ResearchCaseDetail = {
  schemaVersion: 1;
  corpusId: 'research-300';
  id: string;
  description: string;
  family: string;
  locale: Locale;
  engine: ResearchEngine;
  sourceHash: string;
  status: ResearchStatus;
  turns: ResearchTurn[];
  states: ResearchState[];
  acceptance: Raw;
  publicInputReview?: {
    schemaVersion: 1;
    inputEdition: string;
    caseId: string;
    status: 'pending' | 'passed' | 'failed' | 'partial' | 'invalid';
    verified: boolean;
    coverage: Record<
      string,
      {
        required: number;
        matched: number;
        missing: number;
        mismatched: number;
        unexpected: number;
        observation: boolean;
      }
    >;
    findings: {
      category?: string;
      code: string;
      path?: string;
      message?: string;
      turnId?: string;
    }[];
    evidence: { path: string; sha256: string }[];
  };
  diagnostics: Raw | null;
  sources: SourceFile[];
  contract: Raw;
};
export type ResearchCatalogueFacet =
  | 'family'
  | 'category'
  | 'structure'
  | 'dimension'
  | 'difficulty'
  | 'modality'
  | 'engine'
  | 'language';
export type ResearchCatalogueChoice = {
  key: string;
  zh: string;
  en: string;
  description?: string;
  family?: string;
};
export type ResearchCatalogueMetrics = {
  cases: number;
  turns: number;
  states: number;
  attachmentFiles: number;
  attachmentUses: number;
  markdownFiles: number;
  pngFiles: number;
  dxfFiles: number;
};
export type ResearchCatalogueBucket = ResearchCatalogueChoice & ResearchCatalogueMetrics;
export type ResearchCatalogueRow = {
  id: string;
  title: string;
  family: string;
  category: string;
  focus: string;
  structure: string;
  dimension: '2D' | '3D';
  difficulty: 'L1' | 'L2' | 'L3';
  difficultyReason: string;
  engine: ResearchEngine;
  language: 'zh' | 'en';
  modality: 'text' | 'image' | 'dxf';
  turns: number;
  states: number;
  attachmentFiles: number;
  attachmentUses: number;
  markdownFiles: number;
  pngFiles: number;
  dxfFiles: number;
  authored: boolean;
  referenceReady: boolean;
  nativeVerified: boolean;
  inputReviewStatus: 'pending' | 'passed' | 'failed' | 'partial' | 'invalid';
  accepted: boolean;
  modelTrialStatus: 'not-run' | 'run';
};
export type ResearchCatalogue = {
  schemaVersion: 1;
  edition: 'current';
  totals: ResearchCatalogueMetrics;
  definitions: Record<ResearchCatalogueFacet, ResearchCatalogueChoice[]>;
  breakdowns: Record<ResearchCatalogueFacet, ResearchCatalogueBucket[]>;
  cases: ResearchCatalogueRow[];
};
export type ResearchIndex = {
  codexTrial?: TrialIndex;
  schemaVersion: 1;
  corpusId: 'research-300';
  evaluatorVersion: string;
  summary: {
    planned: number;
    discovered: number;
    authored: number;
    referenceReady: number;
    nativeVerified: number;
    inputReviewed: number;
    publicInputReview?: {
      edition: string;
      total: number;
      reviewed: number;
      passed: number;
      partial: number;
      failed: number;
      pending: number;
      invalid: number;
    };
    accepted: number;
    agentNotRun: number;
    turns: number;
    states: number;
    byFamily: Record<string, number>;
    byLanguage: Record<string, number>;
    byEngine: Record<string, number>;
    originalSourcesVerified: boolean;
  };
  cases: ResearchCaseSummary[];
  catalogue?: ResearchCatalogue;
  sources: SourceFile[];
};
export type ResearchModel = {
  caseId: string;
  state: number;
  model: Model;
  source: string;
  sha256: string;
};
