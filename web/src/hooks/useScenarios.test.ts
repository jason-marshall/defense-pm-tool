import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import {
  useScenarios,
  useScenario,
  useCreateScenario,
  useSimulateScenario,
  usePromoteScenario,
  useDeleteScenario,
} from "./useScenarios";

vi.mock("@/services/scenarioApi", () => ({
  getScenarios: vi.fn(),
  getScenario: vi.fn(),
  createScenario: vi.fn(),
  simulateScenario: vi.fn(),
  promoteScenario: vi.fn(),
  deleteScenario: vi.fn(),
}));

import {
  getScenarios,
  getScenario,
  createScenario,
  simulateScenario,
  promoteScenario,
  deleteScenario,
} from "@/services/scenarioApi";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

const wrapper = ({ children }: { children: React.ReactNode }) =>
  React.createElement(QueryClientProvider, { client: queryClient }, children);

const mockScenario = {
  id: "sc-1",
  program_id: "prog-1",
  name: "What-If A",
  status: "draft",
};

describe("useScenarios", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("fetches scenarios for a program", async () => {
    vi.mocked(getScenarios).mockResolvedValue([mockScenario]);

    const { result } = renderHook(() => useScenarios("prog-1"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toHaveLength(1);
    expect(getScenarios).toHaveBeenCalledWith("prog-1");
  });

  it("does not fetch when programId is empty", () => {
    renderHook(() => useScenarios(""), { wrapper });
    expect(getScenarios).not.toHaveBeenCalled();
  });
});

describe("useScenario", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("fetches a single scenario", async () => {
    vi.mocked(getScenario).mockResolvedValue(mockScenario);

    const { result } = renderHook(() => useScenario("sc-1"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(getScenario).toHaveBeenCalledWith("sc-1");
  });

  it("does not fetch when id is empty", () => {
    renderHook(() => useScenario(""), { wrapper });
    expect(getScenario).not.toHaveBeenCalled();
  });
});

describe("useCreateScenario", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("creates a scenario", async () => {
    vi.mocked(createScenario).mockResolvedValue(mockScenario);

    const { result } = renderHook(() => useCreateScenario(), { wrapper });

    result.current.mutate({ program_id: "prog-1", name: "What-If A" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(createScenario).toHaveBeenCalled();
  });
});

describe("useSimulateScenario", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("simulates a scenario", async () => {
    vi.mocked(simulateScenario).mockResolvedValue({ status: "completed" });

    const { result } = renderHook(() => useSimulateScenario(), { wrapper });

    result.current.mutate("sc-1");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(simulateScenario).toHaveBeenCalledWith("sc-1");
  });
});

describe("usePromoteScenario", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("promotes a scenario", async () => {
    vi.mocked(promoteScenario).mockResolvedValue({ status: "promoted" });

    const { result } = renderHook(() => usePromoteScenario(), { wrapper });

    result.current.mutate("sc-1");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(promoteScenario).toHaveBeenCalledWith("sc-1");
  });
});

describe("useDeleteScenario", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("deletes a scenario", async () => {
    vi.mocked(deleteScenario).mockResolvedValue(undefined);

    const { result } = renderHook(() => useDeleteScenario(), { wrapper });

    result.current.mutate("sc-1");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(deleteScenario).toHaveBeenCalledWith("sc-1");
  });
});
