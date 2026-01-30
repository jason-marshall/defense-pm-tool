/**
 * Types for the GanttResourceView component.
 * Resource-centric schedule visualization types.
 */

export interface ResourceLane {
  resourceId: string;
  resourceCode: string;
  resourceName: string;
  resourceType: "labor" | "equipment" | "material";
  capacityPerDay: number;
  assignments: AssignmentBar[];
  dailyUtilization: Map<string, number>; // date -> utilization %
}

export interface AssignmentBar {
  assignmentId: string;
  activityId: string;
  activityCode: string;
  activityName: string;
  startDate: Date;
  endDate: Date;
  units: number; // allocation %
  isCritical: boolean;
  isOverallocated: boolean;
  color?: string;
}

export interface GanttResourceViewConfig {
  startDate: Date;
  endDate: Date;
  scale: "day" | "week" | "month";
  rowHeight: number;
  headerHeight: number;
  sidebarWidth: number;
  showUtilization: boolean;
  highlightOverallocations: boolean;
}

export interface AssignmentChange {
  assignmentId: string;
  type: "move" | "resize" | "delete";
  newStartDate?: Date;
  newEndDate?: Date;
  newUnits?: number;
}

export interface GanttResourceViewProps {
  programId: string;
  startDate?: Date;
  endDate?: Date;
  resourceFilter?: string[];
  onAssignmentChange?: (change: AssignmentChange) => void;
  onAssignmentClick?: (assignmentId: string) => void;
}
