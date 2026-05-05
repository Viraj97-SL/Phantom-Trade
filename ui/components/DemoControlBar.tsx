"use client";
import { Zap, RefreshCw, BarChart2 } from "lucide-react";
import { api } from "@/lib/api";

interface Props {
  onRunDefault: () => void;
  onReset: () => void;
  recentEvent?: string;
  isRunning?: boolean;
}

export default function DemoControlBar({ onRunDefault, onReset, recentEvent, isRunning }: Props) {
  const handleReset = async () => {
    try {
      await api.resetDemo();
      onReset();
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div
      className="flex items-center justify-between px-6 py-2"
      style={{ background: "#111118", borderBottom: "1px solid #1E1E2E" }}
    >
      <div className="flex items-center gap-3">
        <button
          onClick={onRunDefault}
          disabled={isRunning}
          className="flex items-center gap-2 px-4 py-1.5 rounded-md text-sm font-medium transition-all"
          style={{
            background: isRunning ? "#1E1E2E" : "#6366F1",
            color: isRunning ? "#64748B" : "#fff",
            cursor: isRunning ? "not-allowed" : "pointer",
          }}
        >
          <Zap size={14} />
          Run Default Scenario
        </button>

        <button
          onClick={handleReset}
          className="flex items-center gap-2 px-3 py-1.5 rounded-md text-sm transition-all"
          style={{ background: "#1E1E2E", color: "#94A3B8" }}
        >
          <RefreshCw size={14} />
          Reset Demo
        </button>
      </div>

      {recentEvent && (
        <div className="flex items-center gap-2 text-xs" style={{ color: "#475569" }}>
          <BarChart2 size={12} />
          <span className="truncate max-w-sm">{recentEvent}</span>
        </div>
      )}
    </div>
  );
}
