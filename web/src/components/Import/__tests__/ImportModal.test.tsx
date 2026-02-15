/**
 * Unit tests for ImportModal component.
 * Tests modal rendering, file validation, preview workflow, and error handling.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { ImportModal } from "../ImportModal";
import type {
  ImportPreviewResponse,
  ImportResultResponse,
} from "@/types/import";

vi.mock("@/services/importApi", () => ({
  previewMSProjectImport: vi.fn(),
  importMSProject: vi.fn(),
  validateImportFile: vi.fn(),
  getErrorMessage: vi.fn(
    (e: unknown) => (e instanceof Error ? e.message : "Unknown error")
  ),
}));

import {
  previewMSProjectImport,
  importMSProject,
  validateImportFile,
} from "@/services/importApi";

const mockValidateImportFile = vi.mocked(validateImportFile);
const mockPreviewMSProjectImport = vi.mocked(previewMSProjectImport);
const mockImportMSProject = vi.mocked(importMSProject);

function createTestFile(name = "project.xml", size = 1024): File {
  const content = new ArrayBuffer(size);
  return new File([content], name, { type: "application/xml" });
}

const mockPreviewResponse: ImportPreviewResponse = {
  preview: true,
  projectName: "Test Project",
  startDate: "2026-01-01",
  finishDate: "2026-06-30",
  taskCount: 15,
  tasks: [
    {
      name: "Design Phase",
      wbs: "1.1",
      durationHours: 40,
      isMilestone: false,
      predecessors: 0,
    },
    {
      name: "Kickoff Milestone",
      wbs: "1.2",
      durationHours: 0,
      isMilestone: true,
      predecessors: 1,
    },
  ],
  warnings: ["Some tasks have no WBS code"],
};

const mockImportResult: ImportResultResponse = {
  success: true,
  programId: "prog-1",
  tasksImported: 15,
  dependenciesImported: 12,
  wbsElementsCreated: 8,
  warnings: [],
  errors: [],
};

describe("ImportModal", () => {
  const defaultProps = {
    programId: "prog-1",
    isOpen: true,
    onClose: vi.fn(),
    onImportComplete: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ──────────────────────────────────────────────
  // Existing tests (preserved)
  // ──────────────────────────────────────────────

  it("returns null when isOpen is false", () => {
    const { container } = render(
      <ImportModal {...defaultProps} isOpen={false} />
    );
    expect(container.innerHTML).toBe("");
  });

  it("renders modal when isOpen is true", () => {
    render(<ImportModal {...defaultProps} />);
    expect(screen.getByText("Import MS Project File")).toBeInTheDocument();
  });

  it("shows 'Import MS Project File' header", () => {
    render(<ImportModal {...defaultProps} />);
    const header = screen.getByText("Import MS Project File");
    expect(header.tagName).toBe("H2");
  });

  it("shows programName when provided", () => {
    render(<ImportModal {...defaultProps} programName="Alpha Program" />);
    expect(screen.getByText("Alpha Program")).toBeInTheDocument();
    expect(screen.getByText(/Importing into:/)).toBeInTheDocument();
  });

  it("shows dropzone in idle state", () => {
    render(<ImportModal {...defaultProps} />);
    expect(
      screen.getByText("Drag & Drop MS Project XML")
    ).toBeInTheDocument();
    expect(screen.getByText("or click to browse")).toBeInTheDocument();
  });

  it("shows Cancel button in idle state", () => {
    render(<ImportModal {...defaultProps} />);
    expect(screen.getByText("Cancel")).toBeInTheDocument();
  });

  it("shows error for invalid file on drop", async () => {
    mockValidateImportFile.mockReturnValue(
      "File must be an MS Project XML file (.xml)"
    );

    render(<ImportModal {...defaultProps} />);

    const dropzone = screen
      .getByText("Drag & Drop MS Project XML")
      .closest(".import-dropzone")!;

    const badFile = createTestFile("data.txt");
    const dataTransfer = { files: [badFile] };

    fireEvent.drop(dropzone, { dataTransfer });

    await waitFor(() => {
      expect(
        screen.getByText("File must be an MS Project XML file (.xml)")
      ).toBeInTheDocument();
    });
  });

  it("calls previewMSProjectImport on valid file select", async () => {
    mockValidateImportFile.mockReturnValue(null);
    mockPreviewMSProjectImport.mockResolvedValue(mockPreviewResponse);

    render(<ImportModal {...defaultProps} />);

    const dropzone = screen
      .getByText("Drag & Drop MS Project XML")
      .closest(".import-dropzone")!;

    const validFile = createTestFile("project.xml");
    const dataTransfer = { files: [validFile] };

    fireEvent.drop(dropzone, { dataTransfer });

    await waitFor(() => {
      expect(mockPreviewMSProjectImport).toHaveBeenCalledWith(
        "prog-1",
        expect.any(File)
      );
    });
  });

  it("shows preview data when preview succeeds", async () => {
    mockValidateImportFile.mockReturnValue(null);
    mockPreviewMSProjectImport.mockResolvedValue(mockPreviewResponse);

    render(<ImportModal {...defaultProps} />);

    const dropzone = screen
      .getByText("Drag & Drop MS Project XML")
      .closest(".import-dropzone")!;

    const validFile = createTestFile("project.xml");
    fireEvent.drop(dropzone, { dataTransfer: { files: [validFile] } });

    await waitFor(() => {
      expect(screen.getByText("Preview Import")).toBeInTheDocument();
    });

    expect(screen.getByText("15 tasks found")).toBeInTheDocument();
    expect(screen.getByText("Test Project")).toBeInTheDocument();
    expect(screen.getByText("Design Phase")).toBeInTheDocument();
    expect(screen.getByText("Some tasks have no WBS code")).toBeInTheDocument();
  });

  it("shows error state when preview fails", async () => {
    mockValidateImportFile.mockReturnValue(null);
    mockPreviewMSProjectImport.mockRejectedValue(
      new Error("Network error")
    );

    render(<ImportModal {...defaultProps} />);

    const dropzone = screen
      .getByText("Drag & Drop MS Project XML")
      .closest(".import-dropzone")!;

    const validFile = createTestFile("project.xml");
    fireEvent.drop(dropzone, { dataTransfer: { files: [validFile] } });

    await waitFor(() => {
      expect(screen.getByText("Import Failed")).toBeInTheDocument();
    });

    expect(screen.getByText("Network error")).toBeInTheDocument();
  });

  it("has 'Try Again' button in error state", async () => {
    mockValidateImportFile.mockReturnValue(null);
    mockPreviewMSProjectImport.mockRejectedValue(
      new Error("Server error")
    );

    render(<ImportModal {...defaultProps} />);

    const dropzone = screen
      .getByText("Drag & Drop MS Project XML")
      .closest(".import-dropzone")!;

    const validFile = createTestFile("project.xml");
    fireEvent.drop(dropzone, { dataTransfer: { files: [validFile] } });

    await waitFor(() => {
      expect(screen.getByText("Try Again")).toBeInTheDocument();
    });
  });

  it("calls onClose when Cancel is clicked", () => {
    const onClose = vi.fn();
    render(<ImportModal {...defaultProps} onClose={onClose} />);

    fireEvent.click(screen.getByText("Cancel"));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  // ──────────────────────────────────────────────
  // New tests: File selection via input change
  // ──────────────────────────────────────────────

  describe("file input change handler", () => {
    it("selects a file via the hidden file input", async () => {
      mockValidateImportFile.mockReturnValue(null);
      mockPreviewMSProjectImport.mockResolvedValue(mockPreviewResponse);

      render(<ImportModal {...defaultProps} />);

      const fileInput = document.querySelector(
        'input[type="file"]'
      ) as HTMLInputElement;
      expect(fileInput).toBeTruthy();

      const validFile = createTestFile("schedule.xml");
      fireEvent.change(fileInput, { target: { files: [validFile] } });

      await waitFor(() => {
        expect(mockPreviewMSProjectImport).toHaveBeenCalledWith(
          "prog-1",
          expect.any(File)
        );
      });
    });

    it("does nothing when file input change has no files", () => {
      render(<ImportModal {...defaultProps} />);

      const fileInput = document.querySelector(
        'input[type="file"]'
      ) as HTMLInputElement;

      fireEvent.change(fileInput, { target: { files: [] } });

      expect(mockValidateImportFile).not.toHaveBeenCalled();
      expect(mockPreviewMSProjectImport).not.toHaveBeenCalled();
    });
  });

  // ──────────────────────────────────────────────
  // New tests: Browse click
  // ──────────────────────────────────────────────

  describe("browse click", () => {
    it("triggers the hidden file input click when dropzone is clicked", () => {
      render(<ImportModal {...defaultProps} />);

      const fileInput = document.querySelector(
        'input[type="file"]'
      ) as HTMLInputElement;
      const clickSpy = vi.spyOn(fileInput, "click");

      const dropzone = screen
        .getByText("Drag & Drop MS Project XML")
        .closest(".import-dropzone")!;

      fireEvent.click(dropzone);

      expect(clickSpy).toHaveBeenCalled();
    });
  });

  // ──────────────────────────────────────────────
  // New tests: Drag and drop behavior
  // ──────────────────────────────────────────────

  describe("drag and drop events", () => {
    it("adds dragover class on dragOver", () => {
      render(<ImportModal {...defaultProps} />);

      const dropzone = screen
        .getByText("Drag & Drop MS Project XML")
        .closest(".import-dropzone")!;

      fireEvent.dragOver(dropzone);

      expect(dropzone.className).toContain("dragover");
    });

    it("removes dragover class on dragLeave", () => {
      render(<ImportModal {...defaultProps} />);

      const dropzone = screen
        .getByText("Drag & Drop MS Project XML")
        .closest(".import-dropzone")!;

      fireEvent.dragOver(dropzone);
      expect(dropzone.className).toContain("dragover");

      fireEvent.dragLeave(dropzone);
      expect(dropzone.className).not.toContain("dragover");
    });

    it("does not call handleFileSelect if no files are dropped", () => {
      render(<ImportModal {...defaultProps} />);

      const dropzone = screen
        .getByText("Drag & Drop MS Project XML")
        .closest(".import-dropzone")!;

      fireEvent.drop(dropzone, { dataTransfer: { files: [] } });

      expect(mockValidateImportFile).not.toHaveBeenCalled();
    });
  });

  // ──────────────────────────────────────────────
  // New tests: Import success flow
  // ──────────────────────────────────────────────

  describe("import success flow", () => {
    async function navigateToPreview() {
      mockValidateImportFile.mockReturnValue(null);
      mockPreviewMSProjectImport.mockResolvedValue(mockPreviewResponse);

      render(<ImportModal {...defaultProps} />);

      const dropzone = screen
        .getByText("Drag & Drop MS Project XML")
        .closest(".import-dropzone")!;

      const validFile = createTestFile("project.xml");
      fireEvent.drop(dropzone, { dataTransfer: { files: [validFile] } });

      await waitFor(() => {
        expect(screen.getByText("Preview Import")).toBeInTheDocument();
      });
    }

    it("shows success state after successful import", async () => {
      mockImportMSProject.mockResolvedValue(mockImportResult);
      await navigateToPreview();

      const importBtn = screen.getByText("Import 15 Tasks");
      fireEvent.click(importBtn);

      await waitFor(() => {
        expect(screen.getByText("Import Complete!")).toBeInTheDocument();
      });

      expect(screen.getByText("15")).toBeInTheDocument();
      expect(screen.getByText("Activities Created")).toBeInTheDocument();
      expect(screen.getByText("12")).toBeInTheDocument();
      expect(screen.getByText("Dependencies Linked")).toBeInTheDocument();
      expect(screen.getByText("8")).toBeInTheDocument();
      expect(screen.getByText("WBS Elements Added")).toBeInTheDocument();
    });

    it("calls onImportComplete callback on success", async () => {
      mockImportMSProject.mockResolvedValue(mockImportResult);
      await navigateToPreview();

      fireEvent.click(screen.getByText("Import 15 Tasks"));

      await waitFor(() => {
        expect(defaultProps.onImportComplete).toHaveBeenCalledWith(
          mockImportResult
        );
      });
    });

    it("shows Done button in success state", async () => {
      mockImportMSProject.mockResolvedValue(mockImportResult);
      await navigateToPreview();

      fireEvent.click(screen.getByText("Import 15 Tasks"));

      await waitFor(() => {
        expect(screen.getByText("Done")).toBeInTheDocument();
      });
    });

    it("calls onClose when Done is clicked after success", async () => {
      const onClose = vi.fn();
      mockValidateImportFile.mockReturnValue(null);
      mockPreviewMSProjectImport.mockResolvedValue(mockPreviewResponse);
      mockImportMSProject.mockResolvedValue(mockImportResult);

      render(
        <ImportModal
          {...defaultProps}
          onClose={onClose}
        />
      );

      const dropzone = screen
        .getByText("Drag & Drop MS Project XML")
        .closest(".import-dropzone")!;
      fireEvent.drop(dropzone, {
        dataTransfer: { files: [createTestFile()] },
      });

      await waitFor(() => {
        expect(screen.getByText("Import 15 Tasks")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Import 15 Tasks"));

      await waitFor(() => {
        expect(screen.getByText("Done")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Done"));
      expect(onClose).toHaveBeenCalled();
    });

    it("shows success warnings when present", async () => {
      const resultWithWarnings: ImportResultResponse = {
        ...mockImportResult,
        warnings: ["Task A has no predecessor", "Task B has circular ref"],
      };
      mockImportMSProject.mockResolvedValue(resultWithWarnings);
      await navigateToPreview();

      fireEvent.click(screen.getByText("Import 15 Tasks"));

      await waitFor(() => {
        expect(screen.getByText("Import Complete!")).toBeInTheDocument();
      });

      expect(
        screen.getByText("Task A has no predecessor")
      ).toBeInTheDocument();
      expect(
        screen.getByText("Task B has circular ref")
      ).toBeInTheDocument();
    });

    it("truncates warnings list when more than 5", async () => {
      const resultWithManyWarnings: ImportResultResponse = {
        ...mockImportResult,
        warnings: [
          "Warning 1",
          "Warning 2",
          "Warning 3",
          "Warning 4",
          "Warning 5",
          "Warning 6",
          "Warning 7",
        ],
      };
      mockImportMSProject.mockResolvedValue(resultWithManyWarnings);
      await navigateToPreview();

      fireEvent.click(screen.getByText("Import 15 Tasks"));

      await waitFor(() => {
        expect(screen.getByText("Import Complete!")).toBeInTheDocument();
      });

      expect(screen.getByText("Warning 1")).toBeInTheDocument();
      expect(screen.getByText("Warning 5")).toBeInTheDocument();
      expect(screen.getByText("...and 2 more warnings")).toBeInTheDocument();
      expect(screen.queryByText("Warning 6")).not.toBeInTheDocument();
    });
  });

  // ──────────────────────────────────────────────
  // New tests: Import error flow
  // ──────────────────────────────────────────────

  describe("import error flow", () => {
    it("shows error state when import fails", async () => {
      mockValidateImportFile.mockReturnValue(null);
      mockPreviewMSProjectImport.mockResolvedValue(mockPreviewResponse);
      mockImportMSProject.mockRejectedValue(
        new Error("Import failed: database timeout")
      );

      render(<ImportModal {...defaultProps} />);

      const dropzone = screen
        .getByText("Drag & Drop MS Project XML")
        .closest(".import-dropzone")!;
      fireEvent.drop(dropzone, {
        dataTransfer: { files: [createTestFile()] },
      });

      await waitFor(() => {
        expect(screen.getByText("Import 15 Tasks")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Import 15 Tasks"));

      await waitFor(() => {
        expect(screen.getByText("Import Failed")).toBeInTheDocument();
      });

      expect(
        screen.getByText("Import failed: database timeout")
      ).toBeInTheDocument();
    });

    it("shows Cancel and Try Again buttons in import error state", async () => {
      mockValidateImportFile.mockReturnValue(null);
      mockPreviewMSProjectImport.mockResolvedValue(mockPreviewResponse);
      mockImportMSProject.mockRejectedValue(new Error("Timeout"));

      render(<ImportModal {...defaultProps} />);

      const dropzone = screen
        .getByText("Drag & Drop MS Project XML")
        .closest(".import-dropzone")!;
      fireEvent.drop(dropzone, {
        dataTransfer: { files: [createTestFile()] },
      });

      await waitFor(() => {
        expect(screen.getByText("Import 15 Tasks")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Import 15 Tasks"));

      await waitFor(() => {
        expect(screen.getByText("Try Again")).toBeInTheDocument();
        expect(screen.getByText("Cancel")).toBeInTheDocument();
      });
    });
  });

  // ──────────────────────────────────────────────
  // New tests: Cancel / close behavior
  // ──────────────────────────────────────────────

  describe("cancel and close behavior", () => {
    it("closes modal when overlay is clicked", () => {
      const onClose = vi.fn();
      render(<ImportModal {...defaultProps} onClose={onClose} />);

      const overlay = screen.getByRole("dialog");
      fireEvent.click(overlay);

      expect(onClose).toHaveBeenCalledTimes(1);
    });

    it("does not close modal when inner content is clicked", () => {
      const onClose = vi.fn();
      render(<ImportModal {...defaultProps} onClose={onClose} />);

      const header = screen.getByText("Import MS Project File");
      fireEvent.click(header);

      expect(onClose).not.toHaveBeenCalled();
    });

    it("closes modal on Escape key", () => {
      const onClose = vi.fn();
      render(<ImportModal {...defaultProps} onClose={onClose} />);

      const overlay = screen.getByRole("dialog");
      fireEvent.keyDown(overlay, { key: "Escape" });

      expect(onClose).toHaveBeenCalledTimes(1);
    });

    it("does not close modal on non-Escape key", () => {
      const onClose = vi.fn();
      render(<ImportModal {...defaultProps} onClose={onClose} />);

      const overlay = screen.getByRole("dialog");
      fireEvent.keyDown(overlay, { key: "Enter" });

      expect(onClose).not.toHaveBeenCalled();
    });

    it("closes modal when X button is clicked", () => {
      const onClose = vi.fn();
      render(<ImportModal {...defaultProps} onClose={onClose} />);

      const closeBtn = screen.getByLabelText("Close");
      fireEvent.click(closeBtn);

      expect(onClose).toHaveBeenCalledTimes(1);
    });
  });

  // ──────────────────────────────────────────────
  // New tests: Try Again resets state
  // ──────────────────────────────────────────────

  describe("Try Again button", () => {
    it("resets to idle state when Try Again is clicked", async () => {
      mockValidateImportFile.mockReturnValue(null);
      mockPreviewMSProjectImport.mockRejectedValue(
        new Error("Server error")
      );

      render(<ImportModal {...defaultProps} />);

      const dropzone = screen
        .getByText("Drag & Drop MS Project XML")
        .closest(".import-dropzone")!;
      fireEvent.drop(dropzone, {
        dataTransfer: { files: [createTestFile()] },
      });

      await waitFor(() => {
        expect(screen.getByText("Try Again")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Try Again"));

      expect(
        screen.getByText("Drag & Drop MS Project XML")
      ).toBeInTheDocument();
      expect(screen.queryByText("Import Failed")).not.toBeInTheDocument();
    });
  });

  // ──────────────────────────────────────────────
  // New tests: Choose Different File in preview
  // ──────────────────────────────────────────────

  describe("Choose Different File", () => {
    it("returns to idle when Choose Different File is clicked in preview", async () => {
      mockValidateImportFile.mockReturnValue(null);
      mockPreviewMSProjectImport.mockResolvedValue(mockPreviewResponse);

      render(<ImportModal {...defaultProps} />);

      const dropzone = screen
        .getByText("Drag & Drop MS Project XML")
        .closest(".import-dropzone")!;
      fireEvent.drop(dropzone, {
        dataTransfer: { files: [createTestFile()] },
      });

      await waitFor(() => {
        expect(screen.getByText("Preview Import")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Choose Different File"));

      expect(
        screen.getByText("Drag & Drop MS Project XML")
      ).toBeInTheDocument();
      expect(screen.queryByText("Preview Import")).not.toBeInTheDocument();
    });
  });

  // ──────────────────────────────────────────────
  // New tests: Remove file button
  // ──────────────────────────────────────────────

  describe("remove file", () => {
    it("removes selected file and resets to idle when Remove button is clicked in error state", async () => {
      mockValidateImportFile
        .mockReturnValueOnce(null)
        .mockReturnValueOnce(null);
      mockPreviewMSProjectImport.mockRejectedValue(
        new Error("Parse error")
      );

      render(<ImportModal {...defaultProps} />);

      const dropzone = screen
        .getByText("Drag & Drop MS Project XML")
        .closest(".import-dropzone")!;
      fireEvent.drop(dropzone, {
        dataTransfer: { files: [createTestFile()] },
      });

      await waitFor(() => {
        expect(screen.getByText("Import Failed")).toBeInTheDocument();
      });

      // Click Try Again to go back to idle with dropzone
      fireEvent.click(screen.getByText("Try Again"));

      expect(
        screen.getByText("Drag & Drop MS Project XML")
      ).toBeInTheDocument();
    });
  });

  // ──────────────────────────────────────────────
  // New tests: Uploading state display
  // ──────────────────────────────────────────────

  describe("uploading state", () => {
    it("shows analyzing text during file upload", async () => {
      mockValidateImportFile.mockReturnValue(null);
      // Never resolve to keep in uploading state
      mockPreviewMSProjectImport.mockReturnValue(new Promise(() => {}));

      render(<ImportModal {...defaultProps} />);

      const dropzone = screen
        .getByText("Drag & Drop MS Project XML")
        .closest(".import-dropzone")!;
      fireEvent.drop(dropzone, {
        dataTransfer: { files: [createTestFile()] },
      });

      await waitFor(() => {
        expect(screen.getByText("Analyzing file...")).toBeInTheDocument();
      });

      expect(
        screen.getByText("Parsing MS Project XML structure")
      ).toBeInTheDocument();
      expect(screen.getByText("Analyzing...")).toBeInTheDocument();
    });

    it("shows disabled Analyzing button during upload", async () => {
      mockValidateImportFile.mockReturnValue(null);
      mockPreviewMSProjectImport.mockReturnValue(new Promise(() => {}));

      render(<ImportModal {...defaultProps} />);

      const dropzone = screen
        .getByText("Drag & Drop MS Project XML")
        .closest(".import-dropzone")!;
      fireEvent.drop(dropzone, {
        dataTransfer: { files: [createTestFile()] },
      });

      await waitFor(() => {
        const analyzingBtn = screen.getByText("Analyzing...");
        expect(analyzingBtn.closest("button")).toBeDisabled();
      });
    });
  });

  // ──────────────────────────────────────────────
  // New tests: Importing state display
  // ──────────────────────────────────────────────

  describe("importing state", () => {
    it("shows importing progress while import is in progress", async () => {
      mockValidateImportFile.mockReturnValue(null);
      mockPreviewMSProjectImport.mockResolvedValue(mockPreviewResponse);
      // Never resolve to keep in importing state
      mockImportMSProject.mockReturnValue(new Promise(() => {}));

      render(<ImportModal {...defaultProps} />);

      const dropzone = screen
        .getByText("Drag & Drop MS Project XML")
        .closest(".import-dropzone")!;
      fireEvent.drop(dropzone, {
        dataTransfer: { files: [createTestFile()] },
      });

      await waitFor(() => {
        expect(screen.getByText("Import 15 Tasks")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Import 15 Tasks"));

      await waitFor(() => {
        expect(screen.getByText("Importing data...")).toBeInTheDocument();
      });

      expect(
        screen.getByText(
          "Creating activities, dependencies, and WBS elements"
        )
      ).toBeInTheDocument();
      expect(screen.getByText("Importing...")).toBeInTheDocument();
    });

    it("shows disabled Importing button during import", async () => {
      mockValidateImportFile.mockReturnValue(null);
      mockPreviewMSProjectImport.mockResolvedValue(mockPreviewResponse);
      mockImportMSProject.mockReturnValue(new Promise(() => {}));

      render(<ImportModal {...defaultProps} />);

      const dropzone = screen
        .getByText("Drag & Drop MS Project XML")
        .closest(".import-dropzone")!;
      fireEvent.drop(dropzone, {
        dataTransfer: { files: [createTestFile()] },
      });

      await waitFor(() => {
        expect(screen.getByText("Import 15 Tasks")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Import 15 Tasks"));

      await waitFor(() => {
        const importingBtn = screen.getByText("Importing...");
        expect(importingBtn.closest("button")).toBeDisabled();
      });
    });
  });

  // ──────────────────────────────────────────────
  // New tests: Preview details
  // ──────────────────────────────────────────────

  describe("preview details", () => {
    async function navigateToPreview(
      previewData: ImportPreviewResponse = mockPreviewResponse
    ) {
      mockValidateImportFile.mockReturnValue(null);
      mockPreviewMSProjectImport.mockResolvedValue(previewData);

      render(<ImportModal {...defaultProps} />);

      const dropzone = screen
        .getByText("Drag & Drop MS Project XML")
        .closest(".import-dropzone")!;
      fireEvent.drop(dropzone, {
        dataTransfer: { files: [createTestFile()] },
      });

      await waitFor(() => {
        expect(screen.getByText("Preview Import")).toBeInTheDocument();
      });
    }

    it("shows milestone badge for milestone tasks", async () => {
      await navigateToPreview();

      expect(screen.getByText("Milestone")).toBeInTheDocument();
    });

    it("shows Import button with task count", async () => {
      await navigateToPreview();

      expect(screen.getByText("Import 15 Tasks")).toBeInTheDocument();
    });

    it("shows date range in preview info", async () => {
      await navigateToPreview();

      expect(screen.getByText("Project Name")).toBeInTheDocument();
      expect(screen.getByText("Date Range")).toBeInTheDocument();
    });

    it("shows sample tasks table in preview", async () => {
      await navigateToPreview();

      expect(
        screen.getByText("Sample Tasks (first 20)")
      ).toBeInTheDocument();
      expect(screen.getByText("WBS")).toBeInTheDocument();
      expect(screen.getByText("Task Name")).toBeInTheDocument();
      expect(screen.getByText("Duration")).toBeInTheDocument();
      expect(screen.getByText("Links")).toBeInTheDocument();
    });

    it("hides warnings section when there are no warnings", async () => {
      const noWarningsPreview: ImportPreviewResponse = {
        ...mockPreviewResponse,
        warnings: [],
      };
      await navigateToPreview(noWarningsPreview);

      expect(
        screen.queryByText(/Import Warnings/)
      ).not.toBeInTheDocument();
    });

    it("hides tasks table when there are no tasks", async () => {
      const noTasksPreview: ImportPreviewResponse = {
        ...mockPreviewResponse,
        tasks: [],
      };
      await navigateToPreview(noTasksPreview);

      expect(
        screen.queryByText("Sample Tasks (first 20)")
      ).not.toBeInTheDocument();
    });

    it("displays WBS code or dash for tasks without WBS", async () => {
      const previewWithNoWbs: ImportPreviewResponse = {
        ...mockPreviewResponse,
        tasks: [
          {
            name: "Task With WBS",
            wbs: "2.1",
            durationHours: 16,
            isMilestone: false,
            predecessors: 0,
          },
          {
            name: "Task Without WBS",
            wbs: "",
            durationHours: 8,
            isMilestone: false,
            predecessors: 0,
          },
        ],
      };
      await navigateToPreview(previewWithNoWbs);

      expect(screen.getByText("2.1")).toBeInTheDocument();
      expect(screen.getByText("-")).toBeInTheDocument();
    });

    it("formats task durations correctly", async () => {
      const durationPreview: ImportPreviewResponse = {
        ...mockPreviewResponse,
        tasks: [
          {
            name: "Zero Duration",
            wbs: "1.1",
            durationHours: 0,
            isMilestone: true,
            predecessors: 0,
          },
          {
            name: "Hours Only",
            wbs: "1.2",
            durationHours: 4,
            isMilestone: false,
            predecessors: 0,
          },
          {
            name: "Days Only",
            wbs: "1.3",
            durationHours: 16,
            isMilestone: false,
            predecessors: 0,
          },
          {
            name: "Days And Hours",
            wbs: "1.4",
            durationHours: 20,
            isMilestone: false,
            predecessors: 0,
          },
        ],
      };
      await navigateToPreview(durationPreview);

      expect(screen.getByText("0h")).toBeInTheDocument();
      expect(screen.getByText("4h")).toBeInTheDocument();
      expect(screen.getByText("2d")).toBeInTheDocument();
      expect(screen.getByText("2d 4h")).toBeInTheDocument();
    });
  });

  // ──────────────────────────────────────────────
  // New tests: File validation edge cases
  // ──────────────────────────────────────────────

  describe("file validation", () => {
    it("shows error for oversized file", async () => {
      mockValidateImportFile.mockReturnValue("File size exceeds 50MB limit");

      render(<ImportModal {...defaultProps} />);

      const dropzone = screen
        .getByText("Drag & Drop MS Project XML")
        .closest(".import-dropzone")!;

      const bigFile = createTestFile("big.xml", 60 * 1024 * 1024);
      fireEvent.drop(dropzone, { dataTransfer: { files: [bigFile] } });

      await waitFor(() => {
        expect(
          screen.getByText("File size exceeds 50MB limit")
        ).toBeInTheDocument();
      });

      expect(screen.getByText("Import Failed")).toBeInTheDocument();
    });

    it("shows error for empty file", async () => {
      mockValidateImportFile.mockReturnValue("File is empty");

      render(<ImportModal {...defaultProps} />);

      const dropzone = screen
        .getByText("Drag & Drop MS Project XML")
        .closest(".import-dropzone")!;

      const emptyFile = createTestFile("empty.xml", 0);
      fireEvent.drop(dropzone, { dataTransfer: { files: [emptyFile] } });

      await waitFor(() => {
        expect(screen.getByText("File is empty")).toBeInTheDocument();
      });
    });

    it("shows error for non-XML file (e.g., JSON)", async () => {
      mockValidateImportFile.mockReturnValue(
        "File must be an MS Project XML file (.xml)"
      );

      render(<ImportModal {...defaultProps} />);

      const dropzone = screen
        .getByText("Drag & Drop MS Project XML")
        .closest(".import-dropzone")!;

      const jsonFile = new File(
        ['{"tasks":[]}'],
        "schedule.json",
        { type: "application/json" }
      );
      fireEvent.drop(dropzone, { dataTransfer: { files: [jsonFile] } });

      await waitFor(() => {
        expect(
          screen.getByText("File must be an MS Project XML file (.xml)")
        ).toBeInTheDocument();
      });
    });

    it("shows error for .mpp file", async () => {
      mockValidateImportFile.mockReturnValue(
        "File must be an MS Project XML file (.xml)"
      );

      render(<ImportModal {...defaultProps} />);

      const dropzone = screen
        .getByText("Drag & Drop MS Project XML")
        .closest(".import-dropzone")!;

      const mppFile = new File(
        [new ArrayBuffer(1024)],
        "project.mpp",
        { type: "application/octet-stream" }
      );
      fireEvent.drop(dropzone, { dataTransfer: { files: [mppFile] } });

      await waitFor(() => {
        expect(
          screen.getByText("File must be an MS Project XML file (.xml)")
        ).toBeInTheDocument();
      });
    });

    it("shows error for CSV file", async () => {
      mockValidateImportFile.mockReturnValue(
        "File must be an MS Project XML file (.xml)"
      );

      render(<ImportModal {...defaultProps} />);

      const dropzone = screen
        .getByText("Drag & Drop MS Project XML")
        .closest(".import-dropzone")!;

      const csvFile = new File(
        ["task,duration\nA,5"],
        "data.csv",
        { type: "text/csv" }
      );
      fireEvent.drop(dropzone, { dataTransfer: { files: [csvFile] } });

      await waitFor(() => {
        expect(
          screen.getByText("File must be an MS Project XML file (.xml)")
        ).toBeInTheDocument();
      });
    });
  });

  // ──────────────────────────────────────────────
  // New tests: Render without optional props
  // ──────────────────────────────────────────────

  describe("optional props", () => {
    it("renders without programName", () => {
      render(
        <ImportModal
          programId="prog-1"
          isOpen={true}
          onClose={vi.fn()}
        />
      );

      expect(screen.getByText("Import MS Project File")).toBeInTheDocument();
      expect(screen.queryByText(/Importing into:/)).not.toBeInTheDocument();
    });

    it("renders without onImportComplete callback", async () => {
      mockValidateImportFile.mockReturnValue(null);
      mockPreviewMSProjectImport.mockResolvedValue(mockPreviewResponse);
      mockImportMSProject.mockResolvedValue(mockImportResult);

      render(
        <ImportModal
          programId="prog-1"
          isOpen={true}
          onClose={vi.fn()}
        />
      );

      const dropzone = screen
        .getByText("Drag & Drop MS Project XML")
        .closest(".import-dropzone")!;
      fireEvent.drop(dropzone, {
        dataTransfer: { files: [createTestFile()] },
      });

      await waitFor(() => {
        expect(screen.getByText("Import 15 Tasks")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Import 15 Tasks"));

      await waitFor(() => {
        expect(screen.getByText("Import Complete!")).toBeInTheDocument();
      });
    });
  });

  // ──────────────────────────────────────────────
  // New tests: Accessibility attributes
  // ──────────────────────────────────────────────

  describe("accessibility", () => {
    it("has role=dialog and aria-modal on overlay", () => {
      render(<ImportModal {...defaultProps} />);

      const dialog = screen.getByRole("dialog");
      expect(dialog).toHaveAttribute("aria-modal", "true");
    });

    it("has aria-labelledby pointing to the title", () => {
      render(<ImportModal {...defaultProps} />);

      const dialog = screen.getByRole("dialog");
      expect(dialog).toHaveAttribute(
        "aria-labelledby",
        "import-modal-title"
      );

      const title = document.getElementById("import-modal-title");
      expect(title).toBeTruthy();
      expect(title!.textContent).toBe("Import MS Project File");
    });

    it("close button has aria-label", () => {
      render(<ImportModal {...defaultProps} />);

      const closeBtn = screen.getByLabelText("Close");
      expect(closeBtn).toBeInTheDocument();
    });

    it("file input accepts .xml files only", () => {
      render(<ImportModal {...defaultProps} />);

      const fileInput = document.querySelector(
        'input[type="file"]'
      ) as HTMLInputElement;
      expect(fileInput.accept).toBe(".xml");
    });
  });

  // ──────────────────────────────────────────────
  // New tests: Full workflow end-to-end
  // ──────────────────────────────────────────────

  describe("full workflow", () => {
    it("completes full import flow: select -> preview -> import -> done", async () => {
      const onClose = vi.fn();
      const onImportComplete = vi.fn();
      mockValidateImportFile.mockReturnValue(null);
      mockPreviewMSProjectImport.mockResolvedValue(mockPreviewResponse);
      mockImportMSProject.mockResolvedValue(mockImportResult);

      render(
        <ImportModal
          programId="prog-1"
          isOpen={true}
          onClose={onClose}
          onImportComplete={onImportComplete}
        />
      );

      // Step 1: idle state
      expect(
        screen.getByText("Drag & Drop MS Project XML")
      ).toBeInTheDocument();

      // Step 2: drop a file
      const dropzone = screen
        .getByText("Drag & Drop MS Project XML")
        .closest(".import-dropzone")!;
      fireEvent.drop(dropzone, {
        dataTransfer: { files: [createTestFile("schedule.xml")] },
      });

      // Step 3: preview state
      await waitFor(() => {
        expect(screen.getByText("Preview Import")).toBeInTheDocument();
      });
      expect(screen.getByText("15 tasks found")).toBeInTheDocument();

      // Step 4: click import
      fireEvent.click(screen.getByText("Import 15 Tasks"));

      // Step 5: success state
      await waitFor(() => {
        expect(screen.getByText("Import Complete!")).toBeInTheDocument();
      });
      expect(onImportComplete).toHaveBeenCalledWith(mockImportResult);

      // Step 6: click done
      fireEvent.click(screen.getByText("Done"));
      expect(onClose).toHaveBeenCalled();
    });

    it("handles error recovery flow: select -> error -> try again -> select -> preview", async () => {
      mockValidateImportFile.mockReturnValue(null);
      mockPreviewMSProjectImport
        .mockRejectedValueOnce(new Error("Parse error"))
        .mockResolvedValueOnce(mockPreviewResponse);

      render(<ImportModal {...defaultProps} />);

      // Step 1: drop file, get error
      const dropzone = screen
        .getByText("Drag & Drop MS Project XML")
        .closest(".import-dropzone")!;
      fireEvent.drop(dropzone, {
        dataTransfer: { files: [createTestFile()] },
      });

      await waitFor(() => {
        expect(screen.getByText("Import Failed")).toBeInTheDocument();
      });

      // Step 2: click try again
      fireEvent.click(screen.getByText("Try Again"));

      expect(
        screen.getByText("Drag & Drop MS Project XML")
      ).toBeInTheDocument();

      // Step 3: drop file again, this time succeed
      const dropzone2 = screen
        .getByText("Drag & Drop MS Project XML")
        .closest(".import-dropzone")!;
      fireEvent.drop(dropzone2, {
        dataTransfer: { files: [createTestFile()] },
      });

      await waitFor(() => {
        expect(screen.getByText("Preview Import")).toBeInTheDocument();
      });
    });
  });
});
