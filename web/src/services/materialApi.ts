/**
 * API service for Material Tracking endpoints.
 */

import { apiClient } from "@/api/client";
import type {
  MaterialStatusResponse,
  MaterialConsumptionResponse,
  ProgramMaterialSummaryResponse,
} from "@/types/material";

/**
 * Get material status for a resource.
 */
export async function getMaterialStatus(
  resourceId: string
): Promise<MaterialStatusResponse> {
  const response = await apiClient.get<MaterialStatusResponse>(
    `/materials/resources/${resourceId}`
  );
  return response.data;
}

/**
 * Consume material from an assignment.
 */
export async function consumeMaterial(
  assignmentId: string,
  quantity: number
): Promise<MaterialConsumptionResponse> {
  const response = await apiClient.post<MaterialConsumptionResponse>(
    `/materials/assignments/${assignmentId}/consume`,
    { quantity }
  );
  return response.data;
}

/**
 * Get material summary for a program.
 */
export async function getProgramMaterials(
  programId: string
): Promise<ProgramMaterialSummaryResponse> {
  const response = await apiClient.get<ProgramMaterialSummaryResponse>(
    `/materials/programs/${programId}`
  );
  return response.data;
}

export const materialApi = {
  getStatus: getMaterialStatus,
  consume: consumeMaterial,
  getProgramMaterials,
};
