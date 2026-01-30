export enum ResourceType {
  LABOR = "LABOR",
  EQUIPMENT = "EQUIPMENT",
  MATERIAL = "MATERIAL",
}

export interface Resource {
  id: string;
  program_id: string;
  name: string;
  code: string;
  resource_type: ResourceType;
  capacity_per_day: number;
  cost_rate: number | null;
  effective_date: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface ResourceCreate {
  program_id: string;
  name: string;
  code: string;
  resource_type: ResourceType;
  capacity_per_day?: number;
  cost_rate?: number;
  effective_date?: string;
  is_active?: boolean;
}

export interface ResourceUpdate {
  name?: string;
  code?: string;
  resource_type?: ResourceType;
  capacity_per_day?: number;
  cost_rate?: number;
  effective_date?: string;
  is_active?: boolean;
}

export interface ResourceListResponse {
  items: Resource[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}
