/**
 * Unit tests for useAssignmentDrag hook.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useAssignmentDrag } from "../useAssignmentDrag";
import type { AssignmentBar } from "@/types/ganttResource";

describe("useAssignmentDrag", () => {
  const mockOnChange = vi.fn();
  const dayWidth = 20;

  const mockAssignment: AssignmentBar = {
    assignmentId: "test-1",
    activityId: "act-1",
    activityCode: "ACT-001",
    activityName: "Test Activity",
    startDate: new Date("2026-01-01"),
    endDate: new Date("2026-01-05"),
    units: 1.0,
    isCritical: false,
    isOverallocated: false,
  };

  beforeEach(() => {
    mockOnChange.mockClear();
  });

  afterEach(() => {
    // Clean up any global event listeners
    vi.restoreAllMocks();
  });

  it("initializes with no drag state", () => {
    const { result } = renderHook(() =>
      useAssignmentDrag(dayWidth, mockOnChange)
    );

    expect(result.current.isDragging).toBe(false);
    expect(result.current.draggingId).toBeNull();
    expect(result.current.previewDates).toBeNull();
    expect(result.current.dragType).toBeNull();
  });

  it("starts drag on handleDragStart call", () => {
    const { result } = renderHook(() =>
      useAssignmentDrag(dayWidth, mockOnChange)
    );

    const mockEvent = {
      preventDefault: vi.fn(),
      stopPropagation: vi.fn(),
      clientX: 100,
    } as unknown as React.MouseEvent;

    act(() => {
      result.current.handleDragStart(mockEvent, mockAssignment, "move");
    });

    expect(result.current.isDragging).toBe(true);
    expect(result.current.draggingId).toBe("test-1");
    expect(result.current.dragType).toBe("move");
    expect(result.current.previewDates).not.toBeNull();
    expect(mockEvent.preventDefault).toHaveBeenCalled();
    expect(mockEvent.stopPropagation).toHaveBeenCalled();
  });

  it("supports resize-start drag type", () => {
    const { result } = renderHook(() =>
      useAssignmentDrag(dayWidth, mockOnChange)
    );

    const mockEvent = {
      preventDefault: vi.fn(),
      stopPropagation: vi.fn(),
      clientX: 100,
    } as unknown as React.MouseEvent;

    act(() => {
      result.current.handleDragStart(mockEvent, mockAssignment, "resize-start");
    });

    expect(result.current.isDragging).toBe(true);
    expect(result.current.dragType).toBe("resize-start");
  });

  it("supports resize-end drag type", () => {
    const { result } = renderHook(() =>
      useAssignmentDrag(dayWidth, mockOnChange)
    );

    const mockEvent = {
      preventDefault: vi.fn(),
      stopPropagation: vi.fn(),
      clientX: 100,
    } as unknown as React.MouseEvent;

    act(() => {
      result.current.handleDragStart(mockEvent, mockAssignment, "resize-end");
    });

    expect(result.current.isDragging).toBe(true);
    expect(result.current.dragType).toBe("resize-end");
  });

  it("sets initial preview dates on drag start", () => {
    const { result } = renderHook(() =>
      useAssignmentDrag(dayWidth, mockOnChange)
    );

    const mockEvent = {
      preventDefault: vi.fn(),
      stopPropagation: vi.fn(),
      clientX: 100,
    } as unknown as React.MouseEvent;

    act(() => {
      result.current.handleDragStart(mockEvent, mockAssignment, "move");
    });

    expect(result.current.previewDates?.start.getTime()).toBe(
      mockAssignment.startDate.getTime()
    );
    expect(result.current.previewDates?.end.getTime()).toBe(
      mockAssignment.endDate.getTime()
    );
  });

  it("updates preview dates on mouse move during drag", () => {
    const { result } = renderHook(() =>
      useAssignmentDrag(dayWidth, mockOnChange)
    );

    const startEvent = {
      preventDefault: vi.fn(),
      stopPropagation: vi.fn(),
      clientX: 100,
    } as unknown as React.MouseEvent;

    act(() => {
      result.current.handleDragStart(startEvent, mockAssignment, "move");
    });

    // Simulate mouse move (2 days = 40px at dayWidth=20)
    const moveEvent = new MouseEvent("mousemove", { clientX: 140 });

    act(() => {
      window.dispatchEvent(moveEvent);
    });

    // Preview dates should be moved by 2 days
    const expectedStartDate = new Date("2026-01-03");
    const expectedEndDate = new Date("2026-01-07");

    expect(result.current.previewDates?.start.toDateString()).toBe(
      expectedStartDate.toDateString()
    );
    expect(result.current.previewDates?.end.toDateString()).toBe(
      expectedEndDate.toDateString()
    );
  });

  it("calls onAssignmentChange on mouse up after move", () => {
    const { result } = renderHook(() =>
      useAssignmentDrag(dayWidth, mockOnChange)
    );

    const startEvent = {
      preventDefault: vi.fn(),
      stopPropagation: vi.fn(),
      clientX: 100,
    } as unknown as React.MouseEvent;

    act(() => {
      result.current.handleDragStart(startEvent, mockAssignment, "move");
    });

    // Move mouse 2 days
    const moveEvent = new MouseEvent("mousemove", { clientX: 140 });
    act(() => {
      window.dispatchEvent(moveEvent);
    });

    // Release mouse
    const upEvent = new MouseEvent("mouseup");
    act(() => {
      window.dispatchEvent(upEvent);
    });

    expect(mockOnChange).toHaveBeenCalledWith({
      assignmentId: "test-1",
      type: "move",
      newStartDate: expect.any(Date),
      newEndDate: expect.any(Date),
    });
  });

  it("calls onAssignmentChange with resize type on resize-end", () => {
    const { result } = renderHook(() =>
      useAssignmentDrag(dayWidth, mockOnChange)
    );

    const startEvent = {
      preventDefault: vi.fn(),
      stopPropagation: vi.fn(),
      clientX: 100,
    } as unknown as React.MouseEvent;

    act(() => {
      result.current.handleDragStart(startEvent, mockAssignment, "resize-end");
    });

    // Move mouse 1 day
    const moveEvent = new MouseEvent("mousemove", { clientX: 120 });
    act(() => {
      window.dispatchEvent(moveEvent);
    });

    // Release mouse
    const upEvent = new MouseEvent("mouseup");
    act(() => {
      window.dispatchEvent(upEvent);
    });

    expect(mockOnChange).toHaveBeenCalledWith({
      assignmentId: "test-1",
      type: "resize",
      newStartDate: expect.any(Date),
      newEndDate: expect.any(Date),
    });
  });

  it("does not call onAssignmentChange if dates unchanged", () => {
    const { result } = renderHook(() =>
      useAssignmentDrag(dayWidth, mockOnChange)
    );

    const startEvent = {
      preventDefault: vi.fn(),
      stopPropagation: vi.fn(),
      clientX: 100,
    } as unknown as React.MouseEvent;

    act(() => {
      result.current.handleDragStart(startEvent, mockAssignment, "move");
    });

    // Release without moving
    const upEvent = new MouseEvent("mouseup");
    act(() => {
      window.dispatchEvent(upEvent);
    });

    expect(mockOnChange).not.toHaveBeenCalled();
  });

  it("resets drag state on mouse up", () => {
    const { result } = renderHook(() =>
      useAssignmentDrag(dayWidth, mockOnChange)
    );

    const startEvent = {
      preventDefault: vi.fn(),
      stopPropagation: vi.fn(),
      clientX: 100,
    } as unknown as React.MouseEvent;

    act(() => {
      result.current.handleDragStart(startEvent, mockAssignment, "move");
    });

    expect(result.current.isDragging).toBe(true);

    const upEvent = new MouseEvent("mouseup");
    act(() => {
      window.dispatchEvent(upEvent);
    });

    expect(result.current.isDragging).toBe(false);
    expect(result.current.draggingId).toBeNull();
    expect(result.current.previewDates).toBeNull();
  });

  it("prevents start date from going past end date on resize-start", () => {
    const { result } = renderHook(() =>
      useAssignmentDrag(dayWidth, mockOnChange)
    );

    const startEvent = {
      preventDefault: vi.fn(),
      stopPropagation: vi.fn(),
      clientX: 100,
    } as unknown as React.MouseEvent;

    act(() => {
      result.current.handleDragStart(startEvent, mockAssignment, "resize-start");
    });

    // Move start date past end date (10 days forward)
    const moveEvent = new MouseEvent("mousemove", { clientX: 300 });
    act(() => {
      window.dispatchEvent(moveEvent);
    });

    // Start should be limited to 1 day before end
    expect(result.current.previewDates!.start < result.current.previewDates!.end).toBe(true);
  });

  it("prevents end date from going before start date on resize-end", () => {
    const { result } = renderHook(() =>
      useAssignmentDrag(dayWidth, mockOnChange)
    );

    const startEvent = {
      preventDefault: vi.fn(),
      stopPropagation: vi.fn(),
      clientX: 100,
    } as unknown as React.MouseEvent;

    act(() => {
      result.current.handleDragStart(startEvent, mockAssignment, "resize-end");
    });

    // Move end date before start date (10 days backward)
    const moveEvent = new MouseEvent("mousemove", { clientX: -100 });
    act(() => {
      window.dispatchEvent(moveEvent);
    });

    // End should be limited to 1 day after start
    expect(result.current.previewDates!.end > result.current.previewDates!.start).toBe(true);
  });
});
