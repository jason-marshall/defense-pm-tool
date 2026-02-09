/**
 * MaterialSummaryPanel displays program material summary with consumption progress bars.
 */

import { useState } from "react";
import { useProgramMaterials } from "@/hooks/useMaterial";
import { Package } from "lucide-react";
import { MaterialConsumeForm } from "./MaterialConsumeForm";

interface MaterialSummaryPanelProps {
  programId: string;
}

export function MaterialSummaryPanel({ programId }: MaterialSummaryPanelProps) {
  const { data, isLoading, error } = useProgramMaterials(programId);
  const [consumeTarget, setConsumeTarget] = useState<{
    assignmentId: string;
    resourceName: string;
    remaining: number;
  } | null>(null);

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg border p-6 text-center text-gray-500">
        Loading material data...
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg border p-6 text-center text-red-500">
        Failed to load material data
      </div>
    );
  }

  if (!data) {
    return (
      <div className="bg-white rounded-lg border p-6 text-center text-gray-500">
        No material data available
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold flex items-center gap-2 mb-4">
        <Package size={20} />
        Material Tracking
      </h3>

      {/* Summary Cards */}
      <div className="grid grid-cols-4 gap-3 mb-6">
        <div className="bg-gray-50 p-3 rounded">
          <div className="text-xs text-gray-500">Materials</div>
          <div className="text-lg font-semibold">{data.material_count}</div>
        </div>
        <div className="bg-gray-50 p-3 rounded">
          <div className="text-xs text-gray-500">Total Value</div>
          <div className="text-lg font-semibold">
            ${parseFloat(data.total_value).toLocaleString()}
          </div>
        </div>
        <div className="bg-blue-50 p-3 rounded">
          <div className="text-xs text-gray-500">Consumed Value</div>
          <div className="text-lg font-semibold text-blue-700">
            ${parseFloat(data.consumed_value).toLocaleString()}
          </div>
        </div>
        <div className="bg-green-50 p-3 rounded">
          <div className="text-xs text-gray-500">Remaining Value</div>
          <div className="text-lg font-semibold text-green-700">
            ${parseFloat(data.remaining_value).toLocaleString()}
          </div>
        </div>
      </div>

      {/* Material Table */}
      {data.materials.length > 0 ? (
        <div className="border rounded overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50">
                <th className="p-2 text-left">Code</th>
                <th className="p-2 text-left">Name</th>
                <th className="p-2 text-left">Unit</th>
                <th className="p-2 text-right">Available</th>
                <th className="p-2 text-right">Consumed</th>
                <th className="p-2 text-right">Remaining</th>
                <th className="p-2 text-left w-40">Progress</th>
                <th className="p-2 text-right">Unit Cost</th>
              </tr>
            </thead>
            <tbody>
              {data.materials.map((mat) => {
                const pct = parseFloat(mat.percent_consumed);
                return (
                  <tr
                    key={mat.resource_id}
                    className="border-t hover:bg-gray-50"
                  >
                    <td className="p-2 font-mono text-xs">
                      {mat.resource_code}
                    </td>
                    <td className="p-2">{mat.resource_name}</td>
                    <td className="p-2 text-gray-500">{mat.quantity_unit}</td>
                    <td className="p-2 text-right">
                      {parseFloat(mat.quantity_available).toLocaleString()}
                    </td>
                    <td className="p-2 text-right">
                      {parseFloat(mat.quantity_consumed).toLocaleString()}
                    </td>
                    <td className="p-2 text-right">
                      {parseFloat(mat.quantity_remaining).toLocaleString()}
                    </td>
                    <td className="p-2">
                      <div className="flex items-center gap-2">
                        <div className="flex-1 bg-gray-200 rounded-full h-2">
                          <div
                            className={`h-2 rounded-full ${
                              pct >= 90
                                ? "bg-red-500"
                                : pct >= 70
                                  ? "bg-yellow-500"
                                  : "bg-blue-500"
                            }`}
                            style={{ width: `${Math.min(pct, 100)}%` }}
                          />
                        </div>
                        <span className="text-xs text-gray-500 w-10 text-right">
                          {pct.toFixed(0)}%
                        </span>
                      </div>
                    </td>
                    <td className="p-2 text-right">
                      ${parseFloat(mat.unit_cost).toLocaleString()}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="text-center py-6 bg-gray-50 rounded">
          <Package size={32} className="mx-auto text-gray-400 mb-2" />
          <p className="text-gray-500">No materials found</p>
          <p className="text-sm text-gray-400">
            Add MATERIAL type resources to track quantities
          </p>
        </div>
      )}

      {consumeTarget && (
        <MaterialConsumeForm
          assignmentId={consumeTarget.assignmentId}
          resourceName={consumeTarget.resourceName}
          maxQuantity={consumeTarget.remaining}
          onClose={() => setConsumeTarget(null)}
        />
      )}
    </div>
  );
}
