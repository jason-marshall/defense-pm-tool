/**
 * Baseline list with approve and compare actions.
 */

import { useState } from "react";
import { CheckCircle, GitCompare, Trash2 } from "lucide-react";
import { useBaselines, useApproveBaseline, useDeleteBaseline, useCompareBaselines } from "@/hooks/useBaselines";
import { useToast } from "@/components/Toast";

interface BaselineListProps {
  programId: string;
}

const statusColors: Record<string, string> = {
  draft: "bg-gray-100 text-gray-600",
  approved: "bg-green-100 text-green-700",
  superseded: "bg-yellow-100 text-yellow-600",
};

export function BaselineList({ programId }: BaselineListProps) {
  const [compareA, setCompareA] = useState("");
  const [compareB, setCompareB] = useState("");
  const { data, isLoading, error } = useBaselines(programId);
  const approveMutation = useApproveBaseline();
  const deleteMutation = useDeleteBaseline();
  const { data: comparison } = useCompareBaselines(compareA, compareB);
  const toast = useToast();

  if (isLoading) return <div className="p-4 text-gray-500">Loading baselines...</div>;
  if (error) return <div className="p-4 text-red-500">Error loading baselines</div>;

  const baselines = data?.items ?? [];

  const handleApprove = async (id: string) => {
    try {
      await approveMutation.mutateAsync(id);
      toast.success("Baseline approved");
    } catch { toast.error("Approval failed"); }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this baseline?")) return;
    try {
      await deleteMutation.mutateAsync(id);
      toast.success("Baseline deleted");
    } catch { toast.error("Delete failed"); }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold">Baselines</h2>
      </div>

      {baselines.length === 0 ? (
        <div className="bg-white rounded-lg border p-8 text-center text-gray-500">
          No baselines created yet. Promote a scenario to create one.
        </div>
      ) : (
        <div className="bg-white rounded-lg border overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 border-b">
                <th className="text-left px-4 py-2 text-xs font-medium text-gray-500">#</th>
                <th className="text-left px-4 py-2 text-xs font-medium text-gray-500">Name</th>
                <th className="text-left px-4 py-2 text-xs font-medium text-gray-500">Status</th>
                <th className="text-left px-4 py-2 text-xs font-medium text-gray-500">Created</th>
                <th className="text-center px-4 py-2 text-xs font-medium text-gray-500">Compare</th>
                <th className="text-center px-4 py-2 text-xs font-medium text-gray-500">Actions</th>
              </tr>
            </thead>
            <tbody>
              {baselines.map((baseline) => (
                <tr key={baseline.id} className="border-b hover:bg-gray-50">
                  <td className="px-4 py-2 font-mono">{baseline.baseline_number}</td>
                  <td className="px-4 py-2">{baseline.name}</td>
                  <td className="px-4 py-2">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${statusColors[baseline.status]}`}>
                      {baseline.status}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-gray-500">
                    {new Date(baseline.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-2 text-center">
                    <input
                      type="radio"
                      name="compareA"
                      onChange={() => setCompareA(baseline.id)}
                      checked={compareA === baseline.id}
                      className="mr-2"
                    />
                    <input
                      type="radio"
                      name="compareB"
                      onChange={() => setCompareB(baseline.id)}
                      checked={compareB === baseline.id}
                    />
                  </td>
                  <td className="px-4 py-2 text-center">
                    {baseline.status === "draft" && (
                      <button onClick={() => handleApprove(baseline.id)} className="text-green-600 hover:text-green-800 mr-2" title="Approve">
                        <CheckCircle size={14} />
                      </button>
                    )}
                    <button onClick={() => handleDelete(baseline.id)} className="text-red-500 hover:text-red-700" title="Delete">
                      <Trash2 size={14} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {comparison && (
        <div className="mt-6 bg-white rounded-lg border p-4">
          <h3 className="font-semibold mb-3 flex items-center gap-2">
            <GitCompare size={16} /> Comparison: {comparison.baseline_a.name} vs {comparison.baseline_b.name}
          </h3>
          {comparison.deltas.length === 0 ? (
            <p className="text-sm text-gray-500">No differences found.</p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="text-left px-3 py-2 text-xs text-gray-500">Activity</th>
                  <th className="text-left px-3 py-2 text-xs text-gray-500">Field</th>
                  <th className="text-right px-3 py-2 text-xs text-gray-500">Baseline A</th>
                  <th className="text-right px-3 py-2 text-xs text-gray-500">Baseline B</th>
                  <th className="text-right px-3 py-2 text-xs text-gray-500">Change</th>
                </tr>
              </thead>
              <tbody>
                {comparison.deltas.map((delta, i) => (
                  <tr key={i} className="border-b hover:bg-gray-50">
                    <td className="px-3 py-2">{delta.activity_name}</td>
                    <td className="px-3 py-2 text-gray-500">{delta.field}</td>
                    <td className="px-3 py-2 text-right">{delta.value_a}</td>
                    <td className="px-3 py-2 text-right">{delta.value_b}</td>
                    <td className="px-3 py-2 text-right font-medium">{delta.change_percent}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
