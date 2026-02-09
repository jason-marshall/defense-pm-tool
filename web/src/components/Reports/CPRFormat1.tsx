/**
 * CPR Format 1 - WBS summary table with color-coded variances.
 */

import { useCPRFormat1 } from "@/hooks/useReports";

interface CPRFormat1Props {
  programId: string;
}

function varianceClass(value: string): string {
  const num = parseFloat(value);
  if (num > 0) return "text-green-600";
  if (num < 0) return "text-red-600";
  return "text-gray-600";
}

export function CPRFormat1({ programId }: CPRFormat1Props) {
  const { data, isLoading, error } = useCPRFormat1(programId);

  if (isLoading) return <div className="p-4 text-gray-500">Loading Format 1...</div>;
  if (error) return <div className="p-4 text-red-500">Error loading report</div>;
  if (!data) return <div className="p-4 text-gray-500">No report data</div>;

  return (
    <div className="bg-white rounded-lg border overflow-x-auto">
      <div className="p-4 border-b">
        <h3 className="font-semibold">{data.program_name}</h3>
        <p className="text-sm text-gray-500">Period: {data.reporting_period}</p>
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-gray-50 border-b">
            <th className="text-left px-3 py-2 text-xs font-medium text-gray-500">WBS</th>
            <th className="text-left px-3 py-2 text-xs font-medium text-gray-500">Name</th>
            <th className="text-right px-3 py-2 text-xs font-medium text-gray-500">BCWS</th>
            <th className="text-right px-3 py-2 text-xs font-medium text-gray-500">BCWP</th>
            <th className="text-right px-3 py-2 text-xs font-medium text-gray-500">ACWP</th>
            <th className="text-right px-3 py-2 text-xs font-medium text-gray-500">CV</th>
            <th className="text-right px-3 py-2 text-xs font-medium text-gray-500">SV</th>
          </tr>
        </thead>
        <tbody>
          {data.rows.map((row, i) => (
            <tr key={i} className="border-b hover:bg-gray-50">
              <td className="px-3 py-2 font-mono">{row.wbs_code}</td>
              <td className="px-3 py-2">{row.wbs_name}</td>
              <td className="px-3 py-2 text-right">${Number(row.bcws).toLocaleString()}</td>
              <td className="px-3 py-2 text-right">${Number(row.bcwp).toLocaleString()}</td>
              <td className="px-3 py-2 text-right">${Number(row.acwp).toLocaleString()}</td>
              <td className={`px-3 py-2 text-right font-medium ${varianceClass(row.cv)}`}>
                ${Number(row.cv).toLocaleString()}
              </td>
              <td className={`px-3 py-2 text-right font-medium ${varianceClass(row.sv)}`}>
                ${Number(row.sv).toLocaleString()}
              </td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr className="bg-gray-100 font-semibold">
            <td className="px-3 py-2" colSpan={2}>Total</td>
            <td className="px-3 py-2 text-right">${Number(data.totals.bcws).toLocaleString()}</td>
            <td className="px-3 py-2 text-right">${Number(data.totals.bcwp).toLocaleString()}</td>
            <td className="px-3 py-2 text-right">${Number(data.totals.acwp).toLocaleString()}</td>
            <td className={`px-3 py-2 text-right ${varianceClass(data.totals.cv)}`}>
              ${Number(data.totals.cv).toLocaleString()}
            </td>
            <td className={`px-3 py-2 text-right ${varianceClass(data.totals.sv)}`}>
              ${Number(data.totals.sv).toLocaleString()}
            </td>
          </tr>
        </tfoot>
      </table>
    </div>
  );
}
