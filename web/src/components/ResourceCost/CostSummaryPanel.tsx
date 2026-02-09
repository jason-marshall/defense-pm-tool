/**
 * CostSummaryPanel displays program cost summary with WBS breakdown and EVMS sync.
 */

import { useState } from "react";
import { useProgramCostSummary, useSyncCostsToEVMS } from "@/hooks/useCost";
import { useToast } from "@/components/Toast";
import { DollarSign, RefreshCw } from "lucide-react";

interface CostSummaryPanelProps {
  programId: string;
}

export function CostSummaryPanel({ programId }: CostSummaryPanelProps) {
  const { data, isLoading, error } = useProgramCostSummary(programId);
  const syncMutation = useSyncCostsToEVMS();
  const { success, error: showError } = useToast();
  const [periodId, setPeriodId] = useState("");

  const handleSync = async () => {
    if (!periodId.trim()) {
      showError("Please enter a period ID");
      return;
    }
    try {
      const result = await syncMutation.mutateAsync({ programId, periodId });
      if (result.success) {
        success(
          `EVMS sync complete: ${result.wbs_elements_updated} WBS elements updated`
        );
      } else {
        showError("EVMS sync completed with warnings");
      }
    } catch {
      showError("Failed to sync costs to EVMS");
    }
  };

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg border p-6 text-center text-gray-500">
        Loading cost data...
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg border p-6 text-center text-red-500">
        Failed to load cost data
      </div>
    );
  }

  if (!data) {
    return (
      <div className="bg-white rounded-lg border p-6 text-center text-gray-500">
        No cost data available
      </div>
    );
  }

  const variance = parseFloat(data.total_cost_variance);

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold flex items-center gap-2">
          <DollarSign size={20} />
          Cost Summary
        </h3>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-4 gap-3 mb-6">
        <div className="bg-gray-50 p-3 rounded">
          <div className="text-xs text-gray-500">Planned Cost</div>
          <div className="text-lg font-semibold">
            ${parseFloat(data.total_planned_cost).toLocaleString()}
          </div>
        </div>
        <div className="bg-gray-50 p-3 rounded">
          <div className="text-xs text-gray-500">Actual Cost</div>
          <div className="text-lg font-semibold">
            ${parseFloat(data.total_actual_cost).toLocaleString()}
          </div>
        </div>
        <div
          className={`p-3 rounded ${variance < 0 ? "bg-red-50" : "bg-green-50"}`}
        >
          <div className="text-xs text-gray-500">Cost Variance</div>
          <div
            className={`text-lg font-semibold ${variance < 0 ? "text-red-600" : "text-green-600"}`}
          >
            ${variance.toLocaleString()}
          </div>
        </div>
        <div className="bg-gray-50 p-3 rounded">
          <div className="text-xs text-gray-500">Resources / Activities</div>
          <div className="text-lg font-semibold">
            {data.resource_count} / {data.activity_count}
          </div>
        </div>
      </div>

      {/* Cost by Type */}
      <div className="grid grid-cols-3 gap-3 mb-6">
        <div className="bg-blue-50 p-3 rounded">
          <div className="text-xs text-gray-500">Labor</div>
          <div className="text-lg font-semibold text-blue-700">
            ${parseFloat(data.labor_cost).toLocaleString()}
          </div>
        </div>
        <div className="bg-purple-50 p-3 rounded">
          <div className="text-xs text-gray-500">Equipment</div>
          <div className="text-lg font-semibold text-purple-700">
            ${parseFloat(data.equipment_cost).toLocaleString()}
          </div>
        </div>
        <div className="bg-amber-50 p-3 rounded">
          <div className="text-xs text-gray-500">Material</div>
          <div className="text-lg font-semibold text-amber-700">
            ${parseFloat(data.material_cost).toLocaleString()}
          </div>
        </div>
      </div>

      {/* WBS Breakdown Table */}
      {data.wbs_breakdown.length > 0 && (
        <div className="mb-6">
          <h4 className="font-medium mb-2">WBS Cost Breakdown</h4>
          <div className="border rounded overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50">
                  <th className="p-2 text-left">WBS Code</th>
                  <th className="p-2 text-left">Name</th>
                  <th className="p-2 text-right">Planned</th>
                  <th className="p-2 text-right">Actual</th>
                  <th className="p-2 text-right">Variance</th>
                  <th className="p-2 text-right">Activities</th>
                </tr>
              </thead>
              <tbody>
                {data.wbs_breakdown.map((wbs) => {
                  const wbsVariance = parseFloat(wbs.cost_variance);
                  return (
                    <tr key={wbs.wbs_id} className="border-t hover:bg-gray-50">
                      <td className="p-2 font-mono text-xs">{wbs.wbs_code}</td>
                      <td className="p-2">{wbs.wbs_name}</td>
                      <td className="p-2 text-right">
                        ${parseFloat(wbs.planned_cost).toLocaleString()}
                      </td>
                      <td className="p-2 text-right">
                        ${parseFloat(wbs.actual_cost).toLocaleString()}
                      </td>
                      <td
                        className={`p-2 text-right font-medium ${wbsVariance < 0 ? "text-red-600" : "text-green-600"}`}
                      >
                        ${wbsVariance.toLocaleString()}
                      </td>
                      <td className="p-2 text-right">{wbs.activity_count}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* EVMS Sync */}
      <div className="border-t pt-4">
        <h4 className="font-medium mb-2">EVMS Sync</h4>
        <div className="flex gap-2 items-center">
          <input
            type="text"
            value={periodId}
            onChange={(e) => setPeriodId(e.target.value)}
            placeholder="Enter period ID"
            className="border rounded px-3 py-2 flex-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={handleSync}
            disabled={syncMutation.isPending}
            className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 transition-colors"
          >
            <RefreshCw
              size={16}
              className={syncMutation.isPending ? "animate-spin" : ""}
            />
            {syncMutation.isPending ? "Syncing..." : "Sync to EVMS"}
          </button>
        </div>
      </div>
    </div>
  );
}
