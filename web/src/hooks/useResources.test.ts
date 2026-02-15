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

const createQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

let queryClient: QueryClient;

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

const mockEmptyResourceList = {
  items: [],
  total: 0,
  page: 1,
  page_size: 20,
  pages: 0,
};

describe("useResources", () => {
  beforeEach(() => {
    queryClient = createQueryClient();
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

  it("handles fetch error", async () => {
    vi.mocked(getResources).mockRejectedValue(new Error("Server error"));

    const { result } = renderHook(() => useResources("prog-1"), { wrapper });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toBeInstanceOf(Error);
    expect((result.current.error as Error).message).toBe("Server error");
  });

  it("starts in loading state when enabled", () => {
    vi.mocked(getResources).mockReturnValue(new Promise(() => {}));

    const { result } = renderHook(() => useResources("prog-1"), { wrapper });

    expect(result.current.isLoading).toBe(true);
    expect(result.current.data).toBeUndefined();
  });

  it("returns empty list when no resources exist", async () => {
    vi.mocked(getResources).mockResolvedValue(mockEmptyResourceList);

    const { result } = renderHook(() => useResources("prog-1"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.items).toHaveLength(0);
    expect(result.current.data?.total).toBe(0);
    expect(result.current.data?.pages).toBe(0);
  });

  it("filters by resource_type only", async () => {
    vi.mocked(getResources).mockResolvedValue(mockResourceList);

    const { result } = renderHook(
      () => useResources("prog-1", { resource_type: "EQUIPMENT" }),
      { wrapper }
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(getResources).toHaveBeenCalledWith("prog-1", {
      resource_type: "EQUIPMENT",
    });
  });

  it("filters by is_active only", async () => {
    vi.mocked(getResources).mockResolvedValue(mockResourceList);

    const { result } = renderHook(
      () => useResources("prog-1", { is_active: false }),
      { wrapper }
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(getResources).toHaveBeenCalledWith("prog-1", {
      is_active: false,
    });
  });

  it("is disabled when programId is empty string", () => {
    const { result } = renderHook(() => useResources(""), { wrapper });

    expect(result.current.fetchStatus).toBe("idle");
    expect(getResources).not.toHaveBeenCalled();
  });

  it("fetches MATERIAL type resources", async () => {
    const materialResource = {
      ...mockResource,
      id: "res-2",
      name: "Steel Beam",
      code: "MAT-001",
      resource_type: ResourceType.MATERIAL,
      cost_rate: 50,
    };
    vi.mocked(getResources).mockResolvedValue({
      items: [materialResource],
      total: 1,
      page: 1,
      page_size: 20,
      pages: 1,
    });

    const { result } = renderHook(
      () => useResources("prog-1", { resource_type: "MATERIAL" }),
      { wrapper }
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.items[0].resource_type).toBe(ResourceType.MATERIAL);
  });
});

describe("useResource", () => {
  beforeEach(() => {
    queryClient = createQueryClient();
    vi.clearAllMocks();
  });

  it("fetches a single resource", async () => {
    vi.mocked(getResource).mockResolvedValue(mockResource);

    const { result } = renderHook(() => useResource("res-1"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.name).toBe("Senior Engineer");
    expect(getResource).toHaveBeenCalledWith("res-1");
  });

  it("does not fetch when id is empty", () => {
    renderHook(() => useResource(""), { wrapper });
    expect(getResource).not.toHaveBeenCalled();
  });

  it("handles fetch error", async () => {
    vi.mocked(getResource).mockRejectedValue(new Error("Not found"));

    const { result } = renderHook(() => useResource("res-999"), { wrapper });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect((result.current.error as Error).message).toBe("Not found");
  });

  it("starts in loading state when enabled", () => {
    vi.mocked(getResource).mockReturnValue(new Promise(() => {}));

    const { result } = renderHook(() => useResource("res-1"), { wrapper });

    expect(result.current.isLoading).toBe(true);
    expect(result.current.data).toBeUndefined();
  });

  it("is disabled when id is empty string", () => {
    const { result } = renderHook(() => useResource(""), { wrapper });

    expect(result.current.fetchStatus).toBe("idle");
  });

  it("returns resource with null optional fields", async () => {
    const resourceWithNulls = {
      ...mockResource,
      cost_rate: null,
      effective_date: null,
      updated_at: null,
    };
    vi.mocked(getResource).mockResolvedValue(resourceWithNulls);

    const { result } = renderHook(() => useResource("res-1"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.cost_rate).toBeNull();
    expect(result.current.data?.effective_date).toBeNull();
    expect(result.current.data?.updated_at).toBeNull();
  });
});

describe("useCreateResource", () => {
  beforeEach(() => {
    queryClient = createQueryClient();
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

  it("handles create error", async () => {
    vi.mocked(createResource).mockRejectedValue(new Error("Duplicate code"));

    const { result } = renderHook(() => useCreateResource(), { wrapper });

    result.current.mutate({
      program_id: "prog-1",
      name: "Engineer",
      code: "ENG-001",
      resource_type: ResourceType.LABOR,
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect((result.current.error as Error).message).toBe("Duplicate code");
  });

  it("invalidates resource queries on success", async () => {
    vi.mocked(createResource).mockResolvedValue(mockResource);
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    const { result } = renderHook(() => useCreateResource(), { wrapper });

    result.current.mutate({
      program_id: "prog-1",
      name: "Senior Engineer",
      code: "ENG-001",
      resource_type: ResourceType.LABOR,
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["resources"] });
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ["resources", "prog-1"],
    });
  });

  it("starts in idle state", () => {
    const { result } = renderHook(() => useCreateResource(), { wrapper });

    expect(result.current.isIdle).toBe(true);
    expect(result.current.data).toBeUndefined();
  });

  it("creates resource with all optional fields", async () => {
    vi.mocked(createResource).mockResolvedValue(mockResource);

    const { result } = renderHook(() => useCreateResource(), { wrapper });

    result.current.mutate({
      program_id: "prog-1",
      name: "Senior Engineer",
      code: "ENG-001",
      resource_type: ResourceType.LABOR,
      capacity_per_day: 8,
      cost_rate: 150,
      effective_date: "2026-01-01",
      is_active: true,
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(createResource).toHaveBeenCalledWith({
      program_id: "prog-1",
      name: "Senior Engineer",
      code: "ENG-001",
      resource_type: ResourceType.LABOR,
      capacity_per_day: 8,
      cost_rate: 150,
      effective_date: "2026-01-01",
      is_active: true,
    });
  });

  it("creates EQUIPMENT resource", async () => {
    const equipmentResource = {
      ...mockResource,
      resource_type: ResourceType.EQUIPMENT,
      name: "Excavator",
      code: "EQP-001",
    };
    vi.mocked(createResource).mockResolvedValue(equipmentResource);

    const { result } = renderHook(() => useCreateResource(), { wrapper });

    result.current.mutate({
      program_id: "prog-1",
      name: "Excavator",
      code: "EQP-001",
      resource_type: ResourceType.EQUIPMENT,
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.resource_type).toBe(ResourceType.EQUIPMENT);
  });

  it("creates MATERIAL resource", async () => {
    const materialResource = {
      ...mockResource,
      resource_type: ResourceType.MATERIAL,
      name: "Steel Beam",
      code: "MAT-001",
    };
    vi.mocked(createResource).mockResolvedValue(materialResource);

    const { result } = renderHook(() => useCreateResource(), { wrapper });

    result.current.mutate({
      program_id: "prog-1",
      name: "Steel Beam",
      code: "MAT-001",
      resource_type: ResourceType.MATERIAL,
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.resource_type).toBe(ResourceType.MATERIAL);
  });

  it("handles network error", async () => {
    vi.mocked(createResource).mockRejectedValue(new TypeError("Network request failed"));

    const { result } = renderHook(() => useCreateResource(), { wrapper });

    result.current.mutate({
      program_id: "prog-1",
      name: "Engineer",
      code: "ENG-001",
      resource_type: ResourceType.LABOR,
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toBeInstanceOf(TypeError);
  });
});

describe("useUpdateResource", () => {
  beforeEach(() => {
    queryClient = createQueryClient();
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

  it("handles update error", async () => {
    vi.mocked(updateResource).mockRejectedValue(new Error("Conflict"));

    const { result } = renderHook(() => useUpdateResource(), { wrapper });

    result.current.mutate({
      id: "res-1",
      data: { name: "Bad Name" },
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect((result.current.error as Error).message).toBe("Conflict");
  });

  it("invalidates resource queries on success", async () => {
    vi.mocked(updateResource).mockResolvedValue(mockResource);
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    const { result } = renderHook(() => useUpdateResource(), { wrapper });

    result.current.mutate({
      id: "res-1",
      data: { name: "Lead Engineer" },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["resources"] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["resources", "res-1"] });
  });

  it("starts in idle state", () => {
    const { result } = renderHook(() => useUpdateResource(), { wrapper });

    expect(result.current.isIdle).toBe(true);
    expect(result.current.data).toBeUndefined();
  });

  it("updates multiple fields at once", async () => {
    const updatedResource = {
      ...mockResource,
      name: "Lead Engineer",
      cost_rate: 200,
      is_active: false,
    };
    vi.mocked(updateResource).mockResolvedValue(updatedResource);

    const { result } = renderHook(() => useUpdateResource(), { wrapper });

    result.current.mutate({
      id: "res-1",
      data: {
        name: "Lead Engineer",
        cost_rate: 200,
        is_active: false,
      },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(updateResource).toHaveBeenCalledWith("res-1", {
      name: "Lead Engineer",
      cost_rate: 200,
      is_active: false,
    });
  });

  it("updates resource type", async () => {
    vi.mocked(updateResource).mockResolvedValue({
      ...mockResource,
      resource_type: ResourceType.EQUIPMENT,
    });

    const { result } = renderHook(() => useUpdateResource(), { wrapper });

    result.current.mutate({
      id: "res-1",
      data: { resource_type: ResourceType.EQUIPMENT },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(updateResource).toHaveBeenCalledWith("res-1", {
      resource_type: ResourceType.EQUIPMENT,
    });
  });
});

describe("useDeleteResource", () => {
  beforeEach(() => {
    queryClient = createQueryClient();
    vi.clearAllMocks();
  });

  it("deletes a resource", async () => {
    vi.mocked(deleteResource).mockResolvedValue(undefined);

    const { result } = renderHook(() => useDeleteResource(), { wrapper });

    result.current.mutate("res-1");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(deleteResource).toHaveBeenCalledWith("res-1");
  });

  it("handles delete error", async () => {
    vi.mocked(deleteResource).mockRejectedValue(
      new Error("Cannot delete: resource has assignments")
    );

    const { result } = renderHook(() => useDeleteResource(), { wrapper });

    result.current.mutate("res-1");

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect((result.current.error as Error).message).toBe(
      "Cannot delete: resource has assignments"
    );
  });

  it("invalidates resource queries on success", async () => {
    vi.mocked(deleteResource).mockResolvedValue(undefined);
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    const { result } = renderHook(() => useDeleteResource(), { wrapper });

    result.current.mutate("res-1");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["resources"] });
  });

  it("starts in idle state", () => {
    const { result } = renderHook(() => useDeleteResource(), { wrapper });

    expect(result.current.isIdle).toBe(true);
    expect(result.current.data).toBeUndefined();
  });

  it("handles not found error", async () => {
    vi.mocked(deleteResource).mockRejectedValue(new Error("Resource not found"));

    const { result } = renderHook(() => useDeleteResource(), { wrapper });

    result.current.mutate("res-nonexistent");

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect((result.current.error as Error).message).toBe("Resource not found");
  });
});
