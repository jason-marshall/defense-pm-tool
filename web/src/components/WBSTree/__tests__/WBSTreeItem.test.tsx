/**
 * Unit tests for WBSTreeItem component.
 * Tests rendering, expand/collapse, selection, actions, and recursive children.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { WBSTreeItem } from "../WBSTreeItem";
import type { WBSElementTree } from "@/types";

interface WBSElementTreeWithCA extends WBSElementTree {
  isControlAccount?: boolean;
}

const childElement: WBSElementTreeWithCA = {
  id: "child-1",
  programId: "prog-1",
  parentId: "elem-1",
  code: "1.1.1",
  name: "Subsystem A",
  description: null,
  path: "1.1.1",
  level: 3,
  budgetedCost: "25000",
  createdAt: "2026-01-01T00:00:00Z",
  updatedAt: "2026-01-01T00:00:00Z",
  children: [],
};

const elementWithChildren: WBSElementTreeWithCA = {
  id: "elem-1",
  programId: "prog-1",
  parentId: null,
  code: "1.1",
  name: "System Design",
  description: null,
  path: "1.1",
  level: 2,
  budgetedCost: "50000",
  createdAt: "2026-01-01T00:00:00Z",
  updatedAt: "2026-01-01T00:00:00Z",
  children: [childElement],
};

const elementWithoutChildren: WBSElementTreeWithCA = {
  id: "elem-2",
  programId: "prog-1",
  parentId: "elem-1",
  code: "1.2",
  name: "Testing Phase",
  description: null,
  path: "1.2",
  level: 2,
  budgetedCost: "15000",
  createdAt: "2026-01-01T00:00:00Z",
  updatedAt: "2026-01-01T00:00:00Z",
  children: [],
};

const controlAccountElement: WBSElementTreeWithCA = {
  id: "elem-3",
  programId: "prog-1",
  parentId: null,
  code: "2.1",
  name: "Control Account A",
  description: null,
  path: "2.1",
  level: 2,
  budgetedCost: "100000",
  createdAt: "2026-01-01T00:00:00Z",
  updatedAt: "2026-01-01T00:00:00Z",
  children: [],
  isControlAccount: true,
};

describe("WBSTreeItem", () => {
  const defaultProps = {
    element: elementWithChildren,
    level: 0,
    selectedId: null as string | null,
    expandedIds: new Set<string>(),
    onSelect: vi.fn(),
    onToggle: vi.fn(),
    onAddChild: vi.fn(),
    onEdit: vi.fn(),
    onDelete: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders element code and name", () => {
    render(<WBSTreeItem {...defaultProps} />);
    expect(screen.getByText("1.1")).toBeInTheDocument();
    expect(screen.getByText("System Design")).toBeInTheDocument();
  });

  it("shows level badge", () => {
    render(<WBSTreeItem {...defaultProps} />);
    expect(screen.getByText("L2")).toBeInTheDocument();
  });

  it("shows folder icon when has children", () => {
    render(<WBSTreeItem {...defaultProps} />);
    expect(screen.getByText("\uD83D\uDCC1")).toBeInTheDocument();
  });

  it("shows file icon when no children", () => {
    render(
      <WBSTreeItem {...defaultProps} element={elementWithoutChildren} />
    );
    expect(screen.getByText("\uD83D\uDCC4")).toBeInTheDocument();
  });

  it("shows expand arrow when has children", () => {
    render(<WBSTreeItem {...defaultProps} />);
    expect(screen.getByText("\u25B6")).toBeInTheDocument();
  });

  it("shows no arrow when no children", () => {
    render(
      <WBSTreeItem {...defaultProps} element={elementWithoutChildren} />
    );
    // No arrow characters should be present
    expect(screen.queryByText("\u25B6")).not.toBeInTheDocument();
    expect(screen.queryByText("\u25BC")).not.toBeInTheDocument();
  });

  it("click row calls onSelect", () => {
    const onSelect = vi.fn();
    render(<WBSTreeItem {...defaultProps} onSelect={onSelect} />);

    const row = document.querySelector(".wbs-tree-item-row")!;
    fireEvent.click(row);
    expect(onSelect).toHaveBeenCalledWith(elementWithChildren);
  });

  it("click toggle calls onToggle", () => {
    const onToggle = vi.fn();
    render(<WBSTreeItem {...defaultProps} onToggle={onToggle} />);

    const toggle = screen.getByText("\u25B6");
    fireEvent.click(toggle);
    expect(onToggle).toHaveBeenCalledWith("elem-1");
  });

  it("click + calls onAddChild", () => {
    const onAddChild = vi.fn();
    render(<WBSTreeItem {...defaultProps} onAddChild={onAddChild} />);

    const addButton = screen.getByTitle("Add child element");
    fireEvent.click(addButton);
    expect(onAddChild).toHaveBeenCalledWith(elementWithChildren);
  });

  it("click edit calls onEdit", () => {
    const onEdit = vi.fn();
    render(<WBSTreeItem {...defaultProps} onEdit={onEdit} />);

    const editButton = screen.getByTitle("Edit element");
    fireEvent.click(editButton);
    expect(onEdit).toHaveBeenCalledWith(elementWithChildren);
  });

  it("click delete calls onDelete", () => {
    const onDelete = vi.fn();
    render(<WBSTreeItem {...defaultProps} onDelete={onDelete} />);

    const deleteButton = screen.getByTitle("Delete element");
    fireEvent.click(deleteButton);
    expect(onDelete).toHaveBeenCalledWith(elementWithChildren);
  });

  it("shows children when expanded (expandedIds contains id)", () => {
    const expandedIds = new Set(["elem-1"]);
    render(
      <WBSTreeItem {...defaultProps} expandedIds={expandedIds} />
    );

    expect(screen.getByText("Subsystem A")).toBeInTheDocument();
    expect(screen.getByText("1.1.1")).toBeInTheDocument();
  });

  it("hides children when collapsed", () => {
    render(
      <WBSTreeItem {...defaultProps} expandedIds={new Set()} />
    );

    expect(screen.queryByText("Subsystem A")).not.toBeInTheDocument();
    expect(screen.queryByText("1.1.1")).not.toBeInTheDocument();
  });

  it("selected element has 'selected' class", () => {
    render(
      <WBSTreeItem {...defaultProps} selectedId="elem-1" />
    );

    const row = document.querySelector(".wbs-tree-item-row")!;
    expect(row.classList.contains("selected")).toBe(true);
  });

  it("shows budget formatted as currency", () => {
    render(<WBSTreeItem {...defaultProps} />);
    expect(screen.getByText("$50,000")).toBeInTheDocument();
  });

  it("shows CA badge when isControlAccount", () => {
    render(
      <WBSTreeItem {...defaultProps} element={controlAccountElement} />
    );
    expect(screen.getByText("CA")).toBeInTheDocument();
  });
});
