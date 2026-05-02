"use client";
import { useEffect, useCallback } from "react";
import ReactFlow, {
  Background,
  Controls,
  useNodesState,
  useEdgesState,
  addEdge,
  type Node,
  type Edge,
  type Connection,
  MarkerType,
} from "reactflow";
import "reactflow/dist/style.css";
import type { ClaimVariant } from "@/types";

const PLATFORM_COLORS: Record<string, string> = {
  x: "#1DA1F2",
  telegram: "#0088CC",
  reddit: "#FF4500",
  youtube: "#FF0000",
  synthetic: "#6366F1",
};

function variantToNode(v: ClaimVariant, index: number): Node {
  const color = PLATFORM_COLORS[v.platform] ?? "#64748B";
  const size = Math.max(40, Math.min(100, 40 + Math.log10(Math.max(1, v.engagement_count)) * 12));

  return {
    id: v.variant_id,
    type: "default",
    position: { x: (index % 3) * 220 + 40, y: Math.floor(index / 3) * 140 + 40 },
    data: {
      label: (
        <div className="flex flex-col items-center gap-1 text-center" style={{ width: size }}>
          <span className="text-xs font-bold" style={{ color }}>{v.platform.toUpperCase()}</span>
          <span className="text-xs" style={{ color: "#94A3B8", fontSize: "10px" }}>{v.variant_type}</span>
          {v.engagement_count > 0 && (
            <span className="text-xs" style={{ color: "#475569", fontSize: "9px" }}>
              {v.engagement_count.toLocaleString()}
            </span>
          )}
        </div>
      ),
    },
    style: {
      background: "#111118",
      border: `2px solid ${color}`,
      borderRadius: "8px",
      padding: "8px",
      width: size + 20,
      color: "#F1F5F9",
    },
  };
}

function buildEdges(variants: ClaimVariant[]): Edge[] {
  const edges: Edge[] = [];
  const originals = variants.filter((v) => v.variant_type === "original");
  const others = variants.filter((v) => v.variant_type !== "original");

  for (const orig of originals) {
    for (const other of others.slice(0, 4)) {
      edges.push({
        id: `${orig.variant_id}-${other.variant_id}`,
        source: orig.variant_id,
        target: other.variant_id,
        animated: true,
        style: { stroke: "#6366F1", strokeOpacity: 0.6 },
        markerEnd: { type: MarkerType.ArrowClosed, color: "#6366F1" },
      });
    }
  }
  return edges;
}

interface Props {
  variants: ClaimVariant[];
}

export default function MutationGraph({ variants }: Props) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  useEffect(() => {
    if (!variants.length) return;
    const newNodes = variants.map((v, i) => variantToNode(v, i));
    const newEdges = buildEdges(variants);

    // Stagger node appearance
    newNodes.forEach((node, i) => {
      setTimeout(() => {
        setNodes((prev) => {
          const exists = prev.find((n) => n.id === node.id);
          return exists ? prev : [...prev, node];
        });
      }, i * 300);
    });

    setTimeout(() => setEdges(newEdges), variants.length * 300 + 200);
  }, [variants, setNodes, setEdges]);

  if (!variants.length) {
    return (
      <div
        className="flex items-center justify-center rounded-lg text-sm"
        style={{
          height: 300,
          background: "#111118",
          border: "1px solid #1E1E2E",
          color: "#475569",
        }}
      >
        No claim analysed yet. Enter a claim above.
      </div>
    );
  }

  return (
    <div
      className="rounded-lg overflow-hidden"
      style={{ height: 300, border: "1px solid #1E1E2E", background: "#0A0A0F" }}
    >
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        fitView
        attributionPosition="bottom-right"
        style={{ background: "#0A0A0F" }}
      >
        <Background color="#1E1E2E" gap={20} />
        <Controls
          style={{ background: "#111118", border: "1px solid #1E1E2E" }}
        />
      </ReactFlow>
    </div>
  );
}
