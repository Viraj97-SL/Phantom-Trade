import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import type { RiskLabel, Verdict } from "@/types";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function riskColor(label: RiskLabel): string {
  return {
    STABLE: "#22C55E",
    ELEVATED: "#F59E0B",
    HIGH: "#F97316",
    CRITICAL: "#EF4444",
  }[label] ?? "#64748B";
}

export function verdictColor(verdict: Verdict): string {
  return {
    FABRICATED: "#EF4444",
    AUTHENTIC: "#22C55E",
    INCONCLUSIVE: "#F59E0B",
  }[verdict] ?? "#64748B";
}

export function riskColorByLevel(level: number): string {
  if (level < 40) return "#22C55E";
  if (level < 60) return "#F59E0B";
  if (level < 80) return "#F97316";
  return "#EF4444";
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("en-GB", {
    day: "numeric", month: "short", hour: "2-digit", minute: "2-digit",
  });
}
