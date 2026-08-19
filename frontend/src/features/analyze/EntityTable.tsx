import { useMemo, useState } from "react";

import type { EntityOut } from "../../api/types";

type Column = "start" | "label" | "text" | "score";

// Sorting is local to the fetched entity list, which is already the whole document.
export function EntityTable({ entities }: { entities: EntityOut[] }) {
  const [column, setColumn] = useState<Column>("start");
  const [descending, setDescending] = useState(false);

  const rows = useMemo(() => {
    const direction = descending ? -1 : 1;
    return [...entities].sort((a, b) => {
      const left = a[column];
      const right = b[column];
      if (typeof left === "number" && typeof right === "number") return (left - right) * direction;
      return String(left).localeCompare(String(right)) * direction;
    });
  }, [entities, column, descending]);

  const sortBy = (next: Column) => {
    if (next === column) setDescending((prev) => !prev);
    else {
      setColumn(next);
      setDescending(false);
    }
  };

  if (entities.length === 0) return <p className="empty">No entities to list.</p>;

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {(["start", "label", "text", "score"] as Column[]).map((name) => (
              <th key={name} onClick={() => sortBy(name)} className="sortable" data-dir={column === name ? (descending ? "desc" : "asc") : undefined}>
                {name}
              </th>
            ))}
            <th>rule</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((entity, index) => (
            <tr key={`${entity.start}-${index}`}>
              <td className="mono">{entity.start}</td>
              <td>{entity.label}</td>
              <td>{entity.text}</td>
              <td className="mono">{entity.score.toFixed(3)}</td>
              <td>{entity.verified ? "✓" : ""}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
