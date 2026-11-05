import type { HeatmapCell } from "@/lib/types";
import { cn } from "@/lib/utils";

export function DepartmentHeatmap({
  branches,
  criteria,
  cells,
}: {
  branches: string[];
  criteria: string[];
  cells: HeatmapCell[];
}) {
  function value(branch: string, criterion: string): number {
    return cells.find((cell) => cell.branch === branch && cell.criterion === criterion)?.value ?? 0;
  }
  if (!branches.length || !criteria.length) {
    return <p className="py-10 text-center text-sm text-muted">Not enough data yet.</p>;
  }
  return (
    <div className="overflow-x-auto">
      <div
        className="grid min-w-[560px] gap-1.5"
        style={{ gridTemplateColumns: `88px repeat(${criteria.length}, minmax(0, 1fr))` }}
        role="table"
        aria-label="Department readiness heatmap"
      >
        <div />
        {criteria.map((criterion) => (
          <div
            key={criterion}
            className="px-1 pb-1 text-center text-[10px] font-semibold uppercase tracking-wide text-muted"
            role="columnheader"
          >
            {criterion}
          </div>
        ))}
        {branches.map((branch) => (
          <div key={branch} className="contents">
            <div className="flex items-center text-xs font-semibold text-muted" role="rowheader">
              {branch}
            </div>
            {criteria.map((criterion) => {
              const score = value(branch, criterion);
              const intensity = score / 100;
              return (
                <div
                  key={`${branch}-${criterion}`}
                  role="cell"
                  title={`${branch} · ${criterion}: ${score}/100`}
                  aria-label={`${branch} ${criterion}: ${score} out of 100`}
                  className={cn(
                    "flex h-11 items-center justify-center rounded-lg border border-border/50 text-xs font-semibold tabular-nums",
                    score === 0 ? "text-muted/60" : score >= 70 ? "text-white" : "text-fg",
                  )}
                  style={{
                    background:
                      score === 0
                        ? "hsl(var(--surface))"
                        : `linear-gradient(135deg, rgba(124,92,255,${0.18 + intensity * 0.55}), rgba(34,211,238,${0.08 + intensity * 0.38}))`,
                  }}
                >
                  {score === 0 ? "—" : score}
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
}
