export type Criteria = Record<string, string> | string[] | Record<'false' | 'true', string>;

export type Question = {
  id: string;
  domain: string;
  instructions: string;
  type: 'choice' | 'score' | 'noul';
  criteria?: Criteria;
};

export type RubricRef = { id: string; version: number };

export type Draft = {
  role: string;
  creation_source: 'manual' | 'assisted' | 'revision';
  questions: Question[];
  base_version?: RubricRef;
};

export type ApprovedRubric = Draft & RubricRef & { created_at: string };

export type RubricSummary = {
  id: string;
  role: string;
  versions: { version: number; created_at: string }[];
};

export type ProviderOutcome = {
  status: 'ok' | 'error';
  backend: string;
  model: string;
  served_model?: string;
  elapsed_ms: number;
  answers?: Record<string, Record<string, unknown>>;
  usage?: Record<string, unknown>;
  error?: { code: string; message: string };
};

export type Evaluation = {
  rubric: RubricRef;
  jev: ProviderOutcome;
  laya: ProviderOutcome;
};
