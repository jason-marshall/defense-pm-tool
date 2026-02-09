/**
 * Programs list page with CRUD operations.
 */

import { useState } from "react";
import { Link } from "react-router-dom";
import { Plus, Edit2, Trash2, FolderKanban } from "lucide-react";
import { usePrograms, useCreateProgram, useDeleteProgram } from "@/hooks/usePrograms";
import { ProgramFormModal } from "@/components/Programs/ProgramFormModal";
import { useToast } from "@/components/Toast";
import type { Program } from "@/types/program";

const statusColors: Record<string, string> = {
  PLANNING: "bg-blue-100 text-blue-700",
  ACTIVE: "bg-green-100 text-green-700",
  ON_HOLD: "bg-yellow-100 text-yellow-700",
  COMPLETED: "bg-gray-100 text-gray-600",
  CANCELLED: "bg-red-100 text-red-700",
};

export function ProgramsPage() {
  const [showForm, setShowForm] = useState(false);
  const [editingProgram, setEditingProgram] = useState<Program | null>(null);
  const { data, isLoading, error } = usePrograms();
  const createProgram = useCreateProgram();
  const deleteProgram = useDeleteProgram();
  const toast = useToast();

  const handleCreate = () => {
    setEditingProgram(null);
    setShowForm(true);
  };

  const handleEdit = (program: Program) => {
    setEditingProgram(program);
    setShowForm(true);
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Are you sure you want to delete this program?")) return;
    try {
      await deleteProgram.mutateAsync(id);
      toast.success("Program deleted successfully");
    } catch {
      toast.error("Failed to delete program");
    }
  };

  const handleSubmit = async (data: Parameters<typeof createProgram.mutateAsync>[0]) => {
    try {
      await createProgram.mutateAsync(data);
      toast.success(editingProgram ? "Program updated" : "Program created");
      setShowForm(false);
      setEditingProgram(null);
    } catch {
      toast.error("Failed to save program");
    }
  };

  if (isLoading) {
    return <div className="p-4 text-gray-500">Loading programs...</div>;
  }

  if (error) {
    return (
      <div className="p-4 text-red-500">
        Error loading programs: {error instanceof Error ? error.message : "Unknown error"}
      </div>
    );
  }

  const programs = data?.items ?? [];

  return (
    <div className="max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Programs</h1>
        <button
          onClick={handleCreate}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm"
        >
          <Plus size={16} /> New Program
        </button>
      </div>

      {programs.length === 0 ? (
        <div className="bg-white rounded-lg shadow-xs border p-12 text-center">
          <FolderKanban size={48} className="mx-auto mb-3 text-gray-300" />
          <p className="text-gray-500 mb-4">No programs yet.</p>
          <button
            onClick={handleCreate}
            className="text-blue-600 hover:underline text-sm"
          >
            Create your first program
          </button>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow-xs border overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="bg-gray-50 border-b">
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Code</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Name</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Status</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Start Date</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">End Date</th>
                <th className="text-right px-4 py-3 text-xs font-medium text-gray-500 uppercase">BAC</th>
                <th className="text-center px-4 py-3 text-xs font-medium text-gray-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody>
              {programs.map((program) => (
                <tr key={program.id} className="border-b last:border-b-0 hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-sm">
                    <Link
                      to={`/programs/${program.id}`}
                      className="text-blue-600 hover:underline"
                    >
                      {program.code}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-sm">
                    <Link
                      to={`/programs/${program.id}`}
                      className="text-gray-900 hover:text-blue-600"
                    >
                      {program.name}
                    </Link>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-block px-2 py-1 rounded text-xs font-medium ${
                        statusColors[program.status] || "bg-gray-100 text-gray-600"
                      }`}
                    >
                      {program.status.replace("_", " ")}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">
                    {program.planned_start_date?.split("T")[0]}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">
                    {program.planned_end_date?.split("T")[0]}
                  </td>
                  <td className="px-4 py-3 text-sm text-right text-gray-600">
                    {program.budget_at_completion
                      ? `$${Number(program.budget_at_completion).toLocaleString()}`
                      : "-"}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <button
                      onClick={() => handleEdit(program)}
                      className="text-blue-500 hover:text-blue-700 mr-2"
                      title="Edit"
                    >
                      <Edit2 size={16} />
                    </button>
                    <button
                      onClick={() => handleDelete(program.id)}
                      className="text-red-500 hover:text-red-700"
                      title="Delete"
                      disabled={deleteProgram.isPending}
                    >
                      <Trash2 size={16} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showForm && (
        <ProgramFormModal
          program={editingProgram}
          onSubmit={handleSubmit}
          onClose={() => {
            setShowForm(false);
            setEditingProgram(null);
          }}
          isSubmitting={createProgram.isPending}
        />
      )}
    </div>
  );
}
