/**
 * API service for Resource Leveling endpoints.
 */

import { apiClient } from "@/api/client";
import type {
  LevelingOptions,
  LevelingResult,
  ParallelLevelingResult,
  LevelingComparisonResponse,
} from "@/types/leveling";

/**
 * Preview leveling without applying changes.
 */
export async function previewLeveling(
  programId: string,
  options?: Partial<LevelingOptions>
): Promise<LevelingResult> {
  const params = new URLSearchParams();
  if (options?.preserve_critical_path !== undefined) {
    params.append("preserve_critical_path", String(options.preserve_critical_path));
  }
  if (options?.max_iterations !== undefined) {
    params.append("max_iterations", String(options.max_iterations));
  }
  if (options?.level_within_float !== undefined) {
    params.append("level_within_float", String(options.level_within_float));
  }

  const url = `/programs/${programId}/level/preview${params.toString() ? `?${params.toString()}` : ""}`;
  const response = await apiClient.get<LevelingResult>(url);
  return response.data;
}

/**
 * Run leveling algorithm.
 */
export async function runLeveling(
  programId: string,
  options: Partial<LevelingOptions>
): Promise<LevelingResult> {
  const response = await apiClient.post<LevelingResult>(
    `/programs/${programId}/level`,
    options
  );
  return response.data;
}

/**
 * Apply selected leveling shifts.
 */
export async function applyLeveling(
  programId: string,
  shiftIds: string[]
): Promise<{ applied_count: number }> {
  const response = await apiClient.post<{ applied_count: number }>(
    `/programs/${programId}/level/apply`,
    { shifts: shiftIds }
  );
  return response.data;
}

/**
 * Run parallel leveling algorithm.
 */
export async function runParallelLeveling(
  programId: string,
  options: Partial<LevelingOptions>
): Promise<ParallelLevelingResult> {
  const response = await apiClient.post<ParallelLevelingResult>(
    `/programs/${programId}/level/parallel`,
    options
  );
  return response.data;
}

/**
 * Preview parallel leveling without applying changes.
 */
export async function previewParallelLeveling(
  programId: string,
  options?: Partial<LevelingOptions>
): Promise<ParallelLevelingResult> {
  const params = new URLSearchParams();
  if (options?.preserve_critical_path !== undefined) {
    params.append("preserve_critical_path", String(options.preserve_critical_path));
  }
  if (options?.max_iterations !== undefined) {
    params.append("max_iterations", String(options.max_iterations));
  }
  if (options?.level_within_float !== undefined) {
    params.append("level_within_float", String(options.level_within_float));
  }

  const url = `/programs/${programId}/level/parallel/preview${params.toString() ? `?${params.toString()}` : ""}`;
  const response = await apiClient.get<ParallelLevelingResult>(url);
  return response.data;
}

/**
 * Compare serial and parallel leveling algorithms.
 */
export async function compareLevelingAlgorithms(
  programId: string,
  options: Partial<LevelingOptions>
): Promise<LevelingComparisonResponse> {
  const response = await apiClient.post<LevelingComparisonResponse>(
    `/programs/${programId}/level/compare`,
    options
  );
  return response.data;
}

export const levelingApi = {
  preview: previewLeveling,
  run: runLeveling,
  apply: applyLeveling,
  runParallel: runParallelLeveling,
  previewParallel: previewParallelLeveling,
  compare: compareLevelingAlgorithms,
};
