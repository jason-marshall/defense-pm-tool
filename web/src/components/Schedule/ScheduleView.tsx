/**
 * Schedule view showing CPM results with critical path highlighting.
 */

import { Calculator, AlertTriangle } from "lucide-react";
import { useScheduleResults, useCalculateSchedule } from "@/hooks/useSchedule";
import { useToast } from "@/components/Toast";

interface ScheduleViewProps {
  programId: string;
}

export function ScheduleView({ programId }: ScheduleViewProps) {
  const { data, isLoading, error, refetch } = useScheduleResults(programId);
  const calculateMutation = useCalculateSchedule();
  const toast = useToast();

  const handleCalculate = async () => {
    try {
      await calculateMutation.mutateAsync(programId);
      toast.success("Schedule calculated successfully");
      refetch();
    } catch {
      toast.error("Failed to calculate schedule");
    }
  };

  if (isLoading) return <div className="p-4 text-gray-500">Loading schedule...</div>;

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold">Schedule (CPM)</h2>
        <button
          onClick={handleCalculate}
          disabled={calculateMutation.isPending}
          className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 text-sm disabled:opacity-50"
        >
          <Calculator size={16} />
          {calculateMutation.isPending ? "Calculating..." : "Calculate Schedule"}
        </button>
      </div>

      {error || !data ? (
        <div className="bg-white rounded-lg border p-8 text-center text-gray-500">
          <p>No schedule data available. Click "Calculate Schedule" to run CPM.</p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-3 gap-4 mb-4">
            <div className="bg-white rounded-lg border p-4">
              <div className="text-sm text-gray-500">Project Duration</div>
              <div className="text-2xl font-bold">{data.project_duration} days</div>
            </div>
            <div className="bg-white rounded-lg border p-4">
              <div className="text-sm text-gray-500">Total Activities</div>
              <div className="text-2xl font-bold">{data.results.length}</div>
            </div>
            <div className="bg-white rounded-lg border p-4">
              <div className="text-sm text-gray-500">Critical Activities</div>
              <div className="text-2xl font-bold text-red-600">
                {data.results.filter((r) => r.is_critical).length}
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg border overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b">
                  <th className="text-left px-3 py-2 text-xs font-medium text-gray-500 uppercase">Code</th>
                  <th className="text-left px-3 py-2 text-xs font-medium text-gray-500 uppercase">Name</th>
                  <th className="text-right px-3 py-2 text-xs font-medium text-gray-500 uppercase">Duration</th>
                  <th className="text-right px-3 py-2 text-xs font-medium text-gray-500 uppercase">ES</th>
                  <th className="text-right px-3 py-2 text-xs font-medium text-gray-500 uppercase">EF</th>
                  <th className="text-right px-3 py-2 text-xs font-medium text-gray-500 uppercase">LS</th>
                  <th className="text-right px-3 py-2 text-xs font-medium text-gray-500 uppercase">LF</th>
                  <th className="text-right px-3 py-2 text-xs font-medium text-gray-500 uppercase">Total Float</th>
                  <th className="text-right px-3 py-2 text-xs font-medium text-gray-500 uppercase">Free Float</th>
                  <th className="text-center px-3 py-2 text-xs font-medium text-gray-500 uppercase">Critical</th>
                </tr>
              </thead>
              <tbody>
                {data.results.map((result) => (
                  <tr
                    key={result.activity_id}
                    className={`border-b last:border-b-0 ${
                      result.is_critical ? "bg-red-50" : "hover:bg-gray-50"
                    }`}
                  >
                    <td className="px-3 py-2 font-mono">{result.activity_code}</td>
                    <td className="px-3 py-2">{result.activity_name}</td>
                    <td className="px-3 py-2 text-right">{result.duration}</td>
                    <td className="px-3 py-2 text-right">{result.early_start}</td>
                    <td className="px-3 py-2 text-right">{result.early_finish}</td>
                    <td className="px-3 py-2 text-right">{result.late_start}</td>
                    <td className="px-3 py-2 text-right">{result.late_finish}</td>
                    <td className="px-3 py-2 text-right">
                      <span className={result.total_float === 0 ? "text-red-600 font-bold" : ""}>
                        {result.total_float}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-right">{result.free_float}</td>
                    <td className="px-3 py-2 text-center">
                      {result.is_critical && <AlertTriangle size={14} className="inline text-red-500" />}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
