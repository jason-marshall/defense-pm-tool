/**
 * API service for Variance Explanation endpoints.
 */

import { apiClient } from "@/api/client";
import type {
  VarianceExplanationCreate,
  VarianceExplanationUpdate,
  VarianceExplanationResponse,
  VarianceExplanationListResponse,
} from "@/types/variance";

export async function getVariancesByProgram(
  programId: string,
  params?: {
    variance_type?: string;
    include_resolved?: boolean;
    page?: number;
    per_page?: number;
  }
): Promise<VarianceExplanationListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.variance_type) searchParams.set("variance_type", params.variance_type);
  if (params?.include_resolved != null) searchParams.set("include_resolved", String(params.include_resolved));
  if (params?.page) searchParams.set("page", String(params.page));
  if (params?.per_page) searchParams.set("per_page", String(params.per_page));
  const qs = searchParams.toString();
  const response = await apiClient.get<VarianceExplanationListResponse>(
    `/variance-explanations/program/${programId}${qs ? `?${qs}` : ""}`
  );
  return response.data;
}

export async function createVariance(
  data: VarianceExplanationCreate
): Promise<VarianceExplanationResponse> {
  const response = await apiClient.post<VarianceExplanationResponse>(
    "/variance-explanations",
    data
  );
  return response.data;
}

export async function updateVariance(
  id: string,
  data: VarianceExplanationUpdate
): Promise<VarianceExplanationResponse> {
  const response = await apiClient.patch<VarianceExplanationResponse>(
    `/variance-explanations/${id}`,
    data
  );
  return response.data;
}

export async function deleteVariance(id: string): Promise<void> {
  await apiClient.delete(`/variance-explanations/${id}`);
}

export async function restoreVariance(
  id: string
): Promise<VarianceExplanationResponse> {
  const response = await apiClient.post<VarianceExplanationResponse>(
    `/variance-explanations/${id}/restore`
  );
  return response.data;
}

export async function getSignificantVariances(
  programId: string,
  thresholdPercent?: string
): Promise<VarianceExplanationResponse[]> {
  const params = thresholdPercent ? `?threshold_percent=${thresholdPercent}` : "";
  const response = await apiClient.get<VarianceExplanationResponse[]>(
    `/variance-explanations/program/${programId}/significant${params}`
  );
  return response.data;
}

export const varianceApi = {
  listByProgram: getVariancesByProgram,
  create: createVariance,
  update: updateVariance,
  delete: deleteVariance,
  restore: restoreVariance,
  getSignificant: getSignificantVariances,
};
