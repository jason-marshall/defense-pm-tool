/**
 * API service for Jira integration endpoints.
 */

import { apiClient } from "@/api/client";
import type {
  JiraIntegrationCreate,
  JiraIntegrationUpdate,
  JiraIntegrationResponse,
  JiraMappingCreate,
  JiraMappingResponse,
  JiraSyncResponse,
  JiraSyncLogListResponse,
  JiraConnectionTestResponse,
} from "@/types/jira";

// === Integration Management ===

export async function getIntegrationByProgram(
  programId: string
): Promise<JiraIntegrationResponse> {
  const response = await apiClient.get<JiraIntegrationResponse>(
    `/jira/programs/${programId}/integration`
  );
  return response.data;
}

export async function createIntegration(
  data: JiraIntegrationCreate
): Promise<JiraIntegrationResponse> {
  const response = await apiClient.post<JiraIntegrationResponse>(
    "/jira/integrations",
    data
  );
  return response.data;
}

export async function updateIntegration(
  integrationId: string,
  data: JiraIntegrationUpdate
): Promise<JiraIntegrationResponse> {
  const response = await apiClient.patch<JiraIntegrationResponse>(
    `/jira/integrations/${integrationId}`,
    data
  );
  return response.data;
}

export async function deleteIntegration(integrationId: string): Promise<void> {
  await apiClient.delete(`/jira/integrations/${integrationId}`);
}

// === Connection Testing ===

export async function testConnection(
  integrationId: string
): Promise<JiraConnectionTestResponse> {
  const response = await apiClient.post<JiraConnectionTestResponse>(
    `/jira/integrations/${integrationId}/test`
  );
  return response.data;
}

// === Sync Operations ===

export async function syncWbs(integrationId: string): Promise<JiraSyncResponse> {
  const response = await apiClient.post<JiraSyncResponse>(
    `/jira/integrations/${integrationId}/sync/wbs`
  );
  return response.data;
}

export async function syncActivities(integrationId: string): Promise<JiraSyncResponse> {
  const response = await apiClient.post<JiraSyncResponse>(
    `/jira/integrations/${integrationId}/sync/activities`
  );
  return response.data;
}

export async function syncProgress(integrationId: string): Promise<JiraSyncResponse> {
  const response = await apiClient.post<JiraSyncResponse>(
    `/jira/integrations/${integrationId}/sync/progress`
  );
  return response.data;
}

// === Mapping Management ===

export async function getMappings(
  integrationId: string
): Promise<JiraMappingResponse[]> {
  const response = await apiClient.get<JiraMappingResponse[]>(
    `/jira/integrations/${integrationId}/mappings`
  );
  return response.data;
}

export async function createMapping(
  integrationId: string,
  data: JiraMappingCreate
): Promise<JiraMappingResponse> {
  const response = await apiClient.post<JiraMappingResponse>(
    `/jira/integrations/${integrationId}/mappings`,
    data
  );
  return response.data;
}

export async function deleteMapping(mappingId: string): Promise<void> {
  await apiClient.delete(`/jira/mappings/${mappingId}`);
}

// === Sync Logs ===

export async function getSyncLogs(
  integrationId: string,
  limit?: number
): Promise<JiraSyncLogListResponse> {
  const params = limit ? `?limit=${limit}` : "";
  const response = await apiClient.get<JiraSyncLogListResponse>(
    `/jira/integrations/${integrationId}/logs${params}`
  );
  return response.data;
}

export const jiraApi = {
  getByProgram: getIntegrationByProgram,
  create: createIntegration,
  update: updateIntegration,
  delete: deleteIntegration,
  testConnection,
  syncWbs,
  syncActivities,
  syncProgress,
  getMappings,
  createMapping,
  deleteMapping,
  getSyncLogs,
};
