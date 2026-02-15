import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import {
  useJiraIntegration,
  useCreateJiraIntegration,
  useUpdateJiraIntegration,
  useDeleteJiraIntegration,
  useTestJiraConnection,
  useSyncJira,
  useJiraMappings,
  useCreateJiraMapping,
  useDeleteJiraMapping,
  useJiraSyncLogs,
} from "./useJira";

vi.mock("@/services/jiraApi", () => ({
  getIntegrationByProgram: vi.fn(),
  createIntegration: vi.fn(),
  updateIntegration: vi.fn(),
  deleteIntegration: vi.fn(),
  testConnection: vi.fn(),
  syncWbs: vi.fn(),
  syncActivities: vi.fn(),
  syncProgress: vi.fn(),
  getMappings: vi.fn(),
  createMapping: vi.fn(),
  deleteMapping: vi.fn(),
  getSyncLogs: vi.fn(),
}));

import {
  getIntegrationByProgram,
  createIntegration,
  updateIntegration,
  deleteIntegration,
  testConnection,
  syncWbs,
  syncActivities,
  syncProgress,
  getMappings,
  createMapping,
  deleteMapping,
  getSyncLogs,
} from "@/services/jiraApi";

const createQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

let queryClient: QueryClient;

const wrapper = ({ children }: { children: React.ReactNode }) =>
  React.createElement(QueryClientProvider, { client: queryClient }, children);

const mockIntegration = {
  id: "jira-1",
  program_id: "prog-1",
  jira_url: "https://jira.example.com",
  email: "user@example.com",
  project_key: "PROJ",
  sync_enabled: true,
  sync_direction: "TO_JIRA" as const,
  last_sync_at: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: null,
};

const mockMapping = {
  id: "map-1",
  integration_id: "jira-1",
  entity_type: "ACTIVITY" as const,
  local_id: "act-1",
  jira_issue_key: "PROJ-1",
  jira_issue_id: "10001",
  last_synced_at: null,
  created_at: "2026-01-01T00:00:00Z",
};

const mockSyncLog = {
  id: "log-1",
  integration_id: "jira-1",
  sync_type: "PUSH" as const,
  status: "SUCCESS" as const,
  items_synced: 5,
  items_failed: 0,
  error_message: null,
  started_at: "2026-01-01T00:00:00Z",
  completed_at: "2026-01-01T00:01:00Z",
};

