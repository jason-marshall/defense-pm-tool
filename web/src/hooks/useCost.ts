/**
 * React Query hooks for Resource Cost API.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getProgramCostSummary,
  getActivityCost,
  getWBSCost,
  syncCostsToEVMS,
  recordCostEntry,
} from "@/services/costApi";
import type { CostEntryCreate } from "@/types/resourceCost";

const COST_KEY = "cost";

/**
 * Hook to fetch program cost summary.
 */
export function useProgramCostSummary(programId: string) {
  return useQuery({
    queryKey: [COST_KEY, "program", programId],
    queryFn: () => getProgramCostSummary(programId),
    enabled: !!programId,
  });
}

/**
 * Hook to fetch activity cost breakdown.
 */
export function useActivityCost(activityId: string) {
  return useQuery({
    queryKey: [COST_KEY, "activity", activityId],
    queryFn: () => getActivityCost(activityId),
    enabled: !!activityId,
  });
}

/**
 * Hook to fetch WBS cost summary.
 */
export function useWBSCost(wbsId: string, includeChildren?: boolean) {
  return useQuery({
    queryKey: [COST_KEY, "wbs", wbsId, includeChildren],
    queryFn: () => getWBSCost(wbsId, includeChildren),
    enabled: !!wbsId,
  });
}

/**
 * Hook to sync costs to EVMS.
 */
export function useSyncCostsToEVMS() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      programId,
      periodId,
    }: {
      programId: string;
      periodId: string;
    }) => syncCostsToEVMS(programId, periodId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: [COST_KEY] });
      queryClient.invalidateQueries({
        queryKey: [COST_KEY, "program", variables.programId],
      });
    },
  });
}

/**
 * Hook to record a cost entry.
 */
export function useRecordCostEntry() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      assignmentId,
      data,
    }: {
      assignmentId: string;
      data: CostEntryCreate;
    }) => recordCostEntry(assignmentId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [COST_KEY] });
    },
  });
}
