"use client";
import { useEffect, useRef, useState } from "react";
import { riskColorByLevel } from "@/lib/utils";
import type { MaterialThesis } from "@/types";

interface GaugeProps {
  thesis: MaterialThesis;
  highlighted?: boolean;
}

function SemiGauge({ thesis, highlighted }: GaugeProps) {
  const [displayValue, setDisplayValue] = useState(thesis.risk_level);
  const prevRef = useRef(thesis.risk_level);
  const color = riskColorByLevel(thesis.risk_level);

  // Animate value change
  useEffect(() => {
    const from = prevRef.current;
    const to = thesis.risk_level;
    if (from === to) return;
    prevRef.current = to;

    const start = performance.now();
    const duration = 800;
    const raf = (now: number) => {
      const t = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - t, 3);
      setDisplayValue(Math.round(from + (to - from) * eased));
      if (t < 1) requestAnimationFrame(raf);
    };
    requestAnimationFrame(raf);
  }, [thesis.risk_level]);

  // SVG semicircle path
  const r = 52;
  const cx = 70;
  const cy = 70;
  const startAngle = Math.PI;
  const endAngle = 0;
  const valueAngle = Math.PI - (thesis.risk_level / 100) * Math.PI;

  const polarToCartesian = (angle: number) => ({
    x: cx + r * Math.cos(angle),
    y: cy - r * Math.sin(angle),
  });

  const startPt = polarToCartesian(startAngle);
  const endPt = polarToCartesian(endAngle);
  const valuePt = polarToCartesian(valueAngle);

  const trackPath = `M ${startPt.x} ${startPt.y} A ${r} ${r} 0 0 1 ${endPt.x} ${endPt.y}`;
  const fillPath = `M ${startPt.x} ${startPt.y} A ${r} ${r} 0 0 1 ${valuePt.x} ${valuePt.y}`;

  return (
    <div
      className="flex flex-col items-center rounded-lg p-3"
      style={{
        background: "#111118",
        border: `1px solid ${highlighted ? "#6366F1" : "#1E1E2E"}`,
        boxShadow: highlighted ? "0 0 16px rgba(99,102,241,0.3)" : undefined,
        transition: "all 0.4s ease",
      }}
    >
      {highlighted && (
        <div className="text-xs mb-1 text-center" style={{ color: "#6366F1" }}>
          Updated by forensics verdict
        </div>
      )}
      <svg width={140} height={90} viewBox="0 0 140 90">
        {/* Track */}
        <path d={trackPath} fill="none" stroke="#1E1E2E" strokeWidth={10} strokeLinecap="round" />
        {/* Fill */}
        <path d={fillPath} fill="none" stroke={color} strokeWidth={10} strokeLinecap="round"
          style={{ transition: "stroke 0.5s ease" }} />
        {/* Centre value */}
        <text x={cx} y={cy + 5} textAnchor="middle" fill="#F1F5F9"
          fontSize={24} fontWeight="bold">{displayValue}</text>
      </svg>

      <div className="text-sm font-semibold uppercase tracking-wide mt-1" style={{ color: "#F1F5F9" }}>
        {thesis.material}
      </div>
      <div className="text-xs mt-0.5 px-2 py-0.5 rounded-full" style={{ background: "#0A0A0F", color }}>
        {thesis.risk_label}
      </div>
    </div>
  );
}

interface Props {
  theses: MaterialThesis[];
  highlightedMaterial?: string;
}

export default function RiskGauges({ theses, highlightedMaterial }: Props) {
  if (!theses.length) {
    return (
      <div className="grid grid-cols-2 gap-3">
        {["soybeans", "neon", "palladium", "lithium"].map((m) => (
          <div
            key={m}
            className="h-32 rounded-lg animate-pulse"
            style={{ background: "#111118" }}
          />
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-3">
      {theses.map((t) => (
        <SemiGauge
          key={t.material}
          thesis={t}
          highlighted={t.material === highlightedMaterial}
        />
      ))}
    </div>
  );
}
