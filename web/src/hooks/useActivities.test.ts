import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import {
  useActivities,
  useActivity,
  useCreateActivity,
  useUpdateActivity,
  useDeleteActivity,
} from "./useActivities";

vi.mock("@/services/activityApi", () => ({
  getActivities: vi.fn(),
  getActivity: vi.fn(),
  createActivity: vi.fn(),
  updateActivity: vi.fn(),
  deleteActivity: vi.fn(),
}));

import {
  getActivities,
  getActivity,
  createActivity,
  updateActivity,
  deleteActivity,
} from "@/services/activityApi";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

const wrapper = ({ children }: { children: React.ReactNode }) =>
  React.createElement(QueryClientProvider, { client: queryClient }, children);

const mockActivity = {
  id: "act-1",
  program_id: "prog-1",
  name: "Design Review",
  code: "DR-001",
  duration: 5,
  budgeted_cost: "5000.00",
  percent_complete: "0.00",
  is_critical: false,
  is_milestone: false,
  created_at: "2026-01-01T00:00:00Z",
};

describe("useActivities", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("fetches activities for a program", async () => {
    vi.mocked(getActivities).mockResolvedValue([mockActivity]);

    const { result } = renderHook(() => useActivities("prog-1"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toHaveLength(1);
    expect(result.current.data![0].name).toBe("Design Review");
    expect(getActivities).toHaveBeenCalledWith("prog-1");
  });

  it("does not fetch when programId is empty", () => {
    renderHook(() => useActivities(""), { wrapper });
    expect(getActivities).not.toHaveBeenCalled();
  });
});

describe("useActivity", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("fetches a single activity", async () => {
    vi.mocked(getActivity).mockResolvedValue(mockActivity);

    const { result } = renderHook(() => useActivity("act-1"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.name).toBe("Design Review");
    expect(getActivity).toHaveBeenCalledWith("act-1");
  });

  it("does not fetch when id is empty", () => {
    renderHook(() => useActivity(""), { wrapper });
    expect(getActivity).not.toHaveBeenCalled();
  });
});

describe("useCreateActivity", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("creates an activity", async () => {
    vi.mocked(createActivity).mockResolvedValue(mockActivity);

    const { result } = renderHook(() => useCreateActivity(), { wrapper });

    result.current.mutate({
      program_id: "prog-1",
      name: "Design Review",
      code: "DR-001",
      duration: 5,
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(createActivity).toHaveBeenCalledWith(
      expect.objectContaining({ name: "Design Review" })
    );
  });
});

describe("useUpdateActivity", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("updates an activity", async () => {
    vi.mocked(updateActivity).mockResolvedValue(mockActivity);

    const { result } = renderHook(() => useUpdateActivity(), { wrapper });

    result.current.mutate({
      id: "act-1",
      data: { name: "Updated Review" },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(updateActivity).toHaveBeenCalledWith("act-1", { name: "Updated Review" });
  });
});

describe("useDeleteActivity", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("deletes an activity", async () => {
    vi.mocked(deleteActivity).mockResolvedValue(undefined);

    const { result } = renderHook(() => useDeleteActivity(), { wrapper });

    result.current.mutate("act-1");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(deleteActivity).toHaveBeenCalledWith("act-1");
  });
});
