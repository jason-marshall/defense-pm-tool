/**
 * React Query hooks for Monte Carlo simulation API.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  runSimulation,
  getSimulationResult,
  getSimulationResults,
} from "@/services/simulationApi";
import type { MonteCarloConfig } from "@/types/simulation";

const SIMULATIONS_KEY = "simulations";

export function useSimulationResults(programId: string) {
  return useQuery({
    queryKey: [SIMULATIONS_KEY, programId],
    queryFn: () => getSimulationResults(programId),
    enabled: !!programId,
  });
}

export function useSimulationResult(id: string) {
  return useQuery({
    queryKey: [SIMULATIONS_KEY, "detail", id],
    queryFn: () => getSimulationResult(id),
    enabled: !!id,
  });
}

export function useRunSimulation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      programId,
      config,
    }: {
      programId: string;
      config: MonteCarloConfig;
    }) => runSimulation(programId, config),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: [SIMULATIONS_KEY, variables.programId],
      });
    },
  });
}
