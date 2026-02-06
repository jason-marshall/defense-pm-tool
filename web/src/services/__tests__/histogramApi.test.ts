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
  getResourceHistogram,
  getProgramHistogram,
  histogramApi,
} from "../histogramApi";

const mockedGet = vi.mocked(apiClient.get);

const mockResourceHistogram = {
  resource_id: "res-001",
  resource_code: "SE-001",
  resource_name: "Senior Engineer",
  resource_type: "LABOR",
  start_date: "2026-01-01",
  end_date: "2026-01-31",
  data_points: [
    {
      date: "2026-01-06",
      available_hours: 8,
      assigned_hours: 6,
      utilization_percent: 75.0,
      is_overallocated: false,
    },
    {
      date: "2026-01-07",
      available_hours: 8,
      assigned_hours: 10,
      utilization_percent: 125.0,
      is_overallocated: true,
    },
  ],
  peak_utilization: 125.0,
  peak_date: "2026-01-07",
  average_utilization: 100.0,
  overallocated_days: 1,
  total_available_hours: 16,
  total_assigned_hours: 16,
};

const mockProgramHistogram = {
  summary: {
    program_id: "prog-001",
    start_date: "2026-01-01",
    end_date: "2026-03-31",
    resource_count: 3,
    total_overallocated_days: 5,
    resources_with_overallocation: 2,
  },
  histograms: [mockResourceHistogram],
};

