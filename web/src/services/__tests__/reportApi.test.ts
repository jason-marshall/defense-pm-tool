import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/api/client", () => ({
  apiClient: {
    get: vi.fn(),
  },
}));

import { apiClient } from "@/api/client";
import {
  getCPRFormat1,
  getCPRFormat3,
  getCPRFormat5,
  downloadReportPDF,
  getReportAuditTrail,
  reportApi,
} from "../reportApi";

const mockedGet = vi.mocked(apiClient.get);

const mockFormat1 = { program_id: "prog-1", format: "format1", data: {} };
const mockFormat3 = { program_id: "prog-1", format: "format3", data: {} };
const mockFormat5 = { program_id: "prog-1", format: "format5", data: {} };
const mockAuditTrail = [
  { id: "audit-1", action: "generated", created_at: "2026-01-15T10:00:00Z" },
];

describe("reportApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("getCPRFormat1", () => {
    it("should fetch format 1 report without periodId", async () => {
      mockedGet.mockResolvedValue({ data: mockFormat1 });

      const result = await getCPRFormat1("prog-1");

      expect(mockedGet).toHaveBeenCalledWith("/reports/cpr/format1/prog-1");
      expect(result).toEqual(mockFormat1);
    });

    it("should fetch format 1 report with periodId", async () => {
      mockedGet.mockResolvedValue({ data: mockFormat1 });

      const result = await getCPRFormat1("prog-1", "period-1");

      expect(mockedGet).toHaveBeenCalledWith(
        "/reports/cpr/format1/prog-1?period_id=period-1"
      );
      expect(result).toEqual(mockFormat1);
    });

    it("should propagate errors", async () => {
      mockedGet.mockRejectedValue(new Error("Server error"));

      await expect(getCPRFormat1("prog-1")).rejects.toThrow("Server error");
    });
  });

  describe("getCPRFormat3", () => {
    it("should fetch format 3 report", async () => {
      mockedGet.mockResolvedValue({ data: mockFormat3 });

      const result = await getCPRFormat3("prog-1");

      expect(mockedGet).toHaveBeenCalledWith("/reports/cpr/format3/prog-1");
      expect(result).toEqual(mockFormat3);
    });

    it("should propagate errors", async () => {
      mockedGet.mockRejectedValue(new Error("Not found"));

      await expect(getCPRFormat3("bad-id")).rejects.toThrow("Not found");
    });
  });

  describe("getCPRFormat5", () => {
    it("should fetch format 5 report", async () => {
      mockedGet.mockResolvedValue({ data: mockFormat5 });

      const result = await getCPRFormat5("prog-1");

      expect(mockedGet).toHaveBeenCalledWith("/reports/cpr/format5/prog-1");
      expect(result).toEqual(mockFormat5);
    });

    it("should propagate errors", async () => {
      mockedGet.mockRejectedValue(new Error("Server error"));

      await expect(getCPRFormat5("prog-1")).rejects.toThrow("Server error");
    });
  });

  describe("downloadReportPDF", () => {
    it("should fetch PDF blob", async () => {
      const mockBlob = new Blob(["pdf content"], { type: "application/pdf" });
      mockedGet.mockResolvedValue({ data: mockBlob });

      const result = await downloadReportPDF("prog-1", "format1");

      expect(mockedGet).toHaveBeenCalledWith(
        "/reports/cpr/format1/prog-1/pdf",
        { responseType: "blob" }
      );
      expect(result).toBe(mockBlob);
    });

    it("should propagate errors", async () => {
      mockedGet.mockRejectedValue(new Error("Generation failed"));

      await expect(downloadReportPDF("prog-1", "format1")).rejects.toThrow(
        "Generation failed"
      );
    });
  });

  describe("getReportAuditTrail", () => {
    it("should fetch audit trail", async () => {
      mockedGet.mockResolvedValue({ data: mockAuditTrail });

      const result = await getReportAuditTrail("prog-1");

      expect(mockedGet).toHaveBeenCalledWith("/reports/audit/prog-1");
      expect(result).toEqual(mockAuditTrail);
    });

    it("should propagate errors", async () => {
      mockedGet.mockRejectedValue(new Error("Forbidden"));

      await expect(getReportAuditTrail("prog-1")).rejects.toThrow("Forbidden");
    });
  });

  describe("reportApi object", () => {
    it("should export format1 as getCPRFormat1", () => {
      expect(reportApi.format1).toBe(getCPRFormat1);
    });

    it("should export format3 as getCPRFormat3", () => {
      expect(reportApi.format3).toBe(getCPRFormat3);
    });

    it("should export format5 as getCPRFormat5", () => {
      expect(reportApi.format5).toBe(getCPRFormat5);
    });

    it("should export downloadPDF as downloadReportPDF", () => {
      expect(reportApi.downloadPDF).toBe(downloadReportPDF);
    });

    it("should export auditTrail as getReportAuditTrail", () => {
      expect(reportApi.auditTrail).toBe(getReportAuditTrail);
    });
  });
});
