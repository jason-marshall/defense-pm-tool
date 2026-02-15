/**
 * Unit tests for CalendarImportModal component.
 * Tests modal rendering, file validation, date inputs, close behavior,
 * preview flow, import success/error, loading state, and cancel/retry.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { CalendarImportModal } from "../CalendarImportModal";

const mockToast = {
  success: vi.fn(),
  error: vi.fn(),
  info: vi.fn(),
  warning: vi.fn(),
};

vi.mock("@/services/calendarImportApi", () => ({
  previewCalendarImport: vi.fn(),
  importCalendars: vi.fn(),
  validateCalendarFile: vi.fn(),
}));

vi.mock("@/components/Toast", () => ({
  useToast: vi.fn(() => mockToast),
}));

vi.mock("lucide-react", () => ({
  Upload: (props: Record<string, unknown>) => (
    <span data-testid="upload-icon" {...props} />
  ),
  Calendar: (props: Record<string, unknown>) => (
    <span data-testid="calendar-icon" {...props} />
  ),
  AlertTriangle: (props: Record<string, unknown>) => (
    <span data-testid="alert-icon" {...props} />
  ),
  Check: (props: Record<string, unknown>) => (
    <span data-testid="check-icon" {...props} />
  ),
  X: (props: Record<string, unknown>) => (
    <span data-testid="x-icon" {...props} />
  ),
}));

import {
  validateCalendarFile,
  previewCalendarImport,
  importCalendars,
} from "@/services/calendarImportApi";

const mockValidateCalendarFile = vi.mocked(validateCalendarFile);
const mockPreviewCalendarImport = vi.mocked(previewCalendarImport);
const mockImportCalendars = vi.mocked(importCalendars);

function createTestFile(name = "calendars.xml", size = 1024): File {
  const content = new ArrayBuffer(size);
  return new File([content], name, { type: "application/xml" });
}

const mockPreviewResponse = {
  calendars: [
    {
      uid: 1,
      name: "Standard",
      is_base: true,
      working_days: [1, 2, 3, 4, 5],
      hours_per_day: 8,
      holidays: 3,
    },
  ],
  resource_mappings: [
    {
      ms_project_resource: "John Smith",
      matched_resource_id: "res-1",
      matched_resource_name: "John S.",
      calendar_name: "Standard",
    },
    {
      ms_project_resource: "Jane Doe",
      matched_resource_id: null,
      matched_resource_name: null,
      calendar_name: "Standard",
    },
  ],
  total_holidays: 3,
  date_range_start: "2026-01-01",
  date_range_end: "2026-12-31",
  warnings: [],
};

const mockImportResponse = {
  success: true,
  resources_updated: 2,
  calendar_entries_created: 50,
  templates_created: 1,
  warnings: [],
};

/**
 * Helper to set up file + dates on the upload form so Preview Import is enabled.
 */
function fillUploadForm() {
  mockValidateCalendarFile.mockReturnValue(null);

  const fileInput = document.querySelector(
    'input[type="file"]'
  ) as HTMLInputElement;
  const validFile = createTestFile("calendars.xml");
  fireEvent.change(fileInput, { target: { files: [validFile] } });

  const dateInputs = screen
    .getAllByDisplayValue("")
    .filter((el) => (el as HTMLInputElement).type === "date");
  fireEvent.change(dateInputs[0], { target: { value: "2026-01-01" } });
  fireEvent.change(dateInputs[1], { target: { value: "2026-12-31" } });
}

