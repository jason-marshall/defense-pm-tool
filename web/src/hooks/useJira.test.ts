import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import {
  useJiraIntegration,
  useCreateJiraIntegration,
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
  deleteIntegration,
  testConnection,
  syncWbs,
  getMappings,
  createMapping,
  deleteMapping,
  getSyncLogs,
} from "@/services/jiraApi";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

const wrapper = ({ children }: { children: React.ReactNode }) =>
  React.createElement(QueryClientProvider, { client: queryClient }, children);

describe("useJiraIntegration", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("fetches Jira integration for a program", async () => {
    const mockIntegration = { id: "jira-1", project_key: "PROJ" };
    vi.mocked(getIntegrationByProgram).mockResolvedValue(mockIntegration);

    const { result } = renderHook(() => useJiraIntegration("prog-1"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(getIntegrationByProgram).toHaveBeenCalledWith("prog-1");
  });

  it("does not fetch when programId is empty", () => {
    renderHook(() => useJiraIntegration(""), { wrapper });
    expect(getIntegrationByProgram).not.toHaveBeenCalled();
  });
});

describe("useCreateJiraIntegration", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("creates a Jira integration", async () => {
    vi.mocked(createIntegration).mockResolvedValue({ id: "jira-1" });

    const { result } = renderHook(() => useCreateJiraIntegration(), { wrapper });

    result.current.mutate({
      program_id: "prog-1",
      jira_url: "https://jira.example.com",
      project_key: "PROJ",
      api_token: "token",
      username: "user@example.com",
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(createIntegration).toHaveBeenCalled();
  });
});

describe("useDeleteJiraIntegration", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("deletes a Jira integration", async () => {
    vi.mocked(deleteIntegration).mockResolvedValue(undefined);

    const { result } = renderHook(() => useDeleteJiraIntegration(), { wrapper });

    result.current.mutate("jira-1");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(deleteIntegration).toHaveBeenCalledWith("jira-1");
  });
});

describe("useTestJiraConnection", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("tests Jira connection", async () => {
    vi.mocked(testConnection).mockResolvedValue({ success: true });

    const { result } = renderHook(() => useTestJiraConnection(), { wrapper });

    result.current.mutate("jira-1");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(testConnection).toHaveBeenCalledWith("jira-1");
  });
});

describe("useSyncJira", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("syncs WBS to Jira", async () => {
    vi.mocked(syncWbs).mockResolvedValue({ synced: 5 });

    const { result } = renderHook(() => useSyncJira(), { wrapper });

    result.current.mutate({ integrationId: "jira-1", type: "wbs" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(syncWbs).toHaveBeenCalledWith("jira-1");
  });
});

describe("useJiraMappings", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("fetches Jira mappings", async () => {
    vi.mocked(getMappings).mockResolvedValue([]);

    const { result } = renderHook(() => useJiraMappings("jira-1"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(getMappings).toHaveBeenCalledWith("jira-1");
  });

  it("does not fetch when integrationId is empty", () => {
    renderHook(() => useJiraMappings(""), { wrapper });
    expect(getMappings).not.toHaveBeenCalled();
  });
});

describe("useCreateJiraMapping", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("creates a Jira mapping", async () => {
    vi.mocked(createMapping).mockResolvedValue({ id: "map-1" });

    const { result } = renderHook(() => useCreateJiraMapping(), { wrapper });

    result.current.mutate({
      integrationId: "jira-1",
      data: { entity_type: "activity", entity_id: "act-1", jira_key: "PROJ-1" },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(createMapping).toHaveBeenCalled();
  });
});

describe("useDeleteJiraMapping", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("deletes a Jira mapping", async () => {
    vi.mocked(deleteMapping).mockResolvedValue(undefined);

    const { result } = renderHook(() => useDeleteJiraMapping(), { wrapper });

    result.current.mutate("map-1");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(deleteMapping).toHaveBeenCalledWith("map-1");
  });
});

describe("useJiraSyncLogs", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("fetches sync logs", async () => {
    vi.mocked(getSyncLogs).mockResolvedValue([]);

    const { result } = renderHook(() => useJiraSyncLogs("jira-1"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(getSyncLogs).toHaveBeenCalledWith("jira-1", undefined);
  });

  it("does not fetch when integrationId is empty", () => {
    renderHook(() => useJiraSyncLogs(""), { wrapper });
    expect(getSyncLogs).not.toHaveBeenCalled();
  });
});
