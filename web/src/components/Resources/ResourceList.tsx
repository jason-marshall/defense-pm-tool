/**
 * ResourceList component for managing resources.
 * Displays a table of resources with filtering, create, edit, and delete actions.
 */

import { useState } from "react";
import { useResources, useDeleteResource } from "@/hooks/useResources";
import { ResourceForm } from "./ResourceForm";
import type { Resource } from "@/types/resource";
import { ResourceType } from "@/types/resource";
import { Plus, Edit2, Trash2, Users, Wrench, Package } from "lucide-react";
import { useToast } from "@/components/Toast";

interface ResourceListProps {
  programId: string;
}

export function ResourceList({ programId }: ResourceListProps) {
  const [showForm, setShowForm] = useState(false);
  const [editingResource, setEditingResource] = useState<Resource | null>(null);
  const [typeFilter, setTypeFilter] = useState<string>("");

  const { data, isLoading, error } = useResources(programId, {
    resource_type: typeFilter || undefined,
  });
  const deleteResource = useDeleteResource();
  const { success, error: showError } = useToast();

  const getTypeIcon = (type: ResourceType) => {
    switch (type) {
      case ResourceType.LABOR:
        return <Users size={16} />;
      case ResourceType.EQUIPMENT:
        return <Wrench size={16} />;
      case ResourceType.MATERIAL:
        return <Package size={16} />;
    }
  };

  const handleEdit = (resource: Resource) => {
    setEditingResource(resource);
    setShowForm(true);
  };

  const handleCreate = () => {
    setEditingResource(null);
    setShowForm(true);
  };

  const handleCloseForm = () => {
    setShowForm(false);
    setEditingResource(null);
  };

  const handleDelete = async (id: string) => {
    if (confirm("Are you sure you want to delete this resource?")) {
      try {
        await deleteResource.mutateAsync(id);
        success("Resource deleted successfully");
      } catch {
        showError("Failed to delete resource");
      }
    }
  };

  if (isLoading) {
    return (
      <div className="p-4 text-gray-500">Loading resources...</div>
    );
  }

  if (error) {
    return (
      <div className="p-4 text-red-500">
        Error loading resources: {error instanceof Error ? error.message : "Unknown error"}
      </div>
    );
  }

  return (
    <div className="resource-list">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-semibold">Resources</h2>
        <div className="flex gap-2">
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="border rounded px-2 py-1 text-sm"
          >
            <option value="">All Types</option>
            <option value="LABOR">Labor</option>
            <option value="EQUIPMENT">Equipment</option>
            <option value="MATERIAL">Material</option>
          </select>
          <button
            onClick={handleCreate}
            className="bg-blue-500 text-white px-4 py-2 rounded flex items-center gap-2 hover:bg-blue-600 transition-colors"
          >
            <Plus size={16} /> Add Resource
          </button>
        </div>
      </div>

      {data?.items.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          <Package size={48} className="mx-auto mb-2 opacity-50" />
          <p>No resources found.</p>
          <button
            onClick={handleCreate}
            className="mt-2 text-blue-500 hover:underline"
          >
            Create your first resource
          </button>
        </div>
      ) : (
        <table className="w-full border-collapse">
          <thead>
            <tr className="bg-gray-100">
              <th className="border p-2 text-left">Code</th>
              <th className="border p-2 text-left">Name</th>
              <th className="border p-2 text-left">Type</th>
              <th className="border p-2 text-right">Capacity/Day</th>
              <th className="border p-2 text-right">Cost Rate</th>
              <th className="border p-2 text-center">Active</th>
              <th className="border p-2 text-center">Actions</th>
            </tr>
          </thead>
          <tbody>
            {data?.items.map((resource) => (
              <tr key={resource.id} className="hover:bg-gray-50">
                <td className="border p-2 font-mono text-sm">{resource.code}</td>
                <td className="border p-2">{resource.name}</td>
                <td className="border p-2">
                  <span className="flex items-center gap-1">
                    {getTypeIcon(resource.resource_type)}
                    <span className="text-sm">{resource.resource_type}</span>
                  </span>
                </td>
                <td className="border p-2 text-right">{resource.capacity_per_day}h</td>
                <td className="border p-2 text-right">
                  {resource.cost_rate ? `$${resource.cost_rate}/h` : "-"}
                </td>
                <td className="border p-2 text-center">
                  <span className={resource.is_active ? "text-green-600" : "text-gray-400"}>
                    {resource.is_active ? "Active" : "Inactive"}
                  </span>
                </td>
                <td className="border p-2 text-center">
                  <button
                    onClick={() => handleEdit(resource)}
                    className="text-blue-500 hover:text-blue-700 mr-2"
                    title="Edit resource"
                  >
                    <Edit2 size={16} />
                  </button>
                  <button
                    onClick={() => handleDelete(resource.id)}
                    className="text-red-500 hover:text-red-700"
                    title="Delete resource"
                    disabled={deleteResource.isPending}
                  >
                    <Trash2 size={16} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {data && data.total > data.items.length && (
        <div className="mt-4 text-sm text-gray-500 text-center">
          Showing {data.items.length} of {data.total} resources
        </div>
      )}

      {showForm && (
        <ResourceForm
          programId={programId}
          resource={editingResource}
          onClose={handleCloseForm}
        />
      )}
    </div>
  );
}
