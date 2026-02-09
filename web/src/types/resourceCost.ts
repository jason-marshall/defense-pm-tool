export interface ActivityCostResponse {
  activity_id: string;
  activity_code: string;
  activity_name: string;
  planned_cost: string;
  actual_cost: string;
  cost_variance: string;
  percent_spent: string;
  resource_breakdown: ResourceCostBreakdown[];
}

export interface ResourceCostBreakdown {
  resource_id: string;
  resource_name: string;
  resource_type: string;
  planned_cost: string;
  actual_cost: string;
}

export interface WBSCostResponse {
  wbs_id: string;
  wbs_code: string;
  wbs_name: string;
  planned_cost: string;
  actual_cost: string;
  cost_variance: string;
  activity_count: number;
}

export interface ProgramCostSummaryResponse {
  program_id: string;
  total_planned_cost: string;
  total_actual_cost: string;
  total_cost_variance: string;
  labor_cost: string;
  equipment_cost: string;
  material_cost: string;
  resource_count: number;
  activity_count: number;
  wbs_breakdown: WBSCostResponse[];
}

export interface EVMSSyncResponse {
  period_id: string;
  acwp_updated: string;
  wbs_elements_updated: number;
  success: boolean;
  warnings: string[];
}

export interface CostEntryCreate {
  entry_date: string;
  hours_worked: number;
  quantity_used?: number;
  notes?: string;
}

export interface CostEntryResponse {
  id: string;
  assignment_id: string;
  entry_date: string;
  hours_worked: string;
  cost_incurred: string;
  quantity_used: string | null;
  notes: string | null;
  created_at: string;
}
