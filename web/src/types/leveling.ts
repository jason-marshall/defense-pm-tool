export interface LevelingOptions {
  preserve_critical_path: boolean;
  max_iterations: number;
  target_resources: string[] | null;
  level_within_float: boolean;
}

export interface ActivityShift {
  activity_id: string;
  activity_code: string;
  original_start: string;
  original_finish: string;
  new_start: string;
  new_finish: string;
  delay_days: number;
  reason: string;
}

export interface LevelingResult {
  program_id: string;
  success: boolean;
  iterations_used: number;
  activities_shifted: number;
  shifts: ActivityShift[];
  remaining_overallocations: number;
  new_project_finish: string;
  original_project_finish: string;
  schedule_extension_days: number;
  warnings: string[];
}

export interface AlgorithmMetrics {
  algorithm: string;
  execution_time_ms: number;
  activities_shifted: number;
  schedule_extension_days: number;
  remaining_overallocations: number;
}

export interface ParallelLevelingResult extends LevelingResult {
  algorithm: "parallel";
  threads_used: number;
  metrics: AlgorithmMetrics;
}

export interface LevelingComparisonResponse {
  program_id: string;
  serial: AlgorithmMetrics;
  parallel: AlgorithmMetrics;
  recommendation: string;
}
