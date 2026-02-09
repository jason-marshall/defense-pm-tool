export type BaselineStatus = "draft" | "approved" | "superseded";

export interface Baseline {
  id: string;
  program_id: string;
  name: string;
  description: string | null;
  status: BaselineStatus;
  baseline_number: number;
  snapshot_data: Record<string, unknown>;
  approved_by: string | null;
  approved_at: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface BaselineCreate {
  program_id: string;
  name: string;
  description?: string;
}

export interface BaselineComparison {
  baseline_a: { id: string; name: string };
  baseline_b: { id: string; name: string };
  deltas: BaselineDelta[];
}

export interface BaselineDelta {
  field: string;
  activity_code: string;
  activity_name: string;
  value_a: string;
  value_b: string;
  change_percent: string;
}

export interface BaselineListResponse {
  items: Baseline[];
  total: number;
}
