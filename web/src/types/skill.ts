export interface SkillCreate {
  name: string;
  code: string;
  category?: string;
  description?: string | null;
  is_active?: boolean;
  requires_certification?: boolean;
  certification_expiry_months?: number | null;
  program_id?: string | null;
}

export interface SkillUpdate {
  name?: string;
  code?: string;
  category?: string;
  description?: string | null;
  is_active?: boolean;
  requires_certification?: boolean;
  certification_expiry_months?: number | null;
}

export interface SkillResponse {
  id: string;
  name: string;
  code: string;
  category: string;
  description: string | null;
  is_active: boolean;
  requires_certification: boolean;
  certification_expiry_months: number | null;
  program_id: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface SkillListResponse {
  items: SkillResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface ResourceSkillCreate {
  skill_id: string;
  proficiency_level?: number;
  is_certified?: boolean;
  certification_date?: string | null;
  notes?: string | null;
}

export interface ResourceSkillUpdate {
  proficiency_level?: number;
  is_certified?: boolean;
  certification_date?: string | null;
  notes?: string | null;
}

export interface ResourceSkillResponse {
  id: string;
  resource_id: string;
  skill_id: string;
  proficiency_level: number;
  is_certified: boolean;
  certification_date: string | null;
  certification_expires_at: string | null;
  verified_by: string | null;
  verified_at: string | null;
  notes: string | null;
  skill: SkillResponse | null;
}

export interface SkillRequirementCreate {
  skill_id: string;
  required_level?: number;
  is_mandatory?: boolean;
}

export interface SkillRequirementResponse {
  id: string;
  activity_id: string;
  skill_id: string;
  required_level: number;
  is_mandatory: boolean;
  skill: SkillResponse | null;
}
