/**
 * Modal form for creating dependencies with predecessor/successor dropdowns.
 */

import { useState } from "react";
import { X } from "lucide-react";
import { useActivities } from "@/hooks/useActivities";
import { useCreateDependency } from "@/hooks/useDependencies";
import { useToast } from "@/components/Toast";
import type { DependencyType } from "@/types/dependency";

interface DependencyFormModalProps {
  programId: string;
  onClose: () => void;
}

const DEP_TYPES: { value: DependencyType; label: string }[] = [
  { value: "FS", label: "Finish-to-Start (FS)" },
  { value: "SS", label: "Start-to-Start (SS)" },
  { value: "FF", label: "Finish-to-Finish (FF)" },
  { value: "SF", label: "Start-to-Finish (SF)" },
];

export function DependencyFormModal({ programId, onClose }: DependencyFormModalProps) {
  const [predecessorId, setPredecessorId] = useState("");
  const [successorId, setSuccessorId] = useState("");
  const [depType, setDepType] = useState<DependencyType>("FS");
  const [lag, setLag] = useState("0");

  const { data: activitiesData } = useActivities(programId);
  const createMutation = useCreateDependency();
  const toast = useToast();

  const activities = activitiesData?.items ?? [];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createMutation.mutateAsync({
        predecessor_id: predecessorId,
        successor_id: successorId,
        dependency_type: depType,
        lag: Number(lag),
      });
      toast.success("Dependency created");
      onClose();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to create dependency";
      toast.error(msg);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <h2 className="text-lg font-semibold">Add Dependency</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600" aria-label="Close"><X size={20} /></button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label htmlFor="predecessor" className="block text-sm font-medium text-gray-700 mb-1">Predecessor *</label>
            <select id="predecessor" value={predecessorId} onChange={(e) => setPredecessorId(e.target.value)} required className="w-full border rounded-md px-3 py-2 text-sm">
              <option value="">Select activity...</option>
              {activities.map((a) => (
                <option key={a.id} value={a.id}>{a.code} - {a.name}</option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="depType" className="block text-sm font-medium text-gray-700 mb-1">Type</label>
            <select id="depType" value={depType} onChange={(e) => setDepType(e.target.value as DependencyType)} className="w-full border rounded-md px-3 py-2 text-sm">
              {DEP_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="successor" className="block text-sm font-medium text-gray-700 mb-1">Successor *</label>
            <select id="successor" value={successorId} onChange={(e) => setSuccessorId(e.target.value)} required className="w-full border rounded-md px-3 py-2 text-sm">
              <option value="">Select activity...</option>
              {activities.map((a) => (
                <option key={a.id} value={a.id}>{a.code} - {a.name}</option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="lag" className="block text-sm font-medium text-gray-700 mb-1">Lag (days)</label>
            <input id="lag" type="number" value={lag} onChange={(e) => setLag(e.target.value)} className="w-full border rounded-md px-3 py-2 text-sm" />
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t">
            <button type="button" onClick={onClose} className="px-4 py-2 text-sm text-gray-700 border rounded-md hover:bg-gray-50">Cancel</button>
            <button type="submit" disabled={createMutation.isPending} className="px-4 py-2 text-sm text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50">
              {createMutation.isPending ? "Creating..." : "Create"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
