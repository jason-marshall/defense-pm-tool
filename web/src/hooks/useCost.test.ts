import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import {
  useProgramCostSummary,
  useActivityCost,
  useWBSCost,
  useSyncCostsToEVMS,
  useRecordCostEntry,
} from "./useCost";

vi.mock("@/services/costApi", () => ({
  getProgramCostSummary: vi.fn(),
  getActivityCost: vi.fn(),
  getWBSCost: vi.fn(),
  syncCostsToEVMS: vi.fn(),
  recordCostEntry: vi.fn(),
}));

import {
  getProgramCostSummary,
  getActivityCost,
  getWBSCost,
  syncCostsToEVMS,
  recordCostEntry,
} from "@/services/costApi";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

const wrapper = ({ children }: { children: React.ReactNode }) =>
  React.createElement(QueryClientProvider, { client: queryClient }, children);

describe("useProgramCostSummary", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("fetches program cost summary", async () => {
    const mockSummary = { total_cost: "50000.00", labor_cost: "40000.00" };
    vi.mocked(getProgramCostSummary).mockResolvedValue(mockSummary);

    const { result } = renderHook(() => useProgramCostSummary("prog-1"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(getProgramCostSummary).toHaveBeenCalledWith("prog-1");
  });

  it("does not fetch when programId is empty", () => {
    renderHook(() => useProgramCostSummary(""), { wrapper });
    expect(getProgramCostSummary).not.toHaveBeenCalled();
  });
});

describe("useActivityCost", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("fetches activity cost", async () => {
    vi.mocked(getActivityCost).mockResolvedValue({ total: "5000.00" });

    const { result } = renderHook(() => useActivityCost("act-1"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(getActivityCost).toHaveBeenCalledWith("act-1");
  });

  it("does not fetch when activityId is empty", () => {
    renderHook(() => useActivityCost(""), { wrapper });
    expect(getActivityCost).not.toHaveBeenCalled();
  });
});

describe("useWBSCost", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("fetches WBS cost", async () => {
    vi.mocked(getWBSCost).mockResolvedValue({ total: "25000.00" });

    const { result } = renderHook(() => useWBSCost("wbs-1"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(getWBSCost).toHaveBeenCalledWith("wbs-1", undefined);
  });

  it("does not fetch when wbsId is empty", () => {
    renderHook(() => useWBSCost(""), { wrapper });
    expect(getWBSCost).not.toHaveBeenCalled();
  });
});

describe("useSyncCostsToEVMS", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("syncs costs to EVMS", async () => {
    vi.mocked(syncCostsToEVMS).mockResolvedValue({ synced: 10 });

    const { result } = renderHook(() => useSyncCostsToEVMS(), { wrapper });

    result.current.mutate({ programId: "prog-1", periodId: "period-1" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(syncCostsToEVMS).toHaveBeenCalledWith("prog-1", "period-1");
  });
});

describe("useRecordCostEntry", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("records a cost entry", async () => {
    vi.mocked(recordCostEntry).mockResolvedValue({ id: "cost-1" });

    const { result } = renderHook(() => useRecordCostEntry(), { wrapper });

    result.current.mutate({
      assignmentId: "assign-1",
      data: { hours: 8, cost_rate: "125.00", date: "2024-01-15" },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(recordCostEntry).toHaveBeenCalled();
  });
});
