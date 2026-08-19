import { useMemo } from "react";

import type { EntityOut, LabelSpec } from "../../api/types";

interface Segment {
  text: string;
  entity?: EntityOut;
}

// Entities arrive sorted and non overlapping, so one pass builds the render list.
function toSegments(text: string, entities: EntityOut[]): Segment[] {
  const segments: Segment[] = [];
  let cursor = 0;
  for (const entity of entities) {
    if (entity.start > cursor) segments.push({ text: text.slice(cursor, entity.start) });
    segments.push({ text: text.slice(entity.start, entity.end), entity });
    cursor = entity.end;
  }
  if (cursor < text.length) segments.push({ text: text.slice(cursor) });
  return segments;
}

export function HighlightedText({
  text,
  entities,
  labels,
  active,
}: {
  text: string;
  entities: EntityOut[];
  labels: LabelSpec[];
  active: Set<string>;
}) {
  const colors = useMemo(() => new Map(labels.map((label) => [label.code, label.color])), [labels]);
  const shown = useMemo(
    () => entities.filter((entity) => active.size === 0 || active.has(entity.label)),
    [entities, active],
  );
  const segments = useMemo(() => toSegments(text, shown), [text, shown]);

  return (
    <div className="highlight">
      {segments.map((segment, index) =>
        segment.entity ? (
          <mark
            key={index}
            style={{ backgroundColor: `${colors.get(segment.entity.label) ?? "#94a3b8"}33`, borderColor: colors.get(segment.entity.label) }}
            title={`${segment.entity.label} · score ${segment.entity.score.toFixed(3)}${segment.entity.verified ? " · rule verified" : ""}`}
          >
            {segment.text}
            <span className="tag" style={{ color: colors.get(segment.entity.label) }}>
              {segment.entity.label}
              {segment.entity.verified && <span className="check">✓</span>}
            </span>
          </mark>
        ) : (
          <span key={index}>{segment.text}</span>
        ),
      )}
    </div>
  );
}
