/**
 * API service for Resource Assignment endpoints.
 */

import { apiClient } from "@/api/client";
import type {
  ResourceAssignment,
  AssignmentCreate,
  AssignmentUpdate,
} from "@/types/assignment";

/**
 * Get all assignments for a resource.
 */
export async function getResourceAssignments(
  resourceId: string
): Promise<ResourceAssignment[]> {
  const response = await apiClient.get<ResourceAssignment[]>(
    `/resources/${resourceId}/assignments`
  );
  return response.data;
}

/**
 * Get all assignments for an activity.
 */
export async function getActivityAssignments(
  activityId: string
): Promise<ResourceAssignment[]> {
  const response = await apiClient.get<ResourceAssignment[]>(
    `/activities/${activityId}/assignments`
  );
  return response.data;
}

/**
 * Create a new assignment.
 */
export async function createAssignment(
  resourceId: string,
  data: AssignmentCreate
): Promise<ResourceAssignment> {
  const payload = {
    activity_id: data.activity_id,
    resource_id: data.resource_id,
    units: data.units,
    start_date: data.start_date,
    finish_date: data.finish_date,
  };
  const response = await apiClient.post<ResourceAssignment>(
    `/resources/${resourceId}/assignments`,
    payload
  );
  return response.data;
}

/**
 * Update an existing assignment.
 */
export async function updateAssignment(
  assignmentId: string,
  data: AssignmentUpdate
): Promise<ResourceAssignment> {
  const payload: Record<string, unknown> = {};
  if (data.units !== undefined) payload.units = data.units;
  if (data.start_date !== undefined) payload.start_date = data.start_date;
  if (data.finish_date !== undefined) payload.finish_date = data.finish_date;

  const response = await apiClient.put<ResourceAssignment>(
    `/assignments/${assignmentId}`,
    payload
  );
  return response.data;
}

/**
 * Delete an assignment.
 */
export async function deleteAssignment(assignmentId: string): Promise<void> {
  await apiClient.delete(`/assignments/${assignmentId}`);
}

export const assignmentApi = {
  listByResource: getResourceAssignments,
  listByActivity: getActivityAssignments,
  create: createAssignment,
  update: updateAssignment,
  delete: deleteAssignment,
};
