"use client";

import { useId } from "react";
import { cn, clamp } from "@/lib/utils";

export function ReadinessRing({
  score,
  label = "Readiness",
  hint,
  size = 176,
  stroke = 12,
  className,
}: {
  score: number;
  label?: string;
  hint?: string;
  size?: number;
  stroke?: number;
  className?: string;
}) {
  const gradientId = useId().replace(/:/g, "");
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const value = clamp(score);
  const offset = circumference - (value / 100) * circumference;

  return (
    <div className={cn("relative inline-flex flex-col items-center justify-center", className)}>
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        role="img"
        aria-label={`${label}: ${Math.round(value)} out of 100`}
        className="-rotate-90"
      >
        <defs>
          <linearGradient id={`ring-${gradientId}`} x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#7c5cff" />
            <stop offset="55%" stopColor="#4f8bff" />
            <stop offset="100%" stopColor="#22d3ee" />
          </linearGradient>
        </defs>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="hsl(var(--border))"
          strokeWidth={stroke}
          opacity={0.55}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={`url(#ring-${gradientId})`}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="transition-[stroke-dashoffset] duration-1000 ease-out motion-reduce:transition-none"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
        <span className="font-display text-4xl font-semibold tabular-nums">
          {Math.round(value)}
          <span className="ml-0.5 text-base text-muted">/100</span>
        </span>
        <span className="mt-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-muted">
          {label}
        </span>
        {hint ? <span className="mt-1 text-[10px] text-muted/80">{hint}</span> : null}
      </div>
    </div>
  );
}
