// Redaction strategies, ported from backend/app/services/redaction.py.
import { specFor } from "./labels";
import type { Analysis, Entity, RedactResult } from "./types";

const SUFFIX_TYPES = new Set(["PHONE", "SSN"]);

// A small non cryptographic digest is enough for a stable per value pseudonym.
function digest(value: string): string {
  let hash = 0x811c9dc5;
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 0x01000193) >>> 0;
  }
  return hash.toString(16).padStart(6, "0").slice(0, 6);
}

const STRATEGIES: Record<string, (entity: Entity, salt: string) => string> = {
  mask: (entity) => "•".repeat(entity.text.length),
  label: (entity) => `[${entity.label}]`,
  pseudonym: (entity, salt) => `${entity.label}_${digest(`${salt}${entity.label}${entity.text.toLowerCase()}`)}`,
  partial: (entity) => {
    if (entity.label === "EMAIL" && entity.text.includes("@")) {
      const [local, domain] = entity.text.split("@");
      return `${local.slice(0, 1)}${"•".repeat(Math.max(local.length - 1, 1))}@${domain}`;
    }
    if (SUFFIX_TYPES.has(entity.label) && entity.text.length > 4) {
      return `${"•".repeat(entity.text.length - 4)}${entity.text.slice(-4)}`;
    }
    return "•".repeat(entity.text.length);
  },
  remove: () => "",
};

export function strategyNames(): string[] {
  return Object.keys(STRATEGIES).sort();
}

export function redact(
  analysis: Analysis,
  strategy: string,
  minSensitivity: number,
  includeMapping: boolean,
  salt = "",
): RedactResult {
  const engine = STRATEGIES[strategy];
  if (!engine) throw new Error(`unknown strategy: ${strategy}`);
  const targets = analysis.entities.filter((e) => specFor(e.label).sensitivity >= minSensitivity);
  const mapping: Record<string, string> = {};
  let text = analysis.text;
  // Replace right to left so earlier offsets stay valid.
  for (const entity of [...targets].sort((a, b) => b.start - a.start)) {
    const token = engine(entity, salt);
    mapping[entity.text] = token;
    text = `${text.slice(0, entity.start)}${token}${text.slice(entity.end)}`;
  }
  return {
    ...analysis,
    text,
    strategy,
    replaced: targets.length,
    mapping: includeMapping ? mapping : {},
  };
}
