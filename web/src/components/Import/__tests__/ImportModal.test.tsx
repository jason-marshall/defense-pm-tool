/**
 * Unit tests for ImportModal component.
 * Tests modal rendering, file validation, preview workflow, and error handling.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { ImportModal } from "../ImportModal";
import type { ImportPreviewResponse } from "@/types/import";

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
  validateImportFile,
} from "@/services/importApi";

const mockValidateImportFile = vi.mocked(validateImportFile);
const mockPreviewMSProjectImport = vi.mocked(previewMSProjectImport);

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
});
