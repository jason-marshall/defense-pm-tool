import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import {
  useSimulationResults,
  useSimulationResult,
  useRunSimulation,
} from "./useSimulations";

vi.mock("@/services/simulationApi", () => ({
  runSimulation: vi.fn(),
  getSimulationResult: vi.fn(),
  getSimulationResults: vi.fn(),
}));

import {
  runSimulation,
  getSimulationResult,
  getSimulationResults,
} from "@/services/simulationApi";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

const wrapper = ({ children }: { children: React.ReactNode }) =>
  React.createElement(QueryClientProvider, { client: queryClient }, children);

const mockResult = {
  id: "sim-1",
  program_id: "prog-1",
  iterations: 1000,
  mean_duration: 45.5,
  p50: 44,
  p80: 52,
  p95: 60,
};

describe("useSimulationResults", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("fetches simulation results for a program", async () => {
    vi.mocked(getSimulationResults).mockResolvedValue([mockResult]);

    const { result } = renderHook(() => useSimulationResults("prog-1"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toHaveLength(1);
    expect(getSimulationResults).toHaveBeenCalledWith("prog-1");
  });

  it("does not fetch when programId is empty", () => {
    renderHook(() => useSimulationResults(""), { wrapper });
    expect(getSimulationResults).not.toHaveBeenCalled();
  });
});

describe("useSimulationResult", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("fetches a single simulation result", async () => {
    vi.mocked(getSimulationResult).mockResolvedValue(mockResult);

    const { result } = renderHook(() => useSimulationResult("sim-1"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(getSimulationResult).toHaveBeenCalledWith("sim-1");
  });

  it("does not fetch when id is empty", () => {
    renderHook(() => useSimulationResult(""), { wrapper });
    expect(getSimulationResult).not.toHaveBeenCalled();
  });
});

describe("useRunSimulation", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("runs a simulation", async () => {
    vi.mocked(runSimulation).mockResolvedValue(mockResult);

    const { result } = renderHook(() => useRunSimulation(), { wrapper });

    result.current.mutate({
      programId: "prog-1",
      config: { iterations: 1000, distribution: "PERT" },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(runSimulation).toHaveBeenCalledWith("prog-1", {
      iterations: 1000,
      distribution: "PERT",
    });
  });
});
