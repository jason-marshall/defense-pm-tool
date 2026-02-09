/**
 * Variance Explanation panel with table, add/edit form, and type filter.
 */

import { useState } from "react";
import { useVariancesByProgram, useCreateVariance, useUpdateVariance, useDeleteVariance } from "@/hooks/useVariance";
import { useToast } from "@/components/Toast";
import { Plus, Edit2, Trash2 } from "lucide-react";
import type { VarianceExplanationResponse, VarianceType } from "@/types/variance";

interface VariancePanelProps {
  programId: string;
}

export function VariancePanel({ programId }: VariancePanelProps) {
  const [typeFilter, setTypeFilter] = useState<string>("");
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<VarianceExplanationResponse | null>(null);

  const { data, isLoading } = useVariancesByProgram(programId, {
    variance_type: typeFilter || undefined,
    include_resolved: true,
  });
  const createMutation = useCreateVariance();
  const updateMutation = useUpdateVariance();
  const deleteMutation = useDeleteVariance();
  const toast = useToast();

  // Form state
  const [formType, setFormType] = useState<VarianceType>("cost");
  const [formAmount, setFormAmount] = useState("");
  const [formPercent, setFormPercent] = useState("");
  const [formExplanation, setFormExplanation] = useState("");
  const [formAction, setFormAction] = useState("");
  const [formResolution, setFormResolution] = useState("");

  const openCreateForm = () => {
    setEditing(null);
    setFormType("cost");
    setFormAmount("");
    setFormPercent("");
    setFormExplanation("");
    setFormAction("");
    setFormResolution("");
    setShowForm(true);
  };

  const openEditForm = (v: VarianceExplanationResponse) => {
    setEditing(v);
    setFormType(v.variance_type as VarianceType);
    setFormAmount(v.variance_amount);
    setFormPercent(v.variance_percent);
    setFormExplanation(v.explanation);
    setFormAction(v.corrective_action || "");
    setFormResolution(v.expected_resolution || "");
    setShowForm(true);
  };

  const handleSubmit = async () => {
    if (!formExplanation || formExplanation.length < 10) {
      toast.error("Explanation must be at least 10 characters");
      return;
    }
    try {
      if (editing) {
        await updateMutation.mutateAsync({
          id: editing.id,
          data: {
            explanation: formExplanation,
            corrective_action: formAction || undefined,
            expected_resolution: formResolution || undefined,
            variance_amount: formAmount,
            variance_percent: formPercent,
          },
        });
        toast.success("Variance explanation updated");
      } else {
        await createMutation.mutateAsync({
          program_id: programId,
          variance_type: formType,
          variance_amount: formAmount,
          variance_percent: formPercent,
          explanation: formExplanation,
          corrective_action: formAction || undefined,
          expected_resolution: formResolution || undefined,
        });
        toast.success("Variance explanation created");
      }
      setShowForm(false);
    } catch {
      toast.error("Failed to save variance explanation");
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this variance explanation?")) return;
    try {
      await deleteMutation.mutateAsync(id);
      toast.success("Variance explanation deleted");
    } catch {
      toast.error("Failed to delete variance explanation");
    }
  };

  if (isLoading) {
    return <div className="p-4 text-gray-500">Loading variance explanations...</div>;
  }

  return (
    <div className="space-y-4">
      <div className="bg-white rounded-lg border p-6">
        <div className="flex justify-between items-center mb-4">
          <h3 className="font-medium">Variance Explanations (VRID)</h3>
          <div className="flex gap-2">
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="border rounded px-2 py-1 text-sm"
            >
              <option value="">All Types</option>
              <option value="schedule">Schedule</option>
              <option value="cost">Cost</option>
            </select>
            <button
              onClick={openCreateForm}
              className="flex items-center gap-1 px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700"
            >
              <Plus size={14} /> Add
            </button>
          </div>
        </div>

        {data && data.items.length === 0 && (
          <p className="text-sm text-gray-500 text-center py-4">No variance explanations found.</p>
        )}

        {data && data.items.length > 0 && (
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="bg-gray-100">
                <th className="border p-2 text-left">Type</th>
                <th className="border p-2 text-right">Amount</th>
                <th className="border p-2 text-right">Percent</th>
                <th className="border p-2 text-left">Explanation</th>
                <th className="border p-2 text-left">Resolution</th>
                <th className="border p-2 text-center">Actions</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((v) => (
                <tr key={v.id} className="hover:bg-gray-50">
                  <td className="border p-2">
                    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                      v.variance_type === "cost" ? "bg-red-100 text-red-700" : "bg-yellow-100 text-yellow-700"
                    }`}>
                      {v.variance_type}
                    </span>
                  </td>
                  <td className="border p-2 text-right font-mono">
                    ${Number(v.variance_amount).toLocaleString()}
                  </td>
                  <td className="border p-2 text-right font-mono">
                    {Number(v.variance_percent).toFixed(1)}%
                  </td>
                  <td className="border p-2 max-w-xs truncate">{v.explanation}</td>
                  <td className="border p-2">{v.expected_resolution || "-"}</td>
                  <td className="border p-2 text-center">
                    <button
                      onClick={() => openEditForm(v)}
                      className="text-blue-500 hover:text-blue-700 mr-2"
                      title="Edit"
                    >
                      <Edit2 size={14} />
                    </button>
                    <button
                      onClick={() => handleDelete(v.id)}
                      className="text-red-500 hover:text-red-700"
                      title="Delete"
                    >
                      <Trash2 size={14} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Add / Edit Form */}
      {showForm && (
        <div className="bg-white rounded-lg border p-6">
          <h3 className="font-medium mb-4">
            {editing ? "Edit Variance Explanation" : "New Variance Explanation"}
          </h3>
          <div className="space-y-3 max-w-lg">
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label htmlFor="veType" className="block text-sm font-medium text-gray-700 mb-1">Type</label>
                <select
                  id="veType"
                  value={formType}
                  onChange={(e) => setFormType(e.target.value as VarianceType)}
                  disabled={!!editing}
                  className="w-full border rounded-md px-3 py-2 text-sm"
                >
                  <option value="cost">Cost</option>
                  <option value="schedule">Schedule</option>
                </select>
              </div>
              <div>
                <label htmlFor="veAmount" className="block text-sm font-medium text-gray-700 mb-1">Amount ($)</label>
                <input
                  id="veAmount"
                  type="number"
                  value={formAmount}
                  onChange={(e) => setFormAmount(e.target.value)}
                  className="w-full border rounded-md px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label htmlFor="vePercent" className="block text-sm font-medium text-gray-700 mb-1">Percent (%)</label>
                <input
                  id="vePercent"
                  type="number"
                  value={formPercent}
                  onChange={(e) => setFormPercent(e.target.value)}
                  step="0.1"
                  className="w-full border rounded-md px-3 py-2 text-sm"
                />
              </div>
            </div>
            <div>
              <label htmlFor="veExplanation" className="block text-sm font-medium text-gray-700 mb-1">Explanation</label>
              <textarea
                id="veExplanation"
                value={formExplanation}
                onChange={(e) => setFormExplanation(e.target.value)}
                rows={3}
                className="w-full border rounded-md px-3 py-2 text-sm"
                placeholder="Explain the cause of this variance (min 10 characters)"
              />
            </div>
            <div>
              <label htmlFor="veAction" className="block text-sm font-medium text-gray-700 mb-1">Corrective Action</label>
              <textarea
                id="veAction"
                value={formAction}
                onChange={(e) => setFormAction(e.target.value)}
                rows={2}
                className="w-full border rounded-md px-3 py-2 text-sm"
                placeholder="Optional corrective action plan"
              />
            </div>
            <div>
              <label htmlFor="veResolution" className="block text-sm font-medium text-gray-700 mb-1">Expected Resolution</label>
              <input
                id="veResolution"
                type="date"
                value={formResolution}
                onChange={(e) => setFormResolution(e.target.value)}
                className="w-full border rounded-md px-3 py-2 text-sm"
              />
            </div>
            <div className="flex gap-2">
              <button
                onClick={handleSubmit}
                disabled={createMutation.isPending || updateMutation.isPending}
                className="px-4 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
              >
                {editing ? "Update" : "Create"}
              </button>
              <button
                onClick={() => setShowForm(false)}
                className="px-4 py-2 text-sm border rounded hover:bg-gray-50"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
