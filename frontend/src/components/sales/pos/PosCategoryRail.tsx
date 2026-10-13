"use client";

import { LayoutGrid } from "lucide-react";
import { cn } from "@/lib/utils";
import type { CategoryTreeNode } from "@/lib/types";

interface Props {
  tree: CategoryTreeNode[];
  selectedId: number | null;
  onSelect: (id: number | null) => void;
}

function flatten(nodes: CategoryTreeNode[], depth = 0): { node: CategoryTreeNode; depth: number }[] {
  const out: { node: CategoryTreeNode; depth: number }[] = [];
  for (const n of nodes) {
    out.push({ node: n, depth });
    if (n.children?.length) out.push(...flatten(n.children, depth + 1));
  }
  return out;
}

export function PosCategoryRail({ tree, selectedId, onSelect }: Props) {
  const flat = flatten(tree);
  if (flat.length === 0) return null;
  return (
    <div className="flex gap-2 overflow-x-auto pb-1">
      <button
        type="button"
        onClick={() => onSelect(null)}
        className={cn(
          "flex shrink-0 items-center gap-1.5 rounded-full border px-3 py-2 text-sm",
          selectedId === null
            ? "border-primary bg-primary text-white"
            : "border-gray-300 bg-white text-gray-700 hover:bg-gray-50",
        )}
      >
        <LayoutGrid className="h-4 w-4" />
        Tout
      </button>
      {flat.map(({ node, depth }) => (
        <button
          key={node.id}
          type="button"
          onClick={() => onSelect(node.id === selectedId ? null : node.id)}
          title={node.name}
          className={cn(
            "shrink-0 rounded-full border px-3 py-2 text-sm",
            node.id === selectedId
              ? "border-primary bg-primary text-white"
              : "border-gray-300 bg-white text-gray-700 hover:bg-gray-50",
          )}
          style={depth > 0 ? { marginLeft: 0, opacity: 0.92 } : undefined}
        >
          {depth > 0 ? `${"· ".repeat(Math.min(depth, 2))}${node.name}` : node.name}
        </button>
      ))}
    </div>
  );
}
