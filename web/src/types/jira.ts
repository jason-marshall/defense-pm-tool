export type SyncDirection = "TO_JIRA" | "FROM_JIRA" | "BIDIRECTIONAL";
export type EntityType = "WBS" | "ACTIVITY";
export type SyncType = "PUSH" | "PULL" | "WEBHOOK" | "FULL";
export type SyncStatus = "SUCCESS" | "FAILED" | "PARTIAL";

export interface JiraIntegrationCreate {
  program_id: string;
  jira_url: string;
  email: string;
  api_token: string;
  project_key: string;
  sync_enabled?: boolean;
  sync_direction?: SyncDirection;
}

export interface JiraIntegrationUpdate {
  jira_url?: string;
  email?: string;
  api_token?: string;
  project_key?: string;
  sync_enabled?: boolean;
  sync_direction?: SyncDirection;
}

export interface JiraIntegrationResponse {
  id: string;
  program_id: string;
  jira_url: string;
  email: string;
  project_key: string;
  sync_enabled: boolean;
  sync_direction: SyncDirection;
  last_sync_at: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface JiraMappingCreate {
  entity_type: EntityType;
  local_id: string;
  jira_issue_key: string;
}

export interface JiraMappingResponse {
  id: string;
  integration_id: string;
  entity_type: EntityType;
  local_id: string;
  jira_issue_key: string;
  jira_issue_id: string | null;
  last_synced_at: string | null;
  created_at: string;
}

export interface JiraSyncResponse {
  sync_type: SyncType;
  status: SyncStatus;
  total_items: number;
  synced: number;
  failed: number;
  errors: string[];
}

export interface JiraSyncLogResponse {
  id: string;
  integration_id: string;
  sync_type: SyncType;
  status: SyncStatus;
  items_synced: number;
  items_failed: number;
  error_message: string | null;
  started_at: string;
  completed_at: string | null;
}

export interface JiraSyncLogListResponse {
  items: JiraSyncLogResponse[];
  total: number;
}

export interface JiraConnectionTestResponse {
  success: boolean;
  message: string;
  project_name: string | null;
}
