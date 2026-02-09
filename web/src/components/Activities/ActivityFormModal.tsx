/**
 * Modal form for creating and editing activities.
 */

import { useState, useEffect } from "react";
import { X } from "lucide-react";
import { useCreateActivity, useUpdateActivity } from "@/hooks/useActivities";
import { useToast } from "@/components/Toast";
import type { Activity } from "@/types/activity";

interface ActivityFormModalProps {
  programId: string;
  activity?: Activity | null;
  onClose: () => void;
}

export function ActivityFormModal({
  programId,
  activity,
  onClose,
}: ActivityFormModalProps) {
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [description, setDescription] = useState("");
  const [duration, setDuration] = useState("5");
  const [percentComplete, setPercentComplete] = useState("0");
  const [budgetedCost, setBudgetedCost] = useState("");
  const [isMilestone, setIsMilestone] = useState(false);

  const createMutation = useCreateActivity();
  const updateMutation = useUpdateActivity();
  const toast = useToast();

  useEffect(() => {
    if (activity) {
      setName(activity.name);
      setCode(activity.code);
      setDescription(activity.description || "");
      setDuration(String(activity.duration));
      setPercentComplete(activity.percent_complete);
      setBudgetedCost(activity.budgeted_cost || "");
      setIsMilestone(activity.is_milestone);
    }
  }, [activity]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (activity) {
        await updateMutation.mutateAsync({
          id: activity.id,
          data: {
            name,
            code,
            description: description || undefined,
            duration: Number(duration),
            percent_complete: percentComplete,
            budgeted_cost: budgetedCost || undefined,
            is_milestone: isMilestone,
          },
        });
        toast.success("Activity updated");
      } else {
        await createMutation.mutateAsync({
          program_id: programId,
          name,
          code,
          description: description || undefined,
          duration: Number(duration),
          percent_complete: percentComplete,
          budgeted_cost: budgetedCost || undefined,
          is_milestone: isMilestone,
        });
        toast.success("Activity created");
      }
      onClose();
    } catch {
      toast.error("Failed to save activity");
    }
  };

  const isPending = createMutation.isPending || updateMutation.isPending;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg mx-4" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <h2 className="text-lg font-semibold">
            {activity ? "Edit Activity" : "Create Activity"}
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="actName" className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
              <input id="actName" type="text" value={name} onChange={(e) => setName(e.target.value)} required className="w-full border rounded-md px-3 py-2 text-sm" />
            </div>
            <div>
              <label htmlFor="actCode" className="block text-sm font-medium text-gray-700 mb-1">Code *</label>
              <input id="actCode" type="text" value={code} onChange={(e) => setCode(e.target.value)} required className="w-full border rounded-md px-3 py-2 text-sm" />
            </div>
          </div>

          <div>
            <label htmlFor="actDesc" className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <textarea id="actDesc" value={description} onChange={(e) => setDescription(e.target.value)} rows={2} className="w-full border rounded-md px-3 py-2 text-sm" />
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div>
              <label htmlFor="actDur" className="block text-sm font-medium text-gray-700 mb-1">Duration (days)</label>
              <input id="actDur" type="number" value={duration} onChange={(e) => setDuration(e.target.value)} min="0" className="w-full border rounded-md px-3 py-2 text-sm" />
            </div>
            <div>
              <label htmlFor="actPct" className="block text-sm font-medium text-gray-700 mb-1">% Complete</label>
              <input id="actPct" type="number" value={percentComplete} onChange={(e) => setPercentComplete(e.target.value)} min="0" max="100" className="w-full border rounded-md px-3 py-2 text-sm" />
            </div>
            <div>
              <label htmlFor="actBudget" className="block text-sm font-medium text-gray-700 mb-1">Budget ($)</label>
              <input id="actBudget" type="number" value={budgetedCost} onChange={(e) => setBudgetedCost(e.target.value)} step="0.01" min="0" className="w-full border rounded-md px-3 py-2 text-sm" />
            </div>
          </div>

          <div className="flex items-center gap-2">
            <input id="actMilestone" type="checkbox" checked={isMilestone} onChange={(e) => setIsMilestone(e.target.checked)} />
            <label htmlFor="actMilestone" className="text-sm text-gray-700">Milestone (zero duration)</label>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t">
            <button type="button" onClick={onClose} className="px-4 py-2 text-sm text-gray-700 border rounded-md hover:bg-gray-50">Cancel</button>
            <button type="submit" disabled={isPending} className="px-4 py-2 text-sm text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50">
              {isPending ? "Saving..." : activity ? "Update" : "Create"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
