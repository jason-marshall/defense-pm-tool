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
  getPrograms,
  getProgram,
  createProgram,
  updateProgram,
  deleteProgram,
  programApi,
} from "../programApi";

const mockedGet = vi.mocked(apiClient.get);
const mockedPost = vi.mocked(apiClient.post);
const mockedPatch = vi.mocked(apiClient.patch);
const mockedDelete = vi.mocked(apiClient.delete);

const mockProgram = {
  id: "prog-1",
  name: "Test Program",
  code: "TP-001",
  description: null,
  status: "ACTIVE" as const,
  planned_start_date: "2026-01-01",
  planned_end_date: "2026-12-31",
  actual_start_date: null,
  actual_end_date: null,
  budget_at_completion: "5000000",
  contract_number: null,
  contract_type: null,
  owner_id: "user-1",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: null,
};

const mockListResponse = {
  items: [mockProgram],
  total: 1,
  page: 1,
  page_size: 20,
};

describe("programApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("getPrograms", () => {
    it("should fetch programs without params", async () => {
      mockedGet.mockResolvedValue({ data: mockListResponse });

      const result = await getPrograms();

      expect(mockedGet).toHaveBeenCalledWith("/programs");
      expect(result).toEqual(mockListResponse);
    });

    it("should include page and page_size params", async () => {
      mockedGet.mockResolvedValue({ data: mockListResponse });

      await getPrograms({ page: 2, page_size: 50 });

      expect(mockedGet).toHaveBeenCalledWith(
        "/programs?page=2&page_size=50"
      );
    });

    it("should include status filter", async () => {
      mockedGet.mockResolvedValue({ data: mockListResponse });

      await getPrograms({ status: "ACTIVE" });

      expect(mockedGet).toHaveBeenCalledWith("/programs?status=ACTIVE");
    });

    it("should propagate errors", async () => {
      mockedGet.mockRejectedValue(new Error("Network error"));

      await expect(getPrograms()).rejects.toThrow("Network error");
    });
  });

  describe("getProgram", () => {
    it("should fetch a single program by id", async () => {
      mockedGet.mockResolvedValue({ data: mockProgram });

      const result = await getProgram("prog-1");

      expect(mockedGet).toHaveBeenCalledWith("/programs/prog-1");
      expect(result).toEqual(mockProgram);
    });

    it("should propagate errors", async () => {
      mockedGet.mockRejectedValue(new Error("Not found"));

      await expect(getProgram("bad-id")).rejects.toThrow("Not found");
    });
  });

  describe("createProgram", () => {
    it("should post program data", async () => {
      mockedPost.mockResolvedValue({ data: mockProgram });

      const createData = {
        name: "Test Program",
        code: "TP-001",
        planned_start_date: "2026-01-01",
        planned_end_date: "2026-12-31",
      };

      const result = await createProgram(createData);

      expect(mockedPost).toHaveBeenCalledWith("/programs", createData);
      expect(result).toEqual(mockProgram);
    });

    it("should propagate validation errors", async () => {
      mockedPost.mockRejectedValue(new Error("Validation error"));

      await expect(
        createProgram({
          name: "",
          code: "",
          planned_start_date: "",
          planned_end_date: "",
        })
      ).rejects.toThrow("Validation error");
    });
  });

  describe("updateProgram", () => {
    it("should patch program with partial data", async () => {
      const updated = { ...mockProgram, name: "Updated Program" };
      mockedPatch.mockResolvedValue({ data: updated });

      const result = await updateProgram("prog-1", { name: "Updated Program" });

      expect(mockedPatch).toHaveBeenCalledWith("/programs/prog-1", {
        name: "Updated Program",
      });
      expect(result).toEqual(updated);
    });

    it("should propagate errors", async () => {
      mockedPatch.mockRejectedValue(new Error("Conflict"));

      await expect(
        updateProgram("prog-1", { name: "Dup" })
      ).rejects.toThrow("Conflict");
    });
  });

  describe("deleteProgram", () => {
    it("should send delete request", async () => {
      mockedDelete.mockResolvedValue({ data: undefined });

      await deleteProgram("prog-1");

      expect(mockedDelete).toHaveBeenCalledWith("/programs/prog-1");
    });

    it("should propagate errors", async () => {
      mockedDelete.mockRejectedValue(new Error("Forbidden"));

      await expect(deleteProgram("prog-1")).rejects.toThrow("Forbidden");
    });
  });

  describe("programApi object", () => {
    it("should export list as getPrograms", () => {
      expect(programApi.list).toBe(getPrograms);
    });

    it("should export get as getProgram", () => {
      expect(programApi.get).toBe(getProgram);
    });

    it("should export create as createProgram", () => {
      expect(programApi.create).toBe(createProgram);
    });

    it("should export update as updateProgram", () => {
      expect(programApi.update).toBe(updateProgram);
    });

    it("should export delete as deleteProgram", () => {
      expect(programApi.delete).toBe(deleteProgram);
    });
  });
});
