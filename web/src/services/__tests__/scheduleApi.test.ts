import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/api/client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

import { apiClient } from "@/api/client";
import {
  calculateSchedule,
  getScheduleResults,
  scheduleApi,
} from "../scheduleApi";

const mockedGet = vi.mocked(apiClient.get);
const mockedPost = vi.mocked(apiClient.post);

const mockScheduleResult = {
  program_id: "prog-1",
  calculated_at: "2026-01-15T10:00:00Z",
  activities: [],
  critical_path: [],
  project_duration: 120,
};

describe("scheduleApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("calculateSchedule", () => {
    it("should post schedule calculation request", async () => {
      mockedPost.mockResolvedValue({ data: mockScheduleResult });

      const result = await calculateSchedule("prog-1");

      expect(mockedPost).toHaveBeenCalledWith("/schedule/calculate", {
        program_id: "prog-1",
      });
      expect(result).toEqual(mockScheduleResult);
    });

    it("should propagate errors", async () => {
      mockedPost.mockRejectedValue(new Error("Server error"));

      await expect(calculateSchedule("prog-1")).rejects.toThrow("Server error");
    });
  });

  describe("getScheduleResults", () => {
    it("should fetch schedule results by program id", async () => {
      mockedGet.mockResolvedValue({ data: mockScheduleResult });

      const result = await getScheduleResults("prog-1");

      expect(mockedGet).toHaveBeenCalledWith("/schedule/prog-1");
      expect(result).toEqual(mockScheduleResult);
    });

    it("should propagate errors", async () => {
      mockedGet.mockRejectedValue(new Error("Not found"));

      await expect(getScheduleResults("bad-id")).rejects.toThrow("Not found");
    });
  });

  describe("scheduleApi object", () => {
    it("should export calculate as calculateSchedule", () => {
      expect(scheduleApi.calculate).toBe(calculateSchedule);
    });

    it("should export getResults as getScheduleResults", () => {
      expect(scheduleApi.getResults).toBe(getScheduleResults);
    });
  });
});
