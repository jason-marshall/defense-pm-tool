/**
 * PoolAvailabilityView shows availability and conflicts for a resource pool.
 */

import { useState } from "react";
import { usePoolAvailability } from "@/hooks/useResourcePools";
import { AlertTriangle, Calendar } from "lucide-react";

interface PoolAvailabilityViewProps {
  poolId: string;
  poolName: string;
}

export function PoolAvailabilityView({
  poolId,
  poolName,
}: PoolAvailabilityViewProps) {
  const today = new Date().toISOString().split("T")[0];
  const defaultEnd = new Date(Date.now() + 30 * 86400000)
    .toISOString()
    .split("T")[0];

  const [startDate, setStartDate] = useState(today);
  const [endDate, setEndDate] = useState(defaultEnd);

  const { data, isLoading, error } = usePoolAvailability(
    poolId,
    startDate,
    endDate
  );

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold flex items-center gap-2 mb-4">
        <Calendar size={20} />
        Availability - {poolName}
      </h3>

      <div className="flex gap-4 mb-4">
        <div>
          <label
            htmlFor="avail_start"
            className="block text-sm text-gray-600 mb-1"
          >
            Start Date
          </label>
          <input
            id="avail_start"
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label
            htmlFor="avail_end"
            className="block text-sm text-gray-600 mb-1"
          >
            End Date
          </label>
          <input
            id="avail_end"
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      {isLoading && (
        <p className="text-gray-500 text-center py-4">
          Loading availability...
        </p>
      )}

      {error && (
        <p className="text-red-500 text-center py-4">
          Failed to load availability
        </p>
      )}

      {data && (
        <>
          {/* Conflicts */}
          {data.conflict_count > 0 && (
            <div className="bg-yellow-50 border border-yellow-200 rounded p-3 mb-4">
              <div className="flex items-center gap-2 text-yellow-700 font-medium mb-2">
                <AlertTriangle size={16} />
                {data.conflict_count} Conflict{data.conflict_count !== 1 ? "s" : ""} Found
              </div>
              <div className="space-y-2">
                {data.conflicts.map((conflict, idx) => (
                  <div key={idx} className="text-sm text-yellow-600">
                    <span className="font-medium">{conflict.resource_name}</span>{" "}
                    on {conflict.conflict_date} — {conflict.overallocation_hours}h
                    overallocated across{" "}
                    {conflict.programs_involved.join(", ")}
                  </div>
                ))}
              </div>
            </div>
          )}

          {data.conflict_count === 0 && (
            <div className="bg-green-50 rounded p-4 text-center text-green-700 mb-4">
              No conflicts found in the selected date range
            </div>
          )}

          {/* Resource List */}
          {data.resources.length > 0 && (
            <div className="border rounded overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50">
                    <th className="p-2 text-left">Resource</th>
                    <th className="p-2 text-right">Available Hours</th>
                    <th className="p-2 text-right">Assigned Hours</th>
                  </tr>
                </thead>
                <tbody>
                  {data.resources.map((res) => (
                    <tr
                      key={res.resource_id}
                      className="border-t hover:bg-gray-50"
                    >
                      <td className="p-2">{res.resource_name}</td>
                      <td className="p-2 text-right">{res.available_hours}</td>
                      <td className="p-2 text-right">{res.assigned_hours}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}
