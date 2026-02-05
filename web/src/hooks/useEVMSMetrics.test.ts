import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import {
  useEVMSSummary,
  useEVMSPeriods,
  useEVMSPeriodWithData,
  useCreateEVMSPeriod,
  useAddPeriodData,
  useDeleteEVMSPeriod,
} from "./useEVMSMetrics";

vi.mock("@/services/evmsApi", () => ({
  getEVMSSummary: vi.fn(),
  getEVMSPeriods: vi.fn(),
  getEVMSPeriodWithData: vi.fn(),
  createEVMSPeriod: vi.fn(),
  addPeriodData: vi.fn(),
  deleteEVMSPeriod: vi.fn(),
}));

import {
  getEVMSSummary,
  getEVMSPeriods,
  getEVMSPeriodWithData,
  createEVMSPeriod,
  addPeriodData,
  deleteEVMSPeriod,
} from "@/services/evmsApi";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false },
  },
});

const wrapper = ({ children }: { children: React.ReactNode }) =>
  React.createElement(QueryClientProvider, { client: queryClient }, children);

const mockSummary = {
  programId: "prog-1",
  programName: "Test Program",
  budgetAtCompletion: "1000000.00",
  cumulativeBcws: "500000.00",
  cumulativeBcwp: "450000.00",
  cumulativeAcwp: "480000.00",
  costVariance: "-30000.00",
  scheduleVariance: "-50000.00",
  cpi: "0.94",
  spi: "0.90",
  estimateAtCompletion: null,
  estimateToComplete: null,
  varianceAtCompletion: null,
  tcpiEac: null,
  tcpiBac: null,
  percentComplete: "45.0",
  percentSpent: "48.0",
  latestPeriod: null,
};

describe("useEVMSSummary", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("fetches EVMS summary", async () => {
    vi.mocked(getEVMSSummary).mockResolvedValue(mockSummary);

    const { result } = renderHook(() => useEVMSSummary("prog-1"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.programName).toBe("Test Program");
    expect(result.current.data?.cpi).toBe("0.94");
    expect(getEVMSSummary).toHaveBeenCalledWith("prog-1");
  });

  it("does not fetch when programId is empty", () => {
    renderHook(() => useEVMSSummary(""), { wrapper });
    expect(getEVMSSummary).not.toHaveBeenCalled();
  });

  it("handles error", async () => {
    vi.mocked(getEVMSSummary).mockRejectedValue(new Error("API Error"));

    const { result } = renderHook(() => useEVMSSummary("prog-1"), { wrapper });

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.error).toBeTruthy();
  });
});

describe("useEVMSPeriods", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("fetches EVMS periods", async () => {
    vi.mocked(getEVMSPeriods).mockResolvedValue({
      items: [],
      total: 0,
    });

    const { result } = renderHook(() => useEVMSPeriods("prog-1"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(getEVMSPeriods).toHaveBeenCalledWith("prog-1", undefined);
  });

  it("passes status filter", async () => {
    vi.mocked(getEVMSPeriods).mockResolvedValue({
      items: [],
      total: 0,
    });

    const { result } = renderHook(
      () => useEVMSPeriods("prog-1", "approved"),
      { wrapper }
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(getEVMSPeriods).toHaveBeenCalledWith("prog-1", "approved");
  });
});

describe("useEVMSPeriodWithData", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("fetches period with data", async () => {
    const mockPeriod = {
      id: "period-1",
      programId: "prog-1",
      periodStart: "2026-01-01",
      periodEnd: "2026-01-31",
      periodName: "Jan 2026",
      status: "approved" as const,
      notes: null,
      cumulativeBcws: "500000.00",
      cumulativeBcwp: "450000.00",
      cumulativeAcwp: "480000.00",
      costVariance: null,
      scheduleVariance: null,
      cpi: null,
      spi: null,
      createdAt: "2026-01-01T00:00:00Z",
      updatedAt: "2026-01-31T00:00:00Z",
      periodData: [],
    };
    vi.mocked(getEVMSPeriodWithData).mockResolvedValue(mockPeriod);

    const { result } = renderHook(
      () => useEVMSPeriodWithData("period-1"),
      { wrapper }
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.periodName).toBe("Jan 2026");
  });
});

describe("useCreateEVMSPeriod", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("creates a period", async () => {
    vi.mocked(createEVMSPeriod).mockResolvedValue({} as any);

    const { result } = renderHook(() => useCreateEVMSPeriod(), { wrapper });

    result.current.mutate({
      programId: "prog-1",
      periodStart: "2026-02-01",
      periodEnd: "2026-02-28",
      periodName: "Feb 2026",
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(createEVMSPeriod).toHaveBeenCalled();
  });
});

describe("useAddPeriodData", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("adds period data", async () => {
    vi.mocked(addPeriodData).mockResolvedValue({} as any);

    const { result } = renderHook(() => useAddPeriodData("prog-1"), {
      wrapper,
    });

    result.current.mutate({
      periodId: "period-1",
      data: {
        wbsId: "wbs-1",
        bcws: "100000",
        bcwp: "90000",
        acwp: "95000",
      },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(addPeriodData).toHaveBeenCalledWith("period-1", {
      wbsId: "wbs-1",
      bcws: "100000",
      bcwp: "90000",
      acwp: "95000",
    });
  });
});

describe("useDeleteEVMSPeriod", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("deletes a period", async () => {
    vi.mocked(deleteEVMSPeriod).mockResolvedValue(undefined);

    const { result } = renderHook(() => useDeleteEVMSPeriod("prog-1"), {
      wrapper,
    });

    result.current.mutate("period-1");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(deleteEVMSPeriod).toHaveBeenCalledWith("period-1");
  });
});
