// Span cleanup, verification, and statistics, ported from the backend services.
import { specFor, LABELS } from "./labels";
import { GENDER_WORDS, PATTERNS } from "./patterns";
import type { Analysis, Entity, LabelCount, Stats } from "./types";

const TRIM = " \t\n\r.,;:!?()[]{}\"'";
const RULE_SCORE = 0.99;
const BASE_WEIGHT = 15;
const VOLUME_CAP = 25;

function trimSpan(text: string, entity: Entity): Entity | null {
  let { start, end } = entity;
  while (start < end && TRIM.includes(text[start])) start += 1;
  while (end > start && TRIM.includes(text[end - 1])) end -= 1;
  if (end <= start) return null;
  return { ...entity, start, end, text: text.slice(start, end) };
}

// A same type span touching another with no separator is tokenizer fragmentation, so it merges.
export function mergeSpans(text: string, entities: Entity[]): Entity[] {
  const sorted = [...entities].sort((a, b) => a.start - b.start || b.score - a.score);
  const kept: Entity[] = [];
  for (const entity of sorted) {
    const last = kept[kept.length - 1];
    if (last && last.label === entity.label && entity.start <= last.end + 1) {
      const gap = text.slice(last.end, entity.start);
      if (gap === "" || gap.trim() === "") {
        last.end = Math.max(last.end, entity.end);
        last.score = Math.max(last.score, entity.score);
        last.text = text.slice(last.start, last.end);
        continue;
      }
    }
    kept.push({ ...entity });
  }
  return kept;
}

function resolveOverlaps(entities: Entity[]): Entity[] {
  const ordered = [...entities].sort((a, b) => b.score - a.score || a.start - b.start);
  const kept: Entity[] = [];
  for (const entity of ordered) {
    if (kept.some((other) => entity.start < other.end && other.start < entity.end)) continue;
    kept.push(entity);
  }
  return kept.sort((a, b) => a.start - b.start);
}

// Structured types have exact formats, so regex repairs boundaries and recovers misses.
export function verify(text: string, entities: Entity[]): Entity[] {
  const matches: Entity[] = [];
  for (const [label, pattern] of Object.entries(PATTERNS)) {
    for (const found of text.matchAll(pattern)) {
      const start = found.index ?? 0;
      matches.push({
        start,
        end: start + found[0].length,
        label,
        text: found[0],
        score: RULE_SCORE,
        verified: true,
        sensitivity: specFor(label).sensitivity,
      });
    }
  }

  // An exact format match outranks a model guess, so regex owns the structured types outright.
  const repaired: Entity[] = [...matches];
  for (const entity of entities) {
    if (!matches.some((m) => entity.start < m.end && m.start < entity.end)) repaired.push(entity);
  }

  // Repair can map several fragments onto one match, so identical spans collapse.
  const unique = new Map<string, Entity>();
  for (const entity of repaired) {
    const key = `${entity.start}:${entity.end}:${entity.label}`;
    const current = unique.get(key);
    if (!current || entity.score > current.score) unique.set(key, entity);
  }
  return [...unique.values()].sort((a, b) => a.start - b.start);
}

// The model sometimes swallows a gender word into a name, so split it back out.
export function splitGender(text: string, entities: Entity[]): Entity[] {
  const out: Entity[] = [];
  for (const entity of entities) {
    if (entity.label !== "PER") {
      out.push(entity);
      continue;
    }
    const lowered = entity.text.toLowerCase();
    const hit = [...GENDER_WORDS].find((word) => lowered.includes(word));
    if (!hit) {
      out.push(entity);
      continue;
    }
    const at = lowered.indexOf(hit);
    const head = trimSpan(text, { ...entity, end: entity.start + at });
    if (head) out.push(head);
    out.push({
      ...entity,
      start: entity.start + at,
      end: entity.start + at + hit.length,
      label: "GENDER",
      text: text.slice(entity.start + at, entity.start + at + hit.length),
      sensitivity: specFor("GENDER").sensitivity,
    });
  }
  return out;
}

export function buildStats(text: string, entities: Entity[], chunks: number): Stats {
  const counts = new Map<string, number>();
  for (const entity of entities) counts.set(entity.label, (counts.get(entity.label) ?? 0) + 1);
  const byLabel: LabelCount[] = [...counts.entries()]
    .sort((a, b) => b[1] - a[1])
    .map(([label, count]) => ({ label, display: specFor(label).display, count, color: specFor(label).color }));
  const peak = entities.reduce((best, e) => Math.max(best, e.sensitivity), 0);
  const risk = entities.length === 0 ? 0 : Math.min(100, peak * BASE_WEIGHT + Math.min(VOLUME_CAP, entities.length * 2));
  return { total: entities.length, risk, characters: text.length, chunks, by_label: byLabel };
}

export function assemble(text: string, raw: Entity[], minScore: number, chunks: number): Analysis {
  const trimmed = raw.map((e) => trimSpan(text, e)).filter((e): e is Entity => e !== null);
  const strong = trimmed.filter((e) => e.score >= minScore);
  const merged = mergeSpans(text, strong);
  const split = splitGender(text, merged);
  const verified = verify(text, resolveOverlaps(split));
  return { text, truncated: false, stats: buildStats(text, verified, chunks), entities: verified };
}

export const LABEL_SPECS = LABELS;
