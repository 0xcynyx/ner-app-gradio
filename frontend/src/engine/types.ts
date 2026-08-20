export interface Entity {
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
  entities: Entity[];
}

export interface RedactResult extends Analysis {
  strategy: string;
  replaced: number;
  mapping: Record<string, string>;
}
