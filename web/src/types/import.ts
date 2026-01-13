/**
 * TypeScript type definitions for MS Project import functionality.
 */

/**
 * Task preview information shown during import preview.
 */
export interface ImportPreviewTask {
  name: string;
  wbs: string;
  durationHours: number;
  isMilestone: boolean;
  predecessors: number;
}

/**
 * Response from import preview endpoint.
 */
export interface ImportPreviewResponse {
  preview: true;
  projectName: string;
  startDate: string;
  finishDate: string;
  taskCount: number;
  tasks: ImportPreviewTask[];
  warnings: string[];
}

/**
 * Response from import execution endpoint.
 */
export interface ImportResultResponse {
  success: boolean;
  programId: string;
  tasksImported: number;
  dependenciesImported: number;
  wbsElementsCreated: number;
  warnings: string[];
  errors: string[];
}

/**
 * Import state for tracking upload progress.
 */
export type ImportState = "idle" | "uploading" | "preview" | "importing" | "success" | "error";

/**
 * Import workflow data.
 */
export interface ImportWorkflow {
  state: ImportState;
  file: File | null;
  preview: ImportPreviewResponse | null;
  result: ImportResultResponse | null;
  error: string | null;
  progress: number;
}
