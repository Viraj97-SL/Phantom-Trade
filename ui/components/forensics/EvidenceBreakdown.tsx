"use client";
import type { EvidenceItem } from "@/types";

const TYPE_COLORS: Record<string, string> = {
  audio_artefact: "#F59E0B",
  visual_anomaly: "#EF4444",
  ocr_mismatch: "#8B5CF6",
  metadata_inconsistency: "#3B82F6",
  platform_signal: "#10B981",
  prior_pattern: "#6366F1",
};

const TYPE_LABELS: Record<string, string> = {
  audio_artefact: "Audio",
  visual_anomaly: "Visual",
  ocr_mismatch: "OCR",
  metadata_inconsistency: "Metadata",
  platform_signal: "Platform",
  prior_pattern: "Prior pattern",
};

interface Props {
  evidence: EvidenceItem[];
}

export default function EvidenceBreakdown({ evidence }: Props) {
  const grouped = evidence.reduce<Record<string, EvidenceItem[]>>((acc, item) => {
    const key = item.evidence_type;
    if (!acc[key]) acc[key] = [];
    acc[key].push(item);
    return acc;
  }, {});

  if (evidence.length === 0) return null;

  return (
    <div className="flex flex-col gap-2">
      {Object.entries(grouped).map(([type, items]) => {
        const color = TYPE_COLORS[type] ?? "#64748B";
        const label = TYPE_LABELS[type] ?? type;
        return (
          <div key={type}>
            <div className="flex items-center gap-1.5 mb-1">
              <span
                className="w-2 h-2 rounded-full shrink-0"
                style={{ background: color }}
              />
              <span className="text-xs font-medium" style={{ color: "#94A3B8" }}>{label}</span>
              <span className="text-xs" style={{ color: "#475569" }}>({items.length})</span>
            </div>
            <div className="flex flex-col gap-1 pl-3.5">
              {items.map((item, i) => (
                <div key={i} className="flex items-start gap-2 text-xs" style={{ color: "#64748B" }}>
                  <span className="shrink-0">·</span>
                  <span>{item.description}</span>
                  <span
                    className="shrink-0 ml-auto font-mono"
                    style={{ color }}
                  >
                    {Math.round(item.confidence * 100)}%
                  </span>
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
