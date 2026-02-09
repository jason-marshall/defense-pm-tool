/**
 * React Query hooks for Material Tracking API.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getProgramMaterials,
  getMaterialStatus,
  consumeMaterial,
} from "@/services/materialApi";

const MATERIALS_KEY = "materials";

/**
 * Hook to fetch program material summary.
 */
export function useProgramMaterials(programId: string) {
  return useQuery({
    queryKey: [MATERIALS_KEY, "program", programId],
    queryFn: () => getProgramMaterials(programId),
    enabled: !!programId,
  });
}

/**
 * Hook to fetch material status for a resource.
 */
export function useMaterialStatus(resourceId: string) {
  return useQuery({
    queryKey: [MATERIALS_KEY, "resource", resourceId],
    queryFn: () => getMaterialStatus(resourceId),
    enabled: !!resourceId,
  });
}

/**
 * Hook to consume material from an assignment.
 */
export function useConsumeMaterial() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      assignmentId,
      quantity,
    }: {
      assignmentId: string;
      quantity: number;
    }) => consumeMaterial(assignmentId, quantity),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [MATERIALS_KEY] });
    },
  });
}
