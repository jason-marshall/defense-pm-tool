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
  getBaselines,
  getBaseline,
  createBaseline,
  approveBaseline,
  compareBaselines,
  deleteBaseline,
  baselineApi,
} from "../baselineApi";

const mockedGet = vi.mocked(apiClient.get);
const mockedPost = vi.mocked(apiClient.post);
const mockedDelete = vi.mocked(apiClient.delete);

const mockBaseline = {
  id: "bl-1",
  program_id: "prog-1",
  name: "PMB Rev 1",
  description: "Initial performance measurement baseline",
  status: "DRAFT",
  snapshot: {},
  created_at: "2026-01-15T10:00:00Z",
};

const mockListResponse = {
  items: [mockBaseline],
  total: 1,
};

const mockComparison = {
  baseline_a: mockBaseline,
  baseline_b: { ...mockBaseline, id: "bl-2", name: "PMB Rev 2" },
  variances: [],
};

describe("baselineApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("getBaselines", () => {
    it("should fetch baselines for a program", async () => {
      mockedGet.mockResolvedValue({ data: mockListResponse });

      const result = await getBaselines("prog-1");

      expect(mockedGet).toHaveBeenCalledWith(
        "/baselines?program_id=prog-1"
      );
      expect(result).toEqual(mockListResponse);
    });

    it("should propagate errors", async () => {
      mockedGet.mockRejectedValue(new Error("Forbidden"));

      await expect(getBaselines("prog-1")).rejects.toThrow("Forbidden");
    });
  });

  describe("getBaseline", () => {
    it("should fetch a single baseline", async () => {
      mockedGet.mockResolvedValue({ data: mockBaseline });

      const result = await getBaseline("bl-1");

      expect(mockedGet).toHaveBeenCalledWith("/baselines/bl-1");
      expect(result).toEqual(mockBaseline);
    });

    it("should propagate errors", async () => {
      mockedGet.mockRejectedValue(new Error("Not found"));

      await expect(getBaseline("bad-id")).rejects.toThrow("Not found");
    });
  });

  describe("createBaseline", () => {
    it("should post baseline data", async () => {
      mockedPost.mockResolvedValue({ data: mockBaseline });

      const createData = {
        program_id: "prog-1",
        name: "PMB Rev 1",
        description: "Initial performance measurement baseline",
      };

      const result = await createBaseline(createData);

      expect(mockedPost).toHaveBeenCalledWith("/baselines", createData);
      expect(result).toEqual(mockBaseline);
    });

    it("should propagate errors", async () => {
      mockedPost.mockRejectedValue(new Error("Validation error"));

      await expect(
        createBaseline({ program_id: "prog-1", name: "" } as never)
      ).rejects.toThrow("Validation error");
    });
  });

  describe("approveBaseline", () => {
    it("should post approve request", async () => {
      const approved = { ...mockBaseline, status: "APPROVED" };
      mockedPost.mockResolvedValue({ data: approved });

      const result = await approveBaseline("bl-1");

      expect(mockedPost).toHaveBeenCalledWith("/baselines/bl-1/approve");
      expect(result.status).toBe("APPROVED");
    });

    it("should propagate errors", async () => {
      mockedPost.mockRejectedValue(new Error("Conflict"));

      await expect(approveBaseline("bl-1")).rejects.toThrow("Conflict");
    });
  });

  describe("compareBaselines", () => {
    it("should fetch baseline comparison", async () => {
      mockedGet.mockResolvedValue({ data: mockComparison });

      const result = await compareBaselines("bl-1", "bl-2");

      expect(mockedGet).toHaveBeenCalledWith(
        "/baselines/compare?baseline_a=bl-1&baseline_b=bl-2"
      );
      expect(result).toEqual(mockComparison);
    });

    it("should propagate errors", async () => {
      mockedGet.mockRejectedValue(new Error("Not found"));

      await expect(compareBaselines("bl-1", "bad-id")).rejects.toThrow(
        "Not found"
      );
    });
  });

  describe("deleteBaseline", () => {
    it("should send delete request", async () => {
      mockedDelete.mockResolvedValue({ data: undefined });

      await deleteBaseline("bl-1");

      expect(mockedDelete).toHaveBeenCalledWith("/baselines/bl-1");
    });

    it("should propagate errors", async () => {
      mockedDelete.mockRejectedValue(new Error("Forbidden"));

      await expect(deleteBaseline("bl-1")).rejects.toThrow("Forbidden");
    });
  });

  describe("baselineApi object", () => {
    it("should export list as getBaselines", () => {
      expect(baselineApi.list).toBe(getBaselines);
    });

    it("should export get as getBaseline", () => {
      expect(baselineApi.get).toBe(getBaseline);
    });

    it("should export create as createBaseline", () => {
      expect(baselineApi.create).toBe(createBaseline);
    });

    it("should export approve as approveBaseline", () => {
      expect(baselineApi.approve).toBe(approveBaseline);
    });

    it("should export compare as compareBaselines", () => {
      expect(baselineApi.compare).toBe(compareBaselines);
    });

    it("should export delete as deleteBaseline", () => {
      expect(baselineApi.delete).toBe(deleteBaseline);
    });
  });
});
