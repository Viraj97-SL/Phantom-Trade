"use client";
import { useEffect, useState } from "react";
import { ShieldAlert } from "lucide-react";
import { api } from "@/lib/api";
import type { HealthStatus } from "@/types";

function StatusDot({ ok, label }: { ok: boolean | null; label: string }) {
  return (
    <div className="flex items-center gap-1.5">
      <span className="relative flex h-2 w-2">
        {ok && (
          <span
            className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75"
            style={{ background: "#22C55E" }}
          />
        )}
        <span
          className="relative inline-flex rounded-full h-2 w-2"
          style={{ background: ok === null ? "#475569" : ok ? "#22C55E" : "#EF4444" }}
        />
      </span>
      <span className="text-xs" style={{ color: "#94A3B8" }}>{label}</span>
    </div>
  );
}

export default function Header() {
  const [health, setHealth] = useState<HealthStatus | null>(null);

  useEffect(() => {
    const check = async () => {
      try {
        const h = await api.health();
        setHealth(h);
      } catch {
        setHealth({ status: "error", mongodb: false, llm: false });
      }
    };
    check();
    const id = setInterval(check, 10_000);
    return () => clearInterval(id);
  }, []);

  return (
    <header
      className="flex items-center justify-between px-6 py-4"
      style={{ borderBottom: "1px solid #1E1E2E", background: "#0A0A0F" }}
    >
      <div className="flex items-center gap-3">
        <ShieldAlert size={24} style={{ color: "#6366F1" }} />
        <div>
          <h1 className="text-lg font-bold tracking-tight" style={{ color: "#F1F5F9" }}>
            PHANTOM TRADE
          </h1>
          <p className="text-xs" style={{ color: "#64748B" }}>
            Fake signals move real markets. We stop them first.
          </p>
        </div>
      </div>

      <div className="flex items-center gap-5">
        <StatusDot ok={health?.mongodb ?? null} label="MongoDB Atlas" />
        <StatusDot ok={health?.llm ?? null} label="LLM" />
        <StatusDot ok={health ? health.status === "ok" : null} label="API" />
      </div>
    </header>
  );
}
