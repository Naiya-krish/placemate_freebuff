import type { OfficerOverview } from "@/lib/types";

export function ReadinessFunnel({ stages }: { stages: OfficerOverview["funnel"] }) {
  return (
    <div className="space-y-3">
      {stages.map((stage, index) => (
        <div key={stage.stage}>
          <div className="mb-1 flex items-center justify-between text-xs">
            <span className="font-medium text-muted">{stage.stage}</span>
            <span className="font-display tabular-nums">
              {stage.count}
              <span className="ml-1 text-[10px] text-muted">{stage.percent}%</span>
            </span>
          </div>
          <div className="h-2.5 overflow-hidden rounded-full bg-surface">
            <div
              className="h-full rounded-full transition-[width] duration-700"
              style={{
                width: `${Math.max(stage.percent, 3)}%`,
                background: `linear-gradient(90deg, rgba(124,92,255,${0.95 - index * 0.1}), rgba(34,211,238,${0.85 - index * 0.1}))`,
              }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}
