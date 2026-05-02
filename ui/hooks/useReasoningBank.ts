"use client";
import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import type { RBStats, ReasoningEntry } from "@/types";

export function useReasoningBank(pollMs = 8000) {
  const [stats, setStats] = useState<RBStats>({
    total_entries: 0,
    successful_entries: 0,
    avg_accuracy_delta: 0,
    hit_rate: 0,
  });
  const [recent, setRecent] = useState<ReasoningEntry[]>([]);

  const fetch = useCallback(async () => {
    try {
      const [s, r] = await Promise.all([api.getRBStats(), api.getRBRecent()]);
      setStats(s);
      setRecent(r);
    } catch {
      // silently retry
    }
  }, []);

  useEffect(() => {
    fetch();
    const id = setInterval(fetch, pollMs);
    return () => clearInterval(id);
  }, [fetch, pollMs]);

  return { stats, recent, refetch: fetch };
}
