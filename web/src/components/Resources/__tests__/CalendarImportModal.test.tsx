/**
 * Unit tests for CalendarImportModal component.
 * Tests modal rendering, file validation, date inputs, and close behavior.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { CalendarImportModal } from "../CalendarImportModal";

const mockToast = {
  success: vi.fn(),
  error: vi.fn(),
  info: vi.fn(),
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

import { validateCalendarFile } from "@/services/calendarImportApi";

const mockValidateCalendarFile = vi.mocked(validateCalendarFile);

function createTestFile(name = "calendars.xml", size = 1024): File {
  const content = new ArrayBuffer(size);
  return new File([content], name, { type: "application/xml" });
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
});
