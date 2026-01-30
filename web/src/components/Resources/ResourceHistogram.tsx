/**
 * ResourceHistogram component for visualizing resource loading over time.
 * Displays bar chart showing available vs assigned hours with overallocation highlighting.
 */

import { useState, useMemo } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { useResourceHistogram } from "@/hooks/useHistogram";
import { format, addDays, parseISO } from "date-fns";
import { AlertTriangle, Calendar } from "lucide-react";

interface ResourceHistogramProps {
  resourceId: string;
  resourceName: string;
  startDate?: string;
  endDate?: string;
}

interface ChartDataPoint {
  date: string;
  available: number;
  assigned: number;
  utilization: number;
  overallocated: boolean;
}

export function ResourceHistogram({
  resourceId,
  resourceName,
  startDate,
  endDate,
}: ResourceHistogramProps) {
  // Default to next 30 days
  const defaultStart = useMemo(() => format(new Date(), "yyyy-MM-dd"), []);
  const defaultEnd = useMemo(
    () => format(addDays(new Date(), 30), "yyyy-MM-dd"),
    []
  );

  const [dateRange, setDateRange] = useState({
    start: startDate || defaultStart,
    end: endDate || defaultEnd,
  });
  const [granularity, setGranularity] = useState<"daily" | "weekly">("daily");

  const { data, isLoading, error } = useResourceHistogram(
    resourceId,
    dateRange.start,
    dateRange.end,
    granularity
  );

  const chartData: ChartDataPoint[] = useMemo(() => {
    if (!data?.data_points) return [];
    return data.data_points.map((point) => ({
      date: format(
        parseISO(point.date),
        granularity === "weekly" ? "MMM d" : "MM/dd"
      ),
      available: point.available_hours,
      assigned: point.assigned_hours,
      utilization: point.utilization_percent,
      overallocated: point.is_overallocated,
    }));
  }, [data, granularity]);

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow p-4">
        <div className="animate-pulse">
          <div className="h-6 bg-gray-200 rounded w-1/3 mb-4"></div>
          <div className="h-64 bg-gray-100 rounded"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow p-4">
        <div className="text-red-500 flex items-center gap-2">
          <AlertTriangle size={20} />
          Error loading histogram data
        </div>
      </div>
    );
  }

  return (
    <div className="resource-histogram bg-white rounded-lg shadow p-4">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold flex items-center gap-2">
          <Calendar size={20} className="text-gray-500" />
          {resourceName} - Resource Loading
        </h3>
        <div className="flex gap-2 items-center text-sm">
          <input
            type="date"
            value={dateRange.start}
            onChange={(e) =>
              setDateRange({ ...dateRange, start: e.target.value })
            }
            className="border rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <span className="text-gray-500">to</span>
          <input
            type="date"
            value={dateRange.end}
            onChange={(e) =>
              setDateRange({ ...dateRange, end: e.target.value })
            }
            className="border rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <select
            value={granularity}
            onChange={(e) =>
              setGranularity(e.target.value as "daily" | "weekly")
            }
            className="border rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
          </select>
        </div>
      </div>

      {/* Summary Stats */}
      {data && (
        <div className="grid grid-cols-4 gap-4 mb-4">
          <div className="bg-gray-50 p-3 rounded">
            <div className="text-sm text-gray-500">Peak Utilization</div>
            <div className="text-xl font-semibold">
              {data.peak_utilization.toFixed(0)}%
            </div>
            {data.peak_date && (
              <div className="text-xs text-gray-400">
                {format(parseISO(data.peak_date), "MMM d")}
              </div>
            )}
          </div>
          <div className="bg-gray-50 p-3 rounded">
            <div className="text-sm text-gray-500">Avg Utilization</div>
            <div className="text-xl font-semibold">
              {data.average_utilization.toFixed(0)}%
            </div>
          </div>
          <div className="bg-gray-50 p-3 rounded">
            <div className="text-sm text-gray-500">Total Available</div>
            <div className="text-xl font-semibold">
              {data.total_available_hours.toFixed(0)}h
            </div>
          </div>
          <div
            className={`p-3 rounded ${
              data.overallocated_days > 0 ? "bg-red-50" : "bg-gray-50"
            }`}
          >
            <div className="text-sm text-gray-500 flex items-center gap-1">
              {data.overallocated_days > 0 && (
                <AlertTriangle size={14} className="text-red-500" />
              )}
              Overallocated
            </div>
            <div
              className={`text-xl font-semibold ${
                data.overallocated_days > 0 ? "text-red-600" : ""
              }`}
            >
              {data.overallocated_days} days
            </div>
          </div>
        </div>
      )}

      {/* Chart */}
      {chartData.length > 0 ? (
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData} barGap={0}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis
              dataKey="date"
              fontSize={11}
              tick={{ fill: "#6b7280" }}
              tickLine={{ stroke: "#e5e7eb" }}
            />
            <YAxis
              fontSize={11}
              tick={{ fill: "#6b7280" }}
              tickLine={{ stroke: "#e5e7eb" }}
              label={{
                value: "Hours",
                angle: -90,
                position: "insideLeft",
                style: { textAnchor: "middle", fill: "#6b7280" },
              }}
            />
            <Tooltip
              formatter={(value, name) => [
                `${Number(value).toFixed(1)}h`,
                name === "available" ? "Available" : "Assigned",
              ]}
              contentStyle={{
                backgroundColor: "white",
                border: "1px solid #e5e7eb",
                borderRadius: "4px",
              }}
            />
            <Legend />
            <Bar
              dataKey="available"
              fill="#94a3b8"
              name="Available"
              radius={[2, 2, 0, 0]}
            />
            <Bar dataKey="assigned" name="Assigned" radius={[2, 2, 0, 0]}>
              {chartData.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={entry.overallocated ? "#ef4444" : "#3b82f6"}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      ) : (
        <div className="h-64 flex items-center justify-center text-gray-500">
          No data available for the selected date range
        </div>
      )}

      <div className="flex justify-between items-center mt-2">
        <p className="text-xs text-gray-500">
          Red bars indicate overallocation (assigned &gt; available)
        </p>
        <div className="flex gap-4 text-xs">
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 bg-slate-400 rounded"></span>
            Available
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 bg-blue-500 rounded"></span>
            Assigned
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 bg-red-500 rounded"></span>
            Overallocated
          </span>
        </div>
      </div>
    </div>
  );
}
