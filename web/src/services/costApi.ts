/**
 * API service for Resource Cost management endpoints.
 */

import { apiClient } from "@/api/client";
import type {
  ActivityCostResponse,
  WBSCostResponse,
  ProgramCostSummaryResponse,
  EVMSSyncResponse,
  CostEntryCreate,
  CostEntryResponse,
} from "@/types/resourceCost";

/**
 * Get cost breakdown for an activity.
 */
export async function getActivityCost(
  activityId: string
): Promise<ActivityCostResponse> {
  const response = await apiClient.get<ActivityCostResponse>(
    `/cost/activities/${activityId}`
  );
  return response.data;
}

/**
 * Get cost summary for a WBS element.
 */
export async function getWBSCost(
  wbsId: string,
  includeChildren?: boolean
): Promise<WBSCostResponse> {
  const params = new URLSearchParams();
  if (includeChildren !== undefined) {
    params.append("include_children", String(includeChildren));
  }
  const url = `/cost/wbs/${wbsId}${params.toString() ? `?${params.toString()}` : ""}`;
  const response = await apiClient.get<WBSCostResponse>(url);
  return response.data;
}

/**
 * Get cost summary for a program.
 */
export async function getProgramCostSummary(
  programId: string
): Promise<ProgramCostSummaryResponse> {
  const response = await apiClient.get<ProgramCostSummaryResponse>(
    `/cost/programs/${programId}`
  );
  return response.data;
}

/**
 * Sync resource costs to EVMS period.
 */
export async function syncCostsToEVMS(
  programId: string,
  periodId: string
): Promise<EVMSSyncResponse> {
  const params = new URLSearchParams({ period_id: periodId });
  const response = await apiClient.post<EVMSSyncResponse>(
    `/cost/programs/${programId}/evms-sync?${params.toString()}`
  );
  return response.data;
}

/**
 * Record a cost entry for an assignment.
 */
export async function recordCostEntry(
  assignmentId: string,
  data: CostEntryCreate
): Promise<CostEntryResponse> {
  const payload: Record<string, unknown> = {
    entry_date: data.entry_date,
    hours_worked: data.hours_worked,
  };
  if (data.quantity_used !== undefined) {
    payload.quantity_used = data.quantity_used;
  }
  if (data.notes !== undefined) {
    payload.notes = data.notes;
  }
  const response = await apiClient.post<CostEntryResponse>(
    `/cost/assignments/${assignmentId}/entries`,
    payload
  );
  return response.data;
}

export const costApi = {
  getActivityCost,
  getWBSCost,
  getProgramCostSummary,
  syncCostsToEVMS,
  recordCostEntry,
};
