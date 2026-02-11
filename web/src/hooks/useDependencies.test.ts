import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import {
  useDependencies,
  useCreateDependency,
  useDeleteDependency,
} from "./useDependencies";

vi.mock("@/services/dependencyApi", () => ({
  getDependencies: vi.fn(),
  createDependency: vi.fn(),
  deleteDependency: vi.fn(),
}));

import {
  getDependencies,
  createDependency,
  deleteDependency,
} from "@/services/dependencyApi";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

const wrapper = ({ children }: { children: React.ReactNode }) =>
  React.createElement(QueryClientProvider, { client: queryClient }, children);

const mockDependency = {
  id: "dep-1",
  predecessor_id: "act-1",
  successor_id: "act-2",
  dependency_type: "FS",
  lag: 0,
};

describe("useDependencies", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("fetches dependencies for a program", async () => {
    vi.mocked(getDependencies).mockResolvedValue([mockDependency]);

    const { result } = renderHook(() => useDependencies("prog-1"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toHaveLength(1);
    expect(getDependencies).toHaveBeenCalledWith("prog-1");
  });

  it("does not fetch when programId is empty", () => {
    renderHook(() => useDependencies(""), { wrapper });
    expect(getDependencies).not.toHaveBeenCalled();
  });
});

describe("useCreateDependency", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("creates a dependency", async () => {
    vi.mocked(createDependency).mockResolvedValue(mockDependency);

    const { result } = renderHook(() => useCreateDependency(), { wrapper });

    result.current.mutate({
      predecessor_id: "act-1",
      successor_id: "act-2",
      dependency_type: "FS",
      lag: 0,
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(createDependency).toHaveBeenCalledWith(
      expect.objectContaining({ predecessor_id: "act-1" })
    );
  });
});

describe("useDeleteDependency", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("deletes a dependency", async () => {
    vi.mocked(deleteDependency).mockResolvedValue(undefined);

    const { result } = renderHook(() => useDeleteDependency(), { wrapper });

    result.current.mutate("dep-1");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(deleteDependency).toHaveBeenCalledWith("dep-1");
  });
});
