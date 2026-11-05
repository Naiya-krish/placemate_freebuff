"use client";

import { cn } from "@/lib/utils";

export interface TabItem {
  value: string;
  label: string;
  count?: number;
}

export function SegmentedTabs({
  items,
  value,
  onChange,
  className,
}: {
  items: TabItem[];
  value: string;
  onChange: (value: string) => void;
  className?: string;
}) {
  return (
    <div
      role="tablist"
      aria-label="Sections"
      className={cn(
        "scrollbar-none flex gap-1 overflow-x-auto rounded-xl border border-border bg-surface/70 p-1",
        className,
      )}
    >
      {items.map((item) => {
        const selected = item.value === value;
        return (
          <button
            key={item.value}
            role="tab"
            type="button"
            aria-selected={selected}
            onClick={() => onChange(item.value)}
            className={cn(
              "whitespace-nowrap rounded-lg px-3.5 py-2 text-xs font-semibold transition-colors",
              selected
                ? "bg-card text-fg shadow-sm ring-1 ring-border"
                : "text-muted hover:text-fg",
            )}
          >
            {item.label}
            {typeof item.count === "number" ? (
              <span className="ml-1.5 text-[10px] text-muted">{item.count}</span>
            ) : null}
          </button>
        );
      })}
    </div>
  );
}
