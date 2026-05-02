"use client";
import type { RBStats } from "@/types";

interface StatCardProps {
  label: string;
  value: string;
  positive?: boolean;
}

function StatCard({ label, value, positive }: StatCardProps) {
  return (
    <div
      className="rounded-lg p-3 flex flex-col gap-1"
      style={{ background: "#0A0A0F", border: "1px solid #1E1E2E" }}
    >
      <div className="text-xs" style={{ color: "#475569" }}>{label}</div>
      <div
        className="text-2xl font-bold"
        style={{ color: positive === true ? "#22C55E" : positive === false ? "#EF4444" : "#F1F5F9" }}
      >
        {value}
      </div>
    </div>
  );
}

interface Props {
  stats: RBStats;
}

export default function RBStatsPanel({ stats }: Props) {
  return (
    <div className="grid grid-cols-2 gap-2">
      <StatCard label="Total Entries" value={String(stats.total_entries)} />
      <StatCard label="Success Rate" value={`${stats.successful_entries}`} />
      <StatCard
        label="Avg Accuracy Delta"
        value={`${stats.avg_accuracy_delta >= 0 ? "+" : ""}${stats.avg_accuracy_delta.toFixed(3)}`}
        positive={stats.avg_accuracy_delta >= 0}
      />
      <StatCard label="Hit Rate" value={`${Math.round(stats.hit_rate * 100)}%`} />
    </div>
  );
}
