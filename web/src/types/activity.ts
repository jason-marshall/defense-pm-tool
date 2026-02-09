export interface Activity {
  id: string;
  program_id: string;
  wbs_id: string | null;
  name: string;
  code: string;
  description: string | null;
  duration: number;
  remaining_duration: number | null;
  percent_complete: string;
  budgeted_cost: string;
  actual_cost: string;
  constraint_type: string | null;
  constraint_date: string | null;
  early_start: number | null;
  early_finish: number | null;
  late_start: number | null;
  late_finish: number | null;
  total_float: number | null;
  free_float: number | null;
  is_critical: boolean;
  is_milestone: boolean;
  actual_start: string | null;
  actual_finish: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface ActivityCreate {
  program_id: string;
  wbs_id?: string | null;
  name: string;
  code: string;
  description?: string;
  duration: number;
  percent_complete?: string;
  budgeted_cost?: string;
  actual_cost?: string;
  constraint_type?: string;
  constraint_date?: string;
  is_milestone?: boolean;
}

export interface ActivityUpdate {
  name?: string;
  code?: string;
  description?: string | null;
  duration?: number;
  wbs_id?: string | null;
  percent_complete?: string;
  budgeted_cost?: string;
  actual_cost?: string;
  constraint_type?: string | null;
  constraint_date?: string | null;
  is_milestone?: boolean;
}

export interface ActivityListResponse {
  items: Activity[];
  total: number;
}
