/**
 * UtilizationOverlay - Shows daily utilization as background color intensity.
 */

import { eachDayOfInterval } from "date-fns";
import type {
  ResourceLane,
  GanttResourceViewConfig,
} from "@/types/ganttResource";

interface UtilizationOverlayProps {
  lane: ResourceLane;
  config: GanttResourceViewConfig;
  dayWidth: number;
}

function getUtilizationColor(utilization: number, capacity: number): string {
  const percentage = capacity > 0 ? utilization / capacity : 0;

  if (percentage === 0) {
    return "transparent";
  }
  if (percentage <= 0.5) {
    // Light green for under-utilized
    return `rgba(34, 197, 94, ${percentage * 0.3})`;
  }
  if (percentage <= 0.8) {
    // Yellow for moderate
    return `rgba(234, 179, 8, ${percentage * 0.4})`;
  }
  if (percentage <= 1.0) {
    // Light orange for near capacity
    return `rgba(249, 115, 22, ${percentage * 0.4})`;
  }
  // Red for overallocated
  return `rgba(239, 68, 68, ${Math.min(percentage * 0.5, 0.6)})`;
}

export function UtilizationOverlay({
  lane,
  config,
  dayWidth,
}: UtilizationOverlayProps) {
  const days = eachDayOfInterval({
    start: config.startDate,
    end: config.endDate,
  });

  return (
    <div
      className="utilization-overlay"
      data-testid={`utilization-overlay-${lane.resourceId}`}
    >
      {days.map((day, index) => {
        const dateKey = day.toISOString().split("T")[0];
        const utilization = lane.dailyUtilization.get(dateKey) || 0;
        const color = getUtilizationColor(utilization, lane.capacityPerDay);

        return (
          <div
            key={index}
            className="utilization-cell"
            style={{
              left: index * dayWidth,
              width: dayWidth,
              backgroundColor: color,
            }}
            title={`${dateKey}: ${utilization.toFixed(1)}h / ${lane.capacityPerDay}h (${(
              (utilization / lane.capacityPerDay) *
              100
            ).toFixed(0)}%)`}
          />
        );
      })}
    </div>
  );
}
