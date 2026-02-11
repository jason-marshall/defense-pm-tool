import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import {
  useBaselines,
  useCreateBaseline,
  useApproveBaseline,
  useCompareBaselines,
  useDeleteBaseline,
} from "./useBaselines";

vi.mock("@/services/baselineApi", () => ({
  getBaselines: vi.fn(),
  createBaseline: vi.fn(),
  approveBaseline: vi.fn(),
  compareBaselines: vi.fn(),
  deleteBaseline: vi.fn(),
}));

import {
  getBaselines,
  createBaseline,
  approveBaseline,
  compareBaselines,
  deleteBaseline,
} from "@/services/baselineApi";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

const wrapper = ({ children }: { children: React.ReactNode }) =>
  React.createElement(QueryClientProvider, { client: queryClient }, children);

const mockBaseline = {
  id: "bl-1",
  program_id: "prog-1",
  name: "PMB Rev 1",
  version: 1,
  is_approved: false,
};

describe("useBaselines", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("fetches baselines for a program", async () => {
    vi.mocked(getBaselines).mockResolvedValue([mockBaseline]);

    const { result } = renderHook(() => useBaselines("prog-1"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toHaveLength(1);
    expect(getBaselines).toHaveBeenCalledWith("prog-1");
  });

  it("does not fetch when programId is empty", () => {
    renderHook(() => useBaselines(""), { wrapper });
    expect(getBaselines).not.toHaveBeenCalled();
  });
});

describe("useCreateBaseline", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("creates a baseline", async () => {
    vi.mocked(createBaseline).mockResolvedValue(mockBaseline);

    const { result } = renderHook(() => useCreateBaseline(), { wrapper });

    result.current.mutate({
      program_id: "prog-1",
      name: "PMB Rev 1",
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(createBaseline).toHaveBeenCalled();
  });
});

describe("useApproveBaseline", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("approves a baseline", async () => {
    vi.mocked(approveBaseline).mockResolvedValue({ ...mockBaseline, is_approved: true });

    const { result } = renderHook(() => useApproveBaseline(), { wrapper });

    result.current.mutate("bl-1");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(approveBaseline).toHaveBeenCalledWith("bl-1");
  });
});

describe("useCompareBaselines", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("compares two baselines", async () => {
    const comparison = { variances: [] };
    vi.mocked(compareBaselines).mockResolvedValue(comparison);

    const { result } = renderHook(
      () => useCompareBaselines("bl-1", "bl-2"),
      { wrapper }
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(compareBaselines).toHaveBeenCalledWith("bl-1", "bl-2");
  });

  it("does not fetch when IDs are empty", () => {
    renderHook(() => useCompareBaselines("", ""), { wrapper });
    expect(compareBaselines).not.toHaveBeenCalled();
  });
});

describe("useDeleteBaseline", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("deletes a baseline", async () => {
    vi.mocked(deleteBaseline).mockResolvedValue(undefined);

    const { result } = renderHook(() => useDeleteBaseline(), { wrapper });

    result.current.mutate("bl-1");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(deleteBaseline).toHaveBeenCalledWith("bl-1");
  });
});
