/**
 * ResourcePoolForm modal for creating/editing resource pools.
 */

import { useState } from "react";
import { useCreatePool, useUpdatePool } from "@/hooks/useResourcePools";
import { useToast } from "@/components/Toast";
import type { ResourcePoolResponse } from "@/types/resourcePool";

interface ResourcePoolFormProps {
  pool?: ResourcePoolResponse | null;
  onClose: () => void;
}

export function ResourcePoolForm({ pool, onClose }: ResourcePoolFormProps) {
  const isEdit = !!pool;
  const [name, setName] = useState(pool?.name || "");
  const [code, setCode] = useState(pool?.code || "");
  const [description, setDescription] = useState(pool?.description || "");

  const createMutation = useCreatePool();
  const updateMutation = useUpdatePool();
  const { success, error: showError } = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!name.trim() || (!isEdit && !code.trim())) {
      showError("Name and code are required");
      return;
    }

    try {
      if (isEdit && pool) {
        await updateMutation.mutateAsync({
          poolId: pool.id,
          data: {
            name: name.trim(),
            description: description.trim() || undefined,
          },
        });
        success("Pool updated");
      } else {
        await createMutation.mutateAsync({
          name: name.trim(),
          code: code.trim().toUpperCase(),
          description: description.trim() || undefined,
        });
        success("Pool created");
      }
      onClose();
    } catch {
      showError(isEdit ? "Failed to update pool" : "Failed to create pool");
    }
  };

  const isPending = createMutation.isPending || updateMutation.isPending;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md">
        <h3 className="text-lg font-semibold mb-4">
          {isEdit ? "Edit Pool" : "Create Resource Pool"}
        </h3>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="pool_name"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Name
            </label>
            <input
              id="pool_name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              maxLength={100}
              required
            />
          </div>

          {!isEdit && (
            <div>
              <label
                htmlFor="pool_code"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Code
              </label>
              <input
                id="pool_code"
                type="text"
                value={code}
                onChange={(e) => setCode(e.target.value.toUpperCase())}
                className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono"
                maxLength={50}
                pattern="^[A-Z0-9\-_]+$"
                title="Uppercase letters, numbers, hyphens, and underscores only"
                required
              />
            </div>
          )}

          <div>
            <label
              htmlFor="pool_description"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Description (optional)
            </label>
            <textarea
              id="pool_description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              rows={3}
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border rounded hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isPending}
              className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isPending
                ? "Saving..."
                : isEdit
                  ? "Update Pool"
                  : "Create Pool"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
