import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/api/client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

import { apiClient } from "@/api/client";
import {
  getDependencies,
  createDependency,
  updateDependency,
  deleteDependency,
  dependencyApi,
} from "../dependencyApi";

const mockedGet = vi.mocked(apiClient.get);
const mockedPost = vi.mocked(apiClient.post);
const mockedPatch = vi.mocked(apiClient.patch);
const mockedDelete = vi.mocked(apiClient.delete);

const mockDependency = {
  id: "dep-1",
  predecessor_id: "act-1",
  successor_id: "act-2",
  dependency_type: "FS",
  lag: 0,
  created_at: "2026-01-15T10:00:00Z",
  updated_at: "2026-01-15T10:00:00Z",
};

const mockListResponse = {
  items: [mockDependency],
  total: 1,
};

describe("dependencyApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("getDependencies", () => {
    it("should fetch dependencies for a program", async () => {
      mockedGet.mockResolvedValue({ data: mockListResponse });

      const result = await getDependencies("prog-1");

      expect(mockedGet).toHaveBeenCalledWith(
        "/dependencies?program_id=prog-1"
      );
      expect(result).toEqual(mockListResponse);
    });

    it("should propagate errors", async () => {
      mockedGet.mockRejectedValue(new Error("Forbidden"));

      await expect(getDependencies("prog-1")).rejects.toThrow("Forbidden");
    });
  });

  describe("createDependency", () => {
    it("should post dependency data", async () => {
      mockedPost.mockResolvedValue({ data: mockDependency });

      const createData = {
        predecessor_id: "act-1",
        successor_id: "act-2",
        dependency_type: "FS" as const,
        lag: 0,
      };

      const result = await createDependency(createData);

      expect(mockedPost).toHaveBeenCalledWith("/dependencies", createData);
      expect(result).toEqual(mockDependency);
    });

    it("should propagate errors", async () => {
      mockedPost.mockRejectedValue(new Error("Circular dependency"));

      await expect(
        createDependency({
          predecessor_id: "act-1",
          successor_id: "act-1",
        } as never)
      ).rejects.toThrow("Circular dependency");
    });
  });

  describe("updateDependency", () => {
    it("should patch dependency with partial data", async () => {
      const updated = { ...mockDependency, lag: 2 };
      mockedPatch.mockResolvedValue({ data: updated });

      const result = await updateDependency("dep-1", { lag: 2 });

      expect(mockedPatch).toHaveBeenCalledWith("/dependencies/dep-1", {
        lag: 2,
      });
      expect(result).toEqual(updated);
    });

    it("should propagate errors", async () => {
      mockedPatch.mockRejectedValue(new Error("Not found"));

      await expect(
        updateDependency("bad-id", { lag: 1 })
      ).rejects.toThrow("Not found");
    });
  });

  describe("deleteDependency", () => {
    it("should send delete request", async () => {
      mockedDelete.mockResolvedValue({ data: undefined });

      await deleteDependency("dep-1");

      expect(mockedDelete).toHaveBeenCalledWith("/dependencies/dep-1");
    });

    it("should propagate errors", async () => {
      mockedDelete.mockRejectedValue(new Error("Forbidden"));

      await expect(deleteDependency("dep-1")).rejects.toThrow("Forbidden");
    });
  });

  describe("dependencyApi object", () => {
    it("should export list as getDependencies", () => {
      expect(dependencyApi.list).toBe(getDependencies);
    });

    it("should export create as createDependency", () => {
      expect(dependencyApi.create).toBe(createDependency);
    });

    it("should export update as updateDependency", () => {
      expect(dependencyApi.update).toBe(updateDependency);
    });

    it("should export delete as deleteDependency", () => {
      expect(dependencyApi.delete).toBe(deleteDependency);
    });
  });
});
