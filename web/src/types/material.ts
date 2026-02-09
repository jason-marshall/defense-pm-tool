export interface MaterialStatusResponse {
  resource_id: string;
  resource_code: string;
  resource_name: string;
  quantity_unit: string;
  quantity_available: string;
  quantity_assigned: string;
  quantity_consumed: string;
  quantity_remaining: string;
  percent_consumed: string;
  unit_cost: string;
  total_value: string;
  consumed_value: string;
}

export interface MaterialConsumptionRequest {
  quantity: number;
}

export interface MaterialConsumptionResponse {
  assignment_id: string;
  quantity_consumed: string;
  remaining_assigned: string;
  cost_incurred: string;
}

export interface ProgramMaterialSummaryResponse {
  program_id: string;
  material_count: number;
  total_value: string;
  consumed_value: string;
  remaining_value: string;
  materials: MaterialStatusResponse[];
}
