import { useState } from "react";

import type { Meta, RedactResult } from "../../api/types";
import { Button, CopyButton, Empty, Field, Select } from "../../components/ui";

const SENSITIVITY = [
  { value: "0", label: "Everything detected" },
  { value: "3", label: "Sensitivity 3 and above" },
  { value: "4", label: "Sensitivity 4 and above" },
  { value: "5", label: "National ID only" },
];

const DESCRIPTIONS: Record<string, string> = {
  mask: "Replaces characters with blocks and keeps the original length.",
  label: "Swaps the value for its bracketed type, readable for review.",
  pseudonym: "Stable token per value, so the same person stays linkable.",
  partial: "Keeps a phone suffix and the email domain for support workflows.",
  remove: "Deletes the span outright.",
};

export function RedactPanel({
  meta,
  result,
  busy,
  onRun,
}: {
  meta: Meta;
  result: RedactResult | null;
  busy: boolean;
  onRun: (strategy: string, sensitivity: number, mapping: boolean) => void;
}) {
  const [strategy, setStrategy] = useState("mask");
  const [sensitivity, setSensitivity] = useState("0");
  const [mapping, setMapping] = useState(false);

  return (
    <div className="stack">
      <div className="controls">
        <Field label="Strategy" hint={DESCRIPTIONS[strategy]}>
          <Select
            value={strategy}
            options={meta.strategies.map((name) => ({ value: name, label: name }))}
            onChange={setStrategy}
          />
        </Field>
        <Field label="Scope">
          <Select value={sensitivity} options={SENSITIVITY} onChange={setSensitivity} />
        </Field>
        <label className="check-row">
          <input type="checkbox" checked={mapping} onChange={(event) => setMapping(event.target.checked)} />
          <span>Return mapping</span>
        </label>
        <Button onClick={() => onRun(strategy, Number(sensitivity), mapping)} disabled={busy}>
          {busy ? "Working" : "Redact"}
        </Button>
      </div>

      {mapping && <p className="banner info">The mapping re identifies people, treat it as sensitive data.</p>}

      {result ? (
        <>
          <div className="row between">
            <span className="muted">
              {result.replaced} replaced with {result.strategy}
            </span>
            <CopyButton text={result.text} label="Copy redacted text" />
          </div>
          <pre className="output">{result.text}</pre>
          {Object.keys(result.mapping).length > 0 && (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>original</th>
                    <th>token</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(result.mapping).map(([original, token]) => (
                    <tr key={original}>
                      <td>{original}</td>
                      <td className="mono">{token}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      ) : (
        <Empty>Run a redaction to see the rewritten text.</Empty>
      )}
    </div>
  );
}
