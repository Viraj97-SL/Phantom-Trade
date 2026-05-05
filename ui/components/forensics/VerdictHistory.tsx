"use client";
import { useEffect, useState } from "react";
import { History, AlertTriangle, CheckCircle, HelpCircle } from "lucide-react";
import { api } from "@/lib/api";
import { verdictColor, formatDate } from "@/lib/utils";
import type { ClaimVerdict } from "@/types";

function VerdictBadge({ verdict }: { verdict: string }) {
  const color = verdictColor(verdict);
  const Icon =
    verdict === "FABRICATED" ? AlertTriangle :
    verdict === "AUTHENTIC" ? CheckCircle : HelpCircle;
  return (
    <span className="flex items-center gap-1" style={{ color }}>
      <Icon size={11} />
      <span className="text-xs font-medium">{verdict}</span>
    </span>
  );
}

export default function VerdictHistory() {
  const [verdicts, setVerdicts] = useState<ClaimVerdict[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getVerdicts()
      .then(setVerdicts)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return null;
  if (verdicts.length === 0) return null;

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-2">
        <History size={13} style={{ color: "#475569" }} />
        <span className="text-xs font-semibold uppercase tracking-wide" style={{ color: "#64748B" }}>
          Recent Verdicts
        </span>
      </div>

      <div
        className="rounded-lg overflow-hidden"
        style={{ border: "1px solid #1E1E2E" }}
      >
        <table className="w-full text-xs">
          <thead>
            <tr style={{ background: "#0A0A0F", borderBottom: "1px solid #1E1E2E" }}>
              <th className="text-left px-3 py-2 font-medium" style={{ color: "#475569", width: "40%" }}>Claim</th>
              <th className="text-left px-3 py-2 font-medium" style={{ color: "#475569" }}>Verdict</th>
              <th className="text-right px-3 py-2 font-medium" style={{ color: "#475569" }}>Conf.</th>
              <th className="text-right px-3 py-2 font-medium" style={{ color: "#475569" }}>Date</th>
            </tr>
          </thead>
          <tbody>
            {verdicts.slice(0, 10).map((v, i) => (
              <tr
                key={v.claim_id}
                style={{
                  background: i % 2 === 0 ? "#111118" : "#0A0A0F",
                  borderTop: i > 0 ? "1px solid #1E1E2E" : undefined,
                }}
              >
                <td className="px-3 py-2" style={{ color: "#94A3B8", maxWidth: 0 }}>
                  <span className="block truncate" title={v.claim_text}>
                    {v.claim_text.slice(0, 60)}…
                  </span>
                </td>
                <td className="px-3 py-2">
                  <VerdictBadge verdict={v.verdict} />
                </td>
                <td className="px-3 py-2 text-right font-mono" style={{ color: "#64748B" }}>
                  {Math.round(v.confidence * 100)}%
                </td>
                <td className="px-3 py-2 text-right" style={{ color: "#475569" }}>
                  {v.created_at ? formatDate(v.created_at) : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
