/**
 * API service for Monte Carlo simulation endpoints.
 */

import { apiClient } from "@/api/client";
import type { MonteCarloConfig, MonteCarloResult } from "@/types/simulation";

export async function runSimulation(
  programId: string,
  config: MonteCarloConfig
): Promise<MonteCarloResult> {
  const response = await apiClient.post<MonteCarloResult>(
    `/simulations/monte-carlo`,
    { program_id: programId, ...config }
  );
  return response.data;
}

export async function getSimulationResult(
  id: string
): Promise<MonteCarloResult> {
  const response = await apiClient.get<MonteCarloResult>(
    `/simulations/${id}`
  );
  return response.data;
}

export async function getSimulationResults(
  programId: string
): Promise<MonteCarloResult[]> {
  const response = await apiClient.get<MonteCarloResult[]>(
    `/simulations?program_id=${programId}`
  );
  return response.data;
}

export const simulationApi = {
  run: runSimulation,
  get: getSimulationResult,
  list: getSimulationResults,
};
