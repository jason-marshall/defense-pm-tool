import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/api/client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

import { apiClient } from "@/api/client";
import {
  previewLeveling,
  runLeveling,
  applyLeveling,
  levelingApi,
} from "../levelingApi";

const mockedGet = vi.mocked(apiClient.get);
const mockedPost = vi.mocked(apiClient.post);

const mockLevelingResult = {
  program_id: "prog-001",
  success: true,
  iterations_used: 12,
  activities_shifted: 3,
  shifts: [
    {
      activity_id: "act-001",
      activity_code: "A001",
      original_start: "2026-01-06",
      original_finish: "2026-01-10",
      new_start: "2026-01-13",
      new_finish: "2026-01-17",
      delay_days: 5,
      reason: "Resource overallocation on SE-001",
    },
    {
      activity_id: "act-002",
      activity_code: "A002",
      original_start: "2026-01-06",
      original_finish: "2026-01-08",
      new_start: "2026-01-09",
      new_finish: "2026-01-13",
      delay_days: 3,
      reason: "Resource overallocation on SE-002",
    },
  ],
  remaining_overallocations: 0,
  new_project_finish: "2026-03-20",
  original_project_finish: "2026-03-10",
  schedule_extension_days: 10,
  warnings: ["Activity A003 has zero float after leveling"],
};

