/**
 * Distribution histogram for Monte Carlo simulation duration results.
 * Displays a bar chart with percentile reference lines.
 */

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts";
import type { HistogramBin } from "@/types/simulation";

interface DistributionHistogramProps {
  histogram: HistogramBin[];
  mean: number;
  p50: number;
  p80: number;
  p90: number;
}

export function DistributionHistogram({
  histogram,
  mean,
  p50,
  p80,
  p90,
}: DistributionHistogramProps) {
  if (!histogram || histogram.length === 0) {
    return (
      <div className="bg-white rounded-lg border p-8 text-center text-gray-500">
        No histogram data available.
      </div>
    );
  }

  const chartData = histogram.map((bin) => ({
    range: `${bin.bin_start.toFixed(0)}-${bin.bin_end.toFixed(0)}`,
    midpoint: (bin.bin_start + bin.bin_end) / 2,
    count: bin.count,
    frequency: bin.frequency,
  }));

  return (
    <div className="bg-white rounded-lg border p-4">
      <h3 className="text-sm font-medium mb-3">Duration Distribution</h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="range" tick={{ fontSize: 11 }} label={{ value: "Duration (days)", position: "insideBottom", offset: -5 }} />
          <YAxis label={{ value: "Frequency", angle: -90, position: "insideLeft" }} />
          <Tooltip
            formatter={(value, name) =>
              name === "frequency" ? [`${(Number(value) * 100).toFixed(1)}%`, "Frequency"] : [value, "Count"]
            }
            labelFormatter={(label) => `Duration: ${label} days`}
          />
          <Bar dataKey="frequency" fill="#8b5cf6" name="frequency" />
          <ReferenceLine x={closestBinRange(chartData, mean)} stroke="#ef4444" strokeDasharray="5 5" label={{ value: "Mean", position: "top", fill: "#ef4444", fontSize: 11 }} />
          <ReferenceLine x={closestBinRange(chartData, p50)} stroke="#3b82f6" strokeDasharray="5 5" label={{ value: "P50", position: "top", fill: "#3b82f6", fontSize: 11 }} />
          <ReferenceLine x={closestBinRange(chartData, p80)} stroke="#f59e0b" strokeDasharray="5 5" label={{ value: "P80", position: "top", fill: "#f59e0b", fontSize: 11 }} />
          <ReferenceLine x={closestBinRange(chartData, p90)} stroke="#10b981" strokeDasharray="5 5" label={{ value: "P90", position: "top", fill: "#10b981", fontSize: 11 }} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function closestBinRange(
  data: { range: string; midpoint: number }[],
  value: number
): string {
  let closest = data[0];
  let minDiff = Math.abs(data[0].midpoint - value);
  for (const d of data) {
    const diff = Math.abs(d.midpoint - value);
    if (diff < minDiff) {
      minDiff = diff;
      closest = d;
    }
  }
  return closest.range;
}
