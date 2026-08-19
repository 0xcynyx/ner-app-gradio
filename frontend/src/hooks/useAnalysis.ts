import { useCallback, useState } from "react";

import { api } from "../api/client";
import type { Analysis, RedactResult } from "../api/types";

interface State {
  analysis: Analysis | null;
  redaction: RedactResult | null;
  busy: boolean;
  error: string | null;
}

const EMPTY: State = { analysis: null, redaction: null, busy: false, error: null };

// Owns the request lifecycle for one document so panels stay presentational.
export function useAnalysis() {
  const [state, setState] = useState<State>(EMPTY);

  const run = useCallback(async <T,>(task: () => Promise<T>, key: "analysis" | "redaction") => {
    setState((prev) => ({ ...prev, busy: true, error: null }));
    try {
      const value = await task();
      setState((prev) => ({ ...prev, [key]: value, busy: false }));
      return value;
    } catch (cause) {
      setState((prev) => ({ ...prev, busy: false, error: (cause as Error).message }));
      return null;
    }
  }, []);

  const analyze = useCallback(
    (text: string, minScore: number) => run(() => api.analyze(text, minScore), "analysis"),
    [run],
  );

  const redact = useCallback(
    (text: string, minScore: number, strategy: string, sensitivity: number, mapping: boolean) =>
      run(() => api.redact(text, minScore, strategy, sensitivity, mapping), "redaction"),
    [run],
  );

  const reset = useCallback(() => setState(EMPTY), []);
  return { ...state, analyze, redact, reset };
}
