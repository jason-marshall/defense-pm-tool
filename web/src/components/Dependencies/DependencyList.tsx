/**
 * Dependency list with type badges and CRUD operations.
 */

import { useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { useDependencies, useDeleteDependency } from "@/hooks/useDependencies";
import { DependencyFormModal } from "./DependencyFormModal";
import { useToast } from "@/components/Toast";

interface DependencyListProps {
  programId: string;
}

const typeBadgeColors: Record<string, string> = {
  FS: "bg-blue-100 text-blue-700",
  SS: "bg-green-100 text-green-700",
  FF: "bg-purple-100 text-purple-700",
  SF: "bg-orange-100 text-orange-700",
};

export function DependencyList({ programId }: DependencyListProps) {
  const [showForm, setShowForm] = useState(false);
  const { data, isLoading, error } = useDependencies(programId);
  const deleteDependency = useDeleteDependency();
  const toast = useToast();

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this dependency?")) return;
    try {
      await deleteDependency.mutateAsync(id);
      toast.success("Dependency deleted");
    } catch {
      toast.error("Failed to delete dependency");
    }
  };

  if (isLoading) return <div className="p-4 text-gray-500">Loading dependencies...</div>;
  if (error) return <div className="p-4 text-red-500">Error loading dependencies</div>;

  const dependencies = data?.items ?? [];

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold">Dependencies</h2>
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
        >
          <Plus size={16} /> Add Dependency
        </button>
      </div>

      {dependencies.length === 0 ? (
        <div className="bg-white rounded-lg border p-8 text-center text-gray-500">
          <p>No dependencies defined.</p>
          <button onClick={() => setShowForm(true)} className="mt-2 text-blue-600 hover:underline text-sm">
            Add your first dependency
          </button>
        </div>
      ) : (
        <div className="bg-white rounded-lg border overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 border-b">
                <th className="text-left px-4 py-2 text-xs font-medium text-gray-500 uppercase">Predecessor</th>
                <th className="text-center px-4 py-2 text-xs font-medium text-gray-500 uppercase">Type</th>
                <th className="text-left px-4 py-2 text-xs font-medium text-gray-500 uppercase">Successor</th>
                <th className="text-right px-4 py-2 text-xs font-medium text-gray-500 uppercase">Lag</th>
                <th className="text-center px-4 py-2 text-xs font-medium text-gray-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody>
              {dependencies.map((dep) => (
                <tr key={dep.id} className="border-b last:border-b-0 hover:bg-gray-50">
                  <td className="px-4 py-2">{dep.predecessor_name || dep.predecessor_id.slice(0, 8)}</td>
                  <td className="px-4 py-2 text-center">
                    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${typeBadgeColors[dep.dependency_type]}`}>
                      {dep.dependency_type}
                    </span>
                  </td>
                  <td className="px-4 py-2">{dep.successor_name || dep.successor_id.slice(0, 8)}</td>
                  <td className="px-4 py-2 text-right">{dep.lag}d</td>
                  <td className="px-4 py-2 text-center">
                    <button onClick={() => handleDelete(dep.id)} className="text-red-500 hover:text-red-700" title="Delete">
                      <Trash2 size={14} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showForm && (
        <DependencyFormModal
          programId={programId}
          onClose={() => setShowForm(false)}
        />
      )}
    </div>
  );
}
