"use client";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid
} from "recharts";
import type { ReasoningEntry } from "@/types";

interface Props {
  entries: ReasoningEntry[];
}

export default function ImprovementChart({ entries }: Props) {
  const data = [...entries].reverse().map((e, i) => ({
    run: i + 1,
    accuracy: parseFloat((0.5 + e.accuracy_delta).toFixed(3)),
    pipeline: e.pipeline,
  }));

  return (
    <div className="flex flex-col gap-2">
      <div className="text-xs font-semibold uppercase tracking-wide" style={{ color: "#64748B" }}>
        Agent Performance Over Runs
      </div>

      {data.length === 0 ? (
        <div className="text-xs text-center py-4" style={{ color: "#475569" }}>
          No data yet
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={160}>
          <LineChart data={data} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1E1E2E" />
            <XAxis dataKey="run" tick={{ fill: "#475569", fontSize: 10 }} tickLine={false} />
            <YAxis domain={[0, 1]} tick={{ fill: "#475569", fontSize: 10 }} tickLine={false} />
            <Tooltip
              contentStyle={{ background: "#111118", border: "1px solid #1E1E2E", borderRadius: 6 }}
              labelStyle={{ color: "#94A3B8" }}
              itemStyle={{ color: "#F1F5F9" }}
            />
            <Line
              type="monotone"
              dataKey="accuracy"
              stroke="#6366F1"
              strokeWidth={2}
              dot={{ fill: "#6366F1", r: 3 }}
              name="Accuracy"
            />
          </LineChart>
        </ResponsiveContainer>
      )}

      {data.length >= 2 && (
        <div className="text-xs" style={{ color: "#475569" }}>
          Run #1 → #{data.length}: accuracy {
            data[0].accuracy < data[data.length - 1].accuracy ? "improving" : "fluctuating"
          }
        </div>
      )}
    </div>
  );
}
