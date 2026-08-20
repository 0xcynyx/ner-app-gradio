import { useCallback, useEffect, useState } from "react";

import { analyze, defaultMode, getMeta, loadEngine, redactWith } from "../engine";
import type { Mode } from "../engine";
import type { Meta } from "../api/types";
import type { Analysis, RedactResult } from "../engine/types";

// Owns the engine choice, model loading, and the request lifecycle for one document.
export function useEngine() {
  const [mode, setMode] = useState<Mode>(defaultMode());
  const [meta, setMeta] = useState<Meta | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [redaction, setRedaction] = useState<RedactResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    getMeta(mode)
      .then((value) => live && setMeta(value))
      .catch((cause: Error) => live && setError(cause.message));
    return () => {
      live = false;
    };
  }, [mode]);

  const warm = useCallback(async () => {
    if (mode !== "browser") return;
    await loadEngine((message) => setStatus(message));
    setStatus(null);
  }, [mode]);

  const run = useCallback(
    async <T,>(task: () => Promise<T>, apply: (value: T) => void) => {
      setBusy(true);
      setError(null);
      try {
        await warm();
        apply(await task());
      } catch (cause) {
        setError((cause as Error).message);
      } finally {
        setBusy(false);
        setStatus(null);
      }
    },
    [warm],
  );

  const doAnalyze = useCallback(
    (text: string, minScore: number) => run(() => analyze(mode, text, minScore), setAnalysis),
    [mode, run],
  );

  const doRedact = useCallback(
    (text: string, minScore: number, strategy: string, sensitivity: number, mapping: boolean) =>
      run(() => redactWith(mode, text, minScore, strategy, sensitivity, mapping), setRedaction),
    [mode, run],
  );

  return { mode, setMode, meta, status, analysis, redaction, busy, error, doAnalyze, doRedact };
}
