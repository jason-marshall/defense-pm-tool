/**
 * GanttResourceView - Resource-centric schedule visualization.
 * Shows resources as rows with their assignments displayed as bars across a timeline.
 */

import { useState, useRef, useCallback, useMemo } from "react";
import { eachDayOfInterval, addDays } from "date-fns";
import { useGanttResourceData } from "@/hooks/useGanttResourceData";
import { ResourceSidebar } from "./ResourceSidebar";
import { ResourceTimeline } from "./ResourceTimeline";
import { AssignmentBars } from "./AssignmentBars";
import { UtilizationOverlay } from "./UtilizationOverlay";
import type {
  GanttResourceViewConfig,
  AssignmentChange,
  GanttResourceViewProps,
} from "@/types/ganttResource";
import "./GanttResourceView.css";

export function GanttResourceView({
  programId,
  startDate: propStartDate,
  endDate: propEndDate,
  resourceFilter,
  onAssignmentChange,
  onAssignmentClick,
}: GanttResourceViewProps) {
  // Default to 3-month view - memoize to avoid Date.now() during render
  const { defaultStart, defaultEnd } = useMemo(() => {
    const start = propStartDate || new Date();
    const end = propEndDate || addDays(start, 90);
    return { defaultStart: start, defaultEnd: end };
  }, [propStartDate, propEndDate]);

  const [config, setConfig] = useState<GanttResourceViewConfig>({
    startDate: defaultStart,
    endDate: defaultEnd,
    scale: "week",
    rowHeight: 40,
    headerHeight: 60,
    sidebarWidth: 250,
    showUtilization: true,
    highlightOverallocations: true,
  });

  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<HTMLDivElement>(null);

  const {
    resourceLanes,
    isLoading,
    error,
    updateAssignment,
    isUpdating,
  } = useGanttResourceData(programId, config.startDate, config.endDate);

  // Filter resources if specified
  const filteredLanes = resourceFilter
    ? resourceLanes.filter((lane) => resourceFilter.includes(lane.resourceId))
    : resourceLanes;

  // Calculate timeline width
  const days = eachDayOfInterval({
    start: config.startDate,
    end: config.endDate,
  });
  const dayWidth = config.scale === "day" ? 40 : config.scale === "week" ? 20 : 8;
  const timelineWidth = days.length * dayWidth;

  // Handle assignment changes
  const handleAssignmentChange = useCallback(
    (change: AssignmentChange) => {
      updateAssignment(change);
      onAssignmentChange?.(change);
    },
    [updateAssignment, onAssignmentChange]
  );

  // Handle scale change
  const handleScaleChange = (scale: "day" | "week" | "month") => {
    setConfig((c) => ({ ...c, scale }));
  };

  if (isLoading) {
    return (
      <div className="gantt-resource-loading" data-testid="gantt-loading">
        <div className="gantt-resource-spinner" />
        Loading resource view...
      </div>
    );
  }

  if (error) {
    return (
      <div className="gantt-resource-error" data-testid="gantt-error">
        Error: {(error as Error).message}
      </div>
    );
  }

  return (
    <div
      className="gantt-resource-container"
      ref={containerRef}
      data-testid="gantt-resource-view"
    >
      {/* Toolbar */}
      <div className="gantt-resource-toolbar">
        <div className="scale-selector">
          <button
            className={config.scale === "day" ? "active" : ""}
            onClick={() => handleScaleChange("day")}
            data-testid="scale-day"
          >
            Day
          </button>
          <button
            className={config.scale === "week" ? "active" : ""}
            onClick={() => handleScaleChange("week")}
            data-testid="scale-week"
          >
            Week
          </button>
          <button
            className={config.scale === "month" ? "active" : ""}
            onClick={() => handleScaleChange("month")}
            data-testid="scale-month"
          >
            Month
          </button>
        </div>
        <label className="utilization-toggle">
          <input
            type="checkbox"
            checked={config.showUtilization}
            onChange={(e) =>
              setConfig((c) => ({ ...c, showUtilization: e.target.checked }))
            }
            data-testid="toggle-utilization"
          />
          Show Utilization
        </label>
        <label className="overallocation-toggle">
          <input
            type="checkbox"
            checked={config.highlightOverallocations}
            onChange={(e) =>
              setConfig((c) => ({
                ...c,
                highlightOverallocations: e.target.checked,
              }))
            }
            data-testid="toggle-overallocation"
          />
          Highlight Overallocations
        </label>
      </div>

      {/* Main content */}
      <div className="gantt-resource-content">
        {/* Sidebar */}
        <div
          className="gantt-resource-sidebar"
          style={{ width: config.sidebarWidth }}
        >
          <ResourceSidebar
            resources={filteredLanes}
            rowHeight={config.rowHeight}
            headerHeight={config.headerHeight}
          />
        </div>

        {/* Chart area */}
        <div
          className="gantt-resource-chart"
          ref={chartRef}
          style={{ width: `calc(100% - ${config.sidebarWidth}px)` }}
        >
          <ResourceTimeline config={config} width={timelineWidth} />
          <div
            className="gantt-resource-lanes"
            style={{ width: timelineWidth }}
          >
            {filteredLanes.map((lane, index) => (
              <div
                key={lane.resourceId}
                className="gantt-resource-lane"
                style={{
                  height: config.rowHeight,
                  top: index * config.rowHeight,
                }}
                data-testid={`resource-lane-${lane.resourceId}`}
              >
                {config.showUtilization && (
                  <UtilizationOverlay
                    lane={lane}
                    config={config}
                    dayWidth={dayWidth}
                  />
                )}
                <AssignmentBars
                  assignments={lane.assignments}
                  config={config}
                  dayWidth={dayWidth}
                  highlightOverallocations={config.highlightOverallocations}
                  onAssignmentClick={onAssignmentClick}
                  onAssignmentChange={handleAssignmentChange}
                />
              </div>
            ))}
          </div>
        </div>
      </div>

      {isUpdating && (
        <div className="gantt-resource-updating" data-testid="gantt-updating">
          Saving...
        </div>
      )}
    </div>
  );
}
