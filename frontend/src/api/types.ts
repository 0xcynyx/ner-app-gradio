// Wire contract mirrored from the backend schemas.
export type LabelCode = "PER" | "LOC" | "DATE_TIME" | "EMAIL" | "PHONE" | "GENDER" | "SSN";

export interface EntityOut {
  start: number;
  end: number;
  label: string;
  text: string;
  score: number;
  verified: boolean;
  sensitivity: number;
}

export interface LabelCount {
  label: string;
  display: string;
  count: number;
  color: string;
}

export interface Stats {
  total: number;
  risk: number;
  characters: number;
  chunks: number;
  by_label: LabelCount[];
}

export interface Analysis {
  text: string;
  truncated: boolean;
  stats: Stats;
  entities: EntityOut[];
}

export interface RedactResult extends Analysis {
  strategy: string;
  replaced: number;
  mapping: Record<string, string>;
}

export interface LabelSpec {
  code: string;
  display: string;
  color: string;
  sensitivity: number;
  structured: boolean;
}

export interface Meta {
  model: Record<string, string>;
  labels: LabelSpec[];
  strategies: string[];
  formats: string[];
  limits: Record<string, number>;
}

export interface BatchItem {
  id: string;
  error: string | null;
  result: Analysis | null;
}

export interface BatchResult {
  items: BatchItem[];
  documents: number;
  entities: number;
}

export type ExportFormat = "json" | "jsonl" | "csv";
