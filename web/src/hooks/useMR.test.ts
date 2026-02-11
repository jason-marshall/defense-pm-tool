import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { useMRStatus, useMRHistory, useInitializeMR, useRecordMRChange } from "./useMR";

vi.mock("@/services/mrApi", () => ({
  getMRStatus: vi.fn(),
  initializeMR: vi.fn(),
  recordMRChange: vi.fn(),
  getMRHistory: vi.fn(),
}));

import { getMRStatus, initializeMR, recordMRChange, getMRHistory } from "@/services/mrApi";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

const wrapper = ({ children }: { children: React.ReactNode }) =>
  React.createElement(QueryClientProvider, { client: queryClient }, children);

describe("useMRStatus", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("fetches MR status", async () => {
    const mockStatus = { current_balance: "50000.00", original_amount: "100000.00" };
    vi.mocked(getMRStatus).mockResolvedValue(mockStatus);

    const { result } = renderHook(() => useMRStatus("prog-1"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(getMRStatus).toHaveBeenCalledWith("prog-1");
  });

  it("does not fetch when programId is empty", () => {
    renderHook(() => useMRStatus(""), { wrapper });
    expect(getMRStatus).not.toHaveBeenCalled();
  });
});

describe("useMRHistory", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("fetches MR history", async () => {
    vi.mocked(getMRHistory).mockResolvedValue([]);

    const { result } = renderHook(() => useMRHistory("prog-1"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(getMRHistory).toHaveBeenCalledWith("prog-1", undefined);
  });
});

describe("useInitializeMR", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("initializes management reserve", async () => {
    vi.mocked(initializeMR).mockResolvedValue({ current_balance: "100000.00" });

    const { result } = renderHook(() => useInitializeMR(), { wrapper });

    result.current.mutate({
      programId: "prog-1",
      initialAmount: "100000.00",
      reason: "Initial setup",
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(initializeMR).toHaveBeenCalledWith("prog-1", "100000.00", "Initial setup");
  });
});

describe("useRecordMRChange", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("records an MR change", async () => {
    vi.mocked(recordMRChange).mockResolvedValue({ id: "change-1" });

    const { result } = renderHook(() => useRecordMRChange(), { wrapper });

    result.current.mutate({
      programId: "prog-1",
      data: { amount: "5000.00", reason: "Risk mitigation", change_type: "withdrawal" },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(recordMRChange).toHaveBeenCalled();
  });
});
