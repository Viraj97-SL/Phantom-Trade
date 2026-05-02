"use client";
import { formatDate } from "@/lib/utils";
import type { ReasoningEntry } from "@/types";

interface EntryCardProps {
  entry: ReasoningEntry;
  isNew?: boolean;
}

function EntryCard({ entry, isNew }: EntryCardProps) {
  const outcomeColor =
    entry.outcome === "SUCCESS" ? "#22C55E" :
    entry.outcome === "FAILURE" ? "#EF4444" :
    "#F59E0B";

  return (
    <div
      className={`rounded-lg p-3 flex flex-col gap-2 ${isNew ? "animate-flash-green" : ""}`}
      style={{ background: "#0A0A0F", border: "1px solid #1E1E2E" }}
    >
      <div className="flex items-center gap-2 flex-wrap">
        <span
          className="text-xs px-2 py-0.5 rounded-full font-medium"
          style={{ background: "#1E1E2E", color: "#6366F1" }}
        >
          {entry.pipeline.toUpperCase()}
        </span>
        {entry.material && (
          <span className="text-xs px-2 py-0.5 rounded-full" style={{ background: "#1E1E2E", color: "#94A3B8" }}>
            {entry.material}
          </span>
        )}
        <span
          className="text-xs px-2 py-0.5 rounded-full ml-auto font-medium"
          style={{ background: "#1E1E2E", color: outcomeColor }}
        >
          {entry.outcome}
        </span>
      </div>

      <p className="text-xs leading-relaxed line-clamp-2" style={{ color: "#94A3B8" }}>
        {entry.strategy_summary}
      </p>

      <div className="flex items-center justify-between text-xs" style={{ color: "#475569" }}>
        <span>
          Accuracy delta:{" "}
          <span style={{ color: entry.accuracy_delta >= 0 ? "#22C55E" : "#EF4444" }}>
            {entry.accuracy_delta >= 0 ? "+" : ""}{entry.accuracy_delta.toFixed(3)}
          </span>
        </span>
        <span>Decay: {(entry.decay_score ?? 1).toFixed(2)}</span>
        {entry.created_at && <span>{formatDate(entry.created_at)}</span>}
      </div>
    </div>
  );
}

interface Props {
  entries: ReasoningEntry[];
  newEntryId?: string;
}

export default function RBFeed({ entries, newEntryId }: Props) {
  return (
    <div className="flex flex-col gap-2">
      <div className="text-xs font-semibold uppercase tracking-wide" style={{ color: "#64748B" }}>
        Recent Strategies Learned
      </div>
      {entries.length === 0 && (
        <div className="text-xs text-center py-4" style={{ color: "#475569" }}>
          No entries yet — run the demo to populate
        </div>
      )}
      {entries.map((e, i) => (
        <EntryCard key={e.task_signature + i} entry={e} isNew={i === 0 && !!newEntryId} />
      ))}
    </div>
  );
}
