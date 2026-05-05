"use client";
import { useState } from "react";
import { Search, BookOpen, CheckCircle, Circle } from "lucide-react";
import ScenarioLibrary from "./ScenarioLibrary";
import type { ScenarioTemplate } from "@/types";
import { useScenarios } from "@/hooks/useScenarios";

interface Step {
  id: string;
  label: string;
  done: boolean;
}

interface Props {
  onAnalyse: (claim: string) => void;
  onRunScenario: (scenario: ScenarioTemplate) => void;
  isRunning: boolean;
  steps: Step[];
}

export default function ClaimInput({ onAnalyse, onRunScenario, isRunning, steps }: Props) {
  const [text, setText] = useState("");
  const [libraryOpen, setLibraryOpen] = useState(false);
  const { scenarios, loading, createScenario, deleteScenario } = useScenarios();

  const handleSelectScenario = (scenario: ScenarioTemplate) => {
    setText(scenario.claim_text);
    setLibraryOpen(false);
    onRunScenario(scenario);
  };

  return (
    <div className="flex flex-col gap-3">
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={3}
        placeholder={"Paste a supply chain claim to analyse...\ne.g. BREAKING: Rotterdam port workers vote for indefinite strike"}
        className="w-full rounded-lg p-3 text-sm resize-none focus:outline-none"
        style={{
          background: "#0A0A0F",
          border: "1px solid #1E1E2E",
          color: "#F1F5F9",
          lineHeight: 1.6,
        }}
        disabled={isRunning}
      />

      <div className="flex gap-2">
        <button
          onClick={() => onAnalyse(text.trim())}
          disabled={isRunning || !text.trim()}
          className="flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all flex-1"
          style={{
            background: isRunning || !text.trim() ? "#1E1E2E" : "#6366F1",
            color: isRunning || !text.trim() ? "#475569" : "#fff",
            cursor: isRunning || !text.trim() ? "not-allowed" : "pointer",
          }}
        >
          <Search size={14} />
          {isRunning ? "Analysing..." : "Analyse Claim"}
        </button>

        <button
          onClick={() => setLibraryOpen(!libraryOpen)}
          disabled={isRunning}
          className="flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all"
          style={{
            background: libraryOpen ? "#1E293B" : "#1E1E2E",
            color: isRunning ? "#475569" : "#F59E0B",
            cursor: isRunning ? "not-allowed" : "pointer",
            border: libraryOpen ? "1px solid #F59E0B44" : "1px solid transparent",
          }}
        >
          <BookOpen size={14} />
          Library
        </button>
      </div>

      {libraryOpen && !isRunning && (
        <div
          className="rounded-lg p-3"
          style={{ background: "#111118", border: "1px solid #1E1E2E" }}
        >
          <ScenarioLibrary
            scenarios={scenarios}
            loading={loading}
            onSelect={handleSelectScenario}
            onCreate={createScenario}
            onDelete={deleteScenario}
          />
        </div>
      )}

      {steps.length > 0 && (
        <div
          className="rounded-lg p-3 flex flex-col gap-1.5"
          style={{ background: "#0A0A0F", border: "1px solid #1E1E2E" }}
        >
          {steps.map((s) => (
            <div key={s.id} className="flex items-center gap-2 text-xs">
              {s.done ? (
                <CheckCircle size={12} style={{ color: "#22C55E" }} />
              ) : (
                <Circle size={12} style={{ color: "#475569" }} className="animate-pulse-dot" />
              )}
              <span style={{ color: s.done ? "#94A3B8" : "#F1F5F9" }}>{s.label}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
