/**
 * Hook for managing assignment drag-and-drop state.
 * Supports move (change dates) and resize (change duration) operations.
 */

import { useState, useCallback, useEffect, type MouseEvent } from "react";
import type { AssignmentBar, AssignmentChange } from "@/types/ganttResource";

interface DragState {
  assignmentId: string;
  type: "move" | "resize-start" | "resize-end";
  initialX: number;
  initialStart: Date;
  initialEnd: Date;
  currentX: number;
}

export function useAssignmentDrag(
  dayWidth: number,
  onAssignmentChange: (change: AssignmentChange) => void
) {
  const [dragState, setDragState] = useState<DragState | null>(null);
  const [previewDates, setPreviewDates] = useState<{
    start: Date;
    end: Date;
  } | null>(null);

  const handleDragStart = useCallback(
    (
      e: MouseEvent,
      assignment: AssignmentBar,
      type: "move" | "resize-start" | "resize-end"
    ) => {
      e.preventDefault();
      e.stopPropagation();

      setDragState({
        assignmentId: assignment.assignmentId,
        type,
        initialX: e.clientX,
        initialStart: new Date(assignment.startDate),
        initialEnd: new Date(assignment.endDate),
        currentX: e.clientX,
      });

      // Set initial preview
      setPreviewDates({
        start: new Date(assignment.startDate),
        end: new Date(assignment.endDate),
      });
    },
    []
  );

  const handleDragMove = useCallback(
    (e: globalThis.MouseEvent) => {
      if (!dragState) return;

      const deltaX = e.clientX - dragState.initialX;
      const deltaDays = Math.round(deltaX / dayWidth);

      const newStart = new Date(dragState.initialStart);
      const newEnd = new Date(dragState.initialEnd);

      switch (dragState.type) {
        case "move":
          newStart.setDate(newStart.getDate() + deltaDays);
          newEnd.setDate(newEnd.getDate() + deltaDays);
          break;
        case "resize-start":
          newStart.setDate(newStart.getDate() + deltaDays);
          // Ensure start doesn't go past end
          if (newStart >= newEnd) {
            newStart.setTime(newEnd.getTime() - 86400000); // 1 day before end
          }
          break;
        case "resize-end":
          newEnd.setDate(newEnd.getDate() + deltaDays);
          // Ensure end doesn't go before start
          if (newEnd <= newStart) {
            newEnd.setTime(newStart.getTime() + 86400000); // 1 day after start
          }
          break;
      }

      setPreviewDates({ start: newStart, end: newEnd });
      setDragState((prev) => (prev ? { ...prev, currentX: e.clientX } : null));
    },
    [dragState, dayWidth]
  );

  const handleDragEnd = useCallback(() => {
    if (dragState && previewDates) {
      // Only fire change if dates actually changed
      const startChanged =
        previewDates.start.getTime() !== dragState.initialStart.getTime();
      const endChanged =
        previewDates.end.getTime() !== dragState.initialEnd.getTime();

      if (startChanged || endChanged) {
        onAssignmentChange({
          assignmentId: dragState.assignmentId,
          type: dragState.type === "move" ? "move" : "resize",
          newStartDate: previewDates.start,
          newEndDate: previewDates.end,
        });
      }
    }

    setDragState(null);
    setPreviewDates(null);
  }, [dragState, previewDates, onAssignmentChange]);

  // Global mouse event handlers
  useEffect(() => {
    if (dragState) {
      window.addEventListener("mousemove", handleDragMove);
      window.addEventListener("mouseup", handleDragEnd);
      document.body.style.cursor =
        dragState.type === "move" ? "grabbing" : "ew-resize";
      document.body.style.userSelect = "none";

      return () => {
        window.removeEventListener("mousemove", handleDragMove);
        window.removeEventListener("mouseup", handleDragEnd);
        document.body.style.cursor = "";
        document.body.style.userSelect = "";
      };
    }
  }, [dragState, handleDragMove, handleDragEnd]);

  return {
    isDragging: !!dragState,
    draggingId: dragState?.assignmentId || null,
    dragType: dragState?.type || null,
    previewDates,
    handleDragStart,
  };
}
