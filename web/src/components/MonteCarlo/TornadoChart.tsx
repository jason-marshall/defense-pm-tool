/**
 * Tornado chart for Monte Carlo sensitivity analysis.
 * Horizontal bar chart sorted by |correlation|, colored by sign.
 */

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
  ResponsiveContainer,
} from "recharts";
import type { SensitivityItem } from "@/types/simulation";

interface TornadoChartProps {
  sensitivity: SensitivityItem[];
  maxItems?: number;
}

export function TornadoChart({ sensitivity, maxItems = 10 }: TornadoChartProps) {
  if (!sensitivity || sensitivity.length === 0) {
    return (
      <div className="bg-white rounded-lg border p-8 text-center text-gray-500">
        No sensitivity data available.
      </div>
    );
  }

  const sorted = [...sensitivity]
    .sort((a, b) => Math.abs(b.correlation) - Math.abs(a.correlation))
    .slice(0, maxItems);

  const chartData = sorted.map((item) => ({
    name: item.activity_name,
    correlation: Number((item.correlation * 100).toFixed(1)),
    activity_id: item.activity_id,
  }));

  const chartHeight = Math.max(200, chartData.length * 36 + 60);

  return (
    <div className="bg-white rounded-lg border p-4">
      <h3 className="text-sm font-medium mb-3">Sensitivity Analysis (Tornado)</h3>
      <ResponsiveContainer width="100%" height={chartHeight}>
        <BarChart data={chartData} layout="vertical" margin={{ top: 5, right: 30, left: 120, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            type="number"
            domain={[-100, 100]}
            tick={{ fontSize: 11 }}
            label={{ value: "Correlation (%)", position: "insideBottom", offset: -5 }}
          />
          <YAxis
            type="category"
            dataKey="name"
            tick={{ fontSize: 11 }}
            width={110}
          />
          <Tooltip
            formatter={(value) => [`${value}%`, "Correlation"]}
          />
          <Bar dataKey="correlation" name="Correlation">
            {chartData.map((entry, index) => (
              <Cell
                key={index}
                fill={entry.correlation >= 0 ? "#8b5cf6" : "#f97316"}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
