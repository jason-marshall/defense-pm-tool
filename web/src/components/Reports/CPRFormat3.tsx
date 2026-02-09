/**
 * CPR Format 3 - Time-phased PMB display.
 */

import { useCPRFormat3 } from "@/hooks/useReports";

interface CPRFormat3Props {
  programId: string;
}

export function CPRFormat3({ programId }: CPRFormat3Props) {
  const { data, isLoading, error } = useCPRFormat3(programId);

  if (isLoading) return <div className="p-4 text-gray-500">Loading Format 3...</div>;
  if (error) return <div className="p-4 text-red-500">Error loading report</div>;
  if (!data || data.periods.length === 0) return <div className="p-4 text-gray-500">No time-phased data</div>;

  return (
    <div className="bg-white rounded-lg border overflow-x-auto">
      <div className="p-4 border-b">
        <h3 className="font-semibold">{data.program_name}</h3>
        <p className="text-sm text-gray-500">Time-Phased Performance Measurement Baseline</p>
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-gray-50 border-b">
            <th className="text-left px-3 py-2 text-xs font-medium text-gray-500">Period</th>
            <th className="text-right px-3 py-2 text-xs font-medium text-gray-500">BCWS</th>
            <th className="text-right px-3 py-2 text-xs font-medium text-gray-500">BCWP</th>
            <th className="text-right px-3 py-2 text-xs font-medium text-gray-500">ACWP</th>
          </tr>
        </thead>
        <tbody>
          {data.periods.map((period, i) => (
            <tr key={i} className="border-b hover:bg-gray-50">
              <td className="px-3 py-2">{period.period}</td>
              <td className="px-3 py-2 text-right">${Number(period.bcws).toLocaleString()}</td>
              <td className="px-3 py-2 text-right">${Number(period.bcwp).toLocaleString()}</td>
              <td className="px-3 py-2 text-right">${Number(period.acwp).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
