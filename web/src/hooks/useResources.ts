/**
 * React Query hooks for Resource management API.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getResources,
  getResource,
  createResource,
  updateResource,
  deleteResource,
} from "@/services/resourceApi";
import type { ResourceCreate, ResourceUpdate } from "@/types/resource";

const RESOURCES_KEY = "resources";

/**
 * Hook to fetch resources for a program.
 */
export function useResources(
  programId: string,
  filters?: { resource_type?: string; is_active?: boolean }
) {
  return useQuery({
    queryKey: [RESOURCES_KEY, programId, filters],
    queryFn: () => getResources(programId, filters),
    enabled: !!programId,
  });
}

/**
 * Hook to fetch a single resource.
 */
export function useResource(id: string) {
  return useQuery({
    queryKey: [RESOURCES_KEY, id],
    queryFn: () => getResource(id),
    enabled: !!id,
  });
}

/**
 * Hook to create a new resource.
 */
export function useCreateResource() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: ResourceCreate) => createResource(data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: [RESOURCES_KEY] });
      queryClient.invalidateQueries({
        queryKey: [RESOURCES_KEY, variables.program_id],
      });
    },
  });
}

/**
 * Hook to update a resource.
 */
export function useUpdateResource() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: ResourceUpdate }) =>
      updateResource(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: [RESOURCES_KEY] });
      queryClient.invalidateQueries({ queryKey: [RESOURCES_KEY, variables.id] });
    },
  });
}

/**
 * Hook to delete a resource.
 */
export function useDeleteResource() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => deleteResource(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [RESOURCES_KEY] });
    },
  });
}
