import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/api/client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
  getErrorMessage: vi.fn((error: unknown) => {
    if (error instanceof Error) return error.message;
    return "An unexpected error occurred";
  }),
}));

import { apiClient } from "@/api/client";
import {
  previewCalendarImport,
  importCalendars,
  validateCalendarFile,
  calendarImportApi,
} from "../calendarImportApi";

const mockedPost = vi.mocked(apiClient.post);

const mockPreviewResponse = {
  calendars_found: 3,
  calendar_names: ["Standard", "Night Shift", "24 Hours"],
  resource_mappings: [
    { resource_name: "Engineer A", calendar_name: "Standard" },
    { resource_name: "Engineer B", calendar_name: "Night Shift" },
  ],
  working_days_count: 130,
  warnings: [],
};

const mockImportResponse = {
  calendars_created: 3,
  entries_generated: 390,
  resources_updated: 2,
  warnings: ["Calendar '24 Hours' has no matching resources"],
};

describe("calendarImportApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("previewCalendarImport", () => {
    it("should POST to correct URL with all query params", async () => {
      mockedPost.mockResolvedValue({ data: mockPreviewResponse });
      const file = new File(["<Project></Project>"], "calendars.xml", {
        type: "text/xml",
      });

      await previewCalendarImport("prog-001", file, "2026-01-01", "2026-06-30");

      expect(mockedPost).toHaveBeenCalledWith(
        "/calendars/import/preview?program_id=prog-001&start_date=2026-01-01&end_date=2026-06-30",
        expect.any(FormData),
        { headers: { "Content-Type": "multipart/form-data" } }
      );
    });

    it("should include file in FormData", async () => {
      mockedPost.mockResolvedValue({ data: mockPreviewResponse });
      const file = new File(["<Project></Project>"], "calendars.xml", {
        type: "text/xml",
      });

      await previewCalendarImport("prog-001", file, "2026-01-01", "2026-06-30");

      const formDataArg = mockedPost.mock.calls[0][1] as FormData;
      expect(formDataArg).toBeInstanceOf(FormData);
      expect(formDataArg.get("file")).toBe(file);
    });

    it("should return the preview response data", async () => {
      mockedPost.mockResolvedValue({ data: mockPreviewResponse });
      const file = new File(["content"], "test.xml", { type: "text/xml" });

      const result = await previewCalendarImport(
        "prog-001",
        file,
        "2026-01-01",
        "2026-06-30"
      );

      expect(result).toEqual(mockPreviewResponse);
      expect(result.calendars_found).toBe(3);
      expect(result.calendar_names).toHaveLength(3);
    });

    it("should pass multipart/form-data content type header", async () => {
      mockedPost.mockResolvedValue({ data: mockPreviewResponse });
      const file = new File(["content"], "test.xml", { type: "text/xml" });

      await previewCalendarImport("prog-001", file, "2026-03-01", "2026-09-30");

      const configArg = mockedPost.mock.calls[0][2] as {
        headers: Record<string, string>;
      };
      expect(configArg.headers["Content-Type"]).toBe("multipart/form-data");
    });

    it("should construct URL with different date parameters", async () => {
      mockedPost.mockResolvedValue({ data: mockPreviewResponse });
      const file = new File(["content"], "test.xml", { type: "text/xml" });

      await previewCalendarImport(
        "prog-abc",
        file,
        "2025-07-15",
        "2026-12-31"
      );

      expect(mockedPost).toHaveBeenCalledWith(
        "/calendars/import/preview?program_id=prog-abc&start_date=2025-07-15&end_date=2026-12-31",
        expect.any(FormData),
        expect.any(Object)
      );
    });

    it("should propagate errors from apiClient", async () => {
      const error = new Error("Network timeout");
      mockedPost.mockRejectedValue(error);
      const file = new File(["content"], "test.xml", { type: "text/xml" });

      await expect(
        previewCalendarImport("prog-001", file, "2026-01-01", "2026-06-30")
      ).rejects.toThrow("Network timeout");
    });

    it("should include /preview in the URL path", async () => {
      mockedPost.mockResolvedValue({ data: mockPreviewResponse });
      const file = new File(["content"], "test.xml", { type: "text/xml" });

      await previewCalendarImport("prog-001", file, "2026-01-01", "2026-06-30");

      const urlArg = mockedPost.mock.calls[0][0] as string;
      expect(urlArg).toContain("/calendars/import/preview");
    });
  });

  describe("importCalendars", () => {
    it("should POST to correct URL without /preview", async () => {
      mockedPost.mockResolvedValue({ data: mockImportResponse });
      const file = new File(["<Project></Project>"], "calendars.xml", {
        type: "text/xml",
      });

      await importCalendars("prog-001", file, "2026-01-01", "2026-06-30");

      expect(mockedPost).toHaveBeenCalledWith(
        "/calendars/import?program_id=prog-001&start_date=2026-01-01&end_date=2026-06-30",
        expect.any(FormData),
        { headers: { "Content-Type": "multipart/form-data" } }
      );
    });

    it("should include file in FormData", async () => {
      mockedPost.mockResolvedValue({ data: mockImportResponse });
      const file = new File(["<Project></Project>"], "calendars.xml", {
        type: "text/xml",
      });

      await importCalendars("prog-001", file, "2026-01-01", "2026-06-30");

      const formDataArg = mockedPost.mock.calls[0][1] as FormData;
      expect(formDataArg).toBeInstanceOf(FormData);
      expect(formDataArg.get("file")).toBe(file);
    });

    it("should return the import response data", async () => {
      mockedPost.mockResolvedValue({ data: mockImportResponse });
      const file = new File(["content"], "test.xml", { type: "text/xml" });

      const result = await importCalendars(
        "prog-001",
        file,
        "2026-01-01",
        "2026-06-30"
      );

      expect(result).toEqual(mockImportResponse);
      expect(result.calendars_created).toBe(3);
      expect(result.entries_generated).toBe(390);
    });

    it("should pass multipart/form-data content type header", async () => {
      mockedPost.mockResolvedValue({ data: mockImportResponse });
      const file = new File(["content"], "test.xml", { type: "text/xml" });

      await importCalendars("prog-002", file, "2026-02-01", "2026-08-31");

      const configArg = mockedPost.mock.calls[0][2] as {
        headers: Record<string, string>;
      };
      expect(configArg.headers["Content-Type"]).toBe("multipart/form-data");
    });

    it("should construct URL with different parameters", async () => {
      mockedPost.mockResolvedValue({ data: mockImportResponse });
      const file = new File(["content"], "test.xml", { type: "text/xml" });

      await importCalendars(
        "uuid-9999",
        file,
        "2025-11-01",
        "2026-04-30"
      );

      expect(mockedPost).toHaveBeenCalledWith(
        "/calendars/import?program_id=uuid-9999&start_date=2025-11-01&end_date=2026-04-30",
        expect.any(FormData),
        expect.any(Object)
      );
    });

    it("should propagate errors from apiClient", async () => {
      const error = new Error("Internal server error");
      mockedPost.mockRejectedValue(error);
      const file = new File(["content"], "test.xml", { type: "text/xml" });

      await expect(
        importCalendars("prog-001", file, "2026-01-01", "2026-06-30")
      ).rejects.toThrow("Internal server error");
    });

    it("should not include /preview in the URL path", async () => {
      mockedPost.mockResolvedValue({ data: mockImportResponse });
      const file = new File(["content"], "test.xml", { type: "text/xml" });

      await importCalendars("prog-001", file, "2026-01-01", "2026-06-30");

      const urlArg = mockedPost.mock.calls[0][0] as string;
      expect(urlArg).not.toContain("preview");
    });
  });

  describe("validateCalendarFile", () => {
    it("should return null for a valid .xml file", () => {
      const file = new File(["<Project></Project>"], "calendars.xml", {
        type: "text/xml",
      });

      const result = validateCalendarFile(file);

      expect(result).toBeNull();
    });

    it("should return null for uppercase .XML extension", () => {
      const file = new File(["<Project></Project>"], "CALENDARS.XML", {
        type: "text/xml",
      });

      const result = validateCalendarFile(file);

      expect(result).toBeNull();
    });

    it("should return null for mixed case .Xml extension", () => {
      const file = new File(["<Project></Project>"], "Calendars.Xml", {
        type: "text/xml",
      });

      const result = validateCalendarFile(file);

      expect(result).toBeNull();
    });

    it("should return error for non-.xml file extension", () => {
      const file = new File(["data"], "calendars.csv", {
        type: "text/csv",
      });

      const result = validateCalendarFile(file);

      expect(result).toBe("File must be an MS Project XML file (.xml)");
    });

    it("should return error for .mpp file", () => {
      const file = new File(["data"], "project.mpp", {
        type: "application/octet-stream",
      });

      const result = validateCalendarFile(file);

      expect(result).toBe("File must be an MS Project XML file (.xml)");
    });

    it("should return error for file without extension", () => {
      const file = new File(["data"], "calendars", {
        type: "application/octet-stream",
      });

      const result = validateCalendarFile(file);

      expect(result).toBe("File must be an MS Project XML file (.xml)");
    });

    it("should return error for file exceeding 50MB", () => {
      const largeContent = new ArrayBuffer(50 * 1024 * 1024 + 1);
      const file = new File([largeContent], "large.xml", {
        type: "text/xml",
      });

      const result = validateCalendarFile(file);

      expect(result).toBe("File size exceeds 50MB limit");
    });

    it("should return null for file exactly 50MB", () => {
      const content = new ArrayBuffer(50 * 1024 * 1024);
      const file = new File([content], "exact.xml", {
        type: "text/xml",
      });

      const result = validateCalendarFile(file);

      expect(result).toBeNull();
    });

    it("should return error for empty file (0 bytes)", () => {
      const file = new File([], "empty.xml", {
        type: "text/xml",
      });

      const result = validateCalendarFile(file);

      expect(result).toBe("File is empty");
    });

    it("should validate extension before checking size", () => {
      const file = new File([], "empty.txt", {
        type: "text/plain",
      });

      const result = validateCalendarFile(file);

      expect(result).toBe("File must be an MS Project XML file (.xml)");
    });
  });

  describe("calendarImportApi object", () => {
    it("should expose preview as previewCalendarImport", () => {
      expect(calendarImportApi.preview).toBe(previewCalendarImport);
    });

    it("should expose import as importCalendars", () => {
      expect(calendarImportApi.import).toBe(importCalendars);
    });

    it("should expose validate as validateCalendarFile", () => {
      expect(calendarImportApi.validate).toBe(validateCalendarFile);
    });

    it("should have exactly three methods", () => {
      const keys = Object.keys(calendarImportApi);
      expect(keys).toHaveLength(3);
      expect(keys).toContain("preview");
      expect(keys).toContain("import");
      expect(keys).toContain("validate");
    });
  });
});
