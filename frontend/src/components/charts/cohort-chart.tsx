"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { OfficerOverview } from "@/lib/types";

export function CohortChart({ data }: { data: OfficerOverview["cohort_progress"] }) {
  return (
    <div className="h-[220px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 8, right: 8, left: -22, bottom: 0 }}>
          <defs>
            <linearGradient id="cohortFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#7c5cff" stopOpacity={0.45} />
              <stop offset="100%" stopColor="#22d3ee" stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="rgba(148,163,184,0.14)" vertical={false} />
          <XAxis
            dataKey="week"
            tick={{ fill: "currentColor", fontSize: 10, opacity: 0.65 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            domain={[0, 100]}
            tick={{ fill: "currentColor", fontSize: 10, opacity: 0.65 }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            contentStyle={{
              background: "hsl(var(--card))",
              border: "1px solid hsl(var(--border))",
              borderRadius: 12,
              fontSize: 12,
              color: "hsl(var(--fg))",
            }}
            labelStyle={{ color: "hsl(var(--muted))" }}
          />
          <Area
            type="monotone"
            dataKey="avg_score"
            name="Avg score"
            stroke="#8b7cff"
            strokeWidth={2.5}
            fill="url(#cohortFill)"
          />
          <Area
            type="monotone"
            dataKey="interviews"
            name="Interviews"
            stroke="#22d3ee"
            strokeWidth={1.5}
            fill="transparent"
            strokeDasharray="4 4"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
