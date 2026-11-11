export type TrialResult = {
  caseId: string;
  engine: string;
  status: string;
  turns: number;
  repaired: boolean;
  attribution?: { category: string; reason: string };
};
export type TrialIndex = {
  edition?: string;
  diversity?: {
    maximumJCases: number;
    distinctJ: number;
    changedCases: number;
    fixedCases: number;
  };
  historical?: {
    cases: { passed: number; completed: number };
    turns: { passed: number; completed: number };
    revision: string;
  };
  model: string;
  revision: string;
  sutCommit: string;
  reasoningEffort: string;
  cases: { completed: number; passed: number; notPassed: number };
  turns: { completed: number; passed: number; notPassed: number };
  byEngine: Record<string, { cases: number; passed: number; notPassed: number }>;
  byFamily: Record<string, { cases: number; passed: number; notPassed: number }>;
  caseResults: TrialResult[];
  attributionCounts: Record<string, number>;
};
export type TrialAsset = {
  name: string;
  path: string;
  sha256: string;
  scratchPath?: string;
  bytes: number;
};
export type TrialTurn = {
  id: string;
  instruction: string;
  answer: string;
  status: string;
  metrics: { metric: string; pass: boolean; actual: unknown }[];
  attachments?: TrialAsset[];
  artifacts?: TrialAsset[];
  answerFile?: TrialAsset;
  execution?: { threadId: string; completedTurn: boolean; elapsedSeconds: number };
};
export type TrialCase = {
  edition?: string;
  sourceTrial?: string;
  caseId: string;
  engine: string;
  status: string;
  turns: TrialTurn[];
  artifacts: TrialAsset[];
  attribution?: { category: string; reason: string };
  model: string;
  revision: string;
  sutCommit: string;
};
