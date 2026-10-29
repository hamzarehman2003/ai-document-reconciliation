"use client";

import { Bar, BarChart, CartesianGrid, XAxis } from "recharts";

import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";
import type { Dashboard } from "@/lib/api";

type Props = {
  title: string;
  data: Dashboard["daily"];
  metric: "uploaded" | "approved";
};

/** One measure per day as thin bars. One colour: the title says what it is. */
export function DailyChart({ title, data, metric }: Props) {
  const config = { [metric]: { label: title, color: "var(--chart-1)" } } satisfies ChartConfig;
  const total = data.reduce((sum, day) => sum + day[metric], 0);

  return (
    <div className="min-w-0">
      <div className="flex items-baseline justify-between gap-2">
        <p className="text-sm font-medium">{title}</p>
        <p className="numeric text-sm text-muted-foreground">{total} in 14 days</p>
      </div>
      <ChartContainer config={config} className="mt-3 aspect-auto h-36 w-full">
        <BarChart data={data} margin={{ top: 4, right: 0, bottom: 0, left: 0 }} barCategoryGap={3}>
          <CartesianGrid vertical={false} strokeOpacity={0.6} />
          <XAxis
            dataKey="day"
            tickLine={false}
            axisLine={false}
            tickMargin={8}
            interval="preserveStartEnd"
            minTickGap={24}
            tickFormatter={shortDay}
          />
          <ChartTooltip
            cursor={{ fill: "var(--accent)", opacity: 0.6 }}
            content={<ChartTooltipContent labelFormatter={(day) => shortDay(String(day))} />}
          />
          <Bar dataKey={metric} fill={`var(--color-${metric})`} radius={[4, 4, 0, 0]} />
        </BarChart>
      </ChartContainer>
    </div>
  );
}

/** "2026-10-27" → "27 Oct" */
function shortDay(day: string): string {
  return new Date(`${day}T00:00:00`).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
  });
}
