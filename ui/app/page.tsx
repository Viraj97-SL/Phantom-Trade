"use client";
import dynamic from "next/dynamic";
import { useState, useCallback, useRef } from "react";
import Header from "@/components/Header";
import DemoControlBar from "@/components/DemoControlBar";
import ClaimInput from "@/components/forensics/ClaimInput";
import VerdictCard from "@/components/forensics/VerdictCard";
import VerdictHistory from "@/components/forensics/VerdictHistory";
import RiskGauges from "@/components/oracle/RiskGauges";
import ThesisSlider from "@/components/oracle/ThesisSlider";
import RBStatsPanel from "@/components/reasoning-bank/RBStats";
import RBFeed from "@/components/reasoning-bank/RBFeed";
import ImprovementChart from "@/components/reasoning-bank/ImprovementChart";
import { useTheses } from "@/hooks/useTheses";
import { useReasoningBank } from "@/hooks/useReasoningBank";
import { api } from "@/lib/api";
import type { ClaimVariant, ClaimVerdict, SSEEvent, ScenarioTemplate } from "@/types";

const MutationGraph = dynamic(
  () => import("@/components/forensics/MutationGraph"),
  { ssr: false }
);

interface PipelineStep {
  id: string;
  label: string;
  done: boolean;
}

const STEP_DEFS: PipelineStep[] = [
  { id: "tracking_variants", label: "Tracking variants across platforms...", done: false },
  { id: "news_crossref", label: "Cross-referencing live news sources...", done: false },
  { id: "ml_forensics", label: "Running ML scoring (TF-IDF, velocity, templates)...", done: false },
  { id: "forensics", label: "LLM forensics analysis...", done: false },
  { id: "debate", label: "Debate agents deliberating...", done: false },
  { id: "verdict", label: "Writing verdict to MongoDB...", done: false },
];

