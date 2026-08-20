// Entity taxonomy, kept in sync with backend/app/domain/labels.py.
export interface LabelSpec {
  code: string;
  display: string;
  color: string;
  sensitivity: number;
  structured: boolean;
}

export const LABELS: LabelSpec[] = [
  { code: "PER", display: "Person", color: "#e2504f", sensitivity: 4, structured: false },
  { code: "LOC", display: "Location", color: "#d99b2b", sensitivity: 2, structured: false },
  { code: "DATE_TIME", display: "Date or time", color: "#8a63d2", sensitivity: 3, structured: false },
  { code: "EMAIL", display: "Email", color: "#2a9d8f", sensitivity: 4, structured: true },
  { code: "PHONE", display: "Phone", color: "#3b82c4", sensitivity: 4, structured: true },
  { code: "GENDER", display: "Gender", color: "#7d8597", sensitivity: 1, structured: false },
  { code: "SSN", display: "National ID", color: "#b5179e", sensitivity: 5, structured: true },
];

const BY_CODE = new Map(LABELS.map((spec) => [spec.code, spec]));

export function specFor(code: string): LabelSpec {
  return BY_CODE.get(code) ?? { code, display: code, color: "#94a3b8", sensitivity: 2, structured: false };
}
