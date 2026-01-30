export interface HistogramDataPoint {
  date: string;
  available_hours: number;
  assigned_hours: number;
  utilization_percent: number;
  is_overallocated: boolean;
}

export interface ResourceHistogramData {
  resource_id: string;
  resource_code: string;
  resource_name: string;
  resource_type: string;
  start_date: string;
  end_date: string;
  data_points: HistogramDataPoint[];
  peak_utilization: number;
  peak_date: string | null;
  average_utilization: number;
  overallocated_days: number;
  total_available_hours: number;
  total_assigned_hours: number;
}

export interface ProgramHistogramSummary {
  program_id: string;
  start_date: string;
  end_date: string;
  resource_count: number;
  total_overallocated_days: number;
  resources_with_overallocation: number;
}

export interface ProgramHistogramResponse {
  summary: ProgramHistogramSummary;
  histograms: ResourceHistogramData[];
}
