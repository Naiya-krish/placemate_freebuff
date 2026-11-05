"use client";

import {
  PolarAngleAxis,
  PolarGrid,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import type { RadarPoint } from "@/lib/types";

export function SkillRadar({ data }: { data: RadarPoint[] }) {
  const chartData = data.map((point) => ({
    subject: point.label,
    value: point.value,
    fullMark: 100,
  }));
  return (
    <div className="h-[230px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={chartData} outerRadius="72%">
          <PolarGrid stroke="rgba(148,163,184,0.22)" />
          <PolarAngleAxis
            dataKey="subject"
            tick={{ fill: "currentColor", fontSize: 10, opacity: 0.7 }}
            className="text-muted"
          />
          <Tooltip
            contentStyle={{
              background: "hsl(var(--card))",
              border: "1px solid hsl(var(--border))",
              borderRadius: 12,
              fontSize: 12,
              color: "hsl(var(--fg))",
            }}
            formatter={(value: number) => [`${value}/100`, "Score"]}
          />
          <Radar
            name="Readiness"
            dataKey="value"
            stroke="#8b7cff"
            strokeWidth={2}
            fill="#7c5cff"
            fillOpacity={0.3}
            dot={{ r: 2.5, fill: "#22d3ee" }}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
