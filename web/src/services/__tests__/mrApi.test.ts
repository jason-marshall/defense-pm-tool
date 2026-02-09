import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/api/client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

import { apiClient } from "@/api/client";
import { getMRStatus, initializeMR, recordMRChange, getMRHistory, mrApi } from "../mrApi";

const mockedGet = vi.mocked(apiClient.get);
const mockedPost = vi.mocked(apiClient.post);

const mockStatus = {
  program_id: "prog-1",
  current_balance: "50000",
  initial_mr: "100000",
  total_changes_in: "10000",
  total_changes_out: "60000",
  change_count: 5,
  last_change_at: "2026-02-01T12:00:00Z",
};

const mockLogEntry = {
  id: "log-1",
  program_id: "prog-1",
  period_id: null,
  beginning_mr: "100000",
  changes_in: "100000",
  changes_out: "0",
  ending_mr: "100000",
  reason: "Initial allocation",
  approved_by: "user-1",
  created_at: "2026-01-01T12:00:00Z",
};

const mockHistory = {
  items: [mockLogEntry],
  total: 1,
  program_id: "prog-1",
  current_balance: "100000",
};

describe("mrApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("getMRStatus", () => {
    it("should fetch MR status for a program", async () => {
      mockedGet.mockResolvedValue({ data: mockStatus });

      const result = await getMRStatus("prog-1");

      expect(mockedGet).toHaveBeenCalledWith("/mr/prog-1");
      expect(result).toEqual(mockStatus);
    });

    it("should propagate errors", async () => {
      mockedGet.mockRejectedValue(new Error("Not found"));
      await expect(getMRStatus("bad")).rejects.toThrow("Not found");
    });
  });

  describe("initializeMR", () => {
    it("should post initialize with amount and reason", async () => {
      mockedPost.mockResolvedValue({ data: mockLogEntry });

      const result = await initializeMR("prog-1", "100000", "Initial allocation");

      expect(mockedPost).toHaveBeenCalledWith(
        "/mr/prog-1/initialize?initial_amount=100000&reason=Initial+allocation"
      );
      expect(result).toEqual(mockLogEntry);
    });

    it("should post initialize without reason", async () => {
      mockedPost.mockResolvedValue({ data: mockLogEntry });

      await initializeMR("prog-1", "50000");

      expect(mockedPost).toHaveBeenCalledWith(
        "/mr/prog-1/initialize?initial_amount=50000"
      );
    });
  });

  describe("recordMRChange", () => {
    it("should post change data", async () => {
      mockedPost.mockResolvedValue({ data: mockLogEntry });

      const changeData = {
        changes_in: "0",
        changes_out: "10000",
        reason: "Release to WP",
      };

      const result = await recordMRChange("prog-1", changeData);

      expect(mockedPost).toHaveBeenCalledWith("/mr/prog-1/change", changeData);
      expect(result).toEqual(mockLogEntry);
    });
  });

  describe("getMRHistory", () => {
    it("should fetch history without limit", async () => {
      mockedGet.mockResolvedValue({ data: mockHistory });

      const result = await getMRHistory("prog-1");

      expect(mockedGet).toHaveBeenCalledWith("/mr/prog-1/history");
      expect(result).toEqual(mockHistory);
    });

    it("should fetch history with limit", async () => {
      mockedGet.mockResolvedValue({ data: mockHistory });

      await getMRHistory("prog-1", 5);

      expect(mockedGet).toHaveBeenCalledWith("/mr/prog-1/history?limit=5");
    });
  });

  describe("mrApi object", () => {
    it("should export getStatus", () => {
      expect(mrApi.getStatus).toBe(getMRStatus);
    });

    it("should export initialize", () => {
      expect(mrApi.initialize).toBe(initializeMR);
    });

    it("should export recordChange", () => {
      expect(mrApi.recordChange).toBe(recordMRChange);
    });

    it("should export getHistory", () => {
      expect(mrApi.getHistory).toBe(getMRHistory);
    });
  });
});
