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

import { apiClient, getErrorMessage } from "@/api/client";
import {
  previewMSProjectImport,
  importMSProject,
  validateImportFile,
} from "../importApi";
import { getErrorMessage as reExportedGetErrorMessage } from "../importApi";

const mockedPost = vi.mocked(apiClient.post);

const mockPreviewResponse = {
  task_count: 25,
  project_name: "Test Project",
  project_start: "2026-01-01",
  project_finish: "2026-06-30",
  sample_tasks: [
    { name: "Task A", duration: 5, start: "2026-01-01", finish: "2026-01-07" },
    { name: "Task B", duration: 3, start: "2026-01-08", finish: "2026-01-10" },
  ],
  warnings: [],
};

const mockImportResult = {
  activities_created: 25,
  dependencies_created: 18,
  wbs_elements_created: 8,
  warnings: ["Some task had no duration, defaulted to 1 day"],
};

describe("importApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("previewMSProjectImport", () => {
    it("should POST to correct URL with preview=true query param", async () => {
      mockedPost.mockResolvedValue({ data: mockPreviewResponse });
      const file = new File(["<Project></Project>"], "schedule.xml", {
        type: "text/xml",
      });

      await previewMSProjectImport("prog-001", file);

      expect(mockedPost).toHaveBeenCalledWith(
        "/import/msproject/prog-001?preview=true",
        expect.any(FormData),
        { headers: { "Content-Type": "multipart/form-data" } }
      );
    });

    it("should include file in FormData", async () => {
      mockedPost.mockResolvedValue({ data: mockPreviewResponse });
      const file = new File(["<Project></Project>"], "schedule.xml", {
        type: "text/xml",
      });

      await previewMSProjectImport("prog-001", file);

      const formDataArg = mockedPost.mock.calls[0][1] as FormData;
      expect(formDataArg).toBeInstanceOf(FormData);
      expect(formDataArg.get("file")).toBe(file);
    });

    it("should return the preview response data", async () => {
      mockedPost.mockResolvedValue({ data: mockPreviewResponse });
      const file = new File(["<Project></Project>"], "schedule.xml", {
        type: "text/xml",
      });

      const result = await previewMSProjectImport("prog-001", file);

      expect(result).toEqual(mockPreviewResponse);
      expect(result.task_count).toBe(25);
      expect(result.project_name).toBe("Test Project");
    });

    it("should pass multipart/form-data content type header", async () => {
      mockedPost.mockResolvedValue({ data: mockPreviewResponse });
      const file = new File(["content"], "test.xml", { type: "text/xml" });

      await previewMSProjectImport("prog-abc", file);

      const configArg = mockedPost.mock.calls[0][2] as {
        headers: Record<string, string>;
      };
      expect(configArg.headers["Content-Type"]).toBe("multipart/form-data");
    });

    it("should use the provided programId in the URL", async () => {
      mockedPost.mockResolvedValue({ data: mockPreviewResponse });
      const file = new File(["content"], "data.xml", { type: "text/xml" });

      await previewMSProjectImport("uuid-1234-5678", file);

      expect(mockedPost).toHaveBeenCalledWith(
        "/import/msproject/uuid-1234-5678?preview=true",
        expect.any(FormData),
        expect.any(Object)
      );
    });

    it("should propagate errors from apiClient", async () => {
      const error = new Error("Network error");
      mockedPost.mockRejectedValue(error);
      const file = new File(["content"], "test.xml", { type: "text/xml" });

      await expect(
        previewMSProjectImport("prog-001", file)
      ).rejects.toThrow("Network error");
    });
  });

  describe("importMSProject", () => {
    it("should POST to correct URL without preview param", async () => {
      mockedPost.mockResolvedValue({ data: mockImportResult });
      const file = new File(["<Project></Project>"], "schedule.xml", {
        type: "text/xml",
      });

      await importMSProject("prog-001", file);

      expect(mockedPost).toHaveBeenCalledWith(
        "/import/msproject/prog-001",
        expect.any(FormData),
        { headers: { "Content-Type": "multipart/form-data" } }
      );
    });

    it("should include file in FormData", async () => {
      mockedPost.mockResolvedValue({ data: mockImportResult });
      const file = new File(["<Project></Project>"], "schedule.xml", {
        type: "text/xml",
      });

      await importMSProject("prog-001", file);

      const formDataArg = mockedPost.mock.calls[0][1] as FormData;
      expect(formDataArg).toBeInstanceOf(FormData);
      expect(formDataArg.get("file")).toBe(file);
    });

    it("should return the import result data", async () => {
      mockedPost.mockResolvedValue({ data: mockImportResult });
      const file = new File(["content"], "test.xml", { type: "text/xml" });

      const result = await importMSProject("prog-001", file);

      expect(result).toEqual(mockImportResult);
      expect(result.activities_created).toBe(25);
      expect(result.dependencies_created).toBe(18);
    });

    it("should pass multipart/form-data content type header", async () => {
      mockedPost.mockResolvedValue({ data: mockImportResult });
      const file = new File(["content"], "test.xml", { type: "text/xml" });

      await importMSProject("prog-002", file);

      const configArg = mockedPost.mock.calls[0][2] as {
        headers: Record<string, string>;
      };
      expect(configArg.headers["Content-Type"]).toBe("multipart/form-data");
    });

    it("should use the provided programId in the URL", async () => {
      mockedPost.mockResolvedValue({ data: mockImportResult });
      const file = new File(["content"], "data.xml", { type: "text/xml" });

      await importMSProject("uuid-abcd-efgh", file);

      expect(mockedPost).toHaveBeenCalledWith(
        "/import/msproject/uuid-abcd-efgh",
        expect.any(FormData),
        expect.any(Object)
      );
    });

    it("should propagate errors from apiClient", async () => {
      const error = new Error("Server error 500");
      mockedPost.mockRejectedValue(error);
      const file = new File(["content"], "test.xml", { type: "text/xml" });

      await expect(importMSProject("prog-001", file)).rejects.toThrow(
        "Server error 500"
      );
    });

    it("should not include preview query param in URL", async () => {
      mockedPost.mockResolvedValue({ data: mockImportResult });
      const file = new File(["content"], "test.xml", { type: "text/xml" });

      await importMSProject("prog-001", file);

      const urlArg = mockedPost.mock.calls[0][0] as string;
      expect(urlArg).not.toContain("preview");
    });
  });

  describe("validateImportFile", () => {
    it("should return null for a valid .xml file", () => {
      const file = new File(["<Project></Project>"], "schedule.xml", {
        type: "text/xml",
      });

      const result = validateImportFile(file);

      expect(result).toBeNull();
    });

    it("should return null for uppercase .XML extension", () => {
      const file = new File(["<Project></Project>"], "SCHEDULE.XML", {
        type: "text/xml",
      });

      const result = validateImportFile(file);

      expect(result).toBeNull();
    });

    it("should return null for mixed case .Xml extension", () => {
      const file = new File(["<Project></Project>"], "Schedule.Xml", {
        type: "text/xml",
      });

      const result = validateImportFile(file);

      expect(result).toBeNull();
    });

    it("should return error for non-.xml file extension", () => {
      const file = new File(["data"], "schedule.mpp", {
        type: "application/octet-stream",
      });

      const result = validateImportFile(file);

      expect(result).toBe("File must be an MS Project XML file (.xml)");
    });

    it("should return error for .json file", () => {
      const file = new File(["{}"], "data.json", {
        type: "application/json",
      });

      const result = validateImportFile(file);

      expect(result).toBe("File must be an MS Project XML file (.xml)");
    });

    it("should return error for file without extension", () => {
      const file = new File(["data"], "schedule", {
        type: "application/octet-stream",
      });

      const result = validateImportFile(file);

      expect(result).toBe("File must be an MS Project XML file (.xml)");
    });

    it("should return error for file exceeding 50MB", () => {
      const largeContent = new ArrayBuffer(50 * 1024 * 1024 + 1);
      const file = new File([largeContent], "large.xml", {
        type: "text/xml",
      });

      const result = validateImportFile(file);

      expect(result).toBe("File size exceeds 50MB limit");
    });

    it("should return null for file exactly 50MB", () => {
      const content = new ArrayBuffer(50 * 1024 * 1024);
      const file = new File([content], "exact.xml", {
        type: "text/xml",
      });

      const result = validateImportFile(file);

      expect(result).toBeNull();
    });

    it("should return error for empty file (0 bytes)", () => {
      const file = new File([], "empty.xml", {
        type: "text/xml",
      });

      const result = validateImportFile(file);

      expect(result).toBe("File is empty");
    });

    it("should validate extension before checking size", () => {
      // A file with wrong extension and also empty - extension error should come first
      const file = new File([], "empty.txt", {
        type: "text/plain",
      });

      const result = validateImportFile(file);

      expect(result).toBe("File must be an MS Project XML file (.xml)");
    });
  });

  describe("getErrorMessage re-export", () => {
    it("should re-export getErrorMessage from client", () => {
      expect(reExportedGetErrorMessage).toBeDefined();
      expect(typeof reExportedGetErrorMessage).toBe("function");
    });

    it("should be the same function as the one from client", () => {
      expect(reExportedGetErrorMessage).toBe(getErrorMessage);
    });

    it("should return error message for Error instances", () => {
      const error = new Error("Test error message");
      const result = reExportedGetErrorMessage(error);
      expect(result).toBe("Test error message");
    });

    it("should return default message for non-Error values", () => {
      const result = reExportedGetErrorMessage("string error");
      expect(result).toBe("An unexpected error occurred");
    });
  });
});
