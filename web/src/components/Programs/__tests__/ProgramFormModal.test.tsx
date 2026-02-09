import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ProgramFormModal } from "../ProgramFormModal";
import type { Program } from "@/types/program";

const mockOnSubmit = vi.fn();
const mockOnClose = vi.fn();

const defaultProps = {
  onSubmit: mockOnSubmit,
  onClose: mockOnClose,
  isSubmitting: false,
};

const mockProgram: Program = {
  id: "prog-1",
  name: "F-35 Program",
  code: "F35-001",
  description: "Joint Strike Fighter program",
  status: "ACTIVE",
  planned_start_date: "2026-01-01",
  planned_end_date: "2026-12-31",
  actual_start_date: null,
  actual_end_date: null,
  budget_at_completion: "5000000",
  contract_number: "FA-001",
  contract_type: "CPFF",
  owner_id: "user-1",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: null,
};

describe("ProgramFormModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders create mode when no program provided", () => {
    render(<ProgramFormModal {...defaultProps} />);

    expect(screen.getByText("Create Program")).toBeInTheDocument();
    expect(screen.getByText("Create")).toBeInTheDocument();
  });

  it("renders edit mode when program is provided", () => {
    render(<ProgramFormModal {...defaultProps} program={mockProgram} />);

    expect(screen.getByText("Edit Program")).toBeInTheDocument();
    expect(screen.getByText("Update")).toBeInTheDocument();
  });

  it("renders all form fields", () => {
    render(<ProgramFormModal {...defaultProps} />);

    expect(screen.getByLabelText(/name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/code/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/description/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/status/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/start date/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/end date/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/budget at completion/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/contract number/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/contract type/i)).toBeInTheDocument();
  });

  it("populates fields when editing an existing program", () => {
    render(<ProgramFormModal {...defaultProps} program={mockProgram} />);

    expect(screen.getByLabelText(/name/i)).toHaveValue("F-35 Program");
    expect(screen.getByLabelText(/code/i)).toHaveValue("F35-001");
    expect(screen.getByLabelText(/description/i)).toHaveValue(
      "Joint Strike Fighter program"
    );
    expect(screen.getByLabelText(/status/i)).toHaveValue("ACTIVE");
    expect(screen.getByLabelText(/start date/i)).toHaveValue("2026-01-01");
    expect(screen.getByLabelText(/end date/i)).toHaveValue("2026-12-31");
  });

  it("calls onSubmit with form data", () => {
    render(<ProgramFormModal {...defaultProps} />);

    fireEvent.change(screen.getByLabelText(/name/i), {
      target: { value: "New Program" },
    });
    fireEvent.change(screen.getByLabelText(/code/i), {
      target: { value: "NP-001" },
    });
    fireEvent.change(screen.getByLabelText(/start date/i), {
      target: { value: "2026-03-01" },
    });
    fireEvent.change(screen.getByLabelText(/end date/i), {
      target: { value: "2026-09-01" },
    });

    fireEvent.submit(screen.getByRole("button", { name: /create/i }));

    expect(mockOnSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        name: "New Program",
        code: "NP-001",
        planned_start_date: "2026-03-01",
        planned_end_date: "2026-09-01",
      })
    );
  });

  it("calls onClose when Cancel is clicked", () => {
    render(<ProgramFormModal {...defaultProps} />);

    fireEvent.click(screen.getByText("Cancel"));

    expect(mockOnClose).toHaveBeenCalled();
  });

  it("disables submit button when isSubmitting is true", () => {
    render(<ProgramFormModal {...defaultProps} isSubmitting={true} />);

    expect(screen.getByText("Saving...")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /saving/i })
    ).toBeDisabled();
  });

  it("renders status dropdown with all options", () => {
    render(<ProgramFormModal {...defaultProps} />);

    const statusSelect = screen.getByLabelText(/status/i);
    const options = statusSelect.querySelectorAll("option");

    expect(options).toHaveLength(5);
    expect(options[0]).toHaveValue("PLANNING");
    expect(options[1]).toHaveValue("ACTIVE");
    expect(options[2]).toHaveValue("ON_HOLD");
    expect(options[3]).toHaveValue("COMPLETED");
    expect(options[4]).toHaveValue("CANCELLED");
  });
});
