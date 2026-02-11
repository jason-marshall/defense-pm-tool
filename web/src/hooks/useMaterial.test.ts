import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { useProgramMaterials, useMaterialStatus, useConsumeMaterial } from "./useMaterial";

vi.mock("@/services/materialApi", () => ({
  getProgramMaterials: vi.fn(),
  getMaterialStatus: vi.fn(),
  consumeMaterial: vi.fn(),
}));

import {
  getProgramMaterials,
  getMaterialStatus,
  consumeMaterial,
} from "@/services/materialApi";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

const wrapper = ({ children }: { children: React.ReactNode }) =>
  React.createElement(QueryClientProvider, { client: queryClient }, children);

describe("useProgramMaterials", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("fetches program materials", async () => {
    vi.mocked(getProgramMaterials).mockResolvedValue([]);

    const { result } = renderHook(() => useProgramMaterials("prog-1"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(getProgramMaterials).toHaveBeenCalledWith("prog-1");
  });

  it("does not fetch when programId is empty", () => {
    renderHook(() => useProgramMaterials(""), { wrapper });
    expect(getProgramMaterials).not.toHaveBeenCalled();
  });
});

describe("useMaterialStatus", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("fetches material status", async () => {
    vi.mocked(getMaterialStatus).mockResolvedValue({ available: 100, consumed: 20 });

    const { result } = renderHook(() => useMaterialStatus("res-1"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(getMaterialStatus).toHaveBeenCalledWith("res-1");
  });

  it("does not fetch when resourceId is empty", () => {
    renderHook(() => useMaterialStatus(""), { wrapper });
    expect(getMaterialStatus).not.toHaveBeenCalled();
  });
});

describe("useConsumeMaterial", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("consumes material", async () => {
    vi.mocked(consumeMaterial).mockResolvedValue({ remaining: 80 });

    const { result } = renderHook(() => useConsumeMaterial(), { wrapper });

    result.current.mutate({ assignmentId: "assign-1", quantity: 5 });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(consumeMaterial).toHaveBeenCalledWith("assign-1", 5);
  });
});
