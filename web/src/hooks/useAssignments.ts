/**
 * React Query hooks for Resource Assignment API.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getActivityAssignments,
  getResourceAssignments,
  createAssignment,
  updateAssignment,
  deleteAssignment,
} from "@/services/assignmentApi";
import type { AssignmentCreate, AssignmentUpdate } from "@/types/assignment";

const ASSIGNMENTS_KEY = "assignments";

/**
 * Hook to fetch assignments for an activity.
 */
export function useActivityAssignments(activityId: string) {
  return useQuery({
    queryKey: [ASSIGNMENTS_KEY, "activity", activityId],
    queryFn: () => getActivityAssignments(activityId),
    enabled: !!activityId,
  });
}

/**
 * Hook to fetch assignments for a resource.
 */
export function useResourceAssignments(resourceId: string) {
  return useQuery({
    queryKey: [ASSIGNMENTS_KEY, "resource", resourceId],
    queryFn: () => getResourceAssignments(resourceId),
    enabled: !!resourceId,
  });
}

/**
 * Hook to create a new assignment.
 */
export function useCreateAssignment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      resourceId,
      data,
    }: {
      resourceId: string;
      data: AssignmentCreate;
    }) => createAssignment(resourceId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: [ASSIGNMENTS_KEY] });
      queryClient.invalidateQueries({
        queryKey: [ASSIGNMENTS_KEY, "activity", variables.data.activity_id],
      });
      queryClient.invalidateQueries({
        queryKey: [ASSIGNMENTS_KEY, "resource", variables.resourceId],
      });
    },
  });
}

/**
 * Hook to update an assignment.
 */
export function useUpdateAssignment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      assignmentId,
      data,
    }: {
      assignmentId: string;
      data: AssignmentUpdate;
    }) => updateAssignment(assignmentId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [ASSIGNMENTS_KEY] });
    },
  });
}

/**
 * Hook to delete an assignment.
 */
export function useDeleteAssignment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (assignmentId: string) => deleteAssignment(assignmentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [ASSIGNMENTS_KEY] });
    },
  });
}
