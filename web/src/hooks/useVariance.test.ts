import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import {
  useVariancesByProgram,
  useCreateVariance,
  useUpdateVariance,
  useDeleteVariance,
} from "./useVariance";

vi.mock("@/services/varianceApi", () => ({
  getVariancesByProgram: vi.fn(),
  createVariance: vi.fn(),
  updateVariance: vi.fn(),
  deleteVariance: vi.fn(),
}));

import {
  getVariancesByProgram,
  createVariance,
  updateVariance,
  deleteVariance,
} from "@/services/varianceApi";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

const wrapper = ({ children }: { children: React.ReactNode }) =>
  React.createElement(QueryClientProvider, { client: queryClient }, children);

describe("useVariancesByProgram", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("fetches variances for a program", async () => {
    vi.mocked(getVariancesByProgram).mockResolvedValue({ items: [], total: 0 });

    const { result } = renderHook(() => useVariancesByProgram("prog-1"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(getVariancesByProgram).toHaveBeenCalledWith("prog-1", undefined);
  });

  it("does not fetch when programId is empty", () => {
    renderHook(() => useVariancesByProgram(""), { wrapper });
    expect(getVariancesByProgram).not.toHaveBeenCalled();
  });
});

describe("useCreateVariance", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("creates a variance explanation", async () => {
    vi.mocked(createVariance).mockResolvedValue({ id: "var-1" });

    const { result } = renderHook(() => useCreateVariance(), { wrapper });

    result.current.mutate({
      program_id: "prog-1",
      variance_type: "cost",
      explanation: "Material cost increase",
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(createVariance).toHaveBeenCalled();
  });
});

describe("useUpdateVariance", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("updates a variance explanation", async () => {
    vi.mocked(updateVariance).mockResolvedValue({ id: "var-1" });

    const { result } = renderHook(() => useUpdateVariance(), { wrapper });

    result.current.mutate({
      id: "var-1",
      data: { explanation: "Updated explanation" },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(updateVariance).toHaveBeenCalledWith("var-1", { explanation: "Updated explanation" });
  });
});

describe("useDeleteVariance", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("deletes a variance explanation", async () => {
    vi.mocked(deleteVariance).mockResolvedValue(undefined);

    const { result } = renderHook(() => useDeleteVariance(), { wrapper });

    result.current.mutate("var-1");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(deleteVariance).toHaveBeenCalledWith("var-1");
  });
});
