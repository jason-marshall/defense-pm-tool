export interface ManagementReserveStatus {
  program_id: string;
  current_balance: string;
  initial_mr: string;
  total_changes_in: string;
  total_changes_out: string;
  change_count: number;
  last_change_at: string | null;
}

export interface ManagementReserveChangeCreate {
  period_id?: string | null;
  changes_in: string;
  changes_out: string;
  reason?: string | null;
}

export interface ManagementReserveLogResponse {
  id: string;
  program_id: string;
  period_id: string | null;
  beginning_mr: string;
  changes_in: string;
  changes_out: string;
  ending_mr: string;
  reason: string | null;
  approved_by: string | null;
  created_at: string;
}

export interface ManagementReserveHistoryResponse {
  items: ManagementReserveLogResponse[];
  total: number;
  program_id: string;
  current_balance: string;
}
