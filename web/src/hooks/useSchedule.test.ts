import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { useScheduleResults, useCalculateSchedule } from "./useSchedule";

vi.mock("@/services/scheduleApi", () => ({
  calculateSchedule: vi.fn(),
  getScheduleResults: vi.fn(),
}));

import { calculateSchedule, getScheduleResults } from "@/services/scheduleApi";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

const wrapper = ({ children }: { children: React.ReactNode }) =>
  React.createElement(QueryClientProvider, { client: queryClient }, children);

const mockScheduleResult = {
  activities: [
    { id: "act-1", early_start: 0, early_finish: 5, is_critical: true },
  ],
};

describe("useScheduleResults", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("fetches schedule results for a program", async () => {
    vi.mocked(getScheduleResults).mockResolvedValue(mockScheduleResult);

    const { result } = renderHook(() => useScheduleResults("prog-1"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(mockScheduleResult);
    expect(getScheduleResults).toHaveBeenCalledWith("prog-1");
  });

  it("does not fetch when programId is empty", () => {
    renderHook(() => useScheduleResults(""), { wrapper });
    expect(getScheduleResults).not.toHaveBeenCalled();
  });
});

describe("useCalculateSchedule", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("calculates schedule for a program", async () => {
    vi.mocked(calculateSchedule).mockResolvedValue(mockScheduleResult);

    const { result } = renderHook(() => useCalculateSchedule(), { wrapper });

    result.current.mutate("prog-1");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(calculateSchedule).toHaveBeenCalledWith("prog-1");
  });
});
