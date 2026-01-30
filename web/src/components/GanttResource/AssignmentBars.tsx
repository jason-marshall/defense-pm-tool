/**
 * AssignmentBars - Renders assignment bars for a resource lane.
 * Supports drag-and-drop for moving and resizing assignments.
 */

import { useCallback, type KeyboardEvent } from "react";
import { differenceInDays } from "date-fns";
import { useAssignmentDrag } from "@/hooks/useAssignmentDrag";
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
  onAssignmentChange: (change: AssignmentChange) => void;
}

export function AssignmentBars({
  assignments,
  config,
  dayWidth,
  highlightOverallocations,
  onAssignmentClick,
  onAssignmentChange,
}: AssignmentBarsProps) {
  const { isDragging, draggingId, previewDates, handleDragStart } =
    useAssignmentDrag(dayWidth, onAssignmentChange);

  const handleClick = useCallback(
    (assignmentId: string) => {
      // Don't trigger click if we just finished dragging
      if (!isDragging) {
        onAssignmentClick?.(assignmentId);
      }
    },
    [onAssignmentClick, isDragging]
  );

  const handleKeyDown = useCallback(
    (e: KeyboardEvent, assignmentId: string) => {
      if (e.key === "Delete" || e.key === "Backspace") {
        onAssignmentChange({
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
        const isCurrentDragging = draggingId === assignment.assignmentId;

        // Use preview dates if currently dragging this assignment
        const displayStart =
          isCurrentDragging && previewDates
            ? previewDates.start
            : assignment.startDate;
        const displayEnd =
          isCurrentDragging && previewDates
            ? previewDates.end
            : assignment.endDate;

        const startOffset = differenceInDays(displayStart, config.startDate);
        const duration = differenceInDays(displayEnd, displayStart) + 1;
        const left = startOffset * dayWidth;
        const width = duration * dayWidth - 4; // 4px gap between bars

        // Skip bars that are outside the visible range
        if (left + width < 0 || startOffset > 365) {
          return null;
        }

        // Determine bar color
        let barColor = assignment.color || "#3b82f6"; // Default blue
        if (assignment.isCritical) {
          barColor = "#ef4444"; // Red for critical
        }
        if (highlightOverallocations && assignment.isOverallocated) {
          barColor = "#f97316"; // Orange for overallocated
        }

        const barClass = [
          "assignment-bar",
          assignment.isCritical ? "critical" : "",
          highlightOverallocations && assignment.isOverallocated
            ? "overallocated"
            : "",
          isCurrentDragging ? "dragging" : "",
        ]
          .filter(Boolean)
          .join(" ");

        return (
          <div
            key={assignment.assignmentId}
            className={barClass}
            style={{
              left: Math.max(0, left),
              width: Math.max(dayWidth - 4, width),
              backgroundColor: barColor,
            }}
            onClick={() => handleClick(assignment.assignmentId)}
            onKeyDown={(e) => handleKeyDown(e, assignment.assignmentId)}
            tabIndex={0}
            role="button"
            aria-label={`${assignment.activityName} - ${assignment.units * 100}%`}
            data-testid={`assignment-bar-${assignment.assignmentId}`}
          >
            {/* Resize handle - start */}
            <div
              className="resize-handle resize-start"
              onMouseDown={(e) =>
                handleDragStart(e, assignment, "resize-start")
              }
              data-testid={`resize-start-${assignment.assignmentId}`}
            />

            {/* Main bar content - drag to move */}
            <div
              className="assignment-bar-content"
              onMouseDown={(e) => handleDragStart(e, assignment, "move")}
              title={`${assignment.activityCode}: ${assignment.activityName}\nUnits: ${(assignment.units * 100).toFixed(0)}%${
                assignment.isCritical ? "\n(Critical Path)" : ""
              }${assignment.isOverallocated ? "\n(Overallocated)" : ""}\n\nDrag to move • Drag edges to resize`}
            >
              <span className="assignment-bar-label">
                {assignment.activityCode}
              </span>
              <span className="assignment-bar-units">
                {(assignment.units * 100).toFixed(0)}%
              </span>
            </div>

            {/* Resize handle - end */}
            <div
              className="resize-handle resize-end"
              onMouseDown={(e) => handleDragStart(e, assignment, "resize-end")}
              data-testid={`resize-end-${assignment.assignmentId}`}
            />
          </div>
        );
      })}
    </div>
  );
}
