/**
 * API service for Dependency management endpoints.
 */

import { apiClient } from "@/api/client";
import type {
  Dependency,
  DependencyCreate,
  DependencyUpdate,
  DependencyListResponse,
} from "@/types/dependency";

export async function getDependencies(
  programId: string
): Promise<DependencyListResponse> {
  const response = await apiClient.get<DependencyListResponse>(
    `/dependencies?program_id=${programId}`
  );
  return response.data;
}

export async function createDependency(
  data: DependencyCreate
): Promise<Dependency> {
  const response = await apiClient.post<Dependency>("/dependencies", data);
  return response.data;
}

export async function updateDependency(
  id: string,
  data: DependencyUpdate
): Promise<Dependency> {
  const response = await apiClient.patch<Dependency>(
    `/dependencies/${id}`,
    data
  );
  return response.data;
}

export async function deleteDependency(id: string): Promise<void> {
  await apiClient.delete(`/dependencies/${id}`);
}

export const dependencyApi = {
  list: getDependencies,
  create: createDependency,
  update: updateDependency,
  delete: deleteDependency,
};