describe("histogramApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("getResourceHistogram", () => {
    it("should fetch histogram data with required parameters", async () => {
      mockedGet.mockResolvedValue({ data: mockResourceHistogram });

      const result = await getResourceHistogram(
        "res-001",
        "2026-01-01",
        "2026-01-31"
      );

      expect(mockedGet).toHaveBeenCalledWith(
        "/resources/res-001/histogram?start_date=2026-01-01&end_date=2026-01-31&granularity=daily"
      );
      expect(result).toEqual(mockResourceHistogram);
    });

    it("should use default granularity of 'daily'", async () => {
      mockedGet.mockResolvedValue({ data: mockResourceHistogram });

      await getResourceHistogram("res-001", "2026-01-01", "2026-01-31");

      const calledUrl = mockedGet.mock.calls[0][0];
      expect(calledUrl).toContain("granularity=daily");
    });

    it("should use custom granularity when provided", async () => {
      mockedGet.mockResolvedValue({ data: mockResourceHistogram });

      await getResourceHistogram(
        "res-001",
        "2026-01-01",
        "2026-01-31",
        "weekly"
      );

      expect(mockedGet).toHaveBeenCalledWith(
        "/resources/res-001/histogram?start_date=2026-01-01&end_date=2026-01-31&granularity=weekly"
      );
    });

    it("should accept monthly granularity", async () => {
      mockedGet.mockResolvedValue({ data: mockResourceHistogram });

      await getResourceHistogram(
        "res-001",
        "2026-02-01",
        "2026-12-31",
        "monthly"
      );

      expect(mockedGet).toHaveBeenCalledWith(
        "/resources/res-001/histogram?start_date=2026-02-01&end_date=2026-12-31&granularity=monthly"
      );
    });

    it("should construct URL with correct resource ID", async () => {
      mockedGet.mockResolvedValue({ data: mockResourceHistogram });

      await getResourceHistogram("abc-xyz-123", "2026-01-01", "2026-01-31");

      const calledUrl = mockedGet.mock.calls[0][0] as string;
      expect(calledUrl).toMatch(/^\/resources\/abc-xyz-123\/histogram\?/);
    });

    it("should include all query parameters in URL", async () => {
      mockedGet.mockResolvedValue({ data: mockResourceHistogram });

      await getResourceHistogram(
        "res-001",
        "2026-03-15",
        "2026-06-30",
        "weekly"
      );

      const calledUrl = mockedGet.mock.calls[0][0] as string;
      expect(calledUrl).toContain("start_date=2026-03-15");
      expect(calledUrl).toContain("end_date=2026-06-30");
      expect(calledUrl).toContain("granularity=weekly");
    });

    it("should return the histogram data from response", async () => {
      mockedGet.mockResolvedValue({ data: mockResourceHistogram });

      const result = await getResourceHistogram(
        "res-001",
        "2026-01-01",
        "2026-01-31"
      );

      expect(result.resource_id).toBe("res-001");
      expect(result.data_points).toHaveLength(2);
      expect(result.peak_utilization).toBe(125.0);
      expect(result.overallocated_days).toBe(1);
    });

    it("should propagate errors", async () => {
      const error = new Error("Network error");
      mockedGet.mockRejectedValue(error);

      await expect(
        getResourceHistogram("res-001", "2026-01-01", "2026-01-31")
      ).rejects.toThrow("Network error");
    });

    it("should propagate 404 errors", async () => {
      mockedGet.mockRejectedValue(new Error("Resource not found"));

      await expect(
        getResourceHistogram("nonexistent", "2026-01-01", "2026-01-31")
      ).rejects.toThrow("Resource not found");
    });
  });

  describe("getProgramHistogram", () => {
    it("should fetch program histogram without dates", async () => {
      mockedGet.mockResolvedValue({ data: mockProgramHistogram });

      const result = await getProgramHistogram("prog-001");

      expect(mockedGet).toHaveBeenCalledWith(
        "/programs/prog-001/histogram"
      );
      expect(result).toEqual(mockProgramHistogram);
    });

    it("should append no query string when no dates provided", async () => {
      mockedGet.mockResolvedValue({ data: mockProgramHistogram });

      await getProgramHistogram("prog-001");

      const calledUrl = mockedGet.mock.calls[0][0] as string;
      expect(calledUrl).not.toContain("?");
    });

    it("should include start_date when startDate is provided", async () => {
      mockedGet.mockResolvedValue({ data: mockProgramHistogram });

      await getProgramHistogram("prog-001", "2026-01-01");

      expect(mockedGet).toHaveBeenCalledWith(
        "/programs/prog-001/histogram?start_date=2026-01-01"
      );
    });

    it("should include end_date when endDate is provided", async () => {
      mockedGet.mockResolvedValue({ data: mockProgramHistogram });

      await getProgramHistogram("prog-001", undefined, "2026-03-31");

      expect(mockedGet).toHaveBeenCalledWith(
        "/programs/prog-001/histogram?end_date=2026-03-31"
      );
    });

    it("should include both dates when both are provided", async () => {
      mockedGet.mockResolvedValue({ data: mockProgramHistogram });

      await getProgramHistogram("prog-001", "2026-01-01", "2026-03-31");

      expect(mockedGet).toHaveBeenCalledWith(
        "/programs/prog-001/histogram?start_date=2026-01-01&end_date=2026-03-31"
      );
    });

    it("should not include start_date when startDate is empty string", async () => {
      mockedGet.mockResolvedValue({ data: mockProgramHistogram });

      await getProgramHistogram("prog-001", "");

      const calledUrl = mockedGet.mock.calls[0][0] as string;
      expect(calledUrl).not.toContain("start_date");
    });

    it("should construct URL with correct program ID", async () => {
      mockedGet.mockResolvedValue({ data: mockProgramHistogram });

      await getProgramHistogram("my-program-id");

      const calledUrl = mockedGet.mock.calls[0][0] as string;
      expect(calledUrl).toMatch(/^\/programs\/my-program-id\/histogram/);
    });

    it("should return program histogram response data", async () => {
      mockedGet.mockResolvedValue({ data: mockProgramHistogram });

      const result = await getProgramHistogram("prog-001");

      expect(result.summary.program_id).toBe("prog-001");
      expect(result.summary.resource_count).toBe(3);
      expect(result.histograms).toHaveLength(1);
    });

    it("should propagate errors", async () => {
      mockedGet.mockRejectedValue(new Error("Server error"));

      await expect(getProgramHistogram("prog-001")).rejects.toThrow(
        "Server error"
      );
    });

    it("should propagate errors with dates provided", async () => {
      mockedGet.mockRejectedValue(new Error("Timeout"));

      await expect(
        getProgramHistogram("prog-001", "2026-01-01", "2026-03-31")
      ).rejects.toThrow("Timeout");
    });
  });

  describe("histogramApi object", () => {
    it("should export getResourceHistogram", () => {
      expect(histogramApi.getResourceHistogram).toBe(getResourceHistogram);
    });

    it("should export getProgramHistogram", () => {
      expect(histogramApi.getProgramHistogram).toBe(getProgramHistogram);
    });

    it("should have exactly two methods", () => {
      expect(Object.keys(histogramApi)).toHaveLength(2);
    });
  });
});