export default function Home() {
  const { theses, updateThesis } = useTheses(5000);
  const { stats, recent, refetch: refetchRB } = useReasoningBank(8000);

  const [isRunning, setIsRunning] = useState(false);
  const [steps, setSteps] = useState<PipelineStep[]>([]);
  const [variants, setVariants] = useState<ClaimVariant[]>([]);
  const [verdict, setVerdict] = useState<ClaimVerdict | null>(null);
  const [highlightedMaterial, setHighlightedMaterial] = useState<string | undefined>();
  const [recentEvent, setRecentEvent] = useState<string | undefined>();
  const [newEntryId, setNewEntryId] = useState<string | undefined>();

  const esRef = useRef<EventSource | null>(null);

  const markStep = useCallback((stepId: string) => {
    setSteps((prev) =>
      prev.map((s) => (s.id === stepId ? { ...s, done: true } : s))
    );
  }, []);

  const handleSSEEvent = useCallback(
    (event: SSEEvent) => {
      switch (event.type) {
        case "pipeline_started":
          setSteps(STEP_DEFS.map((s) => ({ ...s, done: false })));
          break;
        case "variant_found":
          setVariants((prev) => [...prev, event.data as unknown as ClaimVariant]);
          break;
        case "step": {
          const d = event.data as { step: string; message: string };
          markStep(d.step);
          setRecentEvent(d.message);
          break;
        }
        case "news_crossref_complete": {
          const d = event.data as { total_coverage: number; major_outlets_reporting: boolean };
          markStep("news_crossref");
          setRecentEvent(
            `News: ${d.total_coverage} sources · major outlets: ${d.major_outlets_reporting ? "yes" : "no"}`
          );
          break;
        }
        case "ml_forensics_complete": {
          const d = event.data as { composite_ml_score: number; coordinated_campaign_flag: boolean };
          markStep("ml_forensics");
          setRecentEvent(
            `ML score: ${Math.round(d.composite_ml_score * 100)}%${d.coordinated_campaign_flag ? " · coordinated campaign" : ""}`
          );
          break;
        }
        case "verdict_written": {
          const v = event.data as unknown as ClaimVerdict;
          setVerdict(v);
          setIsRunning(false);
          esRef.current?.close();
          markStep("verdict");
          setRecentEvent(
            `Verdict: ${v.verdict} (${Math.round(v.confidence * 100)}% confidence)`
          );
          break;
        }
        case "thesis_updated": {
          const d = event.data as {
            material: string;
            risk_level: number;
            risk_label: string;
          };
          updateThesis(d.material, {
            risk_level: d.risk_level,
            risk_label: d.risk_label as "STABLE" | "ELEVATED" | "HIGH" | "CRITICAL",
          });
          setHighlightedMaterial(d.material);
          setRecentEvent(
            `Oracle: ${d.material} updated to ${d.risk_level}/100 (${d.risk_label})`
          );
          setTimeout(() => setHighlightedMaterial(undefined), 5000);
          break;
        }
        case "reasoning_bank_updated":
          refetchRB();
          setNewEntryId(String(Date.now()));
          break;
        case "pipeline_complete":
          setIsRunning(false);
          break;
        case "error":
          setIsRunning(false);
          esRef.current?.close();
          break;
      }
    },
    [markStep, updateThesis, refetchRB]
  );

  const startStream = useCallback(
    (claimText?: string, scenarioId?: string) => {
      esRef.current?.close();
      setIsRunning(true);
      setVariants([]);
      setVerdict(null);
      setSteps(STEP_DEFS.map((s) => ({ ...s, done: false })));

      const url = api.streamUrl(claimText, scenarioId);
      const es = new EventSource(url);
      esRef.current = es;

      es.onmessage = (e) => {
        try {
          handleSSEEvent(JSON.parse(e.data as string) as SSEEvent);
        } catch {
          // ignore malformed events
        }
      };
      es.onerror = () => {
        setIsRunning(false);
        es.close();
      };
    },
    [handleSSEEvent]
  );

  const handleAnalyse = useCallback(
    (claimText: string) => {
      if (!claimText) return;
      startStream(claimText);
    },
    [startStream]
  );

  const handleRunScenario = useCallback(
    (scenario: ScenarioTemplate) => {
      startStream(undefined, scenario.id);
    },
    [startStream]
  );

  const handleRunDefault = useCallback(() => startStream(), [startStream]);

  const handleReset = useCallback(() => {
    setVariants([]);
    setVerdict(null);
    setSteps([]);
    setHighlightedMaterial(undefined);
    setRecentEvent("Demo state reset");
  }, []);

  return (
    <div className="flex flex-col min-h-screen" style={{ background: "#0A0A0F" }}>
      <Header />
      <DemoControlBar
        onRunDefault={handleRunDefault}
        onReset={handleReset}
        recentEvent={recentEvent}
        isRunning={isRunning}
      />

      <main className="flex-1 p-4 flex flex-col gap-4">
        {/* Two-panel row */}
        <div className="flex gap-4">
          {/* LEFT — Forensics (55%) */}
          <div className="flex flex-col gap-4" style={{ flex: "0 0 55%" }}>
            <div
              className="rounded-lg p-4 flex flex-col gap-4"
              style={{ background: "#111118", border: "1px solid #1E1E2E" }}
            >
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full inline-block" style={{ background: "#EF4444" }} />
                <span
                  className="text-xs font-semibold uppercase tracking-wide"
                  style={{ color: "#64748B" }}
                >
                  Forensics Pipeline
                </span>
              </div>

              <ClaimInput
                onAnalyse={handleAnalyse}
                onRunScenario={handleRunScenario}
                isRunning={isRunning}
                steps={steps}
              />

              <MutationGraph variants={variants} />

              {verdict && <VerdictCard verdict={verdict} />}
            </div>

            {/* Verdict history below forensics panel */}
            <div
              className="rounded-lg p-4"
              style={{ background: "#111118", border: "1px solid #1E1E2E" }}
            >
              <VerdictHistory />
            </div>
          </div>

          {/* RIGHT — Oracle (45%) */}
          <div className="flex flex-col gap-4" style={{ flex: "1" }}>
            <div
              className="rounded-lg p-4 flex flex-col gap-4"
              style={{ background: "#111118", border: "1px solid #1E1E2E" }}
            >
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full inline-block" style={{ background: "#6366F1" }} />
                <span
                  className="text-xs font-semibold uppercase tracking-wide"
                  style={{ color: "#64748B" }}
                >
                  Oracle — Supply Risk
                </span>
              </div>

              <RiskGauges theses={theses} highlightedMaterial={highlightedMaterial} />

              <ThesisSlider />
            </div>
          </div>
        </div>

        {/* BOTTOM — ReasoningBank */}
        <div
          className="rounded-lg p-4"
          style={{ background: "#111118", border: "1px solid #1E1E2E" }}
        >
          <div className="flex items-center gap-2 mb-4">
            <span className="w-2 h-2 rounded-full inline-block" style={{ background: "#22C55E" }} />
            <span
              className="text-xs font-semibold uppercase tracking-wide"
              style={{ color: "#64748B" }}
            >
              ReasoningBank — Agent Self-Improvement
            </span>
          </div>

          <div className="grid grid-cols-3 gap-6">
            <RBStatsPanel stats={stats} />
            <RBFeed entries={recent} newEntryId={newEntryId} />
            <ImprovementChart entries={recent} />
          </div>
        </div>
      </main>
    </div>
  );
}
