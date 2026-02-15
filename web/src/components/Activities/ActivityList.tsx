/**
 * Activity list component with CRUD, critical path highlighting, and milestone icons.
 */

import { useState } from "react";
import { Plus, Edit2, Trash2, Flag, AlertTriangle } from "lucide-react";
import { useActivities, useDeleteActivity } from "@/hooks/useActivities";
import { ActivityFormModal } from "./ActivityFormModal";
import { useToast } from "@/components/Toast";
import type { Activity } from "@/types/activity";

interface ActivityListProps {
  programId: string;
}

export function ActivityList({ programId }: ActivityListProps) {
  const [showForm, setShowForm] = useState(false);
  const [editingActivity, setEditingActivity] = useState<Activity | null>(null);
  const { data, isLoading, error } = useActivities(programId);
  const deleteActivity = useDeleteActivity();
  const toast = useToast();

  const handleCreate = () => {
    setEditingActivity(null);
    setShowForm(true);
  };

  const handleEdit = (activity: Activity) => {
    setEditingActivity(activity);
    setShowForm(true);
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this activity?")) return;
    try {
      await deleteActivity.mutateAsync(id);
      toast.success("Activity deleted");
    } catch {
      toast.error("Failed to delete activity");
    }
  };

  if (isLoading) return <div className="p-4 text-gray-500">Loading activities...</div>;
  if (error) return <div className="p-4 text-red-500">Error loading activities</div>;

  const activities = data?.items ?? [];

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold">Activities</h2>
        <button
          onClick={handleCreate}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
        >
          <Plus size={16} /> Add Activity
        </button>
      </div>

      {activities.length === 0 ? (
        <div className="bg-white rounded-lg border p-8 text-center text-gray-500">
          <p>No activities yet.</p>
          <button onClick={handleCreate} className="mt-2 text-blue-600 hover:underline text-sm">
            Create your first activity
          </button>
        </div>
      ) : (
        <div className="bg-white rounded-lg border overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 border-b">
                <th className="text-left px-3 py-2 text-xs font-medium text-gray-500 uppercase">Code</th>
                <th className="text-left px-3 py-2 text-xs font-medium text-gray-500 uppercase">Name</th>
                <th className="text-right px-3 py-2 text-xs font-medium text-gray-500 uppercase">Duration</th>
                <th className="text-right px-3 py-2 text-xs font-medium text-gray-500 uppercase">% Complete</th>
                <th className="text-right px-3 py-2 text-xs font-medium text-gray-500 uppercase">ES</th>
                <th className="text-right px-3 py-2 text-xs font-medium text-gray-500 uppercase">EF</th>
                <th className="text-right px-3 py-2 text-xs font-medium text-gray-500 uppercase">TF</th>
                <th className="text-right px-3 py-2 text-xs font-medium text-gray-500 uppercase">Budget</th>
                <th className="text-center px-3 py-2 text-xs font-medium text-gray-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody>
              {activities.map((activity) => (
                <tr
                  key={activity.id}
                  className={`border-b last:border-b-0 hover:bg-gray-50 ${
                    activity.is_critical ? "bg-red-50" : ""
                  }`}
                >
                  <td className="px-3 py-2 font-mono">
                    <span className="flex items-center gap-1">
                      {activity.is_milestone && <Flag size={12} className="text-amber-500" />}
                      {activity.is_critical && <AlertTriangle size={12} className="text-red-500" />}
                      {activity.code}
                    </span>
                  </td>
                  <td className="px-3 py-2">{activity.name}</td>
                  <td className="px-3 py-2 text-right">{activity.duration}d</td>
                  <td className="px-3 py-2 text-right">{activity.percent_complete}%</td>
                  <td className="px-3 py-2 text-right text-gray-500">
                    {activity.early_start ?? "-"}
                  </td>
                  <td className="px-3 py-2 text-right text-gray-500">
                    {activity.early_finish ?? "-"}
                  </td>
                  <td className="px-3 py-2 text-right">
                    <span
                      className={
                        activity.total_float === 0
                          ? "text-red-600 font-medium"
                          : "text-gray-500"
                      }
                    >
                      {activity.total_float ?? "-"}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-right text-gray-600">
                    {activity.budgeted_cost
                      ? `$${Number(activity.budgeted_cost).toLocaleString()}`
                      : "-"}
                  </td>
                  <td className="px-3 py-2 text-center">
                    <button
                      onClick={() => handleEdit(activity)}
                      className="text-blue-500 hover:text-blue-700 mr-2"
                      title="Edit"
                      aria-label={`Edit activity ${activity.name}`}
                    >
                      <Edit2 size={14} />
                    </button>
                    <button
                      onClick={() => handleDelete(activity.id)}
                      className="text-red-500 hover:text-red-700"
                      title="Delete"
                      aria-label={`Delete activity ${activity.name}`}
                    >
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
        <ActivityFormModal
          programId={programId}
          activity={editingActivity}
          onClose={() => {
            setShowForm(false);
            setEditingActivity(null);
          }}
        />
      )}
    </div>
  );
}
