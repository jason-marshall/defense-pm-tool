/**
 * Program overview tab showing metadata and summary stats.
 */

import type { Program } from "@/types/program";

interface ProgramOverviewProps {
  program: Program;
}

const statusColors: Record<string, string> = {
  PLANNING: "bg-blue-100 text-blue-700",
  ACTIVE: "bg-green-100 text-green-700",
  ON_HOLD: "bg-yellow-100 text-yellow-700",
  COMPLETED: "bg-gray-100 text-gray-600",
  CANCELLED: "bg-red-100 text-red-700",
};

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "-";
  return new Date(dateStr).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function ProgramOverview({ program }: ProgramOverviewProps) {
  return (
    <div className="space-y-6">
      <div className="grid md:grid-cols-2 gap-6">
        {/* Program Info */}
        <div className="bg-white rounded-lg border p-6">
          <h3 className="text-sm font-medium text-gray-500 uppercase mb-4">
            Program Information
          </h3>
          <dl className="space-y-3">
            <div className="flex justify-between">
              <dt className="text-sm text-gray-500">Code</dt>
              <dd className="text-sm font-mono font-medium">{program.code}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-sm text-gray-500">Status</dt>
              <dd>
                <span
                  className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                    statusColors[program.status] || "bg-gray-100"
                  }`}
                >
                  {program.status.replace("_", " ")}
                </span>
              </dd>
            </div>
            {program.description && (
              <div>
                <dt className="text-sm text-gray-500 mb-1">Description</dt>
                <dd className="text-sm text-gray-700">{program.description}</dd>
              </div>
            )}
            {program.contract_number && (
              <div className="flex justify-between">
                <dt className="text-sm text-gray-500">Contract</dt>
                <dd className="text-sm">{program.contract_number}</dd>
              </div>
            )}
            {program.contract_type && (
              <div className="flex justify-between">
                <dt className="text-sm text-gray-500">Contract Type</dt>
                <dd className="text-sm">{program.contract_type}</dd>
              </div>
            )}
          </dl>
        </div>

        {/* Schedule & Budget */}
        <div className="bg-white rounded-lg border p-6">
          <h3 className="text-sm font-medium text-gray-500 uppercase mb-4">
            Schedule & Budget
          </h3>
          <dl className="space-y-3">
            <div className="flex justify-between">
              <dt className="text-sm text-gray-500">Planned Start</dt>
              <dd className="text-sm">{formatDate(program.planned_start_date)}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-sm text-gray-500">Planned End</dt>
              <dd className="text-sm">{formatDate(program.planned_end_date)}</dd>
            </div>
            {program.actual_start_date && (
              <div className="flex justify-between">
                <dt className="text-sm text-gray-500">Actual Start</dt>
                <dd className="text-sm">{formatDate(program.actual_start_date)}</dd>
              </div>
            )}
            {program.actual_end_date && (
              <div className="flex justify-between">
                <dt className="text-sm text-gray-500">Actual End</dt>
                <dd className="text-sm">{formatDate(program.actual_end_date)}</dd>
              </div>
            )}
            <div className="flex justify-between">
              <dt className="text-sm text-gray-500">Budget at Completion</dt>
              <dd className="text-sm font-medium">
                {program.budget_at_completion
                  ? `$${Number(program.budget_at_completion).toLocaleString()}`
                  : "-"}
              </dd>
            </div>
          </dl>
        </div>
      </div>
    </div>
  );
}
