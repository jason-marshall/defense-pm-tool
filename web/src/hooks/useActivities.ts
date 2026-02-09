/**
 * React Query hooks for Activity management API.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getActivities,
  getActivity,
  createActivity,
  updateActivity,
  deleteActivity,
} from "@/services/activityApi";
import type { ActivityCreate, ActivityUpdate } from "@/types/activity";

const ACTIVITIES_KEY = "activities";

export function useActivities(programId: string) {
  return useQuery({
    queryKey: [ACTIVITIES_KEY, programId],
    queryFn: () => getActivities(programId),
    enabled: !!programId,
  });
}

export function useActivity(id: string) {
  return useQuery({
    queryKey: [ACTIVITIES_KEY, "detail", id],
    queryFn: () => getActivity(id),
    enabled: !!id,
  });
}

export function useCreateActivity() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: ActivityCreate) => createActivity(data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: [ACTIVITIES_KEY, variables.program_id] });
    },
  });
}

export function useUpdateActivity() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: ActivityUpdate }) =>
      updateActivity(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [ACTIVITIES_KEY] });
    },
  });
}

export function useDeleteActivity() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => deleteActivity(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [ACTIVITIES_KEY] });
    },
  });
}
