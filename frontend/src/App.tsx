import { useCallback, useState } from "react";

import type { ExportFormat } from "./api/types";
import { API_CONFIGURED, download, modelRepo } from "./engine";
import { Toolbar } from "./components/Toolbar";
import { Banner, Button, Card, Empty, Field, Slider } from "./components/ui";
import { EntityTable } from "./features/analyze/EntityTable";
import { HighlightedText } from "./features/analyze/HighlightedText";
import { StatsPanel } from "./features/analyze/StatsPanel";
import { BatchPanel } from "./features/batch/BatchPanel";
import { RedactPanel } from "./features/redact/RedactPanel";
import { useEngine } from "./hooks/useEngine";
import { useTheme } from "./hooks/useTheme";

const EXAMPLES = [
  "Joko Widodo lahir di Surakarta pada tanggal 21 Juni 1961.",
  "Nama saya Budi, pria, NIK 3204 0125 0990 0001, HP +62 812-3456-7890.",
  "Silakan hubungi Siti di siti.rahma+kerja@contoh.co.id atau 081234567890.",
];

type Tab = "analyze" | "redact" | "batch";

export default function App() {
  const { theme, toggle } = useTheme();
  const { mode, setMode, meta, status, analysis, redaction, busy, error, doAnalyze, doRedact } = useEngine();

  const [text, setText] = useState(EXAMPLES[0]);
  const [minScore, setMinScore] = useState(0.5);
  const [tab, setTab] = useState<Tab>("analyze");
  const [active, setActive] = useState<Set<string>>(new Set());

  // An empty active set means show every type, which keeps the filter logic simple.
  const toggleLabel = useCallback((code: string) => {
    setActive((current) => {
      const next = new Set(current);
      if (next.has(code)) next.delete(code);
      else next.add(code);
      return next.size === 0 ? new Set() : next;
    });
  }, []);

  const save = (format: ExportFormat) => analysis && download(analysis, format);

  return (
    <div className="page">
      <Toolbar meta={meta} theme={theme} onToggleTheme={toggle} mode={mode} onModeChange={setMode} apiAvailable={API_CONFIGURED} />

      {mode === "browser" && (
        <Banner kind="info">
          The model runs in your browser, about 12 MB downloaded once and cached. Your text never leaves this device.
        </Banner>
      )}
      {status && <Banner kind="info">{status}</Banner>}

      <Card
        title="Input"
        actions={
          <>
            {EXAMPLES.map((example, index) => (
              <Button key={index} variant="ghost" onClick={() => setText(example)} title={example}>
                Example {index + 1}
              </Button>
            ))}
          </>
        }
      >
        <textarea
          value={text}
          rows={5}
          placeholder="Tulis atau tempel teks Bahasa Indonesia di sini"
          onChange={(event) => setText(event.target.value)}
        />
        <div className="controls">
          <Field label="Minimum score" hint="Raise to keep only confident predictions">
            <Slider value={minScore} min={0} max={0.99} step={0.01} onChange={setMinScore} />
          </Field>
          <Button onClick={() => void doAnalyze(text, minScore)} disabled={busy || !text.trim()}>
            {busy ? "Analyzing" : "Analyze"}
          </Button>
        </div>
        {error && <Banner kind="error">{error}</Banner>}
      </Card>

      <nav className="tabs">
        {(["analyze", "redact", "batch"] as Tab[]).map((name) => (
          <button
            key={name}
            type="button"
            className={`tab ${tab === name ? "active" : ""}`}
            onClick={() => setTab(name)}
          >
            {name}
          </button>
        ))}
      </nav>

      {tab === "analyze" && (
        <Card
          title="Entities"
          actions={
            analysis && meta
              ? meta.formats.map((format) => (
                  <Button key={format} variant="ghost" onClick={() => save(format as ExportFormat)}>
                    {format}
                  </Button>
                ))
              : undefined
          }
        >
          {analysis && meta ? (
            <div className="stack">
              {analysis.truncated && <Banner kind="info">Input was clipped to the character limit.</Banner>}
              <StatsPanel stats={analysis.stats} labels={meta.labels} active={active} onToggle={toggleLabel} />
              <HighlightedText text={analysis.text} entities={analysis.entities} labels={meta.labels} active={active} />
              <EntityTable entities={analysis.entities} />
            </div>
          ) : (
            <Empty>Analyze some text to see highlighted entities.</Empty>
          )}
        </Card>
      )}

      {tab === "redact" && (
        <Card title="Redaction">
          {meta ? (
            <RedactPanel
              meta={meta}
              result={redaction}
              busy={busy}
              onRun={(strategy, sensitivity, mapping) =>
                void doRedact(text, minScore, strategy, sensitivity, mapping)
              }
            />
          ) : (
            <Empty>Waiting for the API.</Empty>
          )}
        </Card>
      )}

      {tab === "batch" && (
        <Card title="Batch">
          <BatchPanel minScore={minScore} mode={mode} />
        </Card>
      )}

      <footer className="foot">
        <span>
          Model{" "}
          <a href={`https://huggingface.co/${modelRepo()}`} target="_blank" rel="noreferrer">
            {modelRepo()}
          </a>
        </span>
        <a href="https://github.com/0xcynyx/ner-app-gradio" target="_blank" rel="noreferrer">
          Source
        </a>
      </footer>
    </div>
  );
}
