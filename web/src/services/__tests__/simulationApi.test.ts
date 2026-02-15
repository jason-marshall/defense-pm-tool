import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/api/client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

import { apiClient } from "@/api/client";
import {
  runSimulation,
  getSimulationResult,
  getSimulationResults,
  simulationApi,
} from "../simulationApi";

const mockedGet = vi.mocked(apiClient.get);
const mockedPost = vi.mocked(apiClient.post);

const mockResult = {
  id: "sim-1",
  program_id: "prog-1",
  iterations: 1000,
  p50_duration: 120,
  p85_duration: 135,
  mean_duration: 122.5,
  std_deviation: 12.3,
};

const mockConfig = {
  iterations: 1000,
  distribution: "PERT" as const,
};

describe("simulationApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("runSimulation", () => {
    it("should post simulation with config", async () => {
      mockedPost.mockResolvedValue({ data: mockResult });

      const result = await runSimulation("prog-1", mockConfig);

      expect(mockedPost).toHaveBeenCalledWith("/simulations/monte-carlo", {
        program_id: "prog-1",
        ...mockConfig,
      });
      expect(result).toEqual(mockResult);
    });

    it("should propagate errors", async () => {
      mockedPost.mockRejectedValue(new Error("Timeout"));

      await expect(runSimulation("prog-1", mockConfig)).rejects.toThrow(
        "Timeout"
      );
    });
  });

  describe("getSimulationResult", () => {
    it("should fetch a single simulation result", async () => {
      mockedGet.mockResolvedValue({ data: mockResult });

      const result = await getSimulationResult("sim-1");

      expect(mockedGet).toHaveBeenCalledWith("/simulations/sim-1");
      expect(result).toEqual(mockResult);
    });

    it("should propagate errors", async () => {
      mockedGet.mockRejectedValue(new Error("Not found"));

      await expect(getSimulationResult("bad-id")).rejects.toThrow("Not found");
    });
  });

  describe("getSimulationResults", () => {
    it("should fetch all simulation results for a program", async () => {
      mockedGet.mockResolvedValue({ data: [mockResult] });

      const result = await getSimulationResults("prog-1");

      expect(mockedGet).toHaveBeenCalledWith(
        "/simulations?program_id=prog-1"
      );
      expect(result).toEqual([mockResult]);
    });

    it("should propagate errors", async () => {
      mockedGet.mockRejectedValue(new Error("Server error"));

      await expect(getSimulationResults("prog-1")).rejects.toThrow(
        "Server error"
      );
    });
  });

  describe("simulationApi object", () => {
    it("should export run as runSimulation", () => {
      expect(simulationApi.run).toBe(runSimulation);
    });

    it("should export get as getSimulationResult", () => {
      expect(simulationApi.get).toBe(getSimulationResult);
    });

    it("should export list as getSimulationResults", () => {
      expect(simulationApi.list).toBe(getSimulationResults);
    });
  });
});
