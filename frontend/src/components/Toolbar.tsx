import type { Meta } from "../api/types";
import { Button } from "./ui";

export function Toolbar({ meta, theme, onToggleTheme }: { meta: Meta | null; theme: string; onToggleTheme: () => void }) {
  const backend = meta?.model.backend ?? "loading";
  return (
    <header className="topbar">
      <div>
        <h1>NER Studio</h1>
        <p className="sub">Entity recognition and PII redaction for Bahasa Indonesia</p>
      </div>
      <div className="row gap">
        <span className={`pill ${backend === "fake" ? "warn" : "ok"}`} title={meta?.model.model ?? ""}>
          {backend === "fake" ? "demo backend" : "model loaded"}
        </span>
        <Button variant="ghost" onClick={onToggleTheme} title="Toggle theme">
          {theme === "dark" ? "☀" : "☾"}
        </Button>
      </div>
    </header>
  );
}
