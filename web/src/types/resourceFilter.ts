/**
 * Types for resource filtering in GanttResourceView.
 */

export interface ResourceFilterState {
  searchTerm: string;
  resourceTypes: ("labor" | "equipment" | "material")[];
  showOnlyOverallocated: boolean;
  showOnlyWithAssignments: boolean;
  poolIds: string[];
}

export const defaultFilterState: ResourceFilterState = {
  searchTerm: "",
  resourceTypes: ["labor", "equipment", "material"],
  showOnlyOverallocated: false,
  showOnlyWithAssignments: false,
  poolIds: [],
};

export interface ResourcePool {
  id: string;
  name: string;
}

export interface FilterStats {
  total: number;
  labor: number;
  equipment: number;
  material: number;
  overallocated: number;
  withAssignments: number;
}
