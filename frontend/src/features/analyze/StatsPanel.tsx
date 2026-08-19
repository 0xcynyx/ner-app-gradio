import type { LabelSpec, Stats } from "../../api/types";

// Risk bands mirror the backend weighting, 60 and above means a direct identifier is present.
function band(risk: number): { label: string; tone: string } {
  if (risk >= 60) return { label: "High", tone: "high" };
  if (risk >= 30) return { label: "Medium", tone: "medium" };
  if (risk > 0) return { label: "Low", tone: "low" };
  return { label: "None", tone: "none" };
}

export function StatsPanel({
  stats,
  labels,
  active,
  onToggle,
}: {
  stats: Stats;
  labels: LabelSpec[];
  active: Set<string>;
  onToggle: (code: string) => void;
}) {
  const risk = band(stats.risk);
  const known = new Map(labels.map((label) => [label.code, label]));

  return (
    <div className="stats">
      <div className="tiles">
        <div className="tile">
          <span className="tile-value">{stats.total}</span>
          <span className="tile-label">Entities</span>
        </div>
        <div className="tile">
          <span className="tile-value">{stats.characters.toLocaleString()}</span>
          <span className="tile-label">Characters</span>
        </div>
        <div className="tile">
          <span className="tile-value">{stats.chunks}</span>
          <span className="tile-label">Windows</span>
        </div>
        <div className={`tile risk ${risk.tone}`}>
          <span className="tile-value">{stats.risk}</span>
          <span className="tile-label">PII risk, {risk.label}</span>
        </div>
      </div>

      {stats.by_label.length > 0 && (
        <div className="chips">
          {stats.by_label.map((item) => {
            const spec = known.get(item.label);
            const on = active.size === 0 || active.has(item.label);
            return (
              <button
                key={item.label}
                type="button"
                className={`chip ${on ? "on" : "off"}`}
                style={{ borderColor: item.color, color: on ? item.color : undefined }}
                onClick={() => onToggle(item.label)}
                title={spec ? `${spec.display}, sensitivity ${spec.sensitivity} of 5` : item.label}
              >
                <span className="dot" style={{ backgroundColor: item.color }} />
                {item.display}
                <span className="count">{item.count}</span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
