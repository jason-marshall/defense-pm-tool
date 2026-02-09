/**
 * API service for Activity management endpoints.
 */

import { apiClient } from "@/api/client";
import type {
  Activity,
  ActivityCreate,
  ActivityUpdate,
  ActivityListResponse,
} from "@/types/activity";

export async function getActivities(
  programId: string
): Promise<ActivityListResponse> {
  const response = await apiClient.get<ActivityListResponse>(
    `/activities?program_id=${programId}`
  );
  return response.data;
}

export async function getActivity(id: string): Promise<Activity> {
  const response = await apiClient.get<Activity>(`/activities/${id}`);
  return response.data;
}

export async function createActivity(data: ActivityCreate): Promise<Activity> {
  const response = await apiClient.post<Activity>("/activities", data);
  return response.data;
}

export async function updateActivity(
  id: string,
  data: ActivityUpdate
): Promise<Activity> {
  const response = await apiClient.patch<Activity>(`/activities/${id}`, data);
  return response.data;
}

export async function deleteActivity(id: string): Promise<void> {
  await apiClient.delete(`/activities/${id}`);
}

export const activityApi = {
  list: getActivities,
  get: getActivity,
  create: createActivity,
  update: updateActivity,
  delete: deleteActivity,
};