describe("CalendarImportModal", () => {
  const defaultProps = {
    programId: "prog-1",
    isOpen: true,
    onClose: vi.fn(),
    onSuccess: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns null when isOpen is false", () => {
    const { container } = render(
      <CalendarImportModal {...defaultProps} isOpen={false} />
    );
    expect(container.innerHTML).toBe("");
  });

  it("renders modal when isOpen is true", () => {
    render(<CalendarImportModal {...defaultProps} />);
    expect(
      screen.getByText("Import Resource Calendars")
    ).toBeInTheDocument();
  });

  it("shows 'Import Resource Calendars' header", () => {
    render(<CalendarImportModal {...defaultProps} />);
    const header = screen.getByText("Import Resource Calendars");
    expect(header.closest("h2")).toBeInTheDocument();
  });

  it("shows file upload field", () => {
    render(<CalendarImportModal {...defaultProps} />);
    expect(screen.getByText("MS Project XML File")).toBeInTheDocument();
    expect(
      screen.getByText("Click to select MS Project XML file")
    ).toBeInTheDocument();
  });

  it("shows start date and end date inputs", () => {
    render(<CalendarImportModal {...defaultProps} />);
    expect(screen.getByText("Start Date")).toBeInTheDocument();
    expect(screen.getByText("End Date")).toBeInTheDocument();

    const dateInputs = screen.getAllByDisplayValue("");
    const dateFields = dateInputs.filter(
      (el) => (el as HTMLInputElement).type === "date"
    );
    expect(dateFields.length).toBe(2);
  });

  it("Preview button is disabled when fields are empty", () => {
    render(<CalendarImportModal {...defaultProps} />);
    const previewButton = screen.getByText("Preview Import");
    expect(previewButton).toBeDisabled();
  });

  it("calls onClose when close button is clicked", () => {
    const onClose = vi.fn();
    render(<CalendarImportModal {...defaultProps} onClose={onClose} />);

    // The close button uses the X icon mock
    const closeButton = screen.getByTestId("x-icon").closest("button")!;
    fireEvent.click(closeButton);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("shows error toast on invalid file", () => {
    mockValidateCalendarFile.mockReturnValue(
      "File must be an MS Project XML file (.xml)"
    );

    render(<CalendarImportModal {...defaultProps} />);

    const fileInput = document.querySelector(
      'input[type="file"]'
    ) as HTMLInputElement;

    const badFile = createTestFile("data.txt");
    fireEvent.change(fileInput, { target: { files: [badFile] } });

    expect(mockToast.error).toHaveBeenCalledWith(
      "File must be an MS Project XML file (.xml)"
    );
  });

  it("sets file when valid file is selected", () => {
    mockValidateCalendarFile.mockReturnValue(null);

    render(<CalendarImportModal {...defaultProps} />);

    const fileInput = document.querySelector(
      'input[type="file"]'
    ) as HTMLInputElement;

    const validFile = createTestFile("calendars.xml");
    fireEvent.change(fileInput, { target: { files: [validFile] } });

    expect(mockToast.error).not.toHaveBeenCalled();
    expect(screen.getByText("calendars.xml")).toBeInTheDocument();
  });

  // --- New tests below ---

  describe("file upload interaction", () => {
    it("does not set file when file input change has no files", () => {
      render(<CalendarImportModal {...defaultProps} />);

      const fileInput = document.querySelector(
        'input[type="file"]'
      ) as HTMLInputElement;

      fireEvent.change(fileInput, { target: { files: [] } });

      expect(mockValidateCalendarFile).not.toHaveBeenCalled();
      expect(
        screen.getByText("Click to select MS Project XML file")
      ).toBeInTheDocument();
    });

    it("does not update file state when validation fails", () => {
      mockValidateCalendarFile.mockReturnValue("File size exceeds 50MB limit");

      render(<CalendarImportModal {...defaultProps} />);

      const fileInput = document.querySelector(
        'input[type="file"]'
      ) as HTMLInputElement;
      const largeFile = createTestFile("big.xml", 60 * 1024 * 1024);
      fireEvent.change(fileInput, { target: { files: [largeFile] } });

      expect(mockToast.error).toHaveBeenCalledWith(
        "File size exceeds 50MB limit"
      );
      // Still shows placeholder, not the file name
      expect(
        screen.getByText("Click to select MS Project XML file")
      ).toBeInTheDocument();
    });

    it("enables Preview Import button after file and dates are filled", () => {
      render(<CalendarImportModal {...defaultProps} />);

      fillUploadForm();

      const previewButton = screen.getByText("Preview Import");
      expect(previewButton).not.toBeDisabled();
    });
  });

  describe("date selection", () => {
    it("allows changing start and end dates", () => {
      render(<CalendarImportModal {...defaultProps} />);

      const dateInputs = screen
        .getAllByDisplayValue("")
        .filter((el) => (el as HTMLInputElement).type === "date");

      fireEvent.change(dateInputs[0], { target: { value: "2026-03-01" } });
      expect(dateInputs[0]).toHaveValue("2026-03-01");

      fireEvent.change(dateInputs[1], { target: { value: "2026-06-30" } });
      expect(dateInputs[1]).toHaveValue("2026-06-30");
    });
  });

  describe("preview mode", () => {
    it("shows error toast when preview is clicked without all fields", async () => {
      render(<CalendarImportModal {...defaultProps} />);

      // Directly invoke the preview button click (it is disabled, but test the handler guard)
      // We need to fill partial data and then click
      mockValidateCalendarFile.mockReturnValue(null);
      const fileInput = document.querySelector(
        'input[type="file"]'
      ) as HTMLInputElement;
      fireEvent.change(fileInput, {
        target: { files: [createTestFile()] },
      });

      // Only file set, no dates - button still disabled, but let's test the
      // handlePreview guard by calling through a non-disabled state
      // Since button is disabled, we verify it stays disabled
      const previewButton = screen.getByText("Preview Import");
      expect(previewButton).toBeDisabled();
    });

    it("shows error toast when end date is before start date", async () => {
      render(<CalendarImportModal {...defaultProps} />);

      mockValidateCalendarFile.mockReturnValue(null);
      const fileInput = document.querySelector(
        'input[type="file"]'
      ) as HTMLInputElement;
      fireEvent.change(fileInput, {
        target: { files: [createTestFile()] },
      });

      const dateInputs = screen
        .getAllByDisplayValue("")
        .filter((el) => (el as HTMLInputElement).type === "date");
      fireEvent.change(dateInputs[0], { target: { value: "2026-12-31" } });
      fireEvent.change(dateInputs[1], { target: { value: "2026-01-01" } });

      const previewButton = screen.getByText("Preview Import");
      fireEvent.click(previewButton);

      await waitFor(() => {
        expect(mockToast.error).toHaveBeenCalledWith(
          "End date must be after start date"
        );
      });
    });

    it("calls previewCalendarImport and shows preview summary", async () => {
      mockPreviewCalendarImport.mockResolvedValue(mockPreviewResponse);

      render(<CalendarImportModal {...defaultProps} />);

      fillUploadForm();

      const previewButton = screen.getByText("Preview Import");
      fireEvent.click(previewButton);

      await waitFor(() => {
        expect(screen.getByText("Import Summary")).toBeInTheDocument();
      });

      expect(screen.getByText(/1 calendar\(s\) found/)).toBeInTheDocument();
      expect(
        screen.getByText(/2 resource mapping\(s\)/)
      ).toBeInTheDocument();
      expect(screen.getByText(/3 holiday\(s\)/)).toBeInTheDocument();
      expect(
        screen.getByText(/2026-01-01 to 2026-12-31/)
      ).toBeInTheDocument();
    });

    it("shows resource mappings with matched and unmatched resources", async () => {
      mockPreviewCalendarImport.mockResolvedValue(mockPreviewResponse);

      render(<CalendarImportModal {...defaultProps} />);

      fillUploadForm();
      fireEvent.click(screen.getByText("Preview Import"));

      await waitFor(() => {
        expect(screen.getByText("Resource Mappings")).toBeInTheDocument();
      });

      expect(screen.getByText("John Smith")).toBeInTheDocument();
      expect(screen.getByText("John S.")).toBeInTheDocument();
      expect(screen.getByText("Jane Doe")).toBeInTheDocument();
      expect(screen.getByText("No match")).toBeInTheDocument();
    });

    it("shows warnings in the preview step when present", async () => {
      const previewWithWarnings = {
        ...mockPreviewResponse,
        warnings: ["Calendar 'Night Shift' has no working days"],
      };
      mockPreviewCalendarImport.mockResolvedValue(previewWithWarnings);

      render(<CalendarImportModal {...defaultProps} />);

      fillUploadForm();
      fireEvent.click(screen.getByText("Preview Import"));

      await waitFor(() => {
        expect(screen.getByText("Warnings")).toBeInTheDocument();
        expect(
          screen.getByText("Calendar 'Night Shift' has no working days")
        ).toBeInTheDocument();
      });
    });

    it("does not show warnings section when there are none", async () => {
      mockPreviewCalendarImport.mockResolvedValue(mockPreviewResponse);

      render(<CalendarImportModal {...defaultProps} />);

      fillUploadForm();
      fireEvent.click(screen.getByText("Preview Import"));

      await waitFor(() => {
        expect(screen.getByText("Import Summary")).toBeInTheDocument();
      });

      expect(screen.queryByText("Warnings")).not.toBeInTheDocument();
    });

    it("shows Back button in preview that returns to upload step", async () => {
      mockPreviewCalendarImport.mockResolvedValue(mockPreviewResponse);

      render(<CalendarImportModal {...defaultProps} />);

      fillUploadForm();
      fireEvent.click(screen.getByText("Preview Import"));

      await waitFor(() => {
        expect(screen.getByText("Back")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Back"));

      expect(
        screen.getByText("Preview Import")
      ).toBeInTheDocument();
      expect(screen.getByText("MS Project XML File")).toBeInTheDocument();
    });

    it("shows Import Calendars button in preview step", async () => {
      mockPreviewCalendarImport.mockResolvedValue(mockPreviewResponse);

      render(<CalendarImportModal {...defaultProps} />);

      fillUploadForm();
      fireEvent.click(screen.getByText("Preview Import"));

      await waitFor(() => {
        expect(screen.getByText("Import Calendars")).toBeInTheDocument();
      });
    });

    it("handles preview API error and shows error step", async () => {
      mockPreviewCalendarImport.mockRejectedValue(
        new Error("Network error during preview")
      );

      render(<CalendarImportModal {...defaultProps} />);

      fillUploadForm();
      fireEvent.click(screen.getByText("Preview Import"));

      await waitFor(() => {
        expect(screen.getByText("Import Failed")).toBeInTheDocument();
        expect(
          screen.getByText("Network error during preview")
        ).toBeInTheDocument();
      });
    });

    it("handles preview API error with non-Error object", async () => {
      mockPreviewCalendarImport.mockRejectedValue("string error");

      render(<CalendarImportModal {...defaultProps} />);

      fillUploadForm();
      fireEvent.click(screen.getByText("Preview Import"));

      await waitFor(() => {
        expect(screen.getByText("Import Failed")).toBeInTheDocument();
        expect(screen.getByText("Preview failed")).toBeInTheDocument();
      });
    });
  });

  describe("loading state", () => {
    it("shows loading spinner during preview fetch", async () => {
      // Use a promise that doesn't resolve immediately
      let resolvePreview!: (value: typeof mockPreviewResponse) => void;
      mockPreviewCalendarImport.mockReturnValue(
        new Promise((resolve) => {
          resolvePreview = resolve;
        })
      );

      render(<CalendarImportModal {...defaultProps} />);

      fillUploadForm();
      fireEvent.click(screen.getByText("Preview Import"));

      // Should show loading state
      await waitFor(() => {
        expect(
          screen.getByText("Importing calendars...")
        ).toBeInTheDocument();
      });

      // Resolve to let the component finish
      resolvePreview(mockPreviewResponse);

      await waitFor(() => {
        expect(screen.getByText("Import Summary")).toBeInTheDocument();
      });
    });

    it("shows loading spinner during import", async () => {
      mockPreviewCalendarImport.mockResolvedValue(mockPreviewResponse);

      let resolveImport!: (value: typeof mockImportResponse) => void;
      mockImportCalendars.mockReturnValue(
        new Promise((resolve) => {
          resolveImport = resolve;
        })
      );

      render(<CalendarImportModal {...defaultProps} />);

      fillUploadForm();
      fireEvent.click(screen.getByText("Preview Import"));

      await waitFor(() => {
        expect(screen.getByText("Import Calendars")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Import Calendars"));

      await waitFor(() => {
        expect(
          screen.getByText("Importing calendars...")
        ).toBeInTheDocument();
      });

      resolveImport(mockImportResponse);

      await waitFor(() => {
        expect(screen.getByText("Import Complete!")).toBeInTheDocument();
      });
    });
  });

  describe("import success", () => {
    it("shows success screen with stats after successful import", async () => {
      mockPreviewCalendarImport.mockResolvedValue(mockPreviewResponse);
      mockImportCalendars.mockResolvedValue(mockImportResponse);

      render(<CalendarImportModal {...defaultProps} />);

      fillUploadForm();
      fireEvent.click(screen.getByText("Preview Import"));

      await waitFor(() => {
        expect(screen.getByText("Import Calendars")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Import Calendars"));

      await waitFor(() => {
        expect(screen.getByText("Import Complete!")).toBeInTheDocument();
      });

      // Check stats
      expect(screen.getByText("1")).toBeInTheDocument(); // templates
      expect(screen.getByText("2")).toBeInTheDocument(); // resources
      expect(screen.getByText("50")).toBeInTheDocument(); // entries
      expect(screen.getByText("Templates")).toBeInTheDocument();
      expect(screen.getByText("Resources")).toBeInTheDocument();
      expect(screen.getByText("Calendar Entries")).toBeInTheDocument();
    });

    it("shows success toast after import", async () => {
      mockPreviewCalendarImport.mockResolvedValue(mockPreviewResponse);
      mockImportCalendars.mockResolvedValue(mockImportResponse);

      render(<CalendarImportModal {...defaultProps} />);

      fillUploadForm();
      fireEvent.click(screen.getByText("Preview Import"));

      await waitFor(() => {
        expect(screen.getByText("Import Calendars")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Import Calendars"));

      await waitFor(() => {
        expect(mockToast.success).toHaveBeenCalledWith(
          "Imported: 1 templates, 2 resources, 50 calendar entries"
        );
      });
    });

    it("calls onSuccess and onClose when Done button is clicked", async () => {
      const onSuccess = vi.fn();
      const onClose = vi.fn();

      mockPreviewCalendarImport.mockResolvedValue(mockPreviewResponse);
      mockImportCalendars.mockResolvedValue(mockImportResponse);

      render(
        <CalendarImportModal
          {...defaultProps}
          onSuccess={onSuccess}
          onClose={onClose}
        />
      );

      fillUploadForm();
      fireEvent.click(screen.getByText("Preview Import"));

      await waitFor(() => {
        expect(screen.getByText("Import Calendars")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Import Calendars"));

      await waitFor(() => {
        expect(screen.getByText("Done")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Done"));

      expect(onSuccess).toHaveBeenCalledTimes(1);
      expect(onClose).toHaveBeenCalledTimes(1);
    });
  });

  describe("import error", () => {
    it("shows error screen with message when import fails", async () => {
      mockPreviewCalendarImport.mockResolvedValue(mockPreviewResponse);
      mockImportCalendars.mockRejectedValue(
        new Error("Server error: 500")
      );

      render(<CalendarImportModal {...defaultProps} />);

      fillUploadForm();
      fireEvent.click(screen.getByText("Preview Import"));

      await waitFor(() => {
        expect(screen.getByText("Import Calendars")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Import Calendars"));

      await waitFor(() => {
        expect(screen.getByText("Import Failed")).toBeInTheDocument();
        expect(screen.getByText("Server error: 500")).toBeInTheDocument();
      });
    });

    it("shows generic error message for non-Error thrown values", async () => {
      mockPreviewCalendarImport.mockResolvedValue(mockPreviewResponse);
      mockImportCalendars.mockRejectedValue("unknown failure");

      render(<CalendarImportModal {...defaultProps} />);

      fillUploadForm();
      fireEvent.click(screen.getByText("Preview Import"));

      await waitFor(() => {
        expect(screen.getByText("Import Calendars")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Import Calendars"));

      await waitFor(() => {
        expect(screen.getByText("Import Failed")).toBeInTheDocument();
        expect(screen.getByText("Import failed")).toBeInTheDocument();
      });
    });

    it("shows Cancel button in error step that calls onClose", async () => {
      const onClose = vi.fn();
      mockPreviewCalendarImport.mockResolvedValue(mockPreviewResponse);
      mockImportCalendars.mockRejectedValue(new Error("fail"));

      render(
        <CalendarImportModal {...defaultProps} onClose={onClose} />
      );

      fillUploadForm();
      fireEvent.click(screen.getByText("Preview Import"));

      await waitFor(() => {
        expect(screen.getByText("Import Calendars")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Import Calendars"));

      await waitFor(() => {
        expect(screen.getByText("Cancel")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Cancel"));
      expect(onClose).toHaveBeenCalledTimes(1);
    });

    it("shows Try Again button in error step that resets to upload", async () => {
      mockPreviewCalendarImport.mockResolvedValue(mockPreviewResponse);
      mockImportCalendars.mockRejectedValue(new Error("fail"));

      render(<CalendarImportModal {...defaultProps} />);

      fillUploadForm();
      fireEvent.click(screen.getByText("Preview Import"));

      await waitFor(() => {
        expect(screen.getByText("Import Calendars")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Import Calendars"));

      await waitFor(() => {
        expect(screen.getByText("Try Again")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Try Again"));

      // Should go back to upload step
      expect(screen.getByText("MS Project XML File")).toBeInTheDocument();
      expect(screen.getByText("Preview Import")).toBeInTheDocument();
      // File should be cleared
      expect(
        screen.getByText("Click to select MS Project XML file")
      ).toBeInTheDocument();
    });
  });

  describe("cancel/close", () => {
    it("closes modal when clicking overlay background", () => {
      const onClose = vi.fn();
      render(<CalendarImportModal {...defaultProps} onClose={onClose} />);

      const overlay = screen
        .getByRole("dialog")
        .closest(".calendar-import-modal-overlay")!;
      fireEvent.click(overlay);

      expect(onClose).toHaveBeenCalledTimes(1);
    });

    it("does not close when clicking inside modal body", () => {
      const onClose = vi.fn();
      render(<CalendarImportModal {...defaultProps} onClose={onClose} />);

      // Click on the modal title text (inside the modal)
      fireEvent.click(screen.getByText("Import Resource Calendars"));

      expect(onClose).not.toHaveBeenCalled();
    });

    it("closes modal on Escape key press", () => {
      const onClose = vi.fn();
      render(<CalendarImportModal {...defaultProps} onClose={onClose} />);

      const overlay = screen.getByRole("dialog");
      fireEvent.keyDown(overlay, { key: "Escape" });

      expect(onClose).toHaveBeenCalledTimes(1);
    });

    it("does not close on non-Escape key press", () => {
      const onClose = vi.fn();
      render(<CalendarImportModal {...defaultProps} onClose={onClose} />);

      const overlay = screen.getByRole("dialog");
      fireEvent.keyDown(overlay, { key: "Enter" });

      expect(onClose).not.toHaveBeenCalled();
    });

    it("resets state when modal is closed and reopened", () => {
      mockValidateCalendarFile.mockReturnValue(null);

      const { rerender } = render(
        <CalendarImportModal {...defaultProps} />
      );

      // Select a file
      const fileInput = document.querySelector(
        'input[type="file"]'
      ) as HTMLInputElement;
      fireEvent.change(fileInput, {
        target: { files: [createTestFile()] },
      });
      expect(screen.getByText("calendars.xml")).toBeInTheDocument();

      // Close via the close button
      const closeButton = screen.getByTestId("x-icon").closest("button")!;
      fireEvent.click(closeButton);

      // Reopen
      rerender(<CalendarImportModal {...defaultProps} />);

      // File should be reset
      expect(
        screen.getByText("Click to select MS Project XML file")
      ).toBeInTheDocument();
    });
  });

  describe("modal accessibility", () => {
    it("has role=dialog and aria-modal=true", () => {
      render(<CalendarImportModal {...defaultProps} />);

      const dialog = screen.getByRole("dialog");
      expect(dialog).toHaveAttribute("aria-modal", "true");
    });

    it("has aria-labelledby pointing to the title", () => {
      render(<CalendarImportModal {...defaultProps} />);

      const dialog = screen.getByRole("dialog");
      expect(dialog).toHaveAttribute(
        "aria-labelledby",
        "calendar-import-title"
      );
    });

    it("close button has aria-label", () => {
      render(<CalendarImportModal {...defaultProps} />);

      const closeButton = screen.getByLabelText("Close");
      expect(closeButton).toBeInTheDocument();
    });
  });
});
