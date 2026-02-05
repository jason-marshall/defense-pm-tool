import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import {
  usePrograms,
  useProgram,
  useCreateProgram,
  useUpdateProgram,
  useDeleteProgram,
} from "./usePrograms";

vi.mock("@/api/client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

import { apiClient } from "@/api/client";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false },
  },
});

const wrapper = ({ children }: { children: React.ReactNode }) =>
  React.createElement(QueryClientProvider, { client: queryClient }, children);

const mockProgram = {
  id: "prog-1",
  name: "Test Program",
  code: "TP-001",
  status: "active",
  start_date: "2026-01-01",
  end_date: "2026-12-31",
  owner_id: "user-1",
};

describe("usePrograms", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("fetches programs list", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: { items: [mockProgram], total: 1 },
    });

    const { result } = renderHook(() => usePrograms(1, 20), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.items).toHaveLength(1);
    expect(result.current.data?.items[0].name).toBe("Test Program");
    expect(apiClient.get).toHaveBeenCalledWith("/programs?page=1&page_size=20");
  });

  it("fetches single program", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockProgram });

    const { result } = renderHook(() => useProgram("prog-1"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.name).toBe("Test Program");
    expect(apiClient.get).toHaveBeenCalledWith("/programs/prog-1");
  });

  it("does not fetch when id is empty", () => {
    renderHook(() => useProgram(""), { wrapper });
    expect(apiClient.get).not.toHaveBeenCalled();
  });
});

describe("useCreateProgram", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("creates a program", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: mockProgram });

    const { result } = renderHook(() => useCreateProgram(), { wrapper });

    result.current.mutate({
      name: "Test Program",
      code: "TP-001",
      start_date: "2026-01-01",
      end_date: "2026-12-31",
    } as any);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(apiClient.post).toHaveBeenCalledWith("/programs", expect.any(Object));
  });
});

describe("useUpdateProgram", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("updates a program", async () => {
    vi.mocked(apiClient.patch).mockResolvedValue({ data: mockProgram });

    const { result } = renderHook(() => useUpdateProgram("prog-1"), {
      wrapper,
    });

    result.current.mutate({ name: "Updated Program" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(apiClient.patch).toHaveBeenCalledWith("/programs/prog-1", {
      name: "Updated Program",
    });
  });
});

describe("useDeleteProgram", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("deletes a program", async () => {
    vi.mocked(apiClient.delete).mockResolvedValue({});

    const { result } = renderHook(() => useDeleteProgram(), { wrapper });

    result.current.mutate("prog-1");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(apiClient.delete).toHaveBeenCalledWith("/programs/prog-1");
  });
});
