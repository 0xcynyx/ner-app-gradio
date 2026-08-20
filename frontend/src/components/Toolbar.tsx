import type { Meta } from "../api/types";
import type { Mode } from "../engine";
import { Button, Select } from "./ui";

export function Toolbar({
  meta,
  theme,
  onToggleTheme,
  mode,
  onModeChange,
  apiAvailable,
}: {
  meta: Meta | null;
  theme: string;
  onToggleTheme: () => void;
  mode: Mode;
  onModeChange: (mode: Mode) => void;
  apiAvailable: boolean;
}) {
  const backend = meta?.model.backend ?? "loading";
  return (
    <header className="topbar">
      <div>
        <h1>NER Studio</h1>
        <p className="sub">Entity recognition and PII redaction for Bahasa Indonesia</p>
      </div>
      <div className="row gap">
        {apiAvailable && (
          <Select
            value={mode}
            options={[
              { value: "browser", label: "run in browser" },
              { value: "server", label: "run on server" },
            ]}
            onChange={(value) => onModeChange(value as Mode)}
          />
        )}
        <span className={`pill ${backend === "fake" ? "warn" : "ok"}`} title={meta?.model.model ?? ""}>
          {backend === "browser" ? "on device" : backend === "fake" ? "demo backend" : "server model"}
        </span>
        <Button variant="ghost" onClick={onToggleTheme} title="Toggle theme">
          {theme === "dark" ? "☀" : "☾"}
        </Button>
      </div>
    </header>
  );
}
