/**
 * React Query hooks for EVMS (Earned Value Management System) API.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getEVMSPeriods,
  getEVMSPeriodWithData,
  getEVMSSummary,
  createEVMSPeriod,
  addPeriodData,
  deleteEVMSPeriod,
  type EVMSPeriodCreate,
  type EVMSPeriodDataCreate,
} from "@/services/evmsApi";

const EVMS_KEY = "evms";
const EVMS_PERIODS_KEY = "evms-periods";
const EVMS_SUMMARY_KEY = "evms-summary";

/**
 * Hook to fetch EVMS summary for a program.
 */
export function useEVMSSummary(programId: string) {
  return useQuery({
    queryKey: [EVMS_SUMMARY_KEY, programId],
    queryFn: () => getEVMSSummary(programId),
    enabled: !!programId,
    staleTime: 30000, // Consider data fresh for 30 seconds
  });
}

/**
 * Hook to fetch EVMS periods for a program.
 */
export function useEVMSPeriods(programId: string, status?: string) {
  return useQuery({
    queryKey: [EVMS_PERIODS_KEY, programId, status],
    queryFn: () => getEVMSPeriods(programId, status),
    enabled: !!programId,
  });
}

/**
 * Hook to fetch a single EVMS period with its data.
 */
export function useEVMSPeriodWithData(periodId: string) {
  return useQuery({
    queryKey: [EVMS_KEY, "period", periodId],
    queryFn: () => getEVMSPeriodWithData(periodId),
    enabled: !!periodId,
  });
}

/**
 * Hook to create a new EVMS period.
 */
export function useCreateEVMSPeriod() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: EVMSPeriodCreate) => createEVMSPeriod(data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: [EVMS_PERIODS_KEY, variables.programId],
      });
      queryClient.invalidateQueries({
        queryKey: [EVMS_SUMMARY_KEY, variables.programId],
      });
    },
  });
}

/**
 * Hook to add data to an EVMS period.
 */
export function useAddPeriodData(programId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      periodId,
      data,
    }: {
      periodId: string;
      data: EVMSPeriodDataCreate;
    }) => addPeriodData(periodId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: [EVMS_KEY, "period", variables.periodId],
      });
      queryClient.invalidateQueries({
        queryKey: [EVMS_SUMMARY_KEY, programId],
      });
    },
  });
}

/**
 * Hook to delete an EVMS period.
 */
export function useDeleteEVMSPeriod(programId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (periodId: string) => deleteEVMSPeriod(periodId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [EVMS_PERIODS_KEY, programId] });
      queryClient.invalidateQueries({ queryKey: [EVMS_SUMMARY_KEY, programId] });
    },
  });
}
