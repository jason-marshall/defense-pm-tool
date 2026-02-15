import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import {
  useRunLeveling,
  usePreviewLeveling,
  useApplyLeveling,
  useRunParallelLeveling,
  useCompareLevelingAlgorithms,
} from "./useLeveling";

vi.mock("@/services/levelingApi", () => ({
  runLeveling: vi.fn(),
  previewLeveling: vi.fn(),
  applyLeveling: vi.fn(),
  runParallelLeveling: vi.fn(),
  compareLevelingAlgorithms: vi.fn(),
}));

import {
  runLeveling,
  previewLeveling,
  applyLeveling,
  runParallelLeveling,
  compareLevelingAlgorithms,
} from "@/services/levelingApi";

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

const mockResult = {
  program_id: "prog-1",
  success: true,
  activities_shifted: 3,
  iterations_used: 42,
  schedule_extension_days: 5,
  remaining_overallocations: 0,
  new_project_finish: "2026-02-19",
  original_project_finish: "2026-02-14",
  shifts: [
    {
      activity_id: "act-1",
      activity_code: "ACT-001",
      original_start: "2026-02-01",
      original_finish: "2026-02-10",
      new_start: "2026-02-05",
      new_finish: "2026-02-14",
      delay_days: 4,
      reason: "Resource conflict",
    },
  ],
  warnings: [],
};

const mockEmptyResult = {
  program_id: "prog-1",
  success: true,
  activities_shifted: 0,
  iterations_used: 0,
  schedule_extension_days: 0,
  remaining_overallocations: 0,
  new_project_finish: "2026-02-14",
  original_project_finish: "2026-02-14",
  shifts: [],
  warnings: [],
};

const mockParallelResult = {
  ...mockResult,
  algorithm: "parallel" as const,
  threads_used: 4,
  metrics: {
    algorithm: "parallel",
    execution_time_ms: 120,
    activities_shifted: 3,
    schedule_extension_days: 5,
    remaining_overallocations: 0,
  },
};

const mockComparisonResult = {
  program_id: "prog-1",
  serial: {
    algorithm: "serial",
    execution_time_ms: 200,
    activities_shifted: 3,
    schedule_extension_days: 5,
    remaining_overallocations: 0,
  },
  parallel: {
    algorithm: "parallel",
    execution_time_ms: 120,
    activities_shifted: 3,
    schedule_extension_days: 4,
    remaining_overallocations: 0,
  },
  recommendation: "parallel",
};

