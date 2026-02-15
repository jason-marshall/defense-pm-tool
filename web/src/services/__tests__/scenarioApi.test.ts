import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/api/client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}));

import { apiClient } from "@/api/client";
import {
  getScenarios,
  getScenario,
  createScenario,
  simulateScenario,
  promoteScenario,
  deleteScenario,
  scenarioApi,
} from "../scenarioApi";

const mockedGet = vi.mocked(apiClient.get);
const mockedPost = vi.mocked(apiClient.post);
const mockedDelete = vi.mocked(apiClient.delete);

const mockScenario = {
  id: "scen-1",
  program_id: "prog-1",
  name: "Optimistic",
  description: "Best case scenario",
  status: "DRAFT",
  created_at: "2026-01-15T10:00:00Z",
};

const mockListResponse = {
  items: [mockScenario],
  total: 1,
};

describe("scenarioApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("getScenarios", () => {
    it("should fetch scenarios for a program", async () => {
      mockedGet.mockResolvedValue({ data: mockListResponse });

      const result = await getScenarios("prog-1");

      expect(mockedGet).toHaveBeenCalledWith(
        "/scenarios?program_id=prog-1"
      );
      expect(result).toEqual(mockListResponse);
    });

    it("should propagate errors", async () => {
      mockedGet.mockRejectedValue(new Error("Forbidden"));

      await expect(getScenarios("prog-1")).rejects.toThrow("Forbidden");
    });
  });

  describe("getScenario", () => {
    it("should fetch a single scenario", async () => {
      mockedGet.mockResolvedValue({ data: mockScenario });

      const result = await getScenario("scen-1");

      expect(mockedGet).toHaveBeenCalledWith("/scenarios/scen-1");
      expect(result).toEqual(mockScenario);
    });

    it("should propagate errors", async () => {
      mockedGet.mockRejectedValue(new Error("Not found"));

      await expect(getScenario("bad-id")).rejects.toThrow("Not found");
    });
  });

  describe("createScenario", () => {
    it("should post scenario data", async () => {
      mockedPost.mockResolvedValue({ data: mockScenario });

      const createData = {
        program_id: "prog-1",
        name: "Optimistic",
        description: "Best case scenario",
      };

      const result = await createScenario(createData);

      expect(mockedPost).toHaveBeenCalledWith("/scenarios", createData);
      expect(result).toEqual(mockScenario);
    });

    it("should propagate errors", async () => {
      mockedPost.mockRejectedValue(new Error("Validation error"));

      await expect(
        createScenario({ program_id: "prog-1", name: "" } as never)
      ).rejects.toThrow("Validation error");
    });
  });

  describe("simulateScenario", () => {
    it("should post simulate request", async () => {
      const simulated = { ...mockScenario, status: "SIMULATED" };
      mockedPost.mockResolvedValue({ data: simulated });

      const result = await simulateScenario("scen-1");

      expect(mockedPost).toHaveBeenCalledWith("/scenarios/scen-1/simulate");
      expect(result.status).toBe("SIMULATED");
    });

    it("should propagate errors", async () => {
      mockedPost.mockRejectedValue(new Error("Timeout"));

      await expect(simulateScenario("scen-1")).rejects.toThrow("Timeout");
    });
  });

  describe("promoteScenario", () => {
    it("should post promote request", async () => {
      const promoted = { ...mockScenario, status: "PROMOTED" };
      mockedPost.mockResolvedValue({ data: promoted });

      const result = await promoteScenario("scen-1");

      expect(mockedPost).toHaveBeenCalledWith("/scenarios/scen-1/promote");
      expect(result.status).toBe("PROMOTED");
    });

    it("should propagate errors", async () => {
      mockedPost.mockRejectedValue(new Error("Conflict"));

      await expect(promoteScenario("scen-1")).rejects.toThrow("Conflict");
    });
  });

  describe("deleteScenario", () => {
    it("should send delete request", async () => {
      mockedDelete.mockResolvedValue({ data: undefined });

      await deleteScenario("scen-1");

      expect(mockedDelete).toHaveBeenCalledWith("/scenarios/scen-1");
    });

    it("should propagate errors", async () => {
      mockedDelete.mockRejectedValue(new Error("Forbidden"));

      await expect(deleteScenario("scen-1")).rejects.toThrow("Forbidden");
    });
  });

  describe("scenarioApi object", () => {
    it("should export list as getScenarios", () => {
      expect(scenarioApi.list).toBe(getScenarios);
    });

    it("should export get as getScenario", () => {
      expect(scenarioApi.get).toBe(getScenario);
    });

    it("should export create as createScenario", () => {
      expect(scenarioApi.create).toBe(createScenario);
    });

    it("should export simulate as simulateScenario", () => {
      expect(scenarioApi.simulate).toBe(simulateScenario);
    });

    it("should export promote as promoteScenario", () => {
      expect(scenarioApi.promote).toBe(promoteScenario);
    });

    it("should export delete as deleteScenario", () => {
      expect(scenarioApi.delete).toBe(deleteScenario);
    });
  });
});
