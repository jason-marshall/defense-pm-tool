import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import {
  useRunLeveling,
  usePreviewLeveling,
  useApplyLeveling,
} from "./useLeveling";

vi.mock("@/services/levelingApi", () => ({
  runLeveling: vi.fn(),
  previewLeveling: vi.fn(),
  applyLeveling: vi.fn(),
}));

import {
  runLeveling,
  previewLeveling,
  applyLeveling,
} from "@/services/levelingApi";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false },
  },
});

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

describe("useRunLeveling", () => {
  beforeEach(() => {
    queryClient.clear();
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
  });
});

describe("usePreviewLeveling", () => {
  beforeEach(() => {
    queryClient.clear();
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
});

describe("useApplyLeveling", () => {
  beforeEach(() => {
    queryClient.clear();
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
});