describe("useRunLeveling", () => {
  beforeEach(() => {
    queryClient = createQueryClient();
    vi.clearAllMocks();
  });

  it("runs leveling algorithm", async () => {
    vi.mocked(runLeveling).mockResolvedValue(mockResult);

    const { result } = renderHook(() => useRunLeveling(), { wrapper });

    result.current.mutate({
      programId: "prog-1",
      options: { preserve_critical_path: true, max_iterations: 100 },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.activities_shifted).toBe(3);
    expect(runLeveling).toHaveBeenCalledWith("prog-1", {
      preserve_critical_path: true,
      max_iterations: 100,
    });
  });

  it("handles failure", async () => {
    vi.mocked(runLeveling).mockRejectedValue(new Error("Server error"));

    const { result } = renderHook(() => useRunLeveling(), { wrapper });

    result.current.mutate({
      programId: "prog-1",
      options: {},
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toBeInstanceOf(Error);
    expect((result.current.error as Error).message).toBe("Server error");
  });

  it("starts in idle state", () => {
    const { result } = renderHook(() => useRunLeveling(), { wrapper });

    expect(result.current.isIdle).toBe(true);
    expect(result.current.isPending).toBe(false);
    expect(result.current.isSuccess).toBe(false);
    expect(result.current.isError).toBe(false);
    expect(result.current.data).toBeUndefined();
  });

  it("transitions to loading state while mutating", async () => {
    let resolvePromise: (value: typeof mockResult) => void;
    const pendingPromise = new Promise<typeof mockResult>((resolve) => {
      resolvePromise = resolve;
    });
    vi.mocked(runLeveling).mockReturnValue(pendingPromise);

    const { result } = renderHook(() => useRunLeveling(), { wrapper });

    result.current.mutate({
      programId: "prog-1",
      options: { preserve_critical_path: false },
    });

    await waitFor(() => expect(result.current.isPending).toBe(true));

    resolvePromise!(mockResult);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });

  it("runs with empty options", async () => {
    vi.mocked(runLeveling).mockResolvedValue(mockEmptyResult);

    const { result } = renderHook(() => useRunLeveling(), { wrapper });

    result.current.mutate({
      programId: "prog-1",
      options: {},
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.activities_shifted).toBe(0);
    expect(result.current.data?.shifts).toHaveLength(0);
    expect(runLeveling).toHaveBeenCalledWith("prog-1", {});
  });

  it("runs with all options specified", async () => {
    vi.mocked(runLeveling).mockResolvedValue(mockResult);

    const { result } = renderHook(() => useRunLeveling(), { wrapper });

    result.current.mutate({
      programId: "prog-1",
      options: {
        preserve_critical_path: true,
        max_iterations: 500,
        level_within_float: true,
        target_resources: ["res-1", "res-2"],
      },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(runLeveling).toHaveBeenCalledWith("prog-1", {
      preserve_critical_path: true,
      max_iterations: 500,
      level_within_float: true,
      target_resources: ["res-1", "res-2"],
    });
  });

  it("handles network error", async () => {
    vi.mocked(runLeveling).mockRejectedValue(new TypeError("Network request failed"));

    const { result } = renderHook(() => useRunLeveling(), { wrapper });

    result.current.mutate({
      programId: "prog-1",
      options: {},
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toBeInstanceOf(TypeError);
  });
});

describe("usePreviewLeveling", () => {
  beforeEach(() => {
    queryClient = createQueryClient();
    vi.clearAllMocks();
  });

  it("previews leveling without applying", async () => {
    vi.mocked(previewLeveling).mockResolvedValue(mockResult);

    const { result } = renderHook(() => usePreviewLeveling(), { wrapper });

    result.current.mutate({
      programId: "prog-1",
      options: { preserve_critical_path: true },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(previewLeveling).toHaveBeenCalledWith("prog-1", {
      preserve_critical_path: true,
    });
  });

  it("handles preview failure", async () => {
    vi.mocked(previewLeveling).mockRejectedValue(new Error("Preview failed"));

    const { result } = renderHook(() => usePreviewLeveling(), { wrapper });

    result.current.mutate({
      programId: "prog-1",
      options: {},
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect((result.current.error as Error).message).toBe("Preview failed");
  });

  it("previews with no options", async () => {
    vi.mocked(previewLeveling).mockResolvedValue(mockEmptyResult);

    const { result } = renderHook(() => usePreviewLeveling(), { wrapper });

    result.current.mutate({
      programId: "prog-1",
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(previewLeveling).toHaveBeenCalledWith("prog-1", undefined);
    expect(result.current.data?.shifts).toHaveLength(0);
  });

  it("starts in idle state", () => {
    const { result } = renderHook(() => usePreviewLeveling(), { wrapper });

    expect(result.current.isIdle).toBe(true);
    expect(result.current.data).toBeUndefined();
  });

  it("returns result with warnings", async () => {
    const resultWithWarnings = {
      ...mockResult,
      warnings: ["Could not resolve all conflicts", "Max iterations reached"],
    };
    vi.mocked(previewLeveling).mockResolvedValue(resultWithWarnings);

    const { result } = renderHook(() => usePreviewLeveling(), { wrapper });

    result.current.mutate({
      programId: "prog-1",
      options: { max_iterations: 10 },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.warnings).toHaveLength(2);
    expect(result.current.data?.warnings[0]).toBe("Could not resolve all conflicts");
  });
});

describe("useApplyLeveling", () => {
  beforeEach(() => {
    queryClient = createQueryClient();
    vi.clearAllMocks();
  });

  it("applies leveling shifts", async () => {
    vi.mocked(applyLeveling).mockResolvedValue(undefined as any);

    const { result } = renderHook(() => useApplyLeveling(), { wrapper });

    result.current.mutate({
      programId: "prog-1",
      shiftIds: ["act-1", "act-2"],
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(applyLeveling).toHaveBeenCalledWith("prog-1", ["act-1", "act-2"]);
  });

  it("handles apply failure", async () => {
    vi.mocked(applyLeveling).mockRejectedValue(new Error("Apply failed"));

    const { result } = renderHook(() => useApplyLeveling(), { wrapper });

    result.current.mutate({
      programId: "prog-1",
      shiftIds: ["act-1"],
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect((result.current.error as Error).message).toBe("Apply failed");
  });

  it("invalidates queries on success", async () => {
    vi.mocked(applyLeveling).mockResolvedValue({ applied_count: 2 } as any);
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    const { result } = renderHook(() => useApplyLeveling(), { wrapper });

    result.current.mutate({
      programId: "prog-1",
      shiftIds: ["act-1", "act-2"],
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["activities"] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["histogram"] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["assignments"] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["resources"] });
  });

  it("applies with empty shift list", async () => {
    vi.mocked(applyLeveling).mockResolvedValue({ applied_count: 0 } as any);

    const { result } = renderHook(() => useApplyLeveling(), { wrapper });

    result.current.mutate({
      programId: "prog-1",
      shiftIds: [],
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(applyLeveling).toHaveBeenCalledWith("prog-1", []);
  });

  it("starts in idle state", () => {
    const { result } = renderHook(() => useApplyLeveling(), { wrapper });

    expect(result.current.isIdle).toBe(true);
    expect(result.current.data).toBeUndefined();
  });
});

describe("useRunParallelLeveling", () => {
  beforeEach(() => {
    queryClient = createQueryClient();
    vi.clearAllMocks();
  });

  it("runs parallel leveling algorithm", async () => {
    vi.mocked(runParallelLeveling).mockResolvedValue(mockParallelResult);

    const { result } = renderHook(() => useRunParallelLeveling(), { wrapper });

    result.current.mutate({
      programId: "prog-1",
      options: { preserve_critical_path: true, max_iterations: 200 },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.algorithm).toBe("parallel");
    expect(result.current.data?.threads_used).toBe(4);
    expect(result.current.data?.activities_shifted).toBe(3);
    expect(runParallelLeveling).toHaveBeenCalledWith("prog-1", {
      preserve_critical_path: true,
      max_iterations: 200,
    });
  });

  it("handles parallel leveling failure", async () => {
    vi.mocked(runParallelLeveling).mockRejectedValue(
      new Error("Parallel leveling failed")
    );

    const { result } = renderHook(() => useRunParallelLeveling(), { wrapper });

    result.current.mutate({
      programId: "prog-1",
      options: {},
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect((result.current.error as Error).message).toBe("Parallel leveling failed");
  });

  it("starts in idle state", () => {
    const { result } = renderHook(() => useRunParallelLeveling(), { wrapper });

    expect(result.current.isIdle).toBe(true);
    expect(result.current.data).toBeUndefined();
  });

  it("runs with level_within_float option", async () => {
    vi.mocked(runParallelLeveling).mockResolvedValue(mockParallelResult);

    const { result } = renderHook(() => useRunParallelLeveling(), { wrapper });

    result.current.mutate({
      programId: "prog-1",
      options: { level_within_float: true },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(runParallelLeveling).toHaveBeenCalledWith("prog-1", {
      level_within_float: true,
    });
  });

  it("returns metrics in result", async () => {
    vi.mocked(runParallelLeveling).mockResolvedValue(mockParallelResult);

    const { result } = renderHook(() => useRunParallelLeveling(), { wrapper });

    result.current.mutate({
      programId: "prog-1",
      options: {},
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.metrics).toBeDefined();
    expect(result.current.data?.metrics.execution_time_ms).toBe(120);
    expect(result.current.data?.metrics.algorithm).toBe("parallel");
  });
});

describe("useCompareLevelingAlgorithms", () => {
  beforeEach(() => {
    queryClient = createQueryClient();
    vi.clearAllMocks();
  });

  it("compares serial and parallel leveling", async () => {
    vi.mocked(compareLevelingAlgorithms).mockResolvedValue(mockComparisonResult);

    const { result } = renderHook(() => useCompareLevelingAlgorithms(), {
      wrapper,
    });

    result.current.mutate({
      programId: "prog-1",
      options: { preserve_critical_path: true },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.serial).toBeDefined();
    expect(result.current.data?.parallel).toBeDefined();
    expect(result.current.data?.recommendation).toBe("parallel");
    expect(result.current.data?.serial.execution_time_ms).toBe(200);
    expect(result.current.data?.parallel.execution_time_ms).toBe(120);
    expect(compareLevelingAlgorithms).toHaveBeenCalledWith("prog-1", {
      preserve_critical_path: true,
    });
  });

  it("handles comparison failure", async () => {
    vi.mocked(compareLevelingAlgorithms).mockRejectedValue(
      new Error("Comparison failed")
    );

    const { result } = renderHook(() => useCompareLevelingAlgorithms(), {
      wrapper,
    });

    result.current.mutate({
      programId: "prog-1",
      options: {},
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect((result.current.error as Error).message).toBe("Comparison failed");
  });

  it("starts in idle state", () => {
    const { result } = renderHook(() => useCompareLevelingAlgorithms(), {
      wrapper,
    });

    expect(result.current.isIdle).toBe(true);
    expect(result.current.data).toBeUndefined();
  });

  it("compares with all options specified", async () => {
    vi.mocked(compareLevelingAlgorithms).mockResolvedValue(mockComparisonResult);

    const { result } = renderHook(() => useCompareLevelingAlgorithms(), {
      wrapper,
    });

    result.current.mutate({
      programId: "prog-1",
      options: {
        preserve_critical_path: false,
        max_iterations: 1000,
        level_within_float: false,
        target_resources: ["res-1"],
      },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(compareLevelingAlgorithms).toHaveBeenCalledWith("prog-1", {
      preserve_critical_path: false,
      max_iterations: 1000,
      level_within_float: false,
      target_resources: ["res-1"],
    });
  });
});
