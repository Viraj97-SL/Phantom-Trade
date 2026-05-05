"use client";
import { useState } from "react";
import { BookOpen, Plus, Trash2, Tag, Loader2 } from "lucide-react";
import type { ScenarioTemplate, ScenarioCategory } from "@/types";

const CATEGORY_COLORS: Record<ScenarioCategory | "all", string> = {
  all: "#6366F1",
  port_strike: "#EF4444",
  sanctions: "#F59E0B",
  weather: "#3B82F6",
  geopolitical: "#8B5CF6",
  financial: "#10B981",
  custom: "#64748B",
};

const CATEGORY_LABELS: Record<ScenarioCategory, string> = {
  port_strike: "Port Strike",
  sanctions: "Sanctions",
  weather: "Weather",
  geopolitical: "Geopolitical",
  financial: "Financial",
  custom: "Custom",
};

interface Props {
  scenarios: ScenarioTemplate[];
  loading: boolean;
  onSelect: (scenario: ScenarioTemplate) => void;
  onCreate: (body: {
    name: string;
    description?: string;
    claim_text: string;
    category?: string;
    tags?: string[];
  }) => Promise<ScenarioTemplate>;
  onDelete: (id: string) => Promise<void>;
}

export default function ScenarioLibrary({ scenarios, loading, onSelect, onCreate, onDelete }: Props) {
  const [activeCategory, setActiveCategory] = useState<ScenarioCategory | "all">("all");
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [form, setForm] = useState({ name: "", description: "", claim_text: "", category: "custom", tags: "" });

  const categories = Array.from(new Set(scenarios.map((s) => s.category))) as ScenarioCategory[];
  const filtered =
    activeCategory === "all" ? scenarios : scenarios.filter((s) => s.category === activeCategory);

  const handleCreate = async () => {
    if (!form.name.trim() || !form.claim_text.trim()) return;
    setCreating(true);
    try {
      await onCreate({
        name: form.name.trim(),
        description: form.description.trim() || undefined,
        claim_text: form.claim_text.trim(),
        category: form.category,
        tags: form.tags ? form.tags.split(",").map((t) => t.trim()).filter(Boolean) : [],
      });
      setForm({ name: "", description: "", claim_text: "", category: "custom", tags: "" });
      setShowCreate(false);
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setDeleting(id);
    try {
      await onDelete(id);
    } catch {
      // built-in scenario — ignore
    } finally {
      setDeleting(null);
    }
  };

  return (
    <div className="flex flex-col gap-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <BookOpen size={14} style={{ color: "#6366F1" }} />
          <span className="text-xs font-semibold uppercase tracking-wide" style={{ color: "#64748B" }}>
            Scenario Library
          </span>
        </div>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="flex items-center gap-1 text-xs px-2 py-1 rounded-md transition-colors"
          style={{ background: "#1E1E2E", color: "#94A3B8" }}
        >
          <Plus size={11} />
          New
        </button>
      </div>

      {/* Create form */}
      {showCreate && (
        <div
          className="flex flex-col gap-2 p-3 rounded-lg"
          style={{ background: "#0A0A0F", border: "1px solid #1E1E2E" }}
        >
          <input
            placeholder="Scenario name"
            value={form.name}
            onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
            className="w-full rounded px-2 py-1.5 text-xs focus:outline-none"
            style={{ background: "#111118", border: "1px solid #1E1E2E", color: "#F1F5F9" }}
          />
          <textarea
            placeholder="Claim text (the news claim to analyse)"
            value={form.claim_text}
            onChange={(e) => setForm((f) => ({ ...f, claim_text: e.target.value }))}
            rows={3}
            className="w-full rounded px-2 py-1.5 text-xs resize-none focus:outline-none"
            style={{ background: "#111118", border: "1px solid #1E1E2E", color: "#F1F5F9" }}
          />
          <div className="flex gap-2">
            <select
              value={form.category}
              onChange={(e) => setForm((f) => ({ ...f, category: e.target.value }))}
              className="flex-1 rounded px-2 py-1.5 text-xs focus:outline-none"
              style={{ background: "#111118", border: "1px solid #1E1E2E", color: "#94A3B8" }}
            >
              {Object.entries(CATEGORY_LABELS).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
            <input
              placeholder="Tags (comma-separated)"
              value={form.tags}
              onChange={(e) => setForm((f) => ({ ...f, tags: e.target.value }))}
              className="flex-1 rounded px-2 py-1.5 text-xs focus:outline-none"
              style={{ background: "#111118", border: "1px solid #1E1E2E", color: "#94A3B8" }}
            />
          </div>
          <div className="flex gap-2 justify-end">
            <button
              onClick={() => setShowCreate(false)}
              className="text-xs px-3 py-1.5 rounded-md"
              style={{ background: "#1E1E2E", color: "#64748B" }}
            >
              Cancel
            </button>
            <button
              onClick={handleCreate}
              disabled={creating || !form.name.trim() || !form.claim_text.trim()}
              className="flex items-center gap-1 text-xs px-3 py-1.5 rounded-md"
              style={{
                background: creating || !form.name.trim() ? "#1E1E2E" : "#6366F1",
                color: creating || !form.name.trim() ? "#475569" : "#fff",
              }}
            >
              {creating && <Loader2 size={11} className="animate-spin" />}
              Save
            </button>
          </div>
        </div>
      )}

      {/* Category pills */}
      <div className="flex flex-wrap gap-1.5">
        <button
          onClick={() => setActiveCategory("all")}
          className="text-xs px-2.5 py-1 rounded-full transition-colors"
          style={{
            background: activeCategory === "all" ? CATEGORY_COLORS.all : "#1E1E2E",
            color: activeCategory === "all" ? "#fff" : "#64748B",
          }}
        >
          All ({scenarios.length})
        </button>
        {categories.map((cat) => (
          <button
            key={cat}
            onClick={() => setActiveCategory(cat)}
            className="text-xs px-2.5 py-1 rounded-full transition-colors"
            style={{
              background: activeCategory === cat ? CATEGORY_COLORS[cat] : "#1E1E2E",
              color: activeCategory === cat ? "#fff" : "#64748B",
            }}
          >
            {CATEGORY_LABELS[cat]}
          </button>
        ))}
      </div>

      {/* Scenario cards */}
      {loading ? (
        <div className="flex items-center justify-center py-4">
          <Loader2 size={16} className="animate-spin" style={{ color: "#475569" }} />
        </div>
      ) : (
        <div className="flex flex-col gap-2 max-h-64 overflow-y-auto pr-1">
          {filtered.map((s) => (
            <div
              key={s.id}
              onClick={() => onSelect(s)}
              className="flex flex-col gap-1 p-3 rounded-lg cursor-pointer transition-all"
              style={{
                background: "#0A0A0F",
                border: "1px solid #1E1E2E",
                borderLeftWidth: "3px",
                borderLeftColor: CATEGORY_COLORS[s.category] ?? "#64748B",
              }}
            >
              <div className="flex items-start justify-between gap-2">
                <span className="text-xs font-medium" style={{ color: "#F1F5F9" }}>
                  {s.name}
                </span>
                {!s.is_builtin && (
                  <button
                    onClick={(e) => handleDelete(s.id, e)}
                    className="shrink-0 opacity-50 hover:opacity-100 transition-opacity"
                  >
                    {deleting === s.id ? (
                      <Loader2 size={11} className="animate-spin" style={{ color: "#EF4444" }} />
                    ) : (
                      <Trash2 size={11} style={{ color: "#EF4444" }} />
                    )}
                  </button>
                )}
              </div>
              {s.description && (
                <p className="text-xs" style={{ color: "#64748B" }}>{s.description}</p>
              )}
              {s.tags.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-0.5">
                  {s.tags.slice(0, 4).map((tag) => (
                    <span
                      key={tag}
                      className="flex items-center gap-0.5 text-xs px-1.5 py-0.5 rounded"
                      style={{ background: "#1E1E2E", color: "#475569" }}
                    >
                      <Tag size={8} />
                      {tag}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
          {filtered.length === 0 && (
            <p className="text-xs text-center py-3" style={{ color: "#475569" }}>
              No scenarios in this category
            </p>
          )}
        </div>
      )}
    </div>
  );
}