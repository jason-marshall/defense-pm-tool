/**
 * PoolMembersPanel modal for managing pool member resources.
 */

import { useState } from "react";
import {
  usePoolMembers,
  useAddPoolMember,
  useRemovePoolMember,
} from "@/hooks/useResourcePools";
import { useResources } from "@/hooks/useResources";
import { useToast } from "@/components/Toast";
import { Plus, Trash2 } from "lucide-react";

interface PoolMembersPanelProps {
  poolId: string;
  poolName: string;
  programId: string;
  onClose: () => void;
}

export function PoolMembersPanel({
  poolId,
  poolName,
  programId,
  onClose,
}: PoolMembersPanelProps) {
  const { data: members, isLoading } = usePoolMembers(poolId);
  const { data: resources } = useResources(programId);
  const addMember = useAddPoolMember();
  const removeMember = useRemovePoolMember();
  const { success, error: showError } = useToast();

  const [selectedResource, setSelectedResource] = useState("");
  const [allocation, setAllocation] = useState("100");

  const handleAdd = async () => {
    if (!selectedResource) {
      showError("Select a resource");
      return;
    }

    try {
      await addMember.mutateAsync({
        poolId,
        data: {
          resource_id: selectedResource,
          allocation_percentage: parseFloat(allocation),
        },
      });
      success("Member added to pool");
      setSelectedResource("");
    } catch {
      showError("Failed to add member");
    }
  };

  const handleRemove = async (memberId: string) => {
    try {
      await removeMember.mutateAsync({ poolId, memberId });
      success("Member removed from pool");
    } catch {
      showError("Failed to remove member");
    }
  };

  const memberResourceIds = new Set(
    members?.map((m) => m.resource_id) || []
  );
  const availableResources =
    resources?.items.filter((r) => !memberResourceIds.has(r.id)) || [];

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-lg">
        <h3 className="text-lg font-semibold mb-4">
          Members - {poolName}
        </h3>

        {/* Add Member Form */}
        <div className="flex gap-2 items-end mb-4">
          <div className="flex-1">
            <label
              htmlFor="resource_select"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Resource
            </label>
            <select
              id="resource_select"
              value={selectedResource}
              onChange={(e) => setSelectedResource(e.target.value)}
              className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Select resource...</option>
              {availableResources.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.code} - {r.name}
                </option>
              ))}
            </select>
          </div>
          <div className="w-24">
            <label
              htmlFor="allocation_pct"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Allocation %
            </label>
            <input
              id="allocation_pct"
              type="number"
              value={allocation}
              onChange={(e) => setAllocation(e.target.value)}
              className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              min="0"
              max="100"
            />
          </div>
          <button
            onClick={handleAdd}
            disabled={addMember.isPending || !selectedResource}
            className="bg-blue-500 text-white px-3 py-2 rounded hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1 transition-colors"
          >
            <Plus size={14} />
            Add
          </button>
        </div>

        {/* Members List */}
        {isLoading ? (
          <p className="text-gray-500 text-center py-4">Loading members...</p>
        ) : members && members.length > 0 ? (
          <div className="border rounded overflow-hidden mb-4">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50">
                  <th className="p-2 text-left">Resource ID</th>
                  <th className="p-2 text-right">Allocation</th>
                  <th className="p-2 text-center">Status</th>
                  <th className="p-2 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {members.map((member) => (
                  <tr key={member.id} className="border-t hover:bg-gray-50">
                    <td className="p-2 font-mono text-xs">
                      {member.resource_id.substring(0, 8)}...
                    </td>
                    <td className="p-2 text-right">
                      {parseFloat(member.allocation_percentage)}%
                    </td>
                    <td className="p-2 text-center">
                      <span
                        className={`inline-block px-2 py-0.5 rounded-full text-xs ${
                          member.is_active
                            ? "bg-green-100 text-green-700"
                            : "bg-gray-100 text-gray-500"
                        }`}
                      >
                        {member.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td className="p-2 text-right">
                      <button
                        onClick={() => handleRemove(member.id)}
                        className="p-1 text-gray-400 hover:text-red-600"
                        title="Remove"
                        aria-label="Remove member"
                      >
                        <Trash2 size={14} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-gray-500 text-center py-4">
            No members in this pool
          </p>
        )}

        <div className="flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 border rounded hover:bg-gray-50 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
