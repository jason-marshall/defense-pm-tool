import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import {
  useActivityAssignments,
  useResourceAssignments,
  useCreateAssignment,
  useUpdateAssignment,
  useDeleteAssignment,
} from "./useAssignments";

vi.mock("@/services/assignmentApi", () => ({
  getActivityAssignments: vi.fn(),
  getResourceAssignments: vi.fn(),
  createAssignment: vi.fn(),
  updateAssignment: vi.fn(),
  deleteAssignment: vi.fn(),
}));

import {
  getActivityAssignments,
  getResourceAssignments,
  createAssignment,
  updateAssignment,
  deleteAssignment,
} from "@/services/assignmentApi";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false },
  },
});

const wrapper = ({ children }: { children: React.ReactNode }) =>
  React.createElement(QueryClientProvider, { client: queryClient }, children);

const mockAssignment = {
  id: "assign-1",
  activity_id: "act-1",
  resource_id: "res-1",
  units: 1.0,
  start_date: null,
  finish_date: null,
};

describe("useActivityAssignments", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("fetches assignments for an activity", async () => {
    vi.mocked(getActivityAssignments).mockResolvedValue([mockAssignment]);

    const { result } = renderHook(
      () => useActivityAssignments("act-1"),
      { wrapper }
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toHaveLength(1);
    expect(result.current.data?.[0].resource_id).toBe("res-1");
    expect(getActivityAssignments).toHaveBeenCalledWith("act-1");
  });

  it("does not fetch when activityId is empty", () => {
    renderHook(() => useActivityAssignments(""), { wrapper });
    expect(getActivityAssignments).not.toHaveBeenCalled();
  });
});

describe("useResourceAssignments", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("fetches assignments for a resource", async () => {
    vi.mocked(getResourceAssignments).mockResolvedValue([mockAssignment]);

    const { result } = renderHook(
      () => useResourceAssignments("res-1"),
      { wrapper }
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toHaveLength(1);
    expect(getResourceAssignments).toHaveBeenCalledWith("res-1");
  });
});

describe("useCreateAssignment", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("creates an assignment", async () => {
    vi.mocked(createAssignment).mockResolvedValue(mockAssignment as any);

    const { result } = renderHook(() => useCreateAssignment(), { wrapper });

    result.current.mutate({
      resourceId: "res-1",
      data: {
        activity_id: "act-1",
        resource_id: "res-1",
        units: 1.0,
      },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(createAssignment).toHaveBeenCalledWith("res-1", {
      activity_id: "act-1",
      resource_id: "res-1",
      units: 1.0,
    });
  });
});

describe("useUpdateAssignment", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("updates an assignment", async () => {
    vi.mocked(updateAssignment).mockResolvedValue(mockAssignment as any);

    const { result } = renderHook(() => useUpdateAssignment(), { wrapper });

    result.current.mutate({
      assignmentId: "assign-1",
      data: { units: 0.5 },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(updateAssignment).toHaveBeenCalledWith("assign-1", { units: 0.5 });
  });
});

describe("useDeleteAssignment", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("deletes an assignment", async () => {
    vi.mocked(deleteAssignment).mockResolvedValue(undefined);

    const { result } = renderHook(() => useDeleteAssignment(), { wrapper });

    result.current.mutate("assign-1");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(deleteAssignment).toHaveBeenCalledWith("assign-1");
  });
});
