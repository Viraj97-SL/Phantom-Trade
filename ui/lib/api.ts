import type {
  ClaimVerdict, MaterialThesis, RBStats, ReasoningEntry, HealthStatus, ScenarioTemplate
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

async function del(path: string): Promise<void> {
  const res = await fetch(`${BASE}${path}`, { method: "DELETE", cache: "no-store" });
  if (!res.ok && res.status !== 204) throw new Error(`DELETE ${path} → ${res.status}`);
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

  injectDemoClaim: (scenarioId?: string) =>
    post<ClaimVerdict>(`/api/demo/inject-claim${scenarioId ? `?scenario_id=${encodeURIComponent(scenarioId)}` : ""}`),
  resetDemo: () => post<{ status: string }>("/api/demo/reset"),

  streamUrl: (claim?: string, scenarioId?: string) => {
    const params = new URLSearchParams();
    if (claim) params.set("claim", claim);
    else if (scenarioId) params.set("scenario_id", scenarioId);
    const qs = params.toString();
    return `${BASE}/api/demo/stream${qs ? `?${qs}` : ""}`;
  },

  getScenarios: (category?: string) =>
    get<ScenarioTemplate[]>(`/api/scenarios${category ? `?category=${category}` : ""}`),
  getScenario: (id: string) => get<ScenarioTemplate>(`/api/scenarios/${id}`),
  createScenario: (body: {
    name: string;
    description?: string;
    claim_text: string;
    category?: string;
    tags?: string[];
  }) => post<ScenarioTemplate>("/api/scenarios", body),
  deleteScenario: (id: string) => del(`/api/scenarios/${id}`),

  getVerdict: (claimId: string) => get<ClaimVerdict>(`/api/forensics/verdict/${claimId}`),
};
