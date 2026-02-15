/**
 * AssignmentModal component for assigning resources to activities.
 * Allows users to add/remove resource assignments with allocation percentage.
 */

import { useState } from "react";
import { useResources } from "@/hooks/useResources";
import {
  useActivityAssignments,
  useCreateAssignment,
  useDeleteAssignment,
} from "@/hooks/useAssignments";
import { useToast } from "@/components/Toast";
import { X, Plus, Trash2, Users } from "lucide-react";

interface AssignmentModalProps {
  activityId: string;
  activityName: string;
  programId: string;
  onClose: () => void;
}

export function AssignmentModal({
  activityId,
  activityName,
  programId,
  onClose,
}: AssignmentModalProps) {
  const [selectedResourceId, setSelectedResourceId] = useState("");
  const [units, setUnits] = useState(1.0);

  const { data: resources } = useResources(programId, { is_active: true });
  const { data: assignments, isLoading } = useActivityAssignments(activityId);
  const createAssignment = useCreateAssignment();
  const deleteAssignment = useDeleteAssignment();
  const { success, error: showError } = useToast();

  const assignedResourceIds = new Set(
    assignments?.map((a) => a.resource_id) || []
  );
  const availableResources =
    resources?.items.filter((r) => !assignedResourceIds.has(r.id)) || [];

  const handleAssign = async () => {
    if (!selectedResourceId) return;

    try {
      await createAssignment.mutateAsync({
        resourceId: selectedResourceId,
        data: {
          activity_id: activityId,
          resource_id: selectedResourceId,
          units,
        },
      });
      success("Resource assigned successfully");
      setSelectedResourceId("");
      setUnits(1.0);
    } catch {
      showError("Failed to assign resource");
    }
  };

  const handleRemove = async (assignmentId: string) => {
    try {
      await deleteAssignment.mutateAsync(assignmentId);
      success("Assignment removed");
    } catch {
      showError("Failed to remove assignment");
    }
  };

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      onClick={handleBackdropClick}
    >
      <div className="bg-white rounded-lg p-6 w-full max-w-lg shadow-xl">
        <div className="flex justify-between items-center mb-4">
          <div>
            <h3 className="text-lg font-semibold">Assign Resources</h3>
            <p className="text-sm text-gray-500">{activityName}</p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700"
            aria-label="Close"
          >
            <X size={20} />
          </button>
        </div>

        {/* Current Assignments */}
        <div className="mb-6">
          <h4 className="text-sm font-medium mb-2 flex items-center gap-1">
            <Users size={16} />
            Current Assignments
          </h4>
          {isLoading ? (
            <p className="text-gray-500 text-sm">Loading...</p>
          ) : assignments?.length === 0 ? (
            <div className="text-center py-4 text-gray-500 bg-gray-50 rounded">
              <p className="text-sm">No resources assigned yet</p>
            </div>
          ) : (
            <table className="w-full text-sm border">
              <thead>
                <tr className="bg-gray-50">
                  <th className="p-2 text-left border-b">Resource</th>
                  <th className="p-2 text-right border-b">Allocation</th>
                  <th className="p-2 text-center border-b w-16">Action</th>
                </tr>
              </thead>
              <tbody>
                {assignments?.map((assignment) => (
                  <tr key={assignment.id} className="hover:bg-gray-50">
                    <td className="p-2 border-b">
                      <span className="font-mono text-xs text-gray-500">
                        {assignment.resource?.code}
                      </span>
                      <span className="mx-1">-</span>
                      {assignment.resource?.name}
                    </td>
                    <td className="p-2 text-right border-b">
                      <span
                        className={
                          assignment.units > 1
                            ? "text-orange-600 font-medium"
                            : ""
                        }
                      >
                        {(assignment.units * 100).toFixed(0)}%
                      </span>
                    </td>
                    <td className="p-2 text-center border-b">
                      <button
                        onClick={() => handleRemove(assignment.id)}
                        className="text-red-500 hover:text-red-700"
                        title="Remove assignment"
                        aria-label="Remove assignment"
                        disabled={deleteAssignment.isPending}
                      >
                        <Trash2 size={16} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Add Assignment */}
        <div className="border-t pt-4">
          <h4 className="text-sm font-medium mb-2">Add Assignment</h4>
          {availableResources.length === 0 ? (
            <p className="text-sm text-gray-500">
              All active resources are already assigned to this activity.
            </p>
          ) : (
            <>
              <div className="flex gap-2">
                <select
                  value={selectedResourceId}
                  onChange={(e) => setSelectedResourceId(e.target.value)}
                  className="flex-1 border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Select resource...</option>
                  {availableResources.map((resource) => (
                    <option key={resource.id} value={resource.id}>
                      {resource.code} - {resource.name} ({resource.resource_type})
                    </option>
                  ))}
                </select>
                <div className="relative">
                  <input
                    type="number"
                    value={units}
                    onChange={(e) => setUnits(Number(e.target.value))}
                    className="w-24 border rounded px-3 py-2 text-right text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    min="0.1"
                    max="10"
                    step="0.1"
                    title="Allocation units (1.0 = 100%)"
                  />
                </div>
                <button
                  onClick={handleAssign}
                  disabled={!selectedResourceId || createAssignment.isPending}
                  className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1 transition-colors"
                >
                  <Plus size={16} />
                  Assign
                </button>
              </div>
              <p className="text-xs text-gray-500 mt-2">
                Units: 1.0 = 100% allocation, 0.5 = 50% (part-time), 2.0 = 200%
                (overtime)
              </p>
            </>
          )}
        </div>

        <div className="flex justify-end mt-6 pt-4 border-t">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-100 rounded hover:bg-gray-200 transition-colors"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
