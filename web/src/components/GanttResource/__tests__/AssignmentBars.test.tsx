/**
 * Unit tests for AssignmentBars component.
 * Tests rendering, interaction, drag-drop mocking, keyboard events.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { AssignmentBars } from "../AssignmentBars";
import type {
  AssignmentBar,
  GanttResourceViewConfig,
} from "@/types/ganttResource";

// Mock the useAssignmentDrag hook
const mockHandleDragStart = vi.fn();
vi.mock("@/hooks/useAssignmentDrag", () => ({
  useAssignmentDrag: vi.fn(() => ({
    isDragging: false,
    draggingId: null,
    previewDates: null,
    handleDragStart: mockHandleDragStart,
  })),
}));

import { useAssignmentDrag } from "@/hooks/useAssignmentDrag";

const baseConfig: GanttResourceViewConfig = {
  startDate: new Date("2026-02-01"),
  endDate: new Date("2026-03-01"),
  scale: "day" as const,
  rowHeight: 40,
  headerHeight: 60,
  sidebarWidth: 200,
  showUtilization: true,
  highlightOverallocations: true,
};

const makeAssignment = (overrides: Partial<AssignmentBar> = {}): AssignmentBar => ({
  assignmentId: "assign-1",
  activityId: "act-1",
  activityCode: "ACT-001",
  activityName: "Design Review",
  startDate: new Date("2026-02-05"),
  endDate: new Date("2026-02-10"),
  units: 1.0,
  isCritical: false,
  isOverallocated: false,
  ...overrides,
});

const defaultAssignments: AssignmentBar[] = [
  makeAssignment(),
  makeAssignment({
    assignmentId: "assign-2",
    activityId: "act-2",
    activityCode: "ACT-002",
    activityName: "Code Review",
    startDate: new Date("2026-02-12"),
    endDate: new Date("2026-02-15"),
    units: 0.5,
  }),
];

describe("AssignmentBars", () => {
  const defaultProps = {
    assignments: defaultAssignments,
    config: baseConfig,
    dayWidth: 40,
    highlightOverallocations: true,
    onAssignmentClick: vi.fn(),
    onAssignmentChange: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useAssignmentDrag).mockReturnValue({
      isDragging: false,
      draggingId: null,
      dragType: null,
      previewDates: null,
      handleDragStart: mockHandleDragStart,
    });
  });

  it("renders assignment bars container", () => {
    render(<AssignmentBars {...defaultProps} />);
    expect(screen.getByTestId("assignment-bars")).toBeInTheDocument();
  });

  it("renders correct number of assignment bars", () => {
    render(<AssignmentBars {...defaultProps} />);
    expect(screen.getByTestId("assignment-bar-assign-1")).toBeInTheDocument();
    expect(screen.getByTestId("assignment-bar-assign-2")).toBeInTheDocument();
  });

  it("shows activity code label", () => {
    render(<AssignmentBars {...defaultProps} />);
    expect(screen.getByText("ACT-001")).toBeInTheDocument();
    expect(screen.getByText("ACT-002")).toBeInTheDocument();
  });

  it("shows units as percentage (e.g., 0.5 -> 50%)", () => {
    render(<AssignmentBars {...defaultProps} />);
    expect(screen.getByText("100%")).toBeInTheDocument();
    expect(screen.getByText("50%")).toBeInTheDocument();
  });

  it("has correct aria-label", () => {
    render(<AssignmentBars {...defaultProps} />);
    expect(
      screen.getByLabelText("Design Review - 100%")
    ).toBeInTheDocument();
    expect(
      screen.getByLabelText("Code Review - 50%")
    ).toBeInTheDocument();
  });

  it("critical assignments have proper styling", () => {
    const criticalAssignments = [
      makeAssignment({ isCritical: true }),
    ];
    render(
      <AssignmentBars {...defaultProps} assignments={criticalAssignments} />
    );
    const bar = screen.getByTestId("assignment-bar-assign-1");
    expect(bar).toHaveClass("critical");
    expect(bar).toHaveStyle({ backgroundColor: "#ef4444" });
  });

  it("overallocated assignments have orange color when highlighted", () => {
    const overallocatedAssignments = [
      makeAssignment({ isOverallocated: true }),
    ];
    render(
      <AssignmentBars
        {...defaultProps}
        assignments={overallocatedAssignments}
        highlightOverallocations={true}
      />
    );
    const bar = screen.getByTestId("assignment-bar-assign-1");
    expect(bar).toHaveClass("overallocated");
    expect(bar).toHaveStyle({ backgroundColor: "#f97316" });
  });

  it("overallocated not highlighted when highlightOverallocations=false", () => {
    const overallocatedAssignments = [
      makeAssignment({ isOverallocated: true }),
    ];
    render(
      <AssignmentBars
        {...defaultProps}
        assignments={overallocatedAssignments}
        highlightOverallocations={false}
      />
    );
    const bar = screen.getByTestId("assignment-bar-assign-1");
    expect(bar).not.toHaveClass("overallocated");
    // Should fall back to default blue since not critical and highlight is off
    expect(bar).toHaveStyle({ backgroundColor: "#3b82f6" });
  });

  it("calls onAssignmentClick when clicking a bar (isDragging=false)", () => {
    const onClick = vi.fn();
    render(
      <AssignmentBars {...defaultProps} onAssignmentClick={onClick} />
    );
    fireEvent.click(screen.getByTestId("assignment-bar-assign-1"));
    expect(onClick).toHaveBeenCalledWith("assign-1");
  });

  it("does NOT call onAssignmentClick when dragging", () => {
    vi.mocked(useAssignmentDrag).mockReturnValue({
      isDragging: true,
      draggingId: "assign-1",
      dragType: "move",
      previewDates: {
        start: new Date("2026-02-05"),
        end: new Date("2026-02-10"),
      },
      handleDragStart: mockHandleDragStart,
    });

    const onClick = vi.fn();
    render(
      <AssignmentBars {...defaultProps} onAssignmentClick={onClick} />
    );
    fireEvent.click(screen.getByTestId("assignment-bar-assign-1"));
    expect(onClick).not.toHaveBeenCalled();
  });

  it("Delete key triggers onAssignmentChange with type delete", () => {
    const onChange = vi.fn();
    render(
      <AssignmentBars {...defaultProps} onAssignmentChange={onChange} />
    );
    const bar = screen.getByTestId("assignment-bar-assign-1");
    fireEvent.keyDown(bar, { key: "Delete" });
    expect(onChange).toHaveBeenCalledWith({
      assignmentId: "assign-1",
      type: "delete",
    });
  });

  it("Backspace key also triggers delete", () => {
    const onChange = vi.fn();
    render(
      <AssignmentBars {...defaultProps} onAssignmentChange={onChange} />
    );
    const bar = screen.getByTestId("assignment-bar-assign-2");
    fireEvent.keyDown(bar, { key: "Backspace" });
    expect(onChange).toHaveBeenCalledWith({
      assignmentId: "assign-2",
      type: "delete",
    });
  });

  it("renders resize handles", () => {
    render(<AssignmentBars {...defaultProps} />);
    expect(screen.getByTestId("resize-start-assign-1")).toBeInTheDocument();
    expect(screen.getByTestId("resize-end-assign-1")).toBeInTheDocument();
    expect(screen.getByTestId("resize-start-assign-2")).toBeInTheDocument();
    expect(screen.getByTestId("resize-end-assign-2")).toBeInTheDocument();
  });

  it("skips bars outside visible range", () => {
    const farFutureAssignments = [
      makeAssignment({
        assignmentId: "assign-far",
        // More than 365 days from config start
        startDate: new Date("2027-06-01"),
        endDate: new Date("2027-06-10"),
      }),
    ];
    render(
      <AssignmentBars {...defaultProps} assignments={farFutureAssignments} />
    );
    expect(screen.queryByTestId("assignment-bar-assign-far")).not.toBeInTheDocument();
  });
});