describe("levelingApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("previewLeveling", () => {
    it("should fetch preview with no options", async () => {
      mockedGet.mockResolvedValue({ data: mockLevelingResult });

      const result = await previewLeveling("prog-001");

      expect(mockedGet).toHaveBeenCalledWith(
        "/programs/prog-001/level/preview"
      );
      expect(result).toEqual(mockLevelingResult);
    });

    it("should not append query string when options is undefined", async () => {
      mockedGet.mockResolvedValue({ data: mockLevelingResult });

      await previewLeveling("prog-001");

      const calledUrl = mockedGet.mock.calls[0][0] as string;
      expect(calledUrl).not.toContain("?");
    });

    it("should not append query string when options is empty object", async () => {
      mockedGet.mockResolvedValue({ data: mockLevelingResult });

      await previewLeveling("prog-001", {});

      const calledUrl = mockedGet.mock.calls[0][0] as string;
      expect(calledUrl).not.toContain("?");
    });

    it("should append preserve_critical_path when true", async () => {
      mockedGet.mockResolvedValue({ data: mockLevelingResult });

      await previewLeveling("prog-001", { preserve_critical_path: true });

      expect(mockedGet).toHaveBeenCalledWith(
        "/programs/prog-001/level/preview?preserve_critical_path=true"
      );
    });

    it("should append preserve_critical_path when false", async () => {
      mockedGet.mockResolvedValue({ data: mockLevelingResult });

      await previewLeveling("prog-001", { preserve_critical_path: false });

      expect(mockedGet).toHaveBeenCalledWith(
        "/programs/prog-001/level/preview?preserve_critical_path=false"
      );
    });

    it("should append max_iterations when provided", async () => {
      mockedGet.mockResolvedValue({ data: mockLevelingResult });

      await previewLeveling("prog-001", { max_iterations: 50 });

      expect(mockedGet).toHaveBeenCalledWith(
        "/programs/prog-001/level/preview?max_iterations=50"
      );
    });

    it("should append level_within_float when true", async () => {
      mockedGet.mockResolvedValue({ data: mockLevelingResult });

      await previewLeveling("prog-001", { level_within_float: true });

      expect(mockedGet).toHaveBeenCalledWith(
        "/programs/prog-001/level/preview?level_within_float=true"
      );
    });

    it("should append level_within_float when false", async () => {
      mockedGet.mockResolvedValue({ data: mockLevelingResult });

      await previewLeveling("prog-001", { level_within_float: false });

      expect(mockedGet).toHaveBeenCalledWith(
        "/programs/prog-001/level/preview?level_within_float=false"
      );
    });

    it("should append all options when all are provided", async () => {
      mockedGet.mockResolvedValue({ data: mockLevelingResult });

      await previewLeveling("prog-001", {
        preserve_critical_path: true,
        max_iterations: 100,
        level_within_float: false,
      });

      expect(mockedGet).toHaveBeenCalledWith(
        "/programs/prog-001/level/preview?preserve_critical_path=true&max_iterations=100&level_within_float=false"
      );
    });

    it("should construct URL with correct program ID", async () => {
      mockedGet.mockResolvedValue({ data: mockLevelingResult });

      await previewLeveling("my-program-xyz");

      const calledUrl = mockedGet.mock.calls[0][0] as string;
      expect(calledUrl).toMatch(
        /^\/programs\/my-program-xyz\/level\/preview/
      );
    });

    it("should return the leveling result data", async () => {
      mockedGet.mockResolvedValue({ data: mockLevelingResult });

      const result = await previewLeveling("prog-001");

      expect(result.success).toBe(true);
      expect(result.iterations_used).toBe(12);
      expect(result.activities_shifted).toBe(3);
      expect(result.shifts).toHaveLength(2);
      expect(result.schedule_extension_days).toBe(10);
    });

    it("should propagate errors", async () => {
      mockedGet.mockRejectedValue(new Error("Server error"));

      await expect(previewLeveling("prog-001")).rejects.toThrow(
        "Server error"
      );
    });

    it("should propagate errors with options provided", async () => {
      mockedGet.mockRejectedValue(new Error("Timeout"));

      await expect(
        previewLeveling("prog-001", { preserve_critical_path: true })
      ).rejects.toThrow("Timeout");
    });
  });

  describe("runLeveling", () => {
    it("should post leveling options to correct URL", async () => {
      mockedPost.mockResolvedValue({ data: mockLevelingResult });

      const options = {
        preserve_critical_path: true,
        max_iterations: 50,
        level_within_float: false,
      };

      const result = await runLeveling("prog-001", options);

      expect(mockedPost).toHaveBeenCalledWith(
        "/programs/prog-001/level",
        options
      );
      expect(result).toEqual(mockLevelingResult);
    });

    it("should send options as request body", async () => {
      mockedPost.mockResolvedValue({ data: mockLevelingResult });

      const options = { preserve_critical_path: false };

      await runLeveling("prog-001", options);

      expect(mockedPost).toHaveBeenCalledWith(
        "/programs/prog-001/level",
        { preserve_critical_path: false }
      );
    });

    it("should send empty options object", async () => {
      mockedPost.mockResolvedValue({ data: mockLevelingResult });

      await runLeveling("prog-001", {});

      expect(mockedPost).toHaveBeenCalledWith(
        "/programs/prog-001/level",
        {}
      );
    });

    it("should construct URL with correct program ID", async () => {
      mockedPost.mockResolvedValue({ data: mockLevelingResult });

      await runLeveling("test-program-456", { max_iterations: 25 });

      expect(mockedPost).toHaveBeenCalledWith(
        "/programs/test-program-456/level",
        { max_iterations: 25 }
      );
    });

    it("should return leveling result from response", async () => {
      mockedPost.mockResolvedValue({ data: mockLevelingResult });

      const result = await runLeveling("prog-001", {});

      expect(result.program_id).toBe("prog-001");
      expect(result.success).toBe(true);
      expect(result.shifts).toHaveLength(2);
      expect(result.warnings).toHaveLength(1);
    });

    it("should propagate errors", async () => {
      mockedPost.mockRejectedValue(new Error("Leveling failed"));

      await expect(
        runLeveling("prog-001", { preserve_critical_path: true })
      ).rejects.toThrow("Leveling failed");
    });

    it("should propagate validation errors", async () => {
      mockedPost.mockRejectedValue(new Error("Invalid options"));

      await expect(
        runLeveling("prog-001", { max_iterations: -1 })
      ).rejects.toThrow("Invalid options");
    });
  });

  describe("applyLeveling", () => {
    it("should post shift IDs to apply endpoint", async () => {
      mockedPost.mockResolvedValue({ data: { applied_count: 3 } });

      const shiftIds = ["shift-001", "shift-002", "shift-003"];
      const result = await applyLeveling("prog-001", shiftIds);

      expect(mockedPost).toHaveBeenCalledWith(
        "/programs/prog-001/level/apply",
        { shifts: shiftIds }
      );
      expect(result).toEqual({ applied_count: 3 });
    });

    it("should send shifts wrapped in object body", async () => {
      mockedPost.mockResolvedValue({ data: { applied_count: 1 } });

      await applyLeveling("prog-001", ["single-shift"]);

      expect(mockedPost).toHaveBeenCalledWith(
        "/programs/prog-001/level/apply",
        { shifts: ["single-shift"] }
      );
    });

    it("should handle empty shift IDs array", async () => {
      mockedPost.mockResolvedValue({ data: { applied_count: 0 } });

      const result = await applyLeveling("prog-001", []);

      expect(mockedPost).toHaveBeenCalledWith(
        "/programs/prog-001/level/apply",
        { shifts: [] }
      );
      expect(result).toEqual({ applied_count: 0 });
    });

    it("should construct URL with correct program ID", async () => {
      mockedPost.mockResolvedValue({ data: { applied_count: 2 } });

      await applyLeveling("program-abc", ["s1", "s2"]);

      expect(mockedPost).toHaveBeenCalledWith(
        "/programs/program-abc/level/apply",
        { shifts: ["s1", "s2"] }
      );
    });

    it("should return applied_count from response", async () => {
      mockedPost.mockResolvedValue({ data: { applied_count: 5 } });

      const result = await applyLeveling("prog-001", [
        "s1",
        "s2",
        "s3",
        "s4",
        "s5",
      ]);

      expect(result.applied_count).toBe(5);
    });

    it("should propagate errors", async () => {
      mockedPost.mockRejectedValue(new Error("Apply failed"));

      await expect(
        applyLeveling("prog-001", ["shift-001"])
      ).rejects.toThrow("Apply failed");
    });

    it("should propagate authorization errors", async () => {
      mockedPost.mockRejectedValue(new Error("Forbidden"));

      await expect(
        applyLeveling("prog-001", ["shift-001"])
      ).rejects.toThrow("Forbidden");
    });
  });

  describe("levelingApi object", () => {
    it("should export preview as previewLeveling", () => {
      expect(levelingApi.preview).toBe(previewLeveling);
    });

    it("should export run as runLeveling", () => {
      expect(levelingApi.run).toBe(runLeveling);
    });

    it("should export apply as applyLeveling", () => {
      expect(levelingApi.apply).toBe(applyLeveling);
    });

    it("should have exactly three methods", () => {
      expect(Object.keys(levelingApi)).toHaveLength(3);
    });
  });
});
