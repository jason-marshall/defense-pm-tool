/**
 * AssignmentBars - Renders assignment bars for a resource lane.
 */

import { useCallback, type KeyboardEvent } from "react";
import { differenceInDays } from "date-fns";
import type {
  AssignmentBar,
  AssignmentChange,
  GanttResourceViewConfig,
} from "@/types/ganttResource";

interface AssignmentBarsProps {
  assignments: AssignmentBar[];
  config: GanttResourceViewConfig;
  dayWidth: number;
  highlightOverallocations: boolean;
  onAssignmentClick?: (assignmentId: string) => void;
  onAssignmentChange?: (change: AssignmentChange) => void;
}

export function AssignmentBars({
  assignments,
  config,
  dayWidth,
  highlightOverallocations,
  onAssignmentClick,
  onAssignmentChange,
}: AssignmentBarsProps) {
  const handleClick = useCallback(
    (assignmentId: string) => {
      onAssignmentClick?.(assignmentId);
    },
    [onAssignmentClick]
  );

  const handleKeyDown = useCallback(
    (e: KeyboardEvent, assignmentId: string) => {
      if (e.key === "Delete" || e.key === "Backspace") {
        onAssignmentChange?.({
          assignmentId,
          type: "delete",
        });
      }
    },
    [onAssignmentChange]
  );

  return (
    <div className="assignment-bars" data-testid="assignment-bars">
      {assignments.map((assignment) => {
        const startOffset = differenceInDays(
          assignment.startDate,
          config.startDate
        );
        const duration =
          differenceInDays(assignment.endDate, assignment.startDate) + 1;
        const left = startOffset * dayWidth;
        const width = duration * dayWidth;

        // Skip bars that are outside the visible range
        if (left + width < 0 || left > config.endDate.getTime()) {
          return null;
        }

        // Determine bar color
        let barColor = assignment.color || "#60a5fa"; // Default blue
        if (assignment.isCritical) {
          barColor = "#ef4444"; // Red for critical
        }
        if (highlightOverallocations && assignment.isOverallocated) {
          barColor = "#f97316"; // Orange for overallocated
        }

        return (
          <div
            key={assignment.assignmentId}
            className={`assignment-bar ${assignment.isCritical ? "critical" : ""} ${
              highlightOverallocations && assignment.isOverallocated
                ? "overallocated"
                : ""
            }`}
            style={{
              left: Math.max(0, left),
              width: Math.max(dayWidth, width),
              backgroundColor: barColor,
            }}
            onClick={() => handleClick(assignment.assignmentId)}
            onKeyDown={(e) => handleKeyDown(e, assignment.assignmentId)}
            tabIndex={0}
            role="button"
            aria-label={`${assignment.activityName} - ${assignment.units * 100}%`}
            title={`${assignment.activityCode}: ${assignment.activityName}\nUnits: ${(assignment.units * 100).toFixed(0)}%${
              assignment.isCritical ? "\n(Critical Path)" : ""
            }${assignment.isOverallocated ? "\n(Overallocated)" : ""}`}
            data-testid={`assignment-bar-${assignment.assignmentId}`}
          >
            <span className="assignment-bar-label">
              {assignment.activityCode}
            </span>
            <span className="assignment-bar-units">
              {(assignment.units * 100).toFixed(0)}%
            </span>
          </div>
        );
      })}
    </div>
  );
}
