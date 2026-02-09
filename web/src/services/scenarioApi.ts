/**
 * API service for Scenario management endpoints.
 */

import { apiClient } from "@/api/client";
import type {
  Scenario,
  ScenarioCreate,
  ScenarioListResponse,
} from "@/types/scenario";

export async function getScenarios(
  programId: string
): Promise<ScenarioListResponse> {
  const response = await apiClient.get<ScenarioListResponse>(
    `/scenarios?program_id=${programId}`
  );
  return response.data;
}

export async function getScenario(id: string): Promise<Scenario> {
  const response = await apiClient.get<Scenario>(`/scenarios/${id}`);
  return response.data;
}

export async function createScenario(data: ScenarioCreate): Promise<Scenario> {
  const response = await apiClient.post<Scenario>("/scenarios", data);
  return response.data;
}

export async function simulateScenario(id: string): Promise<Scenario> {
  const response = await apiClient.post<Scenario>(`/scenarios/${id}/simulate`);
  return response.data;
}

export async function promoteScenario(id: string): Promise<Scenario> {
  const response = await apiClient.post<Scenario>(`/scenarios/${id}/promote`);
  return response.data;
}

export async function deleteScenario(id: string): Promise<void> {
  await apiClient.delete(`/scenarios/${id}`);
}

export const scenarioApi = {
  list: getScenarios,
  get: getScenario,
  create: createScenario,
  simulate: simulateScenario,
  promote: promoteScenario,
  delete: deleteScenario,
};
