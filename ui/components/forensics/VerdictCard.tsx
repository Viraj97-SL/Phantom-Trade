"use client";
import { useState } from "react";
import { ChevronDown, ChevronUp, AlertTriangle, CheckCircle, HelpCircle } from "lucide-react";
import { verdictColor, formatDate } from "@/lib/utils";
import type { ClaimVerdict } from "@/types";

interface Props {
  verdict: ClaimVerdict;
}

function VerdictIcon({ verdict }: { verdict: string }) {
  if (verdict === "FABRICATED") return <AlertTriangle size={20} style={{ color: "#EF4444" }} />;
  if (verdict === "AUTHENTIC") return <CheckCircle size={20} style={{ color: "#22C55E" }} />;
  return <HelpCircle size={20} style={{ color: "#F59E0B" }} />;
}

export default function VerdictCard({ verdict }: Props) {
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  const [debateOpen, setDebateOpen] = useState(false);
  const color = verdictColor(verdict.verdict);

  const debateLines = verdict.debate_transcript?.split("\n\n") ?? [];
  const proAuthLine = debateLines.find((l) => l.startsWith("PRO-AUTHENTIC"));
  const proFabLine = debateLines.find((l) => l.startsWith("PRO-FABRICATED"));

  const proAuthScore = parseFloat(
    proAuthLine?.match(/\((\d+\.\d+)\)/)?.[1] ?? "0"
  );
  const proFabScore = parseFloat(
    proFabLine?.match(/\((\d+\.\d+)\)/)?.[1] ?? "0"
  );

  return (
    <div
      className="rounded-lg p-4 flex flex-col gap-3 animate-slide-up"
      style={{
        background: "#111118",
        borderLeft: `4px solid ${color}`,
        border: `1px solid #1E1E2E`,
        borderLeftColor: color,
        borderLeftWidth: "4px",
      }}
    >
      {/* Top row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <VerdictIcon verdict={verdict.verdict} />
          <span className="text-lg font-bold" style={{ color }}>{verdict.verdict}</span>
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold" style={{ color: "#F1F5F9" }}>
            {Math.round(verdict.confidence * 100)}%
          </div>
          <div className="text-xs" style={{ color: "#475569" }}>confidence</div>
        </div>
      </div>

      {/* Confidence bar */}
      <div className="w-full h-1.5 rounded-full" style={{ background: "#1E1E2E" }}>
        <div
          className="h-1.5 rounded-full transition-all duration-1000"
          style={{ width: `${verdict.confidence * 100}%`, background: color }}
        />
      </div>

      {/* Topics */}
      <div className="flex flex-wrap gap-1.5">
        {verdict.supply_chain_topics.map((t) => (
          <span
            key={t}
            className="text-xs px-2 py-0.5 rounded-full"
            style={{ background: "#1E1E2E", color: "#94A3B8" }}
          >
            {t}
          </span>
        ))}
      </div>

      {/* Stats */}
      <div className="text-xs" style={{ color: "#64748B" }}>
        {verdict.variants_analysed} variants analysed
        {verdict.created_at && ` · ${formatDate(verdict.created_at)}`}
      </div>

      {/* Evidence collapsible */}
      {verdict.evidence.length > 0 && (
        <div>
          <button
            onClick={() => setEvidenceOpen(!evidenceOpen)}
            className="flex items-center gap-1 text-xs font-medium"
            style={{ color: "#94A3B8" }}
          >
            {evidenceOpen ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            Evidence ({verdict.evidence.length})
          </button>
          {evidenceOpen && (
            <div className="mt-2 flex flex-col gap-1.5">
              {verdict.evidence.map((e, i) => (
                <div key={i} className="text-xs" style={{ color: "#94A3B8" }}>
                  · {e.description}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Debate collapsible */}
      {verdict.debate_transcript && (
        <div>
          <button
            onClick={() => setDebateOpen(!debateOpen)}
            className="flex items-center gap-1 text-xs font-medium"
            style={{ color: "#94A3B8" }}
          >
            {debateOpen ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            Debate summary
          </button>
          {debateOpen && (
            <div className="mt-2 flex flex-col gap-2">
              <div className="flex items-center gap-2 text-xs">
                <span style={{ color: "#22C55E", width: 90 }}>Pro-authentic</span>
                <div className="flex-1 h-1.5 rounded-full" style={{ background: "#1E1E2E" }}>
                  <div
                    className="h-1.5 rounded-full"
                    style={{ width: `${proAuthScore * 100}%`, background: "#22C55E" }}
                  />
                </div>
                <span style={{ color: "#94A3B8" }}>{proAuthScore.toFixed(2)}</span>
              </div>
              <div className="flex items-center gap-2 text-xs">
                <span style={{ color: "#EF4444", width: 90 }}>Pro-fabricated</span>
                <div className="flex-1 h-1.5 rounded-full" style={{ background: "#1E1E2E" }}>
                  <div
                    className="h-1.5 rounded-full"
                    style={{ width: `${proFabScore * 100}%`, background: "#EF4444" }}
                  />
                </div>
                <span style={{ color: "#94A3B8" }}>{proFabScore.toFixed(2)}</span>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
