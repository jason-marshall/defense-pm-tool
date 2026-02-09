export type ScenarioStatus = "draft" | "simulated" | "promoted" | "archived";

export interface Scenario {
  id: string;
  program_id: string;
  name: string;
  description: string | null;
  status: ScenarioStatus;
  changes: ScenarioChange[];
  simulation_results: SimulationSummary | null;
  created_at: string;
  updated_at: string | null;
}

export interface ScenarioChange {
  activity_id: string;
  activity_name?: string;
  field: string;
  old_value: string;
  new_value: string;
}

export interface SimulationSummary {
  duration_p10: number;
  duration_p50: number;
  duration_p80: number;
  duration_p90: number;
  cost_p50: string;
  cost_p90: string;
}

export interface ScenarioCreate {
  program_id: string;
  name: string;
  description?: string;
  changes: Omit<ScenarioChange, "activity_name">[];
}

export interface ScenarioListResponse {
  items: Scenario[];
  total: number;
}
