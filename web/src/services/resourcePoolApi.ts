/**
 * API service for Resource Pool management endpoints.
 */

import { apiClient } from "@/api/client";
import type {
  ResourcePoolCreate,
  ResourcePoolUpdate,
  ResourcePoolResponse,
  PoolMemberCreate,
  PoolMemberResponse,
  PoolAccessCreate,
  PoolAccessResponse,
  PoolAvailabilityResponse,
  ConflictCheckRequest,
  ConflictCheckResponse,
} from "@/types/resourcePool";

/**
 * List all accessible resource pools.
 */
export async function listPools(): Promise<ResourcePoolResponse[]> {
  const response =
    await apiClient.get<ResourcePoolResponse[]>("/resource-pools");
  return response.data;
}

/**
 * Get a single resource pool.
 */
export async function getPool(poolId: string): Promise<ResourcePoolResponse> {
  const response = await apiClient.get<ResourcePoolResponse>(
    `/resource-pools/${poolId}`
  );
  return response.data;
}

/**
 * Create a new resource pool.
 */
export async function createPool(
  data: ResourcePoolCreate
): Promise<ResourcePoolResponse> {
  const payload: Record<string, unknown> = {
    name: data.name,
    code: data.code,
  };
  if (data.description !== undefined) {
    payload.description = data.description;
  }
  const response = await apiClient.post<ResourcePoolResponse>(
    "/resource-pools",
    payload
  );
  return response.data;
}

/**
 * Update a resource pool.
 */
export async function updatePool(
  poolId: string,
  data: ResourcePoolUpdate
): Promise<ResourcePoolResponse> {
  const payload: Record<string, unknown> = {};
  if (data.name !== undefined) payload.name = data.name;
  if (data.description !== undefined) payload.description = data.description;
  if (data.is_active !== undefined) payload.is_active = data.is_active;
  const response = await apiClient.patch<ResourcePoolResponse>(
    `/resource-pools/${poolId}`,
    payload
  );
  return response.data;
}

/**
 * Delete a resource pool.
 */
export async function deletePool(poolId: string): Promise<void> {
  await apiClient.delete(`/resource-pools/${poolId}`);
}

/**
 * List members of a resource pool.
 */
export async function listPoolMembers(
  poolId: string
): Promise<PoolMemberResponse[]> {
  const response = await apiClient.get<PoolMemberResponse[]>(
    `/resource-pools/${poolId}/members`
  );
  return response.data;
}

/**
 * Add a member to a resource pool.
 */
export async function addPoolMember(
  poolId: string,
  data: PoolMemberCreate
): Promise<PoolMemberResponse> {
  const payload: Record<string, unknown> = {
    resource_id: data.resource_id,
  };
  if (data.allocation_percentage !== undefined) {
    payload.allocation_percentage = data.allocation_percentage;
  }
  const response = await apiClient.post<PoolMemberResponse>(
    `/resource-pools/${poolId}/members`,
    payload
  );
  return response.data;
}

/**
 * Remove a member from a resource pool.
 */
export async function removePoolMember(
  poolId: string,
  memberId: string
): Promise<void> {
  await apiClient.delete(`/resource-pools/${poolId}/members/${memberId}`);
}

/**
 * Grant pool access to a program.
 */
export async function grantPoolAccess(
  poolId: string,
  data: PoolAccessCreate
): Promise<PoolAccessResponse> {
  const response = await apiClient.post<PoolAccessResponse>(
    `/resource-pools/${poolId}/access`,
    data
  );
  return response.data;
}

/**
 * Get pool availability for a date range.
 */
export async function getPoolAvailability(
  poolId: string,
  startDate: string,
  endDate: string
): Promise<PoolAvailabilityResponse> {
  const params = new URLSearchParams({
    start_date: startDate,
    end_date: endDate,
  });
  const response = await apiClient.get<PoolAvailabilityResponse>(
    `/resource-pools/${poolId}/availability?${params.toString()}`
  );
  return response.data;
}

/**
 * Check for assignment conflicts.
 */
export async function checkConflict(
  data: ConflictCheckRequest
): Promise<ConflictCheckResponse> {
  const response = await apiClient.post<ConflictCheckResponse>(
    "/resource-pools/check-conflict",
    data
  );
  return response.data;
}

export const resourcePoolApi = {
  list: listPools,
  get: getPool,
  create: createPool,
  update: updatePool,
  delete: deletePool,
  listMembers: listPoolMembers,
  addMember: addPoolMember,
  removeMember: removePoolMember,
  grantAccess: grantPoolAccess,
  getAvailability: getPoolAvailability,
  checkConflict,
};
