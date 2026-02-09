export type ProgramStatus = "PLANNING" | "ACTIVE" | "ON_HOLD" | "COMPLETED" | "CANCELLED";

export interface Program {
  id: string;
  name: string;
  code: string;
  description: string | null;
  status: ProgramStatus;
  planned_start_date: string;
  planned_end_date: string;
  actual_start_date: string | null;
  actual_end_date: string | null;
  budget_at_completion: string;
  contract_number: string | null;
  contract_type: string | null;
  owner_id: string;
  created_at: string;
  updated_at: string | null;
}

export interface ProgramCreate {
  name: string;
  code: string;
  description?: string;
  status?: ProgramStatus;
  planned_start_date: string;
  planned_end_date: string;
  budget_at_completion?: string;
  contract_number?: string;
  contract_type?: string;
}

export interface ProgramUpdate {
  name?: string;
  code?: string;
  description?: string | null;
  status?: ProgramStatus;
  planned_start_date?: string;
  planned_end_date?: string;
  budget_at_completion?: string;
  contract_number?: string;
  contract_type?: string;
}

export interface ProgramListResponse {
  items: Program[];
  total: number;
  page: number;
  page_size: number;
}
