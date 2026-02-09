export interface MonteCarloConfig {
  iterations: number;
  distribution_type: "triangular" | "pert" | "normal" | "uniform";
  confidence_levels?: number[];
  include_cost?: boolean;
  correlation_enabled?: boolean;
}

export interface MonteCarloResult {
  id: string;
  program_id: string;
  config: MonteCarloConfig;
  status: "running" | "completed" | "failed";
  duration_results: DurationResults | null;
  cost_results: CostResults | null;
  sensitivity: SensitivityItem[];
  s_curve_data: SCurveDataPoint[];
  created_at: string;
}

export interface DurationResults {
  mean: number;
  std_dev: number;
  min: number;
  max: number;
  p10: number;
  p25: number;
  p50: number;
  p75: number;
  p80: number;
  p90: number;
  p95: number;
  histogram: HistogramBin[];
}

export interface CostResults {
  mean: string;
  p50: string;
  p80: string;
  p90: string;
}

export interface HistogramBin {
  bin_start: number;
  bin_end: number;
  count: number;
  frequency: number;
}

export interface SensitivityItem {
  activity_id: string;
  activity_name: string;
  correlation: number;
  criticality_index: number;
}

export interface SCurveDataPoint {
  period: string;
  bcws: string;
  bcwp: string;
  acwp: string;
  bcws_optimistic?: string;
  bcws_pessimistic?: string;
}
