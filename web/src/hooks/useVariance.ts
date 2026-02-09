/**
 * React Query hooks for Variance Explanation API.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getVariancesByProgram,
  createVariance,
  updateVariance,
  deleteVariance,
} from "@/services/varianceApi";
import type {
  VarianceExplanationCreate,
  VarianceExplanationUpdate,
} from "@/types/variance";

const VARIANCE_KEY = "variance-explanations";

export function useVariancesByProgram(
  programId: string,
  params?: {
    variance_type?: string;
    include_resolved?: boolean;
    page?: number;
    per_page?: number;
  }
) {
  return useQuery({
    queryKey: [VARIANCE_KEY, programId, params],
    queryFn: () => getVariancesByProgram(programId, params),
    enabled: !!programId,
  });
}

export function useCreateVariance() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: VarianceExplanationCreate) => createVariance(data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: [VARIANCE_KEY, variables.program_id],
      });
    },
  });
}

export function useUpdateVariance() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: VarianceExplanationUpdate }) =>
      updateVariance(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [VARIANCE_KEY] });
    },
  });
}

export function useDeleteVariance() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => deleteVariance(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [VARIANCE_KEY] });
    },
  });
}
