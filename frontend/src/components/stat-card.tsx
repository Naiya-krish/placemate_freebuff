import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

export function StatCard({
  label,
  value,
  hint,
  icon: Icon,
  tone = "default",
  className,
}: {
  label: string;
  value: string | number;
  hint?: string;
  icon?: LucideIcon;
  tone?: "default" | "primary" | "accent" | "success" | "warning";
  className?: string;
}) {
  const toneClass = {
    default: "text-fg",
    primary: "text-primary",
    accent: "text-accent",
    success: "text-success",
    warning: "text-warning",
  }[tone];
  return (
    <div className={cn("surface-card flex flex-col gap-2 p-4", className)}>
      <div className="flex items-center justify-between">
        <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-muted">{label}</p>
        {Icon ? (
          <span className="flex size-7 items-center justify-center rounded-lg bg-surface text-muted">
            <Icon className="size-3.5" aria-hidden />
          </span>
        ) : null}
      </div>
      <p className={cn("font-display text-2xl font-semibold tabular-nums", toneClass)}>{value}</p>
      {hint ? <p className="text-[11px] text-muted">{hint}</p> : null}
    </div>
  );
}
