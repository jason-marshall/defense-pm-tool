/**
 * API service for Resource management endpoints.
 */

import { apiClient } from "@/api/client";
import type {
  Resource,
  ResourceCreate,
  ResourceUpdate,
  ResourceListResponse,
} from "@/types/resource";

/**
 * Get all resources for a program.
 */
export async function getResources(
  programId: string,
  params?: { resource_type?: string; is_active?: boolean }
): Promise<ResourceListResponse> {
  const searchParams = new URLSearchParams({ program_id: programId });
  if (params?.resource_type) {
    searchParams.append("resource_type", params.resource_type);
  }
  if (params?.is_active !== undefined) {
    searchParams.append("is_active", String(params.is_active));
  }
  const response = await apiClient.get<ResourceListResponse>(
    `/resources?${searchParams.toString()}`
  );
  return response.data;
}

/**
 * Get a single resource by ID.
 */
export async function getResource(id: string): Promise<Resource> {
  const response = await apiClient.get<Resource>(`/resources/${id}`);
  return response.data;
}

/**
 * Create a new resource.
 */
export async function createResource(data: ResourceCreate): Promise<Resource> {
  const payload = {
    program_id: data.program_id,
    name: data.name,
    code: data.code,
    resource_type: data.resource_type,
    capacity_per_day: data.capacity_per_day,
    cost_rate: data.cost_rate,
    effective_date: data.effective_date,
    is_active: data.is_active,
  };
  const response = await apiClient.post<Resource>("/resources", payload);
  return response.data;
}

/**
 * Update an existing resource.
 */
export async function updateResource(
  id: string,
  data: ResourceUpdate
): Promise<Resource> {
  const payload: Record<string, unknown> = {};
  if (data.name !== undefined) payload.name = data.name;
  if (data.code !== undefined) payload.code = data.code;
  if (data.resource_type !== undefined) payload.resource_type = data.resource_type;
  if (data.capacity_per_day !== undefined) payload.capacity_per_day = data.capacity_per_day;
  if (data.cost_rate !== undefined) payload.cost_rate = data.cost_rate;
  if (data.effective_date !== undefined) payload.effective_date = data.effective_date;
  if (data.is_active !== undefined) payload.is_active = data.is_active;

  const response = await apiClient.put<Resource>(`/resources/${id}`, payload);
  return response.data;
}

/**
 * Delete a resource.
 */
export async function deleteResource(id: string): Promise<void> {
  await apiClient.delete(`/resources/${id}`);
}

export const resourceApi = {
  list: getResources,
  get: getResource,
  create: createResource,
  update: updateResource,
  delete: deleteResource,
};
