import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import {
  useCPRFormat1,
  useCPRFormat3,
  useCPRFormat5,
  useReportAuditTrail,
} from "./useReports";

vi.mock("@/services/reportApi", () => ({
  getCPRFormat1: vi.fn(),
  getCPRFormat3: vi.fn(),
  getCPRFormat5: vi.fn(),
  getReportAuditTrail: vi.fn(),
}));

import {
  getCPRFormat1,
  getCPRFormat3,
  getCPRFormat5,
  getReportAuditTrail,
} from "@/services/reportApi";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

const wrapper = ({ children }: { children: React.ReactNode }) =>
  React.createElement(QueryClientProvider, { client: queryClient }, children);

describe("useCPRFormat1", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("fetches CPR Format 1 report", async () => {
    const mockReport = { program_id: "prog-1", wbs_elements: [] };
    vi.mocked(getCPRFormat1).mockResolvedValue(mockReport);

    const { result } = renderHook(() => useCPRFormat1("prog-1"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(getCPRFormat1).toHaveBeenCalledWith("prog-1", undefined);
  });

  it("passes periodId when provided", async () => {
    vi.mocked(getCPRFormat1).mockResolvedValue({});

    const { result } = renderHook(() => useCPRFormat1("prog-1", "period-1"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(getCPRFormat1).toHaveBeenCalledWith("prog-1", "period-1");
  });

  it("does not fetch when programId is empty", () => {
    renderHook(() => useCPRFormat1(""), { wrapper });
    expect(getCPRFormat1).not.toHaveBeenCalled();
  });
});

describe("useCPRFormat3", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("fetches CPR Format 3 report", async () => {
    vi.mocked(getCPRFormat3).mockResolvedValue({ time_phased_data: [] });

    const { result } = renderHook(() => useCPRFormat3("prog-1"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(getCPRFormat3).toHaveBeenCalledWith("prog-1");
  });

  it("does not fetch when programId is empty", () => {
    renderHook(() => useCPRFormat3(""), { wrapper });
    expect(getCPRFormat3).not.toHaveBeenCalled();
  });
});

describe("useCPRFormat5", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("fetches CPR Format 5 report", async () => {
    vi.mocked(getCPRFormat5).mockResolvedValue({ variances: [] });

    const { result } = renderHook(() => useCPRFormat5("prog-1"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(getCPRFormat5).toHaveBeenCalledWith("prog-1");
  });

  it("does not fetch when programId is empty", () => {
    renderHook(() => useCPRFormat5(""), { wrapper });
    expect(getCPRFormat5).not.toHaveBeenCalled();
  });
});

describe("useReportAuditTrail", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("fetches report audit trail", async () => {
    vi.mocked(getReportAuditTrail).mockResolvedValue([]);

    const { result } = renderHook(() => useReportAuditTrail("prog-1"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(getReportAuditTrail).toHaveBeenCalledWith("prog-1");
  });

  it("does not fetch when programId is empty", () => {
    renderHook(() => useReportAuditTrail(""), { wrapper });
    expect(getReportAuditTrail).not.toHaveBeenCalled();
  });
});
