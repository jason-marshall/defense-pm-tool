import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/api/client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

import { apiClient } from "@/api/client";
import {
  getEVMSPeriods,
  getEVMSPeriodWithData,
  getEVMSSummary,
  createEVMSPeriod,
  addPeriodData,
  deleteEVMSPeriod,
} from "../evmsApi";

const mockedGet = vi.mocked(apiClient.get);
const mockedPost = vi.mocked(apiClient.post);
const mockedDelete = vi.mocked(apiClient.delete);

const mockPeriod = {
  id: "period-001",
  programId: "prog-001",
  periodStart: "2026-01-01",
  periodEnd: "2026-01-31",
  periodName: "January 2026",
  status: "draft" as const,
  notes: "Initial period",
  cumulativeBcws: "100000.00",
  cumulativeBcwp: "95000.00",
  cumulativeAcwp: "98000.00",
  costVariance: "-3000.00",
  scheduleVariance: "-5000.00",
  cpi: "0.969",
  spi: "0.950",
  createdAt: "2026-01-01T00:00:00Z",
  updatedAt: null,
};

const mockApprovedPeriod = {
  ...mockPeriod,
  id: "period-002",
  periodStart: "2026-02-01",
  periodEnd: "2026-02-28",
  periodName: "February 2026",
  status: "approved" as const,
  notes: null,
};

const mockPeriodData = {
  id: "data-001",
  periodId: "period-001",
  wbsId: "wbs-001",
  bcws: "50000.00",
  bcwp: "48000.00",
  acwp: "49000.00",
  cumulativeBcws: "50000.00",
  cumulativeBcwp: "48000.00",
  cumulativeAcwp: "49000.00",
  cv: "-1000.00",
  sv: "-2000.00",
  cpi: "0.980",
  spi: "0.960",
  createdAt: "2026-01-15T00:00:00Z",
  updatedAt: null,
};

const mockPeriodWithData = {
  ...mockPeriod,
  periodData: [mockPeriodData],
};

const mockSummary = {
  programId: "prog-001",
  programName: "Test Program",
  budgetAtCompletion: "1000000.00",
  cumulativeBcws: "100000.00",
  cumulativeBcwp: "95000.00",
  cumulativeAcwp: "98000.00",
  costVariance: "-3000.00",
  scheduleVariance: "-5000.00",
  cpi: "0.969",
  spi: "0.950",
  estimateAtCompletion: "1031958.76",
  estimateToComplete: "933958.76",
  varianceAtCompletion: "-31958.76",
  tcpiEac: "0.969",
  tcpiBac: "1.003",
  percentComplete: "9.50",
  percentSpent: "9.80",
  latestPeriod: mockPeriod,
};

const mockListResponse = {
  items: [mockPeriod, mockApprovedPeriod],
  total: 2,
};

