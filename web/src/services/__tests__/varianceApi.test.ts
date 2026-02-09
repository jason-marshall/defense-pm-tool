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
  getVariancesByProgram,
  createVariance,
  updateVariance,
  deleteVariance,
  restoreVariance,
  getSignificantVariances,
  varianceApi,
} from "../varianceApi";

const mockedGet = vi.mocked(apiClient.get);
const mockedPost = vi.mocked(apiClient.post);
const mockedPatch = vi.mocked(apiClient.patch);
const mockedDelete = vi.mocked(apiClient.delete);

const mockVariance = {
  id: "var-1",
  program_id: "prog-1",
  wbs_id: null,
  period_id: null,
  created_by: "user-1",
  variance_type: "cost",
  variance_amount: "-5000",
  variance_percent: "-12.5",
  explanation: "Material cost overrun due to supply chain delays",
  corrective_action: "Renegotiate supplier contract",
  expected_resolution: "2026-06-01",
  created_at: "2026-02-01T00:00:00Z",
  updated_at: "2026-02-01T00:00:00Z",
  deleted_at: null,
};

const mockListResponse = {
  items: [mockVariance],
  total: 1,
  page: 1,
  per_page: 20,
  pages: 1,
};

describe("varianceApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("getVariancesByProgram", () => {
    it("should fetch variances by program id", async () => {
      mockedGet.mockResolvedValue({ data: mockListResponse });

      const result = await getVariancesByProgram("prog-1");

      expect(mockedGet).toHaveBeenCalledWith("/variance-explanations/program/prog-1");
      expect(result).toEqual(mockListResponse);
    });

    it("should include query params when provided", async () => {
      mockedGet.mockResolvedValue({ data: mockListResponse });

      await getVariancesByProgram("prog-1", { variance_type: "cost", page: 2 });

      expect(mockedGet).toHaveBeenCalledWith(
        "/variance-explanations/program/prog-1?variance_type=cost&page=2"
      );
    });

    it("should include include_resolved param", async () => {
      mockedGet.mockResolvedValue({ data: mockListResponse });

      await getVariancesByProgram("prog-1", { include_resolved: true });

      expect(mockedGet).toHaveBeenCalledWith(
        "/variance-explanations/program/prog-1?include_resolved=true"
      );
    });
  });

  describe("createVariance", () => {
    it("should post variance data", async () => {
      mockedPost.mockResolvedValue({ data: mockVariance });

      const createData = {
        program_id: "prog-1",
        variance_type: "cost" as const,
        variance_amount: "-5000",
        variance_percent: "-12.5",
        explanation: "Material cost overrun due to supply chain delays",
      };

      const result = await createVariance(createData);

      expect(mockedPost).toHaveBeenCalledWith("/variance-explanations", createData);
      expect(result).toEqual(mockVariance);
    });
  });

  describe("updateVariance", () => {
    it("should patch variance data", async () => {
      mockedPatch.mockResolvedValue({ data: mockVariance });

      const result = await updateVariance("var-1", {
        explanation: "Updated explanation for the cost overrun issue",
      });

      expect(mockedPatch).toHaveBeenCalledWith("/variance-explanations/var-1", {
        explanation: "Updated explanation for the cost overrun issue",
      });
      expect(result).toEqual(mockVariance);
    });
  });

  describe("deleteVariance", () => {
    it("should send delete request", async () => {
      mockedDelete.mockResolvedValue({ data: undefined });

      await deleteVariance("var-1");

      expect(mockedDelete).toHaveBeenCalledWith("/variance-explanations/var-1");
    });
  });

  describe("restoreVariance", () => {
    it("should post restore request", async () => {
      mockedPost.mockResolvedValue({ data: mockVariance });

      const result = await restoreVariance("var-1");

      expect(mockedPost).toHaveBeenCalledWith("/variance-explanations/var-1/restore");
      expect(result).toEqual(mockVariance);
    });
  });

  describe("getSignificantVariances", () => {
    it("should fetch significant variances without threshold", async () => {
      mockedGet.mockResolvedValue({ data: [mockVariance] });

      const result = await getSignificantVariances("prog-1");

      expect(mockedGet).toHaveBeenCalledWith(
        "/variance-explanations/program/prog-1/significant"
      );
      expect(result).toEqual([mockVariance]);
    });

    it("should fetch with custom threshold", async () => {
      mockedGet.mockResolvedValue({ data: [mockVariance] });

      await getSignificantVariances("prog-1", "15.0");

      expect(mockedGet).toHaveBeenCalledWith(
        "/variance-explanations/program/prog-1/significant?threshold_percent=15.0"
      );
    });
  });

  describe("varianceApi object", () => {
    it("should export all methods", () => {
      expect(varianceApi.listByProgram).toBe(getVariancesByProgram);
      expect(varianceApi.create).toBe(createVariance);
      expect(varianceApi.update).toBe(updateVariance);
      expect(varianceApi.delete).toBe(deleteVariance);
      expect(varianceApi.restore).toBe(restoreVariance);
      expect(varianceApi.getSignificant).toBe(getSignificantVariances);
    });
  });
});
