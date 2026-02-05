import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { useGanttResourceData } from "./useGanttResourceData";

vi.mock("@/api/client", () => ({
  apiClient: {
    get: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

import { apiClient } from "@/api/client";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false },
  },
});

const wrapper = ({ children }: { children: React.ReactNode }) =>
  React.createElement(QueryClientProvider, { client: queryClient }, children);

const mockResources = {
  items: [
    {
      id: "res-1",
      code: "ENG-001",
      name: "Senior Engineer",
      resource_type: "LABOR",
      capacity_per_day: "8.0",
    },
  ],
};

const mockAssignments = {
  items: [
    {
      id: "assign-1",
      activity_id: "act-1",
      start_date: "2026-02-01",
      finish_date: "2026-02-05",
      units: "1.0",
      activity: {
        code: "ACT-001",
        name: "Design Review",
        early_start: "2026-02-01",
        early_finish: "2026-02-05",
        is_critical: false,
      },
    },
  ],
};

describe("useGanttResourceData", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("fetches resources and assignments", async () => {
    vi.mocked(apiClient.get)
      .mockResolvedValueOnce({ data: mockResources })
      .mockResolvedValueOnce({ data: mockAssignments });

    const startDate = new Date("2026-02-01");
    const endDate = new Date("2026-02-28");

    const { result } = renderHook(
      () => useGanttResourceData("prog-1", startDate, endDate),
      { wrapper }
    );

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.resourceLanes).toHaveLength(1);
    expect(result.current.resourceLanes[0].resourceCode).toBe("ENG-001");
    expect(result.current.resourceLanes[0].resourceName).toBe("Senior Engineer");
    expect(result.current.resourceLanes[0].assignments).toHaveLength(1);
    expect(result.current.resourceLanes[0].assignments[0].activityCode).toBe("ACT-001");
  });

  it("returns empty array when no resources", async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce({
      data: { items: [] },
    });

    const startDate = new Date("2026-02-01");
    const endDate = new Date("2026-02-28");

    const { result } = renderHook(
      () => useGanttResourceData("prog-1", startDate, endDate),
      { wrapper }
    );

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.resourceLanes).toHaveLength(0);
  });

  it("calculates utilization for assignments", async () => {
    vi.mocked(apiClient.get)
      .mockResolvedValueOnce({ data: mockResources })
      .mockResolvedValueOnce({ data: mockAssignments });

    const startDate = new Date("2026-02-01");
    const endDate = new Date("2026-02-28");

    const { result } = renderHook(
      () => useGanttResourceData("prog-1", startDate, endDate),
      { wrapper }
    );

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    const lane = result.current.resourceLanes[0];
    expect(lane.dailyUtilization).toBeDefined();
    expect(lane.capacityPerDay).toBe(8);
  });

  it("does not fetch when programId is empty", () => {
    const startDate = new Date("2026-02-01");
    const endDate = new Date("2026-02-28");

    renderHook(() => useGanttResourceData("", startDate, endDate), {
      wrapper,
    });

    expect(apiClient.get).not.toHaveBeenCalled();
  });

  it("provides updateAssignment mutation", async () => {
    vi.mocked(apiClient.get)
      .mockResolvedValueOnce({ data: mockResources })
      .mockResolvedValueOnce({ data: mockAssignments });
    vi.mocked(apiClient.patch).mockResolvedValue({});

    const startDate = new Date("2026-02-01");
    const endDate = new Date("2026-02-28");

    const { result } = renderHook(
      () => useGanttResourceData("prog-1", startDate, endDate),
      { wrapper }
    );

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(typeof result.current.updateAssignment).toBe("function");
    expect(typeof result.current.refetch).toBe("function");
    expect(result.current.isUpdating).toBe(false);
  });

  it("handles error state", async () => {
    vi.mocked(apiClient.get).mockRejectedValue(new Error("Network error"));

    const startDate = new Date("2026-02-01");
    const endDate = new Date("2026-02-28");

    const { result } = renderHook(
      () => useGanttResourceData("prog-1", startDate, endDate),
      { wrapper }
    );

    await waitFor(() => expect(result.current.error).toBeTruthy());

    expect(result.current.resourceLanes).toHaveLength(0);
  });
});
