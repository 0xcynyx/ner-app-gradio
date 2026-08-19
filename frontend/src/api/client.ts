// Single transport boundary, components never call fetch directly.
import type { Analysis, BatchResult, ExportFormat, Meta, RedactResult } from "./types";

const BASE = import.meta.env.VITE_API_BASE ?? "";

async function post<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return unwrap<T>(response);
}

async function unwrap<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new Error(detail?.detail ?? `${response.status} ${response.statusText}`);
  }
  return (await response.json()) as T;
}

export const api = {
  meta: async (): Promise<Meta> => unwrap<Meta>(await fetch(`${BASE}/api/meta`)),

  analyze: (text: string, minScore: number) => post<Analysis>("/api/analyze", { text, min_score: minScore }),

  redact: (text: string, minScore: number, strategy: string, minSensitivity: number, includeMapping: boolean) =>
    post<RedactResult>("/api/redact", {
      text,
      min_score: minScore,
      strategy,
      min_sensitivity: minSensitivity,
      include_mapping: includeMapping,
    }),

  batch: (texts: string[], minScore: number) =>
    post<BatchResult>("/api/batch", {
      items: texts.map((text, index) => ({ id: String(index + 1), text })),
      min_score: minScore,
    }),

  upload: async (file: File): Promise<BatchResult> => {
    const form = new FormData();
    form.append("file", file);
    return unwrap<BatchResult>(await fetch(`${BASE}/api/upload`, { method: "POST", body: form }));
  },

  // Export streams a file, so the blob is turned into a browser download here.
  download: async (text: string, minScore: number, format: ExportFormat): Promise<void> => {
    const response = await fetch(`${BASE}/api/export`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, min_score: minScore, format }),
    });
    if (!response.ok) throw new Error(`export failed: ${response.status}`);
    const url = URL.createObjectURL(await response.blob());
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `entities.${format}`;
    anchor.click();
    URL.revokeObjectURL(url);
  },
};
