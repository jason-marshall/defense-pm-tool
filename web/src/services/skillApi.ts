/**
 * API service for Skills, Resource Skills, and Skill Requirements.
 */

import { apiClient } from "@/api/client";
import type {
  SkillCreate,
  SkillUpdate,
  SkillResponse,
  SkillListResponse,
  ResourceSkillCreate,
  ResourceSkillUpdate,
  ResourceSkillResponse,
  SkillRequirementCreate,
  SkillRequirementResponse,
} from "@/types/skill";

// === Skill CRUD ===

export async function getSkills(params?: {
  program_id?: string;
  category?: string;
  is_active?: boolean;
  page?: number;
  page_size?: number;
}): Promise<SkillListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.program_id) searchParams.set("program_id", params.program_id);
  if (params?.category) searchParams.set("category", params.category);
  if (params?.is_active != null) searchParams.set("is_active", String(params.is_active));
  if (params?.page) searchParams.set("page", String(params.page));
  if (params?.page_size) searchParams.set("page_size", String(params.page_size));
  const qs = searchParams.toString();
  const response = await apiClient.get<SkillListResponse>(`/skills${qs ? `?${qs}` : ""}`);
  return response.data;
}

export async function createSkill(data: SkillCreate): Promise<SkillResponse> {
  const response = await apiClient.post<SkillResponse>("/skills", data);
  return response.data;
}

export async function updateSkill(id: string, data: SkillUpdate): Promise<SkillResponse> {
  const response = await apiClient.patch<SkillResponse>(`/skills/${id}`, data);
  return response.data;
}

export async function deleteSkill(id: string): Promise<void> {
  await apiClient.delete(`/skills/${id}`);
}

// === Resource Skills ===

export async function getResourceSkills(resourceId: string): Promise<ResourceSkillResponse[]> {
  const response = await apiClient.get<ResourceSkillResponse[]>(
    `/resources/${resourceId}/skills`
  );
  return response.data;
}

export async function addResourceSkill(
  resourceId: string,
  data: ResourceSkillCreate
): Promise<ResourceSkillResponse> {
  const response = await apiClient.post<ResourceSkillResponse>(
    `/resources/${resourceId}/skills`,
    data
  );
  return response.data;
}

export async function updateResourceSkill(
  resourceId: string,
  skillId: string,
  data: ResourceSkillUpdate
): Promise<ResourceSkillResponse> {
  const response = await apiClient.put<ResourceSkillResponse>(
    `/resources/${resourceId}/skills/${skillId}`,
    data
  );
  return response.data;
}

export async function removeResourceSkill(
  resourceId: string,
  skillId: string
): Promise<void> {
  await apiClient.delete(`/resources/${resourceId}/skills/${skillId}`);
}

// === Skill Requirements ===

export async function getSkillRequirements(
  activityId: string
): Promise<SkillRequirementResponse[]> {
  const response = await apiClient.get<SkillRequirementResponse[]>(
    `/activities/${activityId}/skill-requirements`
  );
  return response.data;
}

export async function addSkillRequirement(
  activityId: string,
  data: SkillRequirementCreate
): Promise<SkillRequirementResponse> {
  const response = await apiClient.post<SkillRequirementResponse>(
    `/activities/${activityId}/skill-requirements`,
    data
  );
  return response.data;
}

export async function removeSkillRequirement(
  activityId: string,
  skillId: string
): Promise<void> {
  await apiClient.delete(`/activities/${activityId}/skill-requirements/${skillId}`);
}

export const skillApi = {
  list: getSkills,
  create: createSkill,
  update: updateSkill,
  delete: deleteSkill,
  getResourceSkills,
  addResourceSkill,
  updateResourceSkill,
  removeResourceSkill,
  getSkillRequirements,
  addSkillRequirement,
  removeSkillRequirement,
};
