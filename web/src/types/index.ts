/**
 * TypeScript type definitions for the Defense PM Tool frontend.
 */

// API Response types
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
}

// Program types
export interface Program {
  id: string;
  name: string;
  code: string;
  description: string | null;
  plannedStartDate: string;
  plannedEndDate: string;
  actualStartDate: string | null;
  actualEndDate: string | null;
  budgetAtCompletion: string;
  contractNumber: string | null;
  contractType: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface ProgramCreate {
  name: string;
  code: string;
  description?: string;
  plannedStartDate: string;
  plannedEndDate: string;
  budgetAtCompletion?: string;
  contractNumber?: string;
  contractType?: string;
}

// Activity types
export interface Activity {
  id: string;
  programId: string;
  wbsElementId: string | null;
  name: string;
  code: string;
  description: string | null;
  duration: number;
  remainingDuration: number | null;
  earlyStart: string | null;
  earlyFinish: string | null;
  lateStart: string | null;
  lateFinish: string | null;
  actualStart: string | null;
  actualFinish: string | null;
  totalFloat: number | null;
  freeFloat: number | null;
  percentComplete: string;
  budgetedCost: string;
  actualCost: string;
  isCritical: boolean;
  createdAt: string;
  updatedAt: string;
}

// Dependency types
export type DependencyType = "FS" | "SS" | "FF" | "SF";

export interface Dependency {
  id: string;
  predecessorId: string;
  successorId: string;
  dependencyType: DependencyType;
  lag: number;
  createdAt: string;
  updatedAt: string;
}

// WBS types
export interface WBSElement {
  id: string;
  programId: string;
  parentId: string | null;
  code: string;
  name: string;
  description: string | null;
  path: string;
  level: number;
  budgetedCost: string;
  createdAt: string;
  updatedAt: string;
}

export interface WBSElementTree extends WBSElement {
  children: WBSElementTree[];
}

// Schedule types
export interface ScheduleResult {
  activityId: string;
  earlyStart: number;
  earlyFinish: number;
  lateStart: number;
  lateFinish: number;
  totalFloat: number;
  freeFloat: number;
  isCritical: boolean;
}

// EVMS types
export interface EVMSMetrics {
  bcws: string;
  bcwp: string;
  acwp: string;
  costVariance: string | null;
  scheduleVariance: string | null;
  costPerformanceIndex: string | null;
  schedulePerformanceIndex: string | null;
  budgetAtCompletion: string | null;
  estimateAtCompletion: string | null;
  estimateToComplete: string | null;
  varianceAtCompletion: string | null;
  toCompletePerformanceIndex: string | null;
}
