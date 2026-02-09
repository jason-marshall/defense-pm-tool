/**
 * ResourcePoolList displays all accessible resource pools with CRUD actions.
 */

import { useState } from "react";
import { useResourcePools, useDeletePool } from "@/hooks/useResourcePools";
import { useToast } from "@/components/Toast";
import { Plus, Trash2, Edit2, Users } from "lucide-react";
import { ResourcePoolForm } from "./ResourcePoolForm";
import { PoolMembersPanel } from "./PoolMembersPanel";
import type { ResourcePoolResponse } from "@/types/resourcePool";

interface ResourcePoolListProps {
  programId: string;
}

export function ResourcePoolList({ programId }: ResourcePoolListProps) {
  const { data: pools, isLoading, error } = useResourcePools();
  const deleteMutation = useDeletePool();
  const { success, error: showError } = useToast();
  const [showForm, setShowForm] = useState(false);
  const [editPool, setEditPool] = useState<ResourcePoolResponse | null>(null);
  const [membersPool, setMembersPool] = useState<ResourcePoolResponse | null>(
    null
  );

  const handleDelete = async (poolId: string) => {
    try {
      await deleteMutation.mutateAsync(poolId);
      success("Pool deleted");
    } catch {
      showError("Failed to delete pool");
    }
  };

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg border p-6 text-center text-gray-500">
        Loading resource pools...
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg border p-6 text-center text-red-500">
        Failed to load resource pools
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold">Resource Pools</h3>
        <button
          onClick={() => setShowForm(true)}
          className="bg-blue-500 text-white px-3 py-1.5 rounded hover:bg-blue-600 flex items-center gap-1 text-sm transition-colors"
        >
          <Plus size={14} />
          New Pool
        </button>
      </div>

      {pools && pools.length > 0 ? (
        <div className="border rounded overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50">
                <th className="p-2 text-left">Code</th>
                <th className="p-2 text-left">Name</th>
                <th className="p-2 text-left">Description</th>
                <th className="p-2 text-center">Status</th>
                <th className="p-2 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {pools.map((pool) => (
                <tr key={pool.id} className="border-t hover:bg-gray-50">
                  <td className="p-2 font-mono text-xs">{pool.code}</td>
                  <td className="p-2 font-medium">{pool.name}</td>
                  <td className="p-2 text-gray-500 max-w-[200px] truncate">
                    {pool.description || "-"}
                  </td>
                  <td className="p-2 text-center">
                    <span
                      className={`inline-block px-2 py-0.5 rounded-full text-xs ${
                        pool.is_active
                          ? "bg-green-100 text-green-700"
                          : "bg-gray-100 text-gray-500"
                      }`}
                    >
                      {pool.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                  <td className="p-2 text-right">
                    <div className="flex justify-end gap-1">
                      <button
                        onClick={() => setMembersPool(pool)}
                        className="p-1 text-gray-400 hover:text-blue-600"
                        title="Manage Members"
                      >
                        <Users size={14} />
                      </button>
                      <button
                        onClick={() => setEditPool(pool)}
                        className="p-1 text-gray-400 hover:text-blue-600"
                        title="Edit"
                      >
                        <Edit2 size={14} />
                      </button>
                      <button
                        onClick={() => handleDelete(pool.id)}
                        className="p-1 text-gray-400 hover:text-red-600"
                        title="Delete"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="text-center py-6 bg-gray-50 rounded">
          <p className="text-gray-500">No resource pools found</p>
          <p className="text-sm text-gray-400 mt-1">
            Create a pool to share resources across programs
          </p>
        </div>
      )}

      {(showForm || editPool) && (
        <ResourcePoolForm
          pool={editPool}
          onClose={() => {
            setShowForm(false);
            setEditPool(null);
          }}
        />
      )}

      {membersPool && (
        <PoolMembersPanel
          poolId={membersPool.id}
          poolName={membersPool.name}
          programId={programId}
          onClose={() => setMembersPool(null)}
        />
      )}
    </div>
  );
}
