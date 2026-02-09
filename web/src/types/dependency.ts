export type DependencyType = "FS" | "SS" | "FF" | "SF";

export interface Dependency {
  id: string;
  predecessor_id: string;
  successor_id: string;
  dependency_type: DependencyType;
  lag: number;
  predecessor_name?: string;
  successor_name?: string;
  created_at: string;
  updated_at: string | null;
}

export interface DependencyCreate {
  predecessor_id: string;
  successor_id: string;
  dependency_type: DependencyType;
  lag?: number;
}

export interface DependencyUpdate {
  dependency_type?: DependencyType;
  lag?: number;
}

export interface DependencyListResponse {
  items: Dependency[];
  total: number;
}
