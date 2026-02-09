export type CPRFormat = "format1" | "format3" | "format5";

export interface CPRFormat1Row {
  wbs_code: string;
  wbs_name: string;
  bcws: string;
  bcwp: string;
  acwp: string;
  cv: string;
  sv: string;
  cv_percent: string;
  sv_percent: string;
}

export interface CPRFormat1Report {
  program_id: string;
  program_name: string;
  reporting_period: string;
  rows: CPRFormat1Row[];
  totals: CPRFormat1Row;
}

export interface CPRFormat3Period {
  period: string;
  bcws: string;
  bcwp: string;
  acwp: string;
}

export interface CPRFormat3Report {
  program_id: string;
  program_name: string;
  periods: CPRFormat3Period[];
  cumulative: CPRFormat3Period[];
}

export interface CPRFormat5Item {
  wbs_code: string;
  wbs_name: string;
  variance_type: string;
  variance_amount: string;
  explanation: string;
  corrective_action: string | null;
}

export interface CPRFormat5Report {
  program_id: string;
  program_name: string;
  items: CPRFormat5Item[];
}

export interface ReportAuditEntry {
  id: string;
  report_type: string;
  generated_at: string;
  generated_by: string;
  parameters: Record<string, string>;
}
