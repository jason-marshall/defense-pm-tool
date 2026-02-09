/**
 * CPR Format 5 - Variance explanations.
 */

import { useCPRFormat5 } from "@/hooks/useReports";

interface CPRFormat5Props {
  programId: string;
}

export function CPRFormat5({ programId }: CPRFormat5Props) {
  const { data, isLoading, error } = useCPRFormat5(programId);

  if (isLoading) return <div className="p-4 text-gray-500">Loading Format 5...</div>;
  if (error) return <div className="p-4 text-red-500">Error loading report</div>;
  if (!data || data.items.length === 0) return <div className="p-4 text-gray-500">No variance explanations</div>;

  return (
    <div className="bg-white rounded-lg border">
      <div className="p-4 border-b">
        <h3 className="font-semibold">{data.program_name}</h3>
        <p className="text-sm text-gray-500">Variance Analysis Report</p>
      </div>
      <div className="divide-y">
        {data.items.map((item, i) => (
          <div key={i} className="p-4">
            <div className="flex items-center gap-3 mb-2">
              <span className="font-mono text-sm text-gray-500">{item.wbs_code}</span>
              <span className="font-medium">{item.wbs_name}</span>
              <span className={`text-sm font-medium ${
                item.variance_type === "cost" ? "text-red-600" : "text-amber-600"
              }`}>
                {item.variance_type.toUpperCase()}: ${Number(item.variance_amount).toLocaleString()}
              </span>
            </div>
            <p className="text-sm text-gray-700 mb-1">{item.explanation}</p>
            {item.corrective_action && (
              <p className="text-sm text-blue-700">
                <span className="font-medium">Corrective Action:</span> {item.corrective_action}
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
