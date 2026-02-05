import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import {
  useResources,
  useResource,
  useCreateResource,
  useUpdateResource,
  useDeleteResource,
} from "./useResources";
import { ResourceType } from "@/types/resource";

vi.mock("@/services/resourceApi", () => ({
  getResources: vi.fn(),
  getResource: vi.fn(),
  createResource: vi.fn(),
  updateResource: vi.fn(),
  deleteResource: vi.fn(),
}));

import {
  getResources,
  getResource,
  createResource,
  updateResource,
  deleteResource,
} from "@/services/resourceApi";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false },
  },
});

const wrapper = ({ children }: { children: React.ReactNode }) =>
  React.createElement(QueryClientProvider, { client: queryClient }, children);

const mockResource = {
  id: "res-1",
  program_id: "prog-1",
  name: "Senior Engineer",
  code: "ENG-001",
  resource_type: ResourceType.LABOR,
  capacity_per_day: 8,
  cost_rate: 150,
  effective_date: null,
  is_active: true,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: null,
};

const mockResourceList = {
  items: [mockResource],
  total: 1,
  page: 1,
  page_size: 20,
  pages: 1,
};

describe("useResources", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("fetches resources for a program", async () => {
    vi.mocked(getResources).mockResolvedValue(mockResourceList);

    const { result } = renderHook(() => useResources("prog-1"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.items).toHaveLength(1);
    expect(result.current.data?.items[0].name).toBe("Senior Engineer");
    expect(getResources).toHaveBeenCalledWith("prog-1", undefined);
  });

  it("passes filters to API", async () => {
    vi.mocked(getResources).mockResolvedValue(mockResourceList);

    const { result } = renderHook(
      () => useResources("prog-1", { resource_type: "LABOR", is_active: true }),
      { wrapper }
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(getResources).toHaveBeenCalledWith("prog-1", {
      resource_type: "LABOR",
      is_active: true,
    });
  });

  it("does not fetch when programId is empty", () => {
    renderHook(() => useResources(""), { wrapper });
    expect(getResources).not.toHaveBeenCalled();
  });
});

describe("useResource", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("fetches a single resource", async () => {
    vi.mocked(getResource).mockResolvedValue(mockResource);

    const { result } = renderHook(() => useResource("res-1"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.name).toBe("Senior Engineer");
    expect(getResource).toHaveBeenCalledWith("res-1");
  });
});

describe("useCreateResource", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("creates a resource", async () => {
    vi.mocked(createResource).mockResolvedValue(mockResource);

    const { result } = renderHook(() => useCreateResource(), { wrapper });

    result.current.mutate({
      program_id: "prog-1",
      name: "Senior Engineer",
      code: "ENG-001",
      resource_type: ResourceType.LABOR,
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(createResource).toHaveBeenCalledWith(
      expect.objectContaining({ name: "Senior Engineer" })
    );
  });
});

describe("useUpdateResource", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("updates a resource", async () => {
    vi.mocked(updateResource).mockResolvedValue(mockResource);

    const { result } = renderHook(() => useUpdateResource(), { wrapper });

    result.current.mutate({
      id: "res-1",
      data: { name: "Lead Engineer" },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(updateResource).toHaveBeenCalledWith("res-1", {
      name: "Lead Engineer",
    });
  });
});

describe("useDeleteResource", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("deletes a resource", async () => {
    vi.mocked(deleteResource).mockResolvedValue(undefined);

    const { result } = renderHook(() => useDeleteResource(), { wrapper });

    result.current.mutate("res-1");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(deleteResource).toHaveBeenCalledWith("res-1");
  });
});
