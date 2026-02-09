export enum PoolAccessLevel {
  VIEWER = "VIEWER",
  EDITOR = "EDITOR",
  MANAGER = "MANAGER",
}

export interface ResourcePoolCreate {
  name: string;
  code: string;
  description?: string;
}

export interface ResourcePoolUpdate {
  name?: string;
  description?: string;
  is_active?: boolean;
}

export interface ResourcePoolResponse {
  id: string;
  name: string;
  code: string;
  description: string | null;
  owner_id: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface PoolMemberCreate {
  resource_id: string;
  allocation_percentage?: number;
}

export interface PoolMemberResponse {
  id: string;
  pool_id: string;
  resource_id: string;
  allocation_percentage: string;
  is_active: boolean;
  created_at: string;
}

export interface PoolAccessCreate {
  program_id: string;
  access_level: PoolAccessLevel;
}

export interface PoolAccessResponse {
  id: string;
  pool_id: string;
  program_id: string;
  access_level: PoolAccessLevel;
  granted_by: string | null;
  granted_at: string;
}

export interface PoolAvailabilityResource {
  resource_id: string;
  resource_name: string;
  available_hours: number;
  assigned_hours: number;
}

export interface PoolConflict {
  resource_id: string;
  resource_name: string;
  conflict_date: string;
  programs_involved: string[];
  overallocation_hours: number;
}

export interface PoolAvailabilityResponse {
  pool_id: string;
  pool_name: string;
  date_range_start: string;
  date_range_end: string;
  resources: PoolAvailabilityResource[];
  conflict_count: number;
  conflicts: PoolConflict[];
}

export interface ConflictCheckRequest {
  resource_id: string;
  program_id: string;
  start_date: string;
  end_date: string;
  units?: number;
}

export interface ConflictCheckResponse {
  has_conflicts: boolean;
  conflict_count: number;
  conflicts: Array<{
    date: string;
    programs: string[];
    overallocation_hours: number;
  }>;
}
