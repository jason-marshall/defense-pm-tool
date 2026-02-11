import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import {
  useResourcePools,
  useResourcePool,
  useCreatePool,
  useUpdatePool,
  useDeletePool,
  usePoolMembers,
  useAddPoolMember,
  useRemovePoolMember,
  useGrantPoolAccess,
  usePoolAvailability,
  useCheckConflict,
} from "./useResourcePools";

vi.mock("@/services/resourcePoolApi", () => ({
  listPools: vi.fn(),
  getPool: vi.fn(),
  createPool: vi.fn(),
  updatePool: vi.fn(),
  deletePool: vi.fn(),
  listPoolMembers: vi.fn(),
  addPoolMember: vi.fn(),
  removePoolMember: vi.fn(),
  grantPoolAccess: vi.fn(),
  getPoolAvailability: vi.fn(),
  checkConflict: vi.fn(),
}));

import {
  listPools,
  getPool,
  createPool,
  updatePool,
  deletePool,
  listPoolMembers,
  addPoolMember,
  removePoolMember,
  grantPoolAccess,
  getPoolAvailability,
  checkConflict,
} from "@/services/resourcePoolApi";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

const wrapper = ({ children }: { children: React.ReactNode }) =>
  React.createElement(QueryClientProvider, { client: queryClient }, children);

const mockPool = {
  id: "pool-1",
  name: "Shared Engineers",
  code: "POOL-001",
  is_active: true,
};

describe("useResourcePools", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("fetches all pools", async () => {
    vi.mocked(listPools).mockResolvedValue([mockPool]);

    const { result } = renderHook(() => useResourcePools(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toHaveLength(1);
    expect(listPools).toHaveBeenCalled();
  });
});

describe("useResourcePool", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("fetches a single pool", async () => {
    vi.mocked(getPool).mockResolvedValue(mockPool);

    const { result } = renderHook(() => useResourcePool("pool-1"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(getPool).toHaveBeenCalledWith("pool-1");
  });

  it("does not fetch when poolId is empty", () => {
    renderHook(() => useResourcePool(""), { wrapper });
    expect(getPool).not.toHaveBeenCalled();
  });
});

describe("useCreatePool", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("creates a pool", async () => {
    vi.mocked(createPool).mockResolvedValue(mockPool);

    const { result } = renderHook(() => useCreatePool(), { wrapper });

    result.current.mutate({ name: "Shared Engineers", code: "POOL-001" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(createPool).toHaveBeenCalled();
  });
});

describe("useUpdatePool", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("updates a pool", async () => {
    vi.mocked(updatePool).mockResolvedValue(mockPool);

    const { result } = renderHook(() => useUpdatePool(), { wrapper });

    result.current.mutate({ poolId: "pool-1", data: { name: "Updated Pool" } });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(updatePool).toHaveBeenCalledWith("pool-1", { name: "Updated Pool" });
  });
});

describe("useDeletePool", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("deletes a pool", async () => {
    vi.mocked(deletePool).mockResolvedValue(undefined);

    const { result } = renderHook(() => useDeletePool(), { wrapper });

    result.current.mutate("pool-1");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(deletePool).toHaveBeenCalledWith("pool-1");
  });
});

describe("usePoolMembers", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("fetches pool members", async () => {
    vi.mocked(listPoolMembers).mockResolvedValue([]);

    const { result } = renderHook(() => usePoolMembers("pool-1"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(listPoolMembers).toHaveBeenCalledWith("pool-1");
  });

  it("does not fetch when poolId is empty", () => {
    renderHook(() => usePoolMembers(""), { wrapper });
    expect(listPoolMembers).not.toHaveBeenCalled();
  });
});

describe("useAddPoolMember", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("adds a pool member", async () => {
    vi.mocked(addPoolMember).mockResolvedValue({ id: "mem-1" });

    const { result } = renderHook(() => useAddPoolMember(), { wrapper });

    result.current.mutate({
      poolId: "pool-1",
      data: { resource_id: "res-1", allocation_percentage: 100 },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(addPoolMember).toHaveBeenCalledWith("pool-1", {
      resource_id: "res-1",
      allocation_percentage: 100,
    });
  });
});

describe("useRemovePoolMember", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("removes a pool member", async () => {
    vi.mocked(removePoolMember).mockResolvedValue(undefined);

    const { result } = renderHook(() => useRemovePoolMember(), { wrapper });

    result.current.mutate({ poolId: "pool-1", memberId: "mem-1" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(removePoolMember).toHaveBeenCalledWith("pool-1", "mem-1");
  });
});

describe("useGrantPoolAccess", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("grants pool access", async () => {
    vi.mocked(grantPoolAccess).mockResolvedValue({ id: "access-1" });

    const { result } = renderHook(() => useGrantPoolAccess(), { wrapper });

    result.current.mutate({
      poolId: "pool-1",
      data: { program_id: "prog-1", access_level: "VIEWER" },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(grantPoolAccess).toHaveBeenCalled();
  });
});

describe("usePoolAvailability", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("fetches pool availability", async () => {
    const mockAvailability = { pool_id: "pool-1", resources: [], conflicts: [] };
    vi.mocked(getPoolAvailability).mockResolvedValue(mockAvailability);

    const { result } = renderHook(
      () => usePoolAvailability("pool-1", "2024-01-01", "2024-01-31"),
      { wrapper }
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(getPoolAvailability).toHaveBeenCalledWith("pool-1", "2024-01-01", "2024-01-31");
  });

  it("does not fetch when params are empty", () => {
    renderHook(() => usePoolAvailability("", "", ""), { wrapper });
    expect(getPoolAvailability).not.toHaveBeenCalled();
  });
});

describe("useCheckConflict", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("checks for conflicts", async () => {
    vi.mocked(checkConflict).mockResolvedValue({
      has_conflicts: false,
      conflict_count: 0,
      conflicts: [],
    });

    const { result } = renderHook(() => useCheckConflict(), { wrapper });

    result.current.mutate({
      resource_id: "res-1",
      program_id: "prog-1",
      start_date: "2024-01-01",
      end_date: "2024-01-31",
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(checkConflict).toHaveBeenCalled();
  });
});