describe("useJiraIntegration", () => {
  beforeEach(() => {
    queryClient = createQueryClient();
    vi.clearAllMocks();
  });

  it("fetches Jira integration for a program", async () => {
    vi.mocked(getIntegrationByProgram).mockResolvedValue(mockIntegration);

    const { result } = renderHook(() => useJiraIntegration("prog-1"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(getIntegrationByProgram).toHaveBeenCalledWith("prog-1");
    expect(result.current.data?.project_key).toBe("PROJ");
  });

  it("does not fetch when programId is empty", () => {
    renderHook(() => useJiraIntegration(""), { wrapper });
    expect(getIntegrationByProgram).not.toHaveBeenCalled();
  });

  it("starts in loading state when enabled", () => {
    vi.mocked(getIntegrationByProgram).mockReturnValue(new Promise(() => {}));

    const { result } = renderHook(() => useJiraIntegration("prog-1"), { wrapper });

    expect(result.current.isLoading).toBe(true);
    expect(result.current.data).toBeUndefined();
  });

  it("handles fetch error", async () => {
    vi.mocked(getIntegrationByProgram).mockRejectedValue(new Error("Not found"));

    const { result } = renderHook(() => useJiraIntegration("prog-1"), { wrapper });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toBeInstanceOf(Error);
  });

  it("is disabled when programId is empty string", () => {
    const { result } = renderHook(() => useJiraIntegration(""), { wrapper });

    expect(result.current.fetchStatus).toBe("idle");
    expect(getIntegrationByProgram).not.toHaveBeenCalled();
  });
});

describe("useCreateJiraIntegration", () => {
  beforeEach(() => {
    queryClient = createQueryClient();
    vi.clearAllMocks();
  });

  it("creates a Jira integration", async () => {
    vi.mocked(createIntegration).mockResolvedValue(mockIntegration);

    const { result } = renderHook(() => useCreateJiraIntegration(), { wrapper });

    result.current.mutate({
      program_id: "prog-1",
      jira_url: "https://jira.example.com",
      project_key: "PROJ",
      api_token: "token",
      email: "user@example.com",
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(createIntegration).toHaveBeenCalled();
  });

  it("handles create error", async () => {
    vi.mocked(createIntegration).mockRejectedValue(new Error("Duplicate integration"));

    const { result } = renderHook(() => useCreateJiraIntegration(), { wrapper });

    result.current.mutate({
      program_id: "prog-1",
      jira_url: "https://jira.example.com",
      project_key: "PROJ",
      api_token: "token",
      email: "user@example.com",
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect((result.current.error as Error).message).toBe("Duplicate integration");
  });

  it("invalidates integration query on success", async () => {
    vi.mocked(createIntegration).mockResolvedValue(mockIntegration);
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    const { result } = renderHook(() => useCreateJiraIntegration(), { wrapper });

    result.current.mutate({
      program_id: "prog-1",
      jira_url: "https://jira.example.com",
      project_key: "PROJ",
      api_token: "token",
      email: "user@example.com",
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ["jira", "integration", "prog-1"],
    });
  });

  it("creates with optional sync fields", async () => {
    vi.mocked(createIntegration).mockResolvedValue(mockIntegration);

    const { result } = renderHook(() => useCreateJiraIntegration(), { wrapper });

    result.current.mutate({
      program_id: "prog-1",
      jira_url: "https://jira.example.com",
      project_key: "PROJ",
      api_token: "token",
      email: "user@example.com",
      sync_enabled: true,
      sync_direction: "BIDIRECTIONAL",
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(createIntegration).toHaveBeenCalledWith(
      expect.objectContaining({
        sync_enabled: true,
        sync_direction: "BIDIRECTIONAL",
      })
    );
  });

  it("starts in idle state", () => {
    const { result } = renderHook(() => useCreateJiraIntegration(), { wrapper });

    expect(result.current.isIdle).toBe(true);
    expect(result.current.data).toBeUndefined();
  });
});

describe("useUpdateJiraIntegration", () => {
  beforeEach(() => {
    queryClient = createQueryClient();
    vi.clearAllMocks();
  });

  it("updates a Jira integration", async () => {
    vi.mocked(updateIntegration).mockResolvedValue({
      ...mockIntegration,
      project_key: "NEWPROJ",
    });

    const { result } = renderHook(() => useUpdateJiraIntegration(), { wrapper });

    result.current.mutate({
      integrationId: "jira-1",
      data: { project_key: "NEWPROJ" },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(updateIntegration).toHaveBeenCalledWith("jira-1", {
      project_key: "NEWPROJ",
    });
  });

  it("handles update error", async () => {
    vi.mocked(updateIntegration).mockRejectedValue(new Error("Update failed"));

    const { result } = renderHook(() => useUpdateJiraIntegration(), { wrapper });

    result.current.mutate({
      integrationId: "jira-1",
      data: { project_key: "BAD" },
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect((result.current.error as Error).message).toBe("Update failed");
  });

  it("invalidates jira queries on success", async () => {
    vi.mocked(updateIntegration).mockResolvedValue(mockIntegration);
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    const { result } = renderHook(() => useUpdateJiraIntegration(), { wrapper });

    result.current.mutate({
      integrationId: "jira-1",
      data: { sync_enabled: false },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["jira"] });
  });

  it("updates multiple fields at once", async () => {
    vi.mocked(updateIntegration).mockResolvedValue(mockIntegration);

    const { result } = renderHook(() => useUpdateJiraIntegration(), { wrapper });

    result.current.mutate({
      integrationId: "jira-1",
      data: {
        jira_url: "https://new-jira.example.com",
        project_key: "NEWPROJ",
        sync_enabled: false,
        sync_direction: "FROM_JIRA",
      },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(updateIntegration).toHaveBeenCalledWith("jira-1", {
      jira_url: "https://new-jira.example.com",
      project_key: "NEWPROJ",
      sync_enabled: false,
      sync_direction: "FROM_JIRA",
    });
  });

  it("starts in idle state", () => {
    const { result } = renderHook(() => useUpdateJiraIntegration(), { wrapper });

    expect(result.current.isIdle).toBe(true);
    expect(result.current.data).toBeUndefined();
  });
});

describe("useDeleteJiraIntegration", () => {
  beforeEach(() => {
    queryClient = createQueryClient();
    vi.clearAllMocks();
  });

  it("deletes a Jira integration", async () => {
    vi.mocked(deleteIntegration).mockResolvedValue(undefined);

    const { result } = renderHook(() => useDeleteJiraIntegration(), { wrapper });

    result.current.mutate("jira-1");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(deleteIntegration).toHaveBeenCalledWith("jira-1");
  });

  it("handles delete error", async () => {
    vi.mocked(deleteIntegration).mockRejectedValue(new Error("Cannot delete"));

    const { result } = renderHook(() => useDeleteJiraIntegration(), { wrapper });

    result.current.mutate("jira-1");

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect((result.current.error as Error).message).toBe("Cannot delete");
  });

  it("invalidates jira queries on success", async () => {
    vi.mocked(deleteIntegration).mockResolvedValue(undefined);
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    const { result } = renderHook(() => useDeleteJiraIntegration(), { wrapper });

    result.current.mutate("jira-1");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["jira"] });
  });
});

describe("useTestJiraConnection", () => {
  beforeEach(() => {
    queryClient = createQueryClient();
    vi.clearAllMocks();
  });

  it("tests Jira connection", async () => {
    vi.mocked(testConnection).mockResolvedValue({
      success: true,
      message: "Connected",
      project_name: "My Project",
    });

    const { result } = renderHook(() => useTestJiraConnection(), { wrapper });

    result.current.mutate("jira-1");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(testConnection).toHaveBeenCalledWith("jira-1");
    expect(result.current.data?.success).toBe(true);
    expect(result.current.data?.project_name).toBe("My Project");
  });

  it("handles connection test failure", async () => {
    vi.mocked(testConnection).mockRejectedValue(new Error("Connection refused"));

    const { result } = renderHook(() => useTestJiraConnection(), { wrapper });

    result.current.mutate("jira-1");

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect((result.current.error as Error).message).toBe("Connection refused");
  });

  it("returns failed connection result", async () => {
    vi.mocked(testConnection).mockResolvedValue({
      success: false,
      message: "Invalid credentials",
      project_name: null,
    });

    const { result } = renderHook(() => useTestJiraConnection(), { wrapper });

    result.current.mutate("jira-1");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.success).toBe(false);
    expect(result.current.data?.project_name).toBeNull();
  });

  it("starts in idle state", () => {
    const { result } = renderHook(() => useTestJiraConnection(), { wrapper });

    expect(result.current.isIdle).toBe(true);
    expect(result.current.data).toBeUndefined();
  });
});

describe("useSyncJira", () => {
  beforeEach(() => {
    queryClient = createQueryClient();
    vi.clearAllMocks();
  });

  it("syncs WBS to Jira", async () => {
    vi.mocked(syncWbs).mockResolvedValue({
      sync_type: "PUSH",
      status: "SUCCESS",
      total_items: 5,
      synced: 5,
      failed: 0,
      errors: [],
    });

    const { result } = renderHook(() => useSyncJira(), { wrapper });

    result.current.mutate({ integrationId: "jira-1", type: "wbs" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(syncWbs).toHaveBeenCalledWith("jira-1");
    expect(syncActivities).not.toHaveBeenCalled();
    expect(syncProgress).not.toHaveBeenCalled();
  });

  it("syncs activities to Jira", async () => {
    vi.mocked(syncActivities).mockResolvedValue({
      sync_type: "PUSH",
      status: "SUCCESS",
      total_items: 10,
      synced: 10,
      failed: 0,
      errors: [],
    });

    const { result } = renderHook(() => useSyncJira(), { wrapper });

    result.current.mutate({ integrationId: "jira-1", type: "activities" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(syncActivities).toHaveBeenCalledWith("jira-1");
    expect(syncWbs).not.toHaveBeenCalled();
    expect(syncProgress).not.toHaveBeenCalled();
  });

  it("syncs progress to Jira", async () => {
    vi.mocked(syncProgress).mockResolvedValue({
      sync_type: "PUSH",
      status: "SUCCESS",
      total_items: 8,
      synced: 8,
      failed: 0,
      errors: [],
    });

    const { result } = renderHook(() => useSyncJira(), { wrapper });

    result.current.mutate({ integrationId: "jira-1", type: "progress" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(syncProgress).toHaveBeenCalledWith("jira-1");
    expect(syncWbs).not.toHaveBeenCalled();
    expect(syncActivities).not.toHaveBeenCalled();
  });

  it("handles sync error", async () => {
    vi.mocked(syncWbs).mockRejectedValue(new Error("Sync failed"));

    const { result } = renderHook(() => useSyncJira(), { wrapper });

    result.current.mutate({ integrationId: "jira-1", type: "wbs" });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect((result.current.error as Error).message).toBe("Sync failed");
  });

  it("handles activities sync error", async () => {
    vi.mocked(syncActivities).mockRejectedValue(new Error("Activity sync failed"));

    const { result } = renderHook(() => useSyncJira(), { wrapper });

    result.current.mutate({ integrationId: "jira-1", type: "activities" });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect((result.current.error as Error).message).toBe("Activity sync failed");
  });

  it("handles progress sync error", async () => {
    vi.mocked(syncProgress).mockRejectedValue(new Error("Progress sync failed"));

    const { result } = renderHook(() => useSyncJira(), { wrapper });

    result.current.mutate({ integrationId: "jira-1", type: "progress" });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect((result.current.error as Error).message).toBe("Progress sync failed");
  });

  it("invalidates jira queries on success", async () => {
    vi.mocked(syncWbs).mockResolvedValue({
      sync_type: "PUSH",
      status: "SUCCESS",
      total_items: 5,
      synced: 5,
      failed: 0,
      errors: [],
    });
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    const { result } = renderHook(() => useSyncJira(), { wrapper });

    result.current.mutate({ integrationId: "jira-1", type: "wbs" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["jira"] });
  });

  it("returns partial sync result", async () => {
    vi.mocked(syncActivities).mockResolvedValue({
      sync_type: "PUSH",
      status: "PARTIAL",
      total_items: 10,
      synced: 7,
      failed: 3,
      errors: ["Activity ACT-001 not found in Jira", "ACT-002 mapping conflict"],
    });

    const { result } = renderHook(() => useSyncJira(), { wrapper });

    result.current.mutate({ integrationId: "jira-1", type: "activities" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.status).toBe("PARTIAL");
    expect(result.current.data?.failed).toBe(3);
    expect(result.current.data?.errors).toHaveLength(2);
  });

  it("starts in idle state", () => {
    const { result } = renderHook(() => useSyncJira(), { wrapper });

    expect(result.current.isIdle).toBe(true);
    expect(result.current.data).toBeUndefined();
  });
});

describe("useJiraMappings", () => {
  beforeEach(() => {
    queryClient = createQueryClient();
    vi.clearAllMocks();
  });

  it("fetches Jira mappings", async () => {
    vi.mocked(getMappings).mockResolvedValue([mockMapping]);

    const { result } = renderHook(() => useJiraMappings("jira-1"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(getMappings).toHaveBeenCalledWith("jira-1");
    expect(result.current.data).toHaveLength(1);
    expect(result.current.data?.[0].jira_issue_key).toBe("PROJ-1");
  });

  it("does not fetch when integrationId is empty", () => {
    renderHook(() => useJiraMappings(""), { wrapper });
    expect(getMappings).not.toHaveBeenCalled();
  });

  it("returns empty array when no mappings exist", async () => {
    vi.mocked(getMappings).mockResolvedValue([]);

    const { result } = renderHook(() => useJiraMappings("jira-1"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toHaveLength(0);
  });

  it("handles fetch error", async () => {
    vi.mocked(getMappings).mockRejectedValue(new Error("Forbidden"));

    const { result } = renderHook(() => useJiraMappings("jira-1"), { wrapper });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });

  it("starts in loading state when enabled", () => {
    vi.mocked(getMappings).mockReturnValue(new Promise(() => {}));

    const { result } = renderHook(() => useJiraMappings("jira-1"), { wrapper });

    expect(result.current.isLoading).toBe(true);
  });

  it("is disabled when integrationId is empty string", () => {
    const { result } = renderHook(() => useJiraMappings(""), { wrapper });

    expect(result.current.fetchStatus).toBe("idle");
  });
});

describe("useCreateJiraMapping", () => {
  beforeEach(() => {
    queryClient = createQueryClient();
    vi.clearAllMocks();
  });

  it("creates a Jira mapping", async () => {
    vi.mocked(createMapping).mockResolvedValue(mockMapping);

    const { result } = renderHook(() => useCreateJiraMapping(), { wrapper });

    result.current.mutate({
      integrationId: "jira-1",
      data: { entity_type: "ACTIVITY", local_id: "act-1", jira_issue_key: "PROJ-1" },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(createMapping).toHaveBeenCalledWith("jira-1", {
      entity_type: "ACTIVITY",
      local_id: "act-1",
      jira_issue_key: "PROJ-1",
    });
  });

  it("handles create mapping error", async () => {
    vi.mocked(createMapping).mockRejectedValue(new Error("Mapping already exists"));

    const { result } = renderHook(() => useCreateJiraMapping(), { wrapper });

    result.current.mutate({
      integrationId: "jira-1",
      data: { entity_type: "ACTIVITY", local_id: "act-1", jira_issue_key: "PROJ-1" },
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect((result.current.error as Error).message).toBe("Mapping already exists");
  });

  it("invalidates mappings queries on success", async () => {
    vi.mocked(createMapping).mockResolvedValue(mockMapping);
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    const { result } = renderHook(() => useCreateJiraMapping(), { wrapper });

    result.current.mutate({
      integrationId: "jira-1",
      data: { entity_type: "WBS", local_id: "wbs-1", jira_issue_key: "PROJ-2" },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["jira", "mappings"] });
  });

  it("creates WBS mapping", async () => {
    const wbsMapping = {
      ...mockMapping,
      entity_type: "WBS" as const,
      local_id: "wbs-1",
      jira_issue_key: "PROJ-EPIC-1",
    };
    vi.mocked(createMapping).mockResolvedValue(wbsMapping);

    const { result } = renderHook(() => useCreateJiraMapping(), { wrapper });

    result.current.mutate({
      integrationId: "jira-1",
      data: { entity_type: "WBS", local_id: "wbs-1", jira_issue_key: "PROJ-EPIC-1" },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.entity_type).toBe("WBS");
  });
});

describe("useDeleteJiraMapping", () => {
  beforeEach(() => {
    queryClient = createQueryClient();
    vi.clearAllMocks();
  });

  it("deletes a Jira mapping", async () => {
    vi.mocked(deleteMapping).mockResolvedValue(undefined);

    const { result } = renderHook(() => useDeleteJiraMapping(), { wrapper });

    result.current.mutate("map-1");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(deleteMapping).toHaveBeenCalledWith("map-1");
  });

  it("handles delete mapping error", async () => {
    vi.mocked(deleteMapping).mockRejectedValue(new Error("Not found"));

    const { result } = renderHook(() => useDeleteJiraMapping(), { wrapper });

    result.current.mutate("map-999");

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect((result.current.error as Error).message).toBe("Not found");
  });

  it("invalidates mappings queries on success", async () => {
    vi.mocked(deleteMapping).mockResolvedValue(undefined);
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    const { result } = renderHook(() => useDeleteJiraMapping(), { wrapper });

    result.current.mutate("map-1");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["jira", "mappings"] });
  });
});

describe("useJiraSyncLogs", () => {
  beforeEach(() => {
    queryClient = createQueryClient();
    vi.clearAllMocks();
  });

  it("fetches sync logs", async () => {
    vi.mocked(getSyncLogs).mockResolvedValue({ items: [mockSyncLog], total: 1 });

    const { result } = renderHook(() => useJiraSyncLogs("jira-1"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(getSyncLogs).toHaveBeenCalledWith("jira-1", undefined);
    expect(result.current.data?.items).toHaveLength(1);
  });

  it("does not fetch when integrationId is empty", () => {
    renderHook(() => useJiraSyncLogs(""), { wrapper });
    expect(getSyncLogs).not.toHaveBeenCalled();
  });

  it("fetches sync logs with limit", async () => {
    vi.mocked(getSyncLogs).mockResolvedValue({ items: [mockSyncLog], total: 1 });

    const { result } = renderHook(() => useJiraSyncLogs("jira-1", 10), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(getSyncLogs).toHaveBeenCalledWith("jira-1", 10);
  });

  it("fetches sync logs with limit of 1", async () => {
    vi.mocked(getSyncLogs).mockResolvedValue({ items: [mockSyncLog], total: 1 });

    const { result } = renderHook(() => useJiraSyncLogs("jira-1", 1), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(getSyncLogs).toHaveBeenCalledWith("jira-1", 1);
  });

  it("returns empty logs list", async () => {
    vi.mocked(getSyncLogs).mockResolvedValue({ items: [], total: 0 });

    const { result } = renderHook(() => useJiraSyncLogs("jira-1"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.items).toHaveLength(0);
    expect(result.current.data?.total).toBe(0);
  });

  it("handles fetch error", async () => {
    vi.mocked(getSyncLogs).mockRejectedValue(new Error("Server error"));

    const { result } = renderHook(() => useJiraSyncLogs("jira-1"), { wrapper });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });

  it("starts in loading state when enabled", () => {
    vi.mocked(getSyncLogs).mockReturnValue(new Promise(() => {}));

    const { result } = renderHook(() => useJiraSyncLogs("jira-1"), { wrapper });

    expect(result.current.isLoading).toBe(true);
  });

  it("is disabled when integrationId is empty string", () => {
    const { result } = renderHook(() => useJiraSyncLogs(""), { wrapper });

    expect(result.current.fetchStatus).toBe("idle");
  });

  it("uses limit in query key for cache separation", async () => {
    vi.mocked(getSyncLogs).mockResolvedValue({ items: [], total: 0 });

    const { result: result5 } = renderHook(() => useJiraSyncLogs("jira-1", 5), {
      wrapper,
    });
    const { result: result10 } = renderHook(() => useJiraSyncLogs("jira-1", 10), {
      wrapper,
    });

    await waitFor(() => expect(result5.current.isSuccess).toBe(true));
    await waitFor(() => expect(result10.current.isSuccess).toBe(true));

    // Both should have been called with different limits
    expect(getSyncLogs).toHaveBeenCalledWith("jira-1", 5);
    expect(getSyncLogs).toHaveBeenCalledWith("jira-1", 10);
  });
});
