/**
 * Unit tests for WBSToolbar component.
 * Tests button rendering, click handlers, and disabled state.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { WBSToolbar } from "../WBSToolbar";

describe("WBSToolbar", () => {
  const defaultProps = {
    onExpandAll: vi.fn(),
    onCollapseAll: vi.fn(),
    onAddRoot: vi.fn(),
    hasElements: true,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders all 3 buttons", () => {
    render(<WBSToolbar {...defaultProps} />);
    expect(screen.getByText("+ Add Root Element")).toBeInTheDocument();
    expect(screen.getByText("Expand All")).toBeInTheDocument();
    expect(screen.getByText("Collapse All")).toBeInTheDocument();
  });

  it("'Add Root Element' button calls onAddRoot", () => {
    const onAddRoot = vi.fn();
    render(<WBSToolbar {...defaultProps} onAddRoot={onAddRoot} />);
    fireEvent.click(screen.getByText("+ Add Root Element"));
    expect(onAddRoot).toHaveBeenCalledTimes(1);
  });

  it("'Expand All' calls onExpandAll", () => {
    const onExpandAll = vi.fn();
    render(<WBSToolbar {...defaultProps} onExpandAll={onExpandAll} />);
    fireEvent.click(screen.getByText("Expand All"));
    expect(onExpandAll).toHaveBeenCalledTimes(1);
  });

  it("'Collapse All' calls onCollapseAll", () => {
    const onCollapseAll = vi.fn();
    render(<WBSToolbar {...defaultProps} onCollapseAll={onCollapseAll} />);
    fireEvent.click(screen.getByText("Collapse All"));
    expect(onCollapseAll).toHaveBeenCalledTimes(1);
  });

  it("Expand All is disabled when hasElements is false", () => {
    render(<WBSToolbar {...defaultProps} hasElements={false} />);
    expect(screen.getByText("Expand All")).toBeDisabled();
  });

  it("Collapse All is disabled when hasElements is false", () => {
    render(<WBSToolbar {...defaultProps} hasElements={false} />);
    expect(screen.getByText("Collapse All")).toBeDisabled();
  });

  it("Add Root is always enabled regardless of hasElements", () => {
    render(<WBSToolbar {...defaultProps} hasElements={false} />);
    expect(screen.getByText("+ Add Root Element")).not.toBeDisabled();
  });
});
