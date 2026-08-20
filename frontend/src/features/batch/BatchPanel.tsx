import { useRef, useState } from "react";

import { api } from "../../api/client";
import { analyzeMany } from "../../engine";
import type { Mode } from "../../engine";
import type { BatchResult } from "../../api/types";
import { Banner, Button, Empty, Field } from "../../components/ui";

// Batch mode treats one line as one document, matching the txt upload contract.
export function BatchPanel({ minScore, mode }: { minScore: number; mode: Mode }) {
  const [raw, setRaw] = useState("");
  const [result, setResult] = useState<BatchResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const picker = useRef<HTMLInputElement>(null);

  const run = async (task: () => Promise<BatchResult>) => {
    setBusy(true);
    setError(null);
    try {
      setResult(await task());
    } catch (cause) {
      setError((cause as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const analyzeLines = () => {
    const lines = raw.split("\n").map((line) => line.trim()).filter(Boolean);
    if (lines.length === 0) {
      setError("Add at least one line of text.");
      return;
    }
    void run(() => analyzeMany(mode, lines, minScore) as Promise<BatchResult>);
  };

  // In browser mode the file is read locally, so no server round trip is needed.
  const upload = (file: File | undefined) => {
    if (!file) return;
    if (mode === "server") {
      void run(() => api.upload(file));
      return;
    }
    void run(async () => {
      const body = await file.text();
      const rows = file.name.toLowerCase().endsWith(".csv")
        ? body.split("\n").slice(1).map((line) => line.split(",").slice(1).join(","))
        : body.split("\n");
      const lines = rows.map((line) => line.trim()).filter(Boolean);
      if (lines.length === 0) throw new Error("no readable rows in file");
      return analyzeMany(mode, lines, minScore) as Promise<BatchResult>;
    });
  };

  return (
    <div className="stack">
      <Field label="Documents, one per line">
        <textarea
          value={raw}
          rows={6}
          placeholder={"Joko Widodo lahir di Surakarta\nNIK 3204012509900001\nemail budi@contoh.co.id"}
          onChange={(event) => setRaw(event.target.value)}
        />
      </Field>

      <div className="row gap">
        <Button onClick={analyzeLines} disabled={busy}>
          {busy ? "Working" : "Analyze lines"}
        </Button>
        <Button variant="ghost" onClick={() => picker.current?.click()} disabled={busy}>
          Upload txt or csv
        </Button>
        <input
          ref={picker}
          type="file"
          accept=".txt,.csv"
          hidden
          onChange={(event) => upload(event.target.files?.[0])}
        />
      </div>

      {error && <Banner kind="error">{error}</Banner>}

      {result ? (
        <>
          <p className="muted">
            {result.documents} documents, {result.entities} entities
          </p>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>id</th>
                  <th>entities</th>
                  <th>risk</th>
                  <th>types</th>
                  <th>preview</th>
                </tr>
              </thead>
              <tbody>
                {result.items.map((item) => (
                  <tr key={item.id}>
                    <td className="mono">{item.id}</td>
                    <td className="mono">{item.result?.stats.total ?? "-"}</td>
                    <td className="mono">{item.result?.stats.risk ?? "-"}</td>
                    <td>{item.result?.stats.by_label.map((entry) => entry.label).join(", ") || "-"}</td>
                    <td className="clip">{item.error ?? item.result?.text ?? ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : (
        <Empty>Paste lines or upload a file to scan many documents at once.</Empty>
      )}
    </div>
  );
}
