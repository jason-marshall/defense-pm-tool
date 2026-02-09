/**
 * React Query hooks for Management Reserve API.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getMRStatus, initializeMR, recordMRChange, getMRHistory } from "@/services/mrApi";
import type { ManagementReserveChangeCreate } from "@/types/managementReserve";

const MR_KEY = "management-reserve";

export function useMRStatus(programId: string) {
  return useQuery({
    queryKey: [MR_KEY, "status", programId],
    queryFn: () => getMRStatus(programId),
    enabled: !!programId,
  });
}

export function useMRHistory(programId: string, limit?: number) {
  return useQuery({
    queryKey: [MR_KEY, "history", programId, limit],
    queryFn: () => getMRHistory(programId, limit),
    enabled: !!programId,
  });
}

export function useInitializeMR() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      programId,
      initialAmount,
      reason,
    }: {
      programId: string;
      initialAmount: string;
      reason?: string;
    }) => initializeMR(programId, initialAmount, reason),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: [MR_KEY, "status", variables.programId],
      });
      queryClient.invalidateQueries({
        queryKey: [MR_KEY, "history", variables.programId],
      });
    },
  });
}

export function useRecordMRChange() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      programId,
      data,
    }: {
      programId: string;
      data: ManagementReserveChangeCreate;
    }) => recordMRChange(programId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: [MR_KEY, "status", variables.programId],
      });
      queryClient.invalidateQueries({
        queryKey: [MR_KEY, "history", variables.programId],
      });
    },
  });
}
