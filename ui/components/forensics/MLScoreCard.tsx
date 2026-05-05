"use client";
import { Brain, AlertCircle } from "lucide-react";
import type { MLForensicsResult } from "@/types";

interface SubScoreRowProps {
  label: string;
  score: number;
  flagged: boolean;
}

function SubScoreRow({ label, score, flagged }: SubScoreRowProps) {
  const pct = Math.round(score * 100);
  const color = score >= 0.7 ? "#EF4444" : score >= 0.4 ? "#F59E0B" : "#22C55E";
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="w-32 shrink-0" style={{ color: "#94A3B8" }}>{label}</span>
      <div className="flex-1 h-1.5 rounded-full" style={{ background: "#1E1E2E" }}>
        <div
          className="h-1.5 rounded-full transition-all duration-700"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
      <span className="w-8 text-right font-mono" style={{ color }}>{pct}</span>
      {flagged && <AlertCircle size={10} style={{ color: "#EF4444" }} />}
    </div>
  );
}

interface Props {
  ml: MLForensicsResult;
}

const COMPOSITE_COLOR = (s: number) =>
  s >= 0.7 ? "#EF4444" : s >= 0.45 ? "#F59E0B" : "#22C55E";

export default function MLScoreCard({ ml }: Props) {
  const compositePct = Math.round(ml.composite_ml_score * 100);
  const color = COMPOSITE_COLOR(ml.composite_ml_score);

  const rows: { key: keyof MLForensicsResult; label: string }[] = [
    { key: "spread_velocity_score", label: "Spread velocity" },
    { key: "variant_similarity_score", label: "Variant similarity" },
    { key: "linguistic_score", label: "Linguistic anomaly" },
    { key: "source_credibility_score", label: "Source credibility" },
    { key: "template_match_score", label: "Template match" },
  ];

  return (
    <div
      className="flex flex-col gap-3 p-3 rounded-lg"
      style={{ background: "#0A0A0F", border: "1px solid #1E1E2E" }}
    >
      {/* Header + composite gauge */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Brain size={13} style={{ color: "#6366F1" }} />
          <span className="text-xs font-semibold uppercase tracking-wide" style={{ color: "#64748B" }}>
            ML Forensics
          </span>
          {ml.coordinated_campaign_flag && (
            <span
              className="text-xs px-2 py-0.5 rounded-full font-medium"
              style={{ background: "#EF444422", color: "#EF4444" }}
            >
              Coordinated
            </span>
          )}
        </div>
        <div className="flex flex-col items-end">
          <span className="text-xl font-bold font-mono" style={{ color }}>{compositePct}</span>
          <span className="text-xs" style={{ color: "#475569" }}>composite</span>
        </div>
      </div>

      {/* Sub-score bars */}
      <div className="flex flex-col gap-2">
        {rows.map(({ key, label }) => {
          const score = ml[key] as number;
          return (
            <SubScoreRow
              key={key}
              label={label}
              score={score}
              flagged={score >= 0.7}
            />
          );
        })}
      </div>

      {/* ML flags */}
      {ml.ml_flags.length > 0 && (
        <div className="flex flex-col gap-1">
          {ml.ml_flags.slice(0, 4).map((flag, i) => (
            <div key={i} className="flex items-start gap-1.5 text-xs" style={{ color: "#94A3B8" }}>
              <AlertCircle size={10} className="shrink-0 mt-0.5" style={{ color: "#F59E0B" }} />
              {flag}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
