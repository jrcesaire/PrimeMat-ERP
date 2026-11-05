"use client";

import { LayoutGrid } from "lucide-react";
import { Chip, ChipGroup } from "@/components/ui/chip";
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
    <ChipGroup className="flex-nowrap overflow-x-auto pb-1">
      <Chip
        active={selectedId === null}
        onClick={() => onSelect(null)}
        className="shrink-0"
      >
        <LayoutGrid className="h-3.5 w-3.5" />
        Tout
      </Chip>
      {flat.map(({ node, depth }) => (
        <Chip
          key={node.id}
          active={node.id === selectedId}
          onClick={() => onSelect(node.id === selectedId ? null : node.id)}
          title={node.name}
          className="shrink-0"
        >
          {depth > 0 ? `${"· ".repeat(Math.min(depth, 2))}${node.name}` : node.name}
        </Chip>
      ))}
    </ChipGroup>
  );
}
