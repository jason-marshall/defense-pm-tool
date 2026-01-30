export interface ResourceAssignment {
  id: string;
  activity_id: string;
  resource_id: string;
  units: number;
  start_date: string | null;
  finish_date: string | null;
  resource?: {
    id: string;
    code: string;
    name: string;
    resource_type: string;
  };
}

export interface AssignmentCreate {
  activity_id: string;
  resource_id: string;
  units?: number;
  start_date?: string;
  finish_date?: string;
}

export interface AssignmentUpdate {
  units?: number;
  start_date?: string;
  finish_date?: string;
}
