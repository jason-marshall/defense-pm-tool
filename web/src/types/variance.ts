export type VarianceType = "schedule" | "cost";

export interface VarianceExplanationCreate {
  program_id: string;
  wbs_id?: string | null;
  period_id?: string | null;
  variance_type: VarianceType;
  variance_amount: string;
  variance_percent: string;
  explanation: string;
  corrective_action?: string | null;
  expected_resolution?: string | null;
  create_jira_issue?: boolean;
}

export interface VarianceExplanationUpdate {
  explanation?: string;
  corrective_action?: string | null;
  expected_resolution?: string | null;
  variance_amount?: string;
  variance_percent?: string;
}

export interface VarianceExplanationResponse {
  id: string;
  program_id: string;
  wbs_id: string | null;
  period_id: string | null;
  created_by: string | null;
  variance_type: string;
  variance_amount: string;
  variance_percent: string;
  explanation: string;
  corrective_action: string | null;
  expected_resolution: string | null;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
}

export interface VarianceExplanationListResponse {
  items: VarianceExplanationResponse[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}
