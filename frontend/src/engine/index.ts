// One contract, two implementations: the browser runtime and the optional HTTP API.
import { api } from "../api/client";
import { LABEL_SPECS } from "./postprocess";
import { analyzeLocal, loadEngine, modelRepo } from "./local";
import { redact, strategyNames } from "./redact";
import type { Analysis, RedactResult } from "./types";
import type { Meta } from "../api/types";

export type Mode = "browser" | "server";

export const API_CONFIGURED = Boolean(import.meta.env.VITE_API_BASE);

export function defaultMode(): Mode {
  return API_CONFIGURED ? "server" : "browser";
}

export function localMeta(): Meta {
  return {
    model: { backend: "browser", model: modelRepo(), loaded: "true" },
    labels: LABEL_SPECS,
    strategies: strategyNames(),
    formats: ["json", "jsonl", "csv"],
    limits: { max_characters: 20000, max_batch: 200, default_min_score: 0.5, window: 20000 },
  };
}

export async function getMeta(mode: Mode): Promise<Meta> {
  return mode === "browser" ? localMeta() : api.meta();
}

export async function analyze(mode: Mode, text: string, minScore: number): Promise<Analysis> {
  return mode === "browser" ? analyzeLocal(text, minScore) : (api.analyze(text, minScore) as Promise<Analysis>);
}

export async function redactWith(
  mode: Mode,
  text: string,
  minScore: number,
  strategy: string,
  sensitivity: number,
  mapping: boolean,
): Promise<RedactResult> {
  if (mode === "server") {
    return api.redact(text, minScore, strategy, sensitivity, mapping) as Promise<RedactResult>;
  }
  return redact(await analyzeLocal(text, minScore), strategy, sensitivity, mapping);
}

export async function analyzeMany(mode: Mode, texts: string[], minScore: number) {
  if (mode === "server") return api.batch(texts, minScore);
  const items = [];
  let total = 0;
  for (const [index, text] of texts.entries()) {
    try {
      const result = await analyzeLocal(text, minScore);
      total += result.stats.total;
      items.push({ id: String(index + 1), error: null, result });
    } catch (cause) {
      items.push({ id: String(index + 1), error: (cause as Error).message, result: null });
    }
  }
  return { items, documents: items.length, entities: total };
}

// Exports run client side so a static deployment still downloads files.
export function download(analysis: Analysis, format: "json" | "jsonl" | "csv"): void {
  const rows = analysis.entities.map((entity, index) => ({
    index, label: entity.label, text: entity.text, start: entity.start,
    end: entity.end, score: Number(entity.score.toFixed(4)), verified: entity.verified,
  }));
  let body: string;
  if (format === "csv") {
    const header = "index,label,text,start,end,score,verified";
    const lines = rows.map((r) => [r.index, r.label, `"${r.text.replace(/"/g, '""')}"`, r.start, r.end, r.score, r.verified].join(","));
    body = [header, ...lines].join("\n");
  } else if (format === "jsonl") {
    body = rows.map((r) => JSON.stringify(r)).join("\n");
  } else {
    body = JSON.stringify({ text: analysis.text, stats: analysis.stats, entities: rows }, null, 2);
  }
  const blob = new Blob([body], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `entities.${format}`;
  anchor.click();
  URL.revokeObjectURL(url);
}

export { loadEngine, modelRepo };
export type { Analysis, RedactResult };
