"use client";
import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import type { ScenarioTemplate } from "@/types";

export function useScenarios() {
  const [scenarios, setScenarios] = useState<ScenarioTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchScenarios = useCallback(async () => {
    try {
      setLoading(true);
      const data = await api.getScenarios();
      setScenarios(data);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load scenarios");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchScenarios();
  }, [fetchScenarios]);

  const createScenario = useCallback(
    async (body: {
      name: string;
      description?: string;
      claim_text: string;
      category?: string;
      tags?: string[];
    }) => {
      const created = await api.createScenario(body);
      setScenarios((prev) => [...prev, created]);
      return created;
    },
    []
  );

  const deleteScenario = useCallback(async (id: string) => {
    await api.deleteScenario(id);
    setScenarios((prev) => prev.filter((s) => s.id !== id));
  }, []);

  return { scenarios, loading, error, refetch: fetchScenarios, createScenario, deleteScenario };
}
