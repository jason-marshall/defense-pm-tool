/**
 * API service for Management Reserve endpoints.
 */

import { apiClient } from "@/api/client";
import type {
  ManagementReserveStatus,
  ManagementReserveChangeCreate,
  ManagementReserveLogResponse,
  ManagementReserveHistoryResponse,
} from "@/types/managementReserve";

export async function getMRStatus(
  programId: string
): Promise<ManagementReserveStatus> {
  const response = await apiClient.get<ManagementReserveStatus>(
    `/mr/${programId}`
  );
  return response.data;
}

export async function initializeMR(
  programId: string,
  initialAmount: string,
  reason?: string
): Promise<ManagementReserveLogResponse> {
  const params = new URLSearchParams({ initial_amount: initialAmount });
  if (reason) params.set("reason", reason);
  const response = await apiClient.post<ManagementReserveLogResponse>(
    `/mr/${programId}/initialize?${params.toString()}`
  );
  return response.data;
}

export async function recordMRChange(
  programId: string,
  data: ManagementReserveChangeCreate
): Promise<ManagementReserveLogResponse> {
  const response = await apiClient.post<ManagementReserveLogResponse>(
    `/mr/${programId}/change`,
    data
  );
  return response.data;
}

export async function getMRHistory(
  programId: string,
  limit?: number
): Promise<ManagementReserveHistoryResponse> {
  const params = limit ? `?limit=${limit}` : "";
  const response = await apiClient.get<ManagementReserveHistoryResponse>(
    `/mr/${programId}/history${params}`
  );
  return response.data;
}

export const mrApi = {
  getStatus: getMRStatus,
  initialize: initializeMR,
  recordChange: recordMRChange,
  getHistory: getMRHistory,
};
