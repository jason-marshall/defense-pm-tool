/**
 * React Query hooks for Baseline management API.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getBaselines,
  createBaseline,
  approveBaseline,
  compareBaselines,
  deleteBaseline,
} from "@/services/baselineApi";
import type { BaselineCreate } from "@/types/baseline";

const BASELINES_KEY = "baselines";

export function useBaselines(programId: string) {
  return useQuery({
    queryKey: [BASELINES_KEY, programId],
    queryFn: () => getBaselines(programId),
    enabled: !!programId,
  });
}

export function useCreateBaseline() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: BaselineCreate) => createBaseline(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [BASELINES_KEY] });
    },
  });
}

export function useApproveBaseline() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => approveBaseline(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [BASELINES_KEY] });
    },
  });
}

export function useCompareBaselines(
  baselineAId: string,
  baselineBId: string
) {
  return useQuery({
    queryKey: [BASELINES_KEY, "compare", baselineAId, baselineBId],
    queryFn: () => compareBaselines(baselineAId, baselineBId),
    enabled: !!baselineAId && !!baselineBId,
  });
}

export function useDeleteBaseline() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => deleteBaseline(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [BASELINES_KEY] });
    },
  });
}
