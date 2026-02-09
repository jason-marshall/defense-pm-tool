/**
 * S-Curve chart for Monte Carlo cost/schedule results.
 * Displays BCWS, BCWP, ACWP lines with optional confidence band.
 */

import {
  LineChart,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import type { SCurveDataPoint } from "@/types/simulation";

interface SCurveChartProps {
  data: SCurveDataPoint[];
}

export function SCurveChart({ data }: SCurveChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="bg-white rounded-lg border p-8 text-center text-gray-500">
        No S-curve data available.
      </div>
    );
  }

  const hasConfidenceBand = data.some(
    (d) => d.bcws_optimistic != null && d.bcws_pessimistic != null
  );

  const chartData = data.map((d) => ({
    period: d.period,
    bcws: Number(d.bcws),
    bcwp: Number(d.bcwp),
    acwp: Number(d.acwp),
    optimistic: d.bcws_optimistic != null ? Number(d.bcws_optimistic) : undefined,
    pessimistic: d.bcws_pessimistic != null ? Number(d.bcws_pessimistic) : undefined,
  }));

  return (
    <div className="bg-white rounded-lg border p-4">
      <h3 className="text-sm font-medium mb-3">S-Curve</h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="period" tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} label={{ value: "Cost ($)", angle: -90, position: "insideLeft" }} />
          <Tooltip formatter={(value) => [`$${Number(value).toLocaleString()}`, ""]} />
          <Legend />
          {hasConfidenceBand && (
            <Area
              type="monotone"
              dataKey="pessimistic"
              stroke="none"
              fill="#93c5fd"
              fillOpacity={0.3}
              name="Confidence Band"
            />
          )}
          {hasConfidenceBand && (
            <Area
              type="monotone"
              dataKey="optimistic"
              stroke="none"
              fill="#ffffff"
              fillOpacity={1}
              name=""
              legendType="none"
            />
          )}
          <Line type="monotone" dataKey="bcws" stroke="#3b82f6" strokeDasharray="5 5" name="BCWS (PV)" dot={false} />
          <Line type="monotone" dataKey="bcwp" stroke="#10b981" name="BCWP (EV)" dot={false} />
          <Line type="monotone" dataKey="acwp" stroke="#ef4444" name="ACWP (AC)" dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
