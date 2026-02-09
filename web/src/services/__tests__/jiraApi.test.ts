import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/api/client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

import { apiClient } from "@/api/client";
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
  jiraApi,
} from "../jiraApi";

const mockedGet = vi.mocked(apiClient.get);
const mockedPost = vi.mocked(apiClient.post);
const mockedPatch = vi.mocked(apiClient.patch);
const mockedDelete = vi.mocked(apiClient.delete);

const mockIntegration = {
  id: "jira-1",
  program_id: "prog-1",
  jira_url: "https://test.atlassian.net",
  email: "user@test.com",
  project_key: "PROJ",
  sync_enabled: true,
  sync_direction: "BIDIRECTIONAL",
  last_sync_at: "2026-02-01T12:00:00Z",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: null,
};

const mockMapping = {
  id: "map-1",
  integration_id: "jira-1",
  entity_type: "ACTIVITY",
  local_id: "act-1",
  jira_issue_key: "PROJ-123",
  jira_issue_id: null,
  last_synced_at: null,
  created_at: "2026-01-01T00:00:00Z",
};

const mockSyncResponse = {
  sync_type: "PUSH",
  status: "SUCCESS",
  total_items: 10,
  synced: 10,
  failed: 0,
  errors: [],
};

describe("jiraApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("getIntegrationByProgram", () => {
    it("should fetch integration for a program", async () => {
      mockedGet.mockResolvedValue({ data: mockIntegration });

      const result = await getIntegrationByProgram("prog-1");

      expect(mockedGet).toHaveBeenCalledWith("/jira/programs/prog-1/integration");
      expect(result).toEqual(mockIntegration);
    });
  });

  describe("createIntegration", () => {
    it("should post integration data", async () => {
      mockedPost.mockResolvedValue({ data: mockIntegration });

      const data = {
        program_id: "prog-1",
        jira_url: "https://test.atlassian.net",
        email: "user@test.com",
        api_token: "token",
        project_key: "PROJ",
      };

      const result = await createIntegration(data);

      expect(mockedPost).toHaveBeenCalledWith("/jira/integrations", data);
      expect(result).toEqual(mockIntegration);
    });
  });

  describe("updateIntegration", () => {
    it("should patch integration data", async () => {
      mockedPatch.mockResolvedValue({ data: mockIntegration });

      await updateIntegration("jira-1", { sync_enabled: false });

      expect(mockedPatch).toHaveBeenCalledWith("/jira/integrations/jira-1", {
        sync_enabled: false,
      });
    });
  });

  describe("deleteIntegration", () => {
    it("should delete integration", async () => {
      mockedDelete.mockResolvedValue({ data: undefined });

      await deleteIntegration("jira-1");

      expect(mockedDelete).toHaveBeenCalledWith("/jira/integrations/jira-1");
    });
  });

  describe("testConnection", () => {
    it("should post test connection request", async () => {
      mockedPost.mockResolvedValue({
        data: { success: true, message: "Connected", project_name: "Test Project" },
      });

      const result = await testConnection("jira-1");

      expect(mockedPost).toHaveBeenCalledWith("/jira/integrations/jira-1/test");
      expect(result.success).toBe(true);
    });
  });

  describe("sync operations", () => {
    it("should sync WBS", async () => {
      mockedPost.mockResolvedValue({ data: mockSyncResponse });

      const result = await syncWbs("jira-1");

      expect(mockedPost).toHaveBeenCalledWith("/jira/integrations/jira-1/sync/wbs");
      expect(result.status).toBe("SUCCESS");
    });

    it("should sync activities", async () => {
      mockedPost.mockResolvedValue({ data: mockSyncResponse });

      await syncActivities("jira-1");

      expect(mockedPost).toHaveBeenCalledWith("/jira/integrations/jira-1/sync/activities");
    });

    it("should sync progress", async () => {
      mockedPost.mockResolvedValue({ data: mockSyncResponse });

      await syncProgress("jira-1");

      expect(mockedPost).toHaveBeenCalledWith("/jira/integrations/jira-1/sync/progress");
    });
  });

  describe("getMappings", () => {
    it("should fetch mappings", async () => {
      mockedGet.mockResolvedValue({ data: [mockMapping] });

      const result = await getMappings("jira-1");

      expect(mockedGet).toHaveBeenCalledWith("/jira/integrations/jira-1/mappings");
      expect(result).toHaveLength(1);
    });
  });

  describe("createMapping", () => {
    it("should post mapping data", async () => {
      mockedPost.mockResolvedValue({ data: mockMapping });

      await createMapping("jira-1", {
        entity_type: "ACTIVITY",
        local_id: "act-1",
        jira_issue_key: "PROJ-123",
      });

      expect(mockedPost).toHaveBeenCalledWith("/jira/integrations/jira-1/mappings", {
        entity_type: "ACTIVITY",
        local_id: "act-1",
        jira_issue_key: "PROJ-123",
      });
    });
  });

  describe("deleteMapping", () => {
    it("should delete mapping", async () => {
      mockedDelete.mockResolvedValue({ data: undefined });

      await deleteMapping("map-1");

      expect(mockedDelete).toHaveBeenCalledWith("/jira/mappings/map-1");
    });
  });

  describe("getSyncLogs", () => {
    it("should fetch sync logs", async () => {
      mockedGet.mockResolvedValue({ data: { items: [], total: 0 } });

      const result = await getSyncLogs("jira-1");

      expect(mockedGet).toHaveBeenCalledWith("/jira/integrations/jira-1/logs");
      expect(result.total).toBe(0);
    });

    it("should fetch with limit", async () => {
      mockedGet.mockResolvedValue({ data: { items: [], total: 0 } });

      await getSyncLogs("jira-1", 5);

      expect(mockedGet).toHaveBeenCalledWith("/jira/integrations/jira-1/logs?limit=5");
    });
  });

  describe("jiraApi object", () => {
    it("should export all methods", () => {
      expect(jiraApi.getByProgram).toBe(getIntegrationByProgram);
      expect(jiraApi.create).toBe(createIntegration);
      expect(jiraApi.update).toBe(updateIntegration);
      expect(jiraApi.delete).toBe(deleteIntegration);
      expect(jiraApi.testConnection).toBe(testConnection);
      expect(jiraApi.syncWbs).toBe(syncWbs);
      expect(jiraApi.syncActivities).toBe(syncActivities);
      expect(jiraApi.syncProgress).toBe(syncProgress);
      expect(jiraApi.getMappings).toBe(getMappings);
      expect(jiraApi.createMapping).toBe(createMapping);
      expect(jiraApi.deleteMapping).toBe(deleteMapping);
      expect(jiraApi.getSyncLogs).toBe(getSyncLogs);
    });
  });
});
