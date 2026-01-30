export interface CalendarPreview {
  uid: number;
  name: string;
  is_base: boolean;
  working_days: number[];
  hours_per_day: number;
  holidays: number;
}

export interface ResourceMapping {
  ms_project_resource: string;
  matched_resource_id: string | null;
  matched_resource_name: string | null;
  calendar_name: string;
}

export interface CalendarImportPreviewResponse {
  calendars: CalendarPreview[];
  resource_mappings: ResourceMapping[];
  total_holidays: number;
  date_range_start: string;
  date_range_end: string;
  warnings: string[];
}

export interface CalendarImportResponse {
  success: boolean;
  resources_updated: number;
  calendar_entries_created: number;
  templates_created: number;
  warnings: string[];
}