describe("evmsApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("getEVMSPeriods", () => {
    it("should fetch periods with only programId", async () => {
      mockedGet.mockResolvedValue({ data: mockListResponse });

      const result = await getEVMSPeriods("prog-001");

      expect(mockedGet).toHaveBeenCalledWith(
        "/evms/periods?program_id=prog-001"
      );
      expect(result).toEqual(mockListResponse);
    });

    it("should return items and total from response", async () => {
      mockedGet.mockResolvedValue({ data: mockListResponse });

      const result = await getEVMSPeriods("prog-001");

      expect(result.items).toHaveLength(2);
      expect(result.total).toBe(2);
    });

    it("should include status filter when provided", async () => {
      mockedGet.mockResolvedValue({
        data: { items: [mockApprovedPeriod], total: 1 },
      });

      const result = await getEVMSPeriods("prog-001", "approved");

      expect(mockedGet).toHaveBeenCalledWith(
        "/evms/periods?program_id=prog-001&status=approved"
      );
      expect(result.items).toHaveLength(1);
    });

    it("should include draft status filter", async () => {
      mockedGet.mockResolvedValue({
        data: { items: [mockPeriod], total: 1 },
      });

      await getEVMSPeriods("prog-001", "draft");

      expect(mockedGet).toHaveBeenCalledWith(
        "/evms/periods?program_id=prog-001&status=draft"
      );
    });

    it("should include submitted status filter", async () => {
      mockedGet.mockResolvedValue({ data: { items: [], total: 0 } });

      await getEVMSPeriods("prog-001", "submitted");

      expect(mockedGet).toHaveBeenCalledWith(
        "/evms/periods?program_id=prog-001&status=submitted"
      );
    });

    it("should include rejected status filter", async () => {
      mockedGet.mockResolvedValue({ data: { items: [], total: 0 } });

      await getEVMSPeriods("prog-001", "rejected");

      expect(mockedGet).toHaveBeenCalledWith(
        "/evms/periods?program_id=prog-001&status=rejected"
      );
    });

    it("should not include status when undefined", async () => {
      mockedGet.mockResolvedValue({ data: mockListResponse });

      await getEVMSPeriods("prog-001", undefined);

      expect(mockedGet).toHaveBeenCalledWith(
        "/evms/periods?program_id=prog-001"
      );
    });

    it("should not include status when empty string", async () => {
      mockedGet.mockResolvedValue({ data: mockListResponse });

      await getEVMSPeriods("prog-001", "");

      // Empty string is falsy, so status should not be appended
      expect(mockedGet).toHaveBeenCalledWith(
        "/evms/periods?program_id=prog-001"
      );
    });

    it("should handle empty list response", async () => {
      const emptyResponse = { items: [], total: 0 };
      mockedGet.mockResolvedValue({ data: emptyResponse });

      const result = await getEVMSPeriods("prog-999");

      expect(result.items).toHaveLength(0);
      expect(result.total).toBe(0);
    });

    it("should construct URL with the given programId", async () => {
      mockedGet.mockResolvedValue({ data: mockListResponse });

      await getEVMSPeriods("abc-def-123");

      expect(mockedGet).toHaveBeenCalledWith(
        "/evms/periods?program_id=abc-def-123"
      );
    });

    it("should propagate errors", async () => {
      mockedGet.mockRejectedValue(new Error("Network error"));

      await expect(getEVMSPeriods("prog-001")).rejects.toThrow(
        "Network error"
      );
    });
  });

  describe("getEVMSPeriodWithData", () => {
    it("should fetch a single period with its data", async () => {
      mockedGet.mockResolvedValue({ data: mockPeriodWithData });

      const result = await getEVMSPeriodWithData("period-001");

      expect(mockedGet).toHaveBeenCalledWith("/evms/periods/period-001");
      expect(result).toEqual(mockPeriodWithData);
    });

    it("should return period with periodData array", async () => {
      mockedGet.mockResolvedValue({ data: mockPeriodWithData });

      const result = await getEVMSPeriodWithData("period-001");

      expect(result.periodData).toHaveLength(1);
      expect(result.periodData[0].wbsId).toBe("wbs-001");
    });

    it("should handle period with empty periodData", async () => {
      const emptyDataPeriod = { ...mockPeriod, periodData: [] };
      mockedGet.mockResolvedValue({ data: emptyDataPeriod });

      const result = await getEVMSPeriodWithData("period-002");

      expect(mockedGet).toHaveBeenCalledWith("/evms/periods/period-002");
      expect(result.periodData).toHaveLength(0);
    });

    it("should construct URL with the given periodId", async () => {
      mockedGet.mockResolvedValue({ data: mockPeriodWithData });

      await getEVMSPeriodWithData("xyz-789");

      expect(mockedGet).toHaveBeenCalledWith("/evms/periods/xyz-789");
    });

    it("should propagate errors for not found", async () => {
      mockedGet.mockRejectedValue(new Error("Not found"));

      await expect(getEVMSPeriodWithData("bad-id")).rejects.toThrow(
        "Not found"
      );
    });
  });

  describe("getEVMSSummary", () => {
    it("should fetch EVMS summary for a program", async () => {
      mockedGet.mockResolvedValue({ data: mockSummary });

      const result = await getEVMSSummary("prog-001");

      expect(mockedGet).toHaveBeenCalledWith("/evms/summary/prog-001");
      expect(result).toEqual(mockSummary);
    });

    it("should return all summary fields", async () => {
      mockedGet.mockResolvedValue({ data: mockSummary });

      const result = await getEVMSSummary("prog-001");

      expect(result.programId).toBe("prog-001");
      expect(result.programName).toBe("Test Program");
      expect(result.budgetAtCompletion).toBe("1000000.00");
      expect(result.cpi).toBe("0.969");
      expect(result.spi).toBe("0.950");
      expect(result.latestPeriod).toEqual(mockPeriod);
    });

    it("should handle summary with null performance indices", async () => {
      const noDataSummary = {
        ...mockSummary,
        costVariance: null,
        scheduleVariance: null,
        cpi: null,
        spi: null,
        estimateAtCompletion: null,
        estimateToComplete: null,
        varianceAtCompletion: null,
        tcpiEac: null,
        tcpiBac: null,
        latestPeriod: null,
      };
      mockedGet.mockResolvedValue({ data: noDataSummary });

      const result = await getEVMSSummary("prog-002");

      expect(result.cpi).toBeNull();
      expect(result.spi).toBeNull();
      expect(result.latestPeriod).toBeNull();
    });

    it("should construct URL with the given programId", async () => {
      mockedGet.mockResolvedValue({ data: mockSummary });

      await getEVMSSummary("abc-def-123");

      expect(mockedGet).toHaveBeenCalledWith("/evms/summary/abc-def-123");
    });

    it("should propagate errors", async () => {
      mockedGet.mockRejectedValue(new Error("Server error"));

      await expect(getEVMSSummary("prog-001")).rejects.toThrow("Server error");
    });
  });

  describe("createEVMSPeriod", () => {
    it("should post period data with all fields", async () => {
      mockedPost.mockResolvedValue({ data: mockPeriod });

      const createData = {
        programId: "prog-001",
        periodStart: "2026-01-01",
        periodEnd: "2026-01-31",
        periodName: "January 2026",
        notes: "Initial period",
      };

      const result = await createEVMSPeriod(createData);

      expect(mockedPost).toHaveBeenCalledWith("/evms/periods", {
        program_id: "prog-001",
        period_start: "2026-01-01",
        period_end: "2026-01-31",
        period_name: "January 2026",
        notes: "Initial period",
      });
      expect(result).toEqual(mockPeriod);
    });

    it("should transform camelCase to snake_case in payload", async () => {
      mockedPost.mockResolvedValue({ data: mockPeriod });

      await createEVMSPeriod({
        programId: "prog-001",
        periodStart: "2026-03-01",
        periodEnd: "2026-03-31",
        periodName: "March 2026",
      });

      const payload = mockedPost.mock.calls[0][1];
      expect(payload).toHaveProperty("program_id", "prog-001");
      expect(payload).toHaveProperty("period_start", "2026-03-01");
      expect(payload).toHaveProperty("period_end", "2026-03-31");
      expect(payload).toHaveProperty("period_name", "March 2026");
    });

    it("should handle optional notes as undefined", async () => {
      mockedPost.mockResolvedValue({ data: mockPeriod });

      await createEVMSPeriod({
        programId: "prog-001",
        periodStart: "2026-02-01",
        periodEnd: "2026-02-28",
        periodName: "February 2026",
      });

      expect(mockedPost).toHaveBeenCalledWith("/evms/periods", {
        program_id: "prog-001",
        period_start: "2026-02-01",
        period_end: "2026-02-28",
        period_name: "February 2026",
        notes: undefined,
      });
    });

    it("should send null notes when explicitly set to null", async () => {
      mockedPost.mockResolvedValue({ data: mockPeriod });

      await createEVMSPeriod({
        programId: "prog-001",
        periodStart: "2026-04-01",
        periodEnd: "2026-04-30",
        periodName: "April 2026",
        notes: null,
      });

      const payload = mockedPost.mock.calls[0][1] as Record<string, unknown>;
      expect(payload.notes).toBeNull();
    });

    it("should send notes when provided as string", async () => {
      mockedPost.mockResolvedValue({ data: mockPeriod });

      await createEVMSPeriod({
        programId: "prog-001",
        periodStart: "2026-05-01",
        periodEnd: "2026-05-31",
        periodName: "May 2026",
        notes: "Quarterly review period",
      });

      const payload = mockedPost.mock.calls[0][1] as Record<string, unknown>;
      expect(payload.notes).toBe("Quarterly review period");
    });

    it("should propagate errors", async () => {
      mockedPost.mockRejectedValue(new Error("Validation error"));

      await expect(
        createEVMSPeriod({
          programId: "prog-001",
          periodStart: "2026-01-31",
          periodEnd: "2026-01-01",
          periodName: "Invalid",
        })
      ).rejects.toThrow("Validation error");
    });
  });

  describe("addPeriodData", () => {
    it("should post period data to the correct period", async () => {
      mockedPost.mockResolvedValue({ data: mockPeriodData });

      const dataPayload = {
        wbsId: "wbs-001",
        bcws: "50000.00",
        bcwp: "48000.00",
        acwp: "49000.00",
      };

      const result = await addPeriodData("period-001", dataPayload);

      expect(mockedPost).toHaveBeenCalledWith(
        "/evms/periods/period-001/data",
        {
          wbs_id: "wbs-001",
          bcws: "50000.00",
          bcwp: "48000.00",
          acwp: "49000.00",
        }
      );
      expect(result).toEqual(mockPeriodData);
    });

    it("should transform camelCase to snake_case in payload", async () => {
      mockedPost.mockResolvedValue({ data: mockPeriodData });

      await addPeriodData("period-001", {
        wbsId: "wbs-002",
        bcws: "25000.00",
        bcwp: "24000.00",
        acwp: "26000.00",
      });

      const payload = mockedPost.mock.calls[0][1];
      expect(payload).toHaveProperty("wbs_id", "wbs-002");
      expect(payload).toHaveProperty("bcws", "25000.00");
      expect(payload).toHaveProperty("bcwp", "24000.00");
      expect(payload).toHaveProperty("acwp", "26000.00");
      expect(payload).not.toHaveProperty("wbsId");
    });

    it("should construct URL with the given periodId", async () => {
      mockedPost.mockResolvedValue({ data: mockPeriodData });

      await addPeriodData("period-xyz", {
        wbsId: "wbs-001",
        bcws: "10000.00",
        bcwp: "9000.00",
        acwp: "9500.00",
      });

      expect(mockedPost).toHaveBeenCalledWith(
        "/evms/periods/period-xyz/data",
        expect.any(Object)
      );
    });

    it("should handle zero values", async () => {
      mockedPost.mockResolvedValue({ data: mockPeriodData });

      await addPeriodData("period-001", {
        wbsId: "wbs-001",
        bcws: "0.00",
        bcwp: "0.00",
        acwp: "0.00",
      });

      const payload = mockedPost.mock.calls[0][1] as Record<string, unknown>;
      expect(payload.bcws).toBe("0.00");
      expect(payload.bcwp).toBe("0.00");
      expect(payload.acwp).toBe("0.00");
    });

    it("should handle large decimal values", async () => {
      mockedPost.mockResolvedValue({ data: mockPeriodData });

      await addPeriodData("period-001", {
        wbsId: "wbs-001",
        bcws: "9999999.99",
        bcwp: "8888888.88",
        acwp: "7777777.77",
      });

      const payload = mockedPost.mock.calls[0][1] as Record<string, unknown>;
      expect(payload.bcws).toBe("9999999.99");
      expect(payload.bcwp).toBe("8888888.88");
      expect(payload.acwp).toBe("7777777.77");
    });

    it("should propagate errors", async () => {
      mockedPost.mockRejectedValue(new Error("Conflict"));

      await expect(
        addPeriodData("period-001", {
          wbsId: "wbs-001",
          bcws: "50000.00",
          bcwp: "48000.00",
          acwp: "49000.00",
        })
      ).rejects.toThrow("Conflict");
    });

    it("should propagate not found errors for invalid periodId", async () => {
      mockedPost.mockRejectedValue(new Error("Period not found"));

      await expect(
        addPeriodData("bad-period", {
          wbsId: "wbs-001",
          bcws: "1000.00",
          bcwp: "900.00",
          acwp: "950.00",
        })
      ).rejects.toThrow("Period not found");
    });
  });

  describe("deleteEVMSPeriod", () => {
    it("should send delete request with correct id", async () => {
      mockedDelete.mockResolvedValue({ data: undefined });

      await deleteEVMSPeriod("period-001");

      expect(mockedDelete).toHaveBeenCalledWith("/evms/periods/period-001");
    });

    it("should construct URL with the given periodId", async () => {
      mockedDelete.mockResolvedValue({ data: undefined });

      await deleteEVMSPeriod("period-002");

      expect(mockedDelete).toHaveBeenCalledWith("/evms/periods/period-002");
    });

    it("should return void", async () => {
      mockedDelete.mockResolvedValue({ data: undefined });

      const result = await deleteEVMSPeriod("period-001");

      expect(result).toBeUndefined();
    });

    it("should propagate errors", async () => {
      mockedDelete.mockRejectedValue(new Error("Forbidden"));

      await expect(deleteEVMSPeriod("period-001")).rejects.toThrow(
        "Forbidden"
      );
    });

    it("should propagate not found errors", async () => {
      mockedDelete.mockRejectedValue(new Error("Not found"));

      await expect(deleteEVMSPeriod("bad-id")).rejects.toThrow("Not found");
    });
  });
});
