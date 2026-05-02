import type {
  ClaimVerdict, MaterialThesis, RBStats, ReasoningEntry, HealthStatus
} from "@/types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`GET ${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`POST ${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

export const api = {
  health: () => get<HealthStatus>("/api/health"),

  getTheses: () => get<MaterialThesis[]>("/api/thesis"),
  getThesisHistory: (material: string) =>
    get<MaterialThesis[]>(`/api/thesis/${material}/history`),
  getThesisAt: (material: string, date: string) =>
    get<MaterialThesis>(`/api/thesis/${material}/at/${date}`),

  analyseCliam: (claimText: string) =>
    post<ClaimVerdict>("/api/forensics/analyse", { claim_text: claimText }),
  getVerdicts: () => get<ClaimVerdict[]>("/api/forensics/verdicts"),
  getVariants: (claimId: string) =>
    get<unknown[]>(`/api/forensics/variants/${claimId}`),

  getRBStats: () => get<RBStats>("/api/reasoning-bank/stats"),
  getRBRecent: () => get<ReasoningEntry[]>("/api/reasoning-bank/recent"),

  injectDemoClaim: () => post<ClaimVerdict>("/api/demo/inject-claim"),
  resetDemo: () => post<{ status: string }>("/api/demo/reset"),

  streamUrl: (claim?: string) =>
    `${BASE}/api/demo/stream${claim ? `?claim=${encodeURIComponent(claim)}` : ""}`,
};
