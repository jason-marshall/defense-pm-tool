import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { useResourceHistogram, useProgramHistogram } from "./useHistogram";

vi.mock("@/services/histogramApi", () => ({
  getResourceHistogram: vi.fn(),
  getProgramHistogram: vi.fn(),
}));

import {
  getResourceHistogram,
  getProgramHistogram,
} from "@/services/histogramApi";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false },
  },
});

const wrapper = ({ children }: { children: React.ReactNode }) =>
  React.createElement(QueryClientProvider, { client: queryClient }, children);

const mockResourceHistogram = {
  resource_id: "res-1",
  resource_code: "ENG-001",
  resource_name: "Senior Engineer",
  resource_type: "LABOR",
  start_date: "2026-02-01",
  end_date: "2026-02-28",
  data_points: [
    {
      date: "2026-02-01",
      available_hours: 8,
      assigned_hours: 6,
      utilization_percent: 75,
      is_overallocated: false,
    },
  ],
  peak_utilization: 75,
  peak_date: "2026-02-01",
  average_utilization: 75,
  total_available_hours: 160,
  total_assigned_hours: 6,
  overallocated_days: 0,
};

const mockProgramHistogram = {
  summary: {
    program_id: "prog-1",
    start_date: "2026-02-01",
    end_date: "2026-02-28",
    resource_count: 1,
    total_overallocated_days: 0,
    resources_with_overallocation: 0,
  },
  histograms: [],
};

describe("useResourceHistogram", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("fetches resource histogram data", async () => {
    vi.mocked(getResourceHistogram).mockResolvedValue(mockResourceHistogram);

    const { result } = renderHook(
      () =>
        useResourceHistogram("res-1", "2026-02-01", "2026-02-28", "daily"),
      { wrapper }
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.peak_utilization).toBe(75);
    expect(getResourceHistogram).toHaveBeenCalledWith(
      "res-1",
      "2026-02-01",
      "2026-02-28",
      "daily"
    );
  });

  it("does not fetch when resourceId is empty", () => {
    renderHook(
      () => useResourceHistogram("", "2026-02-01", "2026-02-28"),
      { wrapper }
    );
    expect(getResourceHistogram).not.toHaveBeenCalled();
  });

  it("does not fetch when dates are missing", () => {
    renderHook(() => useResourceHistogram("res-1", "", ""), { wrapper });
    expect(getResourceHistogram).not.toHaveBeenCalled();
  });

  it("uses daily granularity by default", async () => {
    vi.mocked(getResourceHistogram).mockResolvedValue(mockResourceHistogram);

    renderHook(
      () => useResourceHistogram("res-1", "2026-02-01", "2026-02-28"),
      { wrapper }
    );

    await waitFor(() => {
      expect(getResourceHistogram).toHaveBeenCalledWith(
        "res-1",
        "2026-02-01",
        "2026-02-28",
        "daily"
      );
    });
  });
});

describe("useProgramHistogram", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("fetches program histogram data", async () => {
    vi.mocked(getProgramHistogram).mockResolvedValue(mockProgramHistogram);

    const { result } = renderHook(
      () => useProgramHistogram("prog-1", "2026-02-01", "2026-02-28"),
      { wrapper }
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(getProgramHistogram).toHaveBeenCalledWith(
      "prog-1",
      "2026-02-01",
      "2026-02-28"
    );
  });

  it("does not fetch when programId is empty", () => {
    renderHook(() => useProgramHistogram(""), { wrapper });
    expect(getProgramHistogram).not.toHaveBeenCalled();
  });

  it("works without date parameters", async () => {
    vi.mocked(getProgramHistogram).mockResolvedValue(mockProgramHistogram);

    const { result } = renderHook(
      () => useProgramHistogram("prog-1"),
      { wrapper }
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(getProgramHistogram).toHaveBeenCalledWith(
      "prog-1",
      undefined,
      undefined
    );
  });
});
