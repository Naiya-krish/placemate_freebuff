import { cn, clamp } from "@/lib/utils";

export function Progress({
  value,
  className,
  barClassName,
  label,
}: {
  value: number;
  className?: string;
  barClassName?: string;
  label?: string;
}) {
  const safe = clamp(value, 0, 100);
  return (
    <div
      className={cn("h-2 w-full overflow-hidden rounded-full bg-border/60", className)}
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(safe)}
      aria-label={label}
    >
      <div
        className={cn(
          "h-full rounded-full bg-brand-gradient transition-[width] duration-700",
          barClassName,
        )}
        style={{ width: `${safe}%` }}
      />
    </div>
  );
}
