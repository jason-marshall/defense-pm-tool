/**
 * Visual critical path display component.
 */

import type { ScheduleResult } from "@/types/schedule";

interface CriticalPathViewProps {
  results: ScheduleResult[];
  criticalPath: string[];
}

export function CriticalPathView({ results, criticalPath }: CriticalPathViewProps) {
  const criticalActivities = results.filter((r) => r.is_critical);

  if (criticalActivities.length === 0) {
    return (
      <div className="bg-white rounded-lg border p-6 text-center text-gray-500">
        No critical path identified. Calculate the schedule first.
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border p-6">
      <h3 className="text-lg font-semibold mb-4">Critical Path</h3>
      <div className="flex items-center gap-2 overflow-x-auto pb-2">
        {criticalActivities.map((activity, idx) => (
          <div key={activity.activity_id} className="flex items-center gap-2">
            <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-2 min-w-fit">
              <div className="text-xs font-mono text-red-600">{activity.activity_code}</div>
              <div className="text-sm font-medium">{activity.activity_name}</div>
              <div className="text-xs text-gray-500">{activity.duration}d</div>
            </div>
            {idx < criticalActivities.length - 1 && (
              <div className="text-gray-300 text-lg shrink-0">&rarr;</div>
            )}
          </div>
        ))}
      </div>
      <div className="mt-3 text-sm text-gray-500">
        {criticalPath.length} activities on critical path
      </div>
    </div>
  );
}
