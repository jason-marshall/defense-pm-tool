/**
 * ResourceForm modal component for creating and editing resources.
 */

import { useState, FormEvent } from "react";
import type { Resource } from "@/types/resource";
import { ResourceType } from "@/types/resource";
import { useCreateResource, useUpdateResource } from "@/hooks/useResources";
import { useToast } from "@/components/Toast";
import { X } from "lucide-react";

interface ResourceFormProps {
  programId: string;
  resource: Resource | null;
  onClose: () => void;
}

export function ResourceForm({ programId, resource, onClose }: ResourceFormProps) {
  const [formData, setFormData] = useState({
    name: resource?.name || "",
    code: resource?.code || "",
    resource_type: resource?.resource_type || ResourceType.LABOR,
    capacity_per_day: resource?.capacity_per_day || 8,
    cost_rate: resource?.cost_rate?.toString() || "",
    is_active: resource?.is_active ?? true,
  });

  const createResource = useCreateResource();
  const updateResource = useUpdateResource();
  const { success, error: showError } = useToast();
  const isEditing = !!resource;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();

    try {
      if (isEditing) {
        await updateResource.mutateAsync({
          id: resource.id,
          data: {
            name: formData.name,
            code: formData.code,
            resource_type: formData.resource_type,
            capacity_per_day: formData.capacity_per_day,
            cost_rate: formData.cost_rate ? Number(formData.cost_rate) : undefined,
            is_active: formData.is_active,
          },
        });
        success("Resource updated successfully");
      } else {
        await createResource.mutateAsync({
          program_id: programId,
          name: formData.name,
          code: formData.code,
          resource_type: formData.resource_type,
          capacity_per_day: formData.capacity_per_day,
          cost_rate: formData.cost_rate ? Number(formData.cost_rate) : undefined,
          is_active: formData.is_active,
        });
        success("Resource created successfully");
      }
      onClose();
    } catch {
      showError(`Failed to ${isEditing ? "update" : "create"} resource`);
    }
  };

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  const isPending = createResource.isPending || updateResource.isPending;

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      onClick={handleBackdropClick}
    >
      <div className="bg-white rounded-lg p-6 w-full max-w-md shadow-xl">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold">
            {isEditing ? "Edit Resource" : "New Resource"}
          </h3>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700"
            type="button"
            aria-label="Close"
          >
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">
                Code <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={formData.code}
                onChange={(e) =>
                  setFormData({ ...formData, code: e.target.value.toUpperCase() })
                }
                className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
                pattern="[A-Z0-9\-_]+"
                placeholder="e.g., ENG-001"
                title="Code must contain only uppercase letters, numbers, hyphens, and underscores"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">
                Name <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
                placeholder="e.g., Senior Engineer"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">Type</label>
              <select
                value={formData.resource_type}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    resource_type: e.target.value as ResourceType,
                  })
                }
                className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value={ResourceType.LABOR}>Labor</option>
                <option value={ResourceType.EQUIPMENT}>Equipment</option>
                <option value={ResourceType.MATERIAL}>Material</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">
                Capacity per Day (hours)
              </label>
              <input
                type="number"
                value={formData.capacity_per_day}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    capacity_per_day: Number(e.target.value),
                  })
                }
                className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                min="0"
                max="24"
                step="0.5"
              />
              <p className="text-xs text-gray-500 mt-1">
                Standard work day is 8 hours
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">
                Cost Rate ($/hour)
              </label>
              <input
                type="number"
                value={formData.cost_rate}
                onChange={(e) =>
                  setFormData({ ...formData, cost_rate: e.target.value })
                }
                className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                min="0"
                step="0.01"
                placeholder="Optional"
              />
            </div>

            <div className="flex items-center">
              <input
                type="checkbox"
                id="is_active"
                checked={formData.is_active}
                onChange={(e) =>
                  setFormData({ ...formData, is_active: e.target.checked })
                }
                className="mr-2 h-4 w-4"
              />
              <label htmlFor="is_active" className="text-sm">
                Active
              </label>
            </div>
          </div>

          <div className="flex justify-end gap-2 mt-6">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border rounded hover:bg-gray-50 transition-colors"
              disabled={isPending}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={isPending}
            >
              {isPending ? (
                <span className="flex items-center gap-2">
                  <span className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full" />
                  {isEditing ? "Updating..." : "Creating..."}
                </span>
              ) : isEditing ? (
                "Update"
              ) : (
                "Create"
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
