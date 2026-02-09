/**
 * React Query hooks for Dependency management API.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getDependencies,
  createDependency,
  deleteDependency,
} from "@/services/dependencyApi";
import type { DependencyCreate } from "@/types/dependency";

const DEPENDENCIES_KEY = "dependencies";

export function useDependencies(programId: string) {
  return useQuery({
    queryKey: [DEPENDENCIES_KEY, programId],
    queryFn: () => getDependencies(programId),
    enabled: !!programId,
  });
}

export function useCreateDependency() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: DependencyCreate) => createDependency(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [DEPENDENCIES_KEY] });
    },
  });
}

export function useDeleteDependency() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => deleteDependency(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [DEPENDENCIES_KEY] });
    },
  });
}
