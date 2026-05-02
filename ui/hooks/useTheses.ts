"use client";
import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import type { MaterialThesis } from "@/types";

export function useTheses(pollMs = 5000) {
  const [theses, setTheses] = useState<MaterialThesis[]>([]);
  const [loading, setLoading] = useState(true);

  const fetch = useCallback(async () => {
    try {
      const data = await api.getTheses();
      setTheses(data);
    } catch {
      // silently retry
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetch();
    const id = setInterval(fetch, pollMs);
    return () => clearInterval(id);
  }, [fetch, pollMs]);

  const updateThesis = useCallback((material: string, patch: Partial<MaterialThesis>) => {
    setTheses((prev) =>
      prev.map((t) => (t.material === material ? { ...t, ...patch } : t))
    );
  }, []);

  return { theses, loading, refetch: fetch, updateThesis };
}
