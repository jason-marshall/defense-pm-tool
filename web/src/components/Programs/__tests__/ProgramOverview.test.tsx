import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ProgramOverview } from "../ProgramOverview";
import type { Program } from "@/types/program";

const mockProgram: Program = {
  id: "prog-1",
  name: "F-35 Program",
  code: "F35-001",
  description: "Joint Strike Fighter program",
  status: "ACTIVE",
  planned_start_date: "2026-01-15",
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

describe("ProgramOverview", () => {
  it("renders program info card with code and status", () => {
    render(<ProgramOverview program={mockProgram} />);

    expect(screen.getByText("Program Information")).toBeInTheDocument();
    expect(screen.getByText("F35-001")).toBeInTheDocument();
    expect(screen.getByText("ACTIVE")).toBeInTheDocument();
  });

  it("renders schedule and budget card", () => {
    render(<ProgramOverview program={mockProgram} />);

    expect(screen.getByText("Schedule & Budget")).toBeInTheDocument();
    expect(screen.getByText("Budget at Completion")).toBeInTheDocument();
    expect(screen.getByText("$5,000,000")).toBeInTheDocument();
  });

  it("shows colored status badge", () => {
    render(<ProgramOverview program={mockProgram} />);

    const badge = screen.getByText("ACTIVE");
    expect(badge.className).toContain("bg-green-100");
  });

  it("conditionally renders optional fields", () => {
    const minimalProgram: Program = {
      ...mockProgram,
      description: null,
      contract_number: null,
      contract_type: null,
      budget_at_completion: null,
    };

    render(<ProgramOverview program={minimalProgram} />);

    expect(screen.queryByText("Description")).not.toBeInTheDocument();
    expect(screen.queryByText("Contract")).not.toBeInTheDocument();
    expect(screen.queryByText("Contract Type")).not.toBeInTheDocument();
    expect(screen.getByText("-")).toBeInTheDocument(); // budget shows "-"
  });
});
