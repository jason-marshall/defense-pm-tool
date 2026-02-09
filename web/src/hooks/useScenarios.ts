/**
 * React Query hooks for Scenario management API.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getScenarios,
  getScenario,
  createScenario,
  simulateScenario,
  promoteScenario,
  deleteScenario,
} from "@/services/scenarioApi";
import type { ScenarioCreate } from "@/types/scenario";

const SCENARIOS_KEY = "scenarios";

export function useScenarios(programId: string) {
  return useQuery({
    queryKey: [SCENARIOS_KEY, programId],
    queryFn: () => getScenarios(programId),
    enabled: !!programId,
  });
}

export function useScenario(id: string) {
  return useQuery({
    queryKey: [SCENARIOS_KEY, "detail", id],
    queryFn: () => getScenario(id),
    enabled: !!id,
  });
}

export function useCreateScenario() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: ScenarioCreate) => createScenario(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [SCENARIOS_KEY] });
    },
  });
}

export function useSimulateScenario() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => simulateScenario(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [SCENARIOS_KEY] });
    },
  });
}

export function usePromoteScenario() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => promoteScenario(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [SCENARIOS_KEY] });
      queryClient.invalidateQueries({ queryKey: ["baselines"] });
    },
  });
}

export function useDeleteScenario() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => deleteScenario(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [SCENARIOS_KEY] });
    },
  });
}
