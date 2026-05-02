"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { riskColor, formatDate } from "@/lib/utils";
import type { Material, MaterialThesis } from "@/types";

const MATERIALS: Material[] = ["soybeans", "neon", "palladium", "lithium"];

interface Props {
  initialTheses?: MaterialThesis[];
}

export default function ThesisSlider({ initialTheses }: Props) {
  const [selected, setSelected] = useState<Material>("soybeans");
  const [history, setHistory] = useState<MaterialThesis[]>([]);
  const [index, setIndex] = useState(0);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api.getThesisHistory(selected).then((data) => {
      if (!cancelled) {
        setHistory(data);
        setIndex(0);
      }
    }).finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [selected]);

  const current = history[index] ?? null;
  const color = current ? riskColor(current.risk_label) : "#64748B";

  return (
    <div
      className="rounded-lg p-4 flex flex-col gap-4"
      style={{ background: "#111118", border: "1px solid #1E1E2E" }}
    >
      <div className="text-xs font-semibold uppercase tracking-wide" style={{ color: "#64748B" }}>
        Bi-Temporal Thesis History
      </div>

      {/* Material tabs */}
      <div className="flex gap-1">
        {MATERIALS.map((m) => (
          <button
            key={m}
            onClick={() => setSelected(m)}
            className="px-3 py-1 rounded text-xs font-medium transition-all"
            style={{
              background: selected === m ? "#6366F1" : "#0A0A0F",
              color: selected === m ? "#fff" : "#64748B",
              border: "1px solid",
              borderColor: selected === m ? "#6366F1" : "#1E1E2E",
            }}
          >
            {m.toUpperCase()}
          </button>
        ))}
      </div>

      {loading && (
        <div className="text-xs text-center" style={{ color: "#475569" }}>Loading...</div>
      )}

      {!loading && history.length > 0 && (
        <>
          {/* Timeline dots */}
          <div className="relative flex items-center gap-0">
            <div className="absolute left-0 right-0 h-0.5" style={{ background: "#1E1E2E" }} />
            <div className="relative flex justify-between w-full">
              {history.map((h, i) => (
                <button
                  key={i}
                  onClick={() => setIndex(i)}
                  title={formatDate(h.valid_from)}
                  className="relative z-10 rounded-full border-2 transition-all"
                  style={{
                    width: i === index ? 14 : 10,
                    height: i === index ? 14 : 10,
                    background: riskColor(h.risk_label),
                    borderColor: i === index ? "#F1F5F9" : "transparent",
                  }}
                />
              ))}
            </div>
          </div>

          {/* Slider */}
          <input
            type="range"
            min={0}
            max={history.length - 1}
            value={index}
            onChange={(e) => setIndex(Number(e.target.value))}
            className="w-full"
            style={{ accentColor: "#6366F1" }}
          />

          {current && (
            <div className="flex flex-col gap-2">
              <div className="text-xs" style={{ color: "#475569" }}>
                As of: {formatDate(current.valid_from)}
                {current.valid_to && ` → closed ${formatDate(current.valid_to)}`}
                {!current.valid_to && " (CURRENT)"}
              </div>

              <div className="flex items-baseline gap-2">
                <span className="text-3xl font-bold" style={{ color }}>
                  {current.risk_level}
                </span>
                <span className="text-sm" style={{ color }}>{current.risk_label}</span>
              </div>

              <p className="text-xs leading-relaxed" style={{ color: "#94A3B8" }}>
                {current.narrative}
              </p>

              {current.triggered_by && (
                <div className="text-xs" style={{ color: "#475569" }}>
                  Triggered by: {current.triggered_by}
                </div>
              )}

              {current.key_drivers && current.key_drivers.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {current.key_drivers.map((d, i) => (
                    <span
                      key={i}
                      className="text-xs px-2 py-0.5 rounded-full"
                      style={{ background: "#0A0A0F", color: "#64748B" }}
                    >
                      {d}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}
        </>
      )}

      {!loading && history.length === 0 && (
        <div className="text-xs text-center" style={{ color: "#475569" }}>
          No history available
        </div>
      )}
    </div>
  );
}
