export interface ScheduleResult {
  activity_id: string;
  activity_name: string;
  activity_code: string;
  duration: number;
  early_start: number;
  early_finish: number;
  late_start: number;
  late_finish: number;
  total_float: number;
  free_float: number;
  is_critical: boolean;
}

export interface ScheduleCalculationResponse {
  results: ScheduleResult[];
  critical_path: string[];
  project_duration: number;
  calculated_at: string;
}
