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
  creation_source: 'manual' | 'revision';
  questions: Question[];
  base_version?: RubricRef;
};

export type ApprovedRubric = Draft & RubricRef & { created_at: string };

export type RubricSummary = {
  id: string;
  role: string;
  versions: { version: number; created_at: string }[];
};
