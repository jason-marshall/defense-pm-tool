/**
 * API service for Baseline management endpoints.
 */

import { apiClient } from "@/api/client";
import type {
  Baseline,
  BaselineCreate,
  BaselineComparison,
  BaselineListResponse,
} from "@/types/baseline";

export async function getBaselines(
  programId: string
): Promise<BaselineListResponse> {
  const response = await apiClient.get<BaselineListResponse>(
    `/baselines?program_id=${programId}`
  );
  return response.data;
}

export async function getBaseline(id: string): Promise<Baseline> {
  const response = await apiClient.get<Baseline>(`/baselines/${id}`);
  return response.data;
}

export async function createBaseline(data: BaselineCreate): Promise<Baseline> {
  const response = await apiClient.post<Baseline>("/baselines", data);
  return response.data;
}

export async function approveBaseline(id: string): Promise<Baseline> {
  const response = await apiClient.post<Baseline>(`/baselines/${id}/approve`);
  return response.data;
}

export async function compareBaselines(
  baselineAId: string,
  baselineBId: string
): Promise<BaselineComparison> {
  const response = await apiClient.get<BaselineComparison>(
    `/baselines/compare?baseline_a=${baselineAId}&baseline_b=${baselineBId}`
  );
  return response.data;
}

export async function deleteBaseline(id: string): Promise<void> {
  await apiClient.delete(`/baselines/${id}`);
}

export const baselineApi = {
  list: getBaselines,
  get: getBaseline,
  create: createBaseline,
  approve: approveBaseline,
  compare: compareBaselines,
  delete: deleteBaseline,
};
