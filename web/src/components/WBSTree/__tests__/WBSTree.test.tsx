import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { WBSTree } from "../WBSTree";

vi.mock("@/services/wbsApi", () => ({
  getWBSTree: vi.fn(),
  getWBSElements: vi.fn(),
  getWBSElement: vi.fn(),
  createWBSElement: vi.fn(),
  updateWBSElement: vi.fn(),
  deleteWBSElement: vi.fn(),
}));

import {
  getWBSTree,
  createWBSElement,
  updateWBSElement,
  deleteWBSElement,
} from "@/services/wbsApi";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false },
  },
});

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
);

const mockTree = [
  {
    id: "wbs-1",
    programId: "prog-1",
    parentId: null,
    code: "1.0",
    name: "Project Root",
    description: null,
    path: "1",
    level: 0,
    budgetedCost: "100000",
    createdAt: "2026-01-01T00:00:00Z",
    updatedAt: "2026-01-01T00:00:00Z",
    isControlAccount: false,
    children: [
      {
        id: "wbs-2",
        programId: "prog-1",
        parentId: "wbs-1",
        code: "1.1",
        name: "Design Phase",
        description: "Design activities",
        path: "1.1",
        level: 1,
        budgetedCost: "50000",
        createdAt: "2026-01-01T00:00:00Z",
        updatedAt: "2026-01-01T00:00:00Z",
        isControlAccount: true,
        children: [],
      },
      {
        id: "wbs-3",
        programId: "prog-1",
        parentId: "wbs-1",
        code: "1.2",
        name: "Build Phase",
        description: null,
        path: "1.2",
        level: 1,
        budgetedCost: "50000",
        createdAt: "2026-01-01T00:00:00Z",
        updatedAt: "2026-01-01T00:00:00Z",
        isControlAccount: false,
        children: [],
      },
    ],
  },
];

describe("WBSTree", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("renders loading state", () => {
    vi.mocked(getWBSTree).mockImplementation(() => new Promise(() => {}));

    render(<WBSTree programId="prog-1" />, { wrapper });

    expect(screen.getByText("Loading WBS hierarchy...")).toBeInTheDocument();
  });

  it("renders error state", async () => {
    vi.mocked(getWBSTree).mockRejectedValue(new Error("API Error"));

    render(<WBSTree programId="prog-1" />, { wrapper });

    expect(
      await screen.findByText(/Error loading WBS/)
    ).toBeInTheDocument();
  });

  it("renders empty state", async () => {
    vi.mocked(getWBSTree).mockResolvedValue([]);

    render(<WBSTree programId="prog-1" />, { wrapper });

    expect(
      await screen.findByText(/No WBS elements/)
    ).toBeInTheDocument();
  });

  it("renders tree with data", async () => {
    vi.mocked(getWBSTree).mockResolvedValue(mockTree);

    render(<WBSTree programId="prog-1" />, { wrapper });

    expect(await screen.findByText("Project Root")).toBeInTheDocument();
    expect(screen.getByText("1.0")).toBeInTheDocument();
  });

  it("calls onSelect when element is clicked", async () => {
    vi.mocked(getWBSTree).mockResolvedValue(mockTree);
    const onSelect = vi.fn();

    render(<WBSTree programId="prog-1" onSelect={onSelect} />, { wrapper });

    await screen.findByText("Project Root");
    fireEvent.click(screen.getByText("Project Root"));

    expect(onSelect).toHaveBeenCalledWith(
      expect.objectContaining({ id: "wbs-1", name: "Project Root" })
    );
  });

  it("opens add root modal when Add Root Element button is clicked", async () => {
    vi.mocked(getWBSTree).mockResolvedValue(mockTree);

    render(<WBSTree programId="prog-1" />, { wrapper });

    await screen.findByText("Project Root");

    // Look for the "Add Root Element" button in toolbar
    const addButtons = screen.getAllByRole("button");
    const addRootBtn = addButtons.find(
      (btn) => btn.textContent?.includes("Add Root") || btn.textContent?.includes("Add")
    );
    if (addRootBtn) {
      fireEvent.click(addRootBtn);
      expect(screen.getByText("Add Root Element")).toBeInTheDocument();
    }
  });

  it("submits add form with correct data", async () => {
    vi.mocked(getWBSTree).mockResolvedValue([]);
    vi.mocked(createWBSElement).mockResolvedValue({
      id: "new-1",
      programId: "prog-1",
      code: "1.0",
      name: "New Element",
      description: null,
      level: 0,
      budgetedCost: "0",
    } as any);

    render(<WBSTree programId="prog-1" />, { wrapper });

    await screen.findByText(/No WBS elements/);

    // Click add root button
    const addButtons = screen.getAllByRole("button");
    const addRootBtn = addButtons.find((btn) =>
      btn.textContent?.includes("Add Root")
    );
    if (addRootBtn) {
      fireEvent.click(addRootBtn);

      // Fill form
      fireEvent.change(screen.getByLabelText(/WBS Code/), {
        target: { value: "1.0" },
      });
      fireEvent.change(screen.getByLabelText(/Name \*/), {
        target: { value: "New Root" },
      });

      fireEvent.click(screen.getByText("Add Element"));

      await waitFor(() => {
        expect(createWBSElement).toHaveBeenCalled();
      });
    }
  });

  it("closes modal when cancel is clicked", async () => {
    vi.mocked(getWBSTree).mockResolvedValue([]);

    render(<WBSTree programId="prog-1" />, { wrapper });

    await screen.findByText(/No WBS elements/);

    const addButtons = screen.getAllByRole("button");
    const addRootBtn = addButtons.find((btn) =>
      btn.textContent?.includes("Add Root")
    );
    if (addRootBtn) {
      fireEvent.click(addRootBtn);
      expect(screen.getByText("Add Root Element")).toBeInTheDocument();

      fireEvent.click(screen.getByText("Cancel"));
      await waitFor(() => {
        expect(screen.queryByText("Add Root Element")).not.toBeInTheDocument();
      });
    }
  });

  // ============================================================
  // NEW TESTS: Expand/Collapse tree nodes
  // ============================================================

  describe("expand/collapse tree nodes", () => {
    it("expands a parent node to show children when toggle is clicked", async () => {
      vi.mocked(getWBSTree).mockResolvedValue(mockTree);

      render(<WBSTree programId="prog-1" />, { wrapper });

      await screen.findByText("Project Root");

      // Children should not be visible initially (not expanded)
      expect(screen.queryByText("Design Phase")).not.toBeInTheDocument();

      // Click the expand toggle (the triangle)
      const toggles = screen.getAllByText("▶");
      expect(toggles.length).toBeGreaterThan(0);
      fireEvent.click(toggles[0]);

      // Children should now be visible
      expect(screen.getByText("Design Phase")).toBeInTheDocument();
      expect(screen.getByText("Build Phase")).toBeInTheDocument();
    });

    it("collapses an expanded node to hide children", async () => {
      vi.mocked(getWBSTree).mockResolvedValue(mockTree);

      render(<WBSTree programId="prog-1" />, { wrapper });

      await screen.findByText("Project Root");

      // Expand first
      const expandToggle = screen.getByText("▶");
      fireEvent.click(expandToggle);

      expect(screen.getByText("Design Phase")).toBeInTheDocument();

      // Now collapse (toggle should be ▼ when expanded)
      const collapseToggle = screen.getByText("▼");
      fireEvent.click(collapseToggle);

      // Children should be hidden
      expect(screen.queryByText("Design Phase")).not.toBeInTheDocument();
    });

    it("expands all nodes when Expand All is clicked", async () => {
      vi.mocked(getWBSTree).mockResolvedValue(mockTree);

      render(<WBSTree programId="prog-1" />, { wrapper });

      await screen.findByText("Project Root");

      // Children should not be visible initially
      expect(screen.queryByText("Design Phase")).not.toBeInTheDocument();

      // Click Expand All
      fireEvent.click(screen.getByText("Expand All"));

      // All children should be visible
      expect(screen.getByText("Design Phase")).toBeInTheDocument();
      expect(screen.getByText("Build Phase")).toBeInTheDocument();
    });

    it("collapses all nodes when Collapse All is clicked", async () => {
      vi.mocked(getWBSTree).mockResolvedValue(mockTree);

      render(<WBSTree programId="prog-1" />, { wrapper });

      await screen.findByText("Project Root");

      // Expand first
      fireEvent.click(screen.getByText("Expand All"));
      expect(screen.getByText("Design Phase")).toBeInTheDocument();

      // Collapse All
      fireEvent.click(screen.getByText("Collapse All"));

      // Children should be hidden
      expect(screen.queryByText("Design Phase")).not.toBeInTheDocument();
    });

    it("disables Expand All and Collapse All when tree is empty", async () => {
      vi.mocked(getWBSTree).mockResolvedValue([]);

      render(<WBSTree programId="prog-1" />, { wrapper });

      await screen.findByText(/No WBS elements/);

      expect(screen.getByText("Expand All")).toBeDisabled();
      expect(screen.getByText("Collapse All")).toBeDisabled();
    });
  });

  // ============================================================
  // NEW TESTS: Add child WBS element
  // ============================================================

  describe("add child WBS element", () => {
    it("opens add child modal when add child button is clicked", async () => {
      vi.mocked(getWBSTree).mockResolvedValue(mockTree);

      render(<WBSTree programId="prog-1" />, { wrapper });

      await screen.findByText("Project Root");

      // Click the add child button for Project Root
      const addChildBtn = screen.getByLabelText("Add child to Project Root");
      fireEvent.click(addChildBtn);

      // Modal should show with parent name
      expect(screen.getByText('Add Child to "Project Root"')).toBeInTheDocument();
    });

    it("submits add child form and calls createWBSElement", async () => {
      vi.mocked(getWBSTree).mockResolvedValue(mockTree);
      vi.mocked(createWBSElement).mockResolvedValue({
        id: "new-child",
        programId: "prog-1",
        parentId: "wbs-1",
        code: "1.3",
        name: "Test Phase",
        description: null,
        level: 1,
        budgetedCost: "0",
      } as any);

      render(<WBSTree programId="prog-1" />, { wrapper });

      await screen.findByText("Project Root");

      // Click add child for root
      fireEvent.click(screen.getByLabelText("Add child to Project Root"));

      // Fill form fields
      fireEvent.change(screen.getByLabelText(/WBS Code/), {
        target: { value: "1.3" },
      });
      fireEvent.change(screen.getByLabelText(/Name \*/), {
        target: { value: "Test Phase" },
      });

      // Submit form
      fireEvent.click(screen.getByText("Add Element"));

      await waitFor(() => {
        expect(createWBSElement).toHaveBeenCalledWith(
          expect.objectContaining({
            programId: "prog-1",
            parentId: "wbs-1",
            wbsCode: "1.3",
            name: "Test Phase",
          })
        );
      });
    });

    it("fills in description and budgeted cost in add child form", async () => {
      vi.mocked(getWBSTree).mockResolvedValue(mockTree);
      vi.mocked(createWBSElement).mockResolvedValue({
        id: "new-child",
        programId: "prog-1",
        code: "1.4",
        name: "QA Phase",
        description: "Quality assurance",
        level: 1,
        budgetedCost: "25000",
      } as any);

      render(<WBSTree programId="prog-1" />, { wrapper });

      await screen.findByText("Project Root");

      fireEvent.click(screen.getByLabelText("Add child to Project Root"));

      fireEvent.change(screen.getByLabelText(/WBS Code/), {
        target: { value: "1.4" },
      });
      fireEvent.change(screen.getByLabelText(/Name \*/), {
        target: { value: "QA Phase" },
      });
      fireEvent.change(screen.getByLabelText(/Description/), {
        target: { value: "Quality assurance" },
      });
      fireEvent.change(screen.getByLabelText(/Budgeted Cost/), {
        target: { value: "25000" },
      });

      fireEvent.click(screen.getByText("Add Element"));

      await waitFor(() => {
        expect(createWBSElement).toHaveBeenCalledWith(
          expect.objectContaining({
            name: "QA Phase",
            description: "Quality assurance",
            budgetedCost: "25000",
          })
        );
      });
    });

    it("toggles control account checkbox in add form", async () => {
      vi.mocked(getWBSTree).mockResolvedValue(mockTree);
      vi.mocked(createWBSElement).mockResolvedValue({
        id: "new-child",
        programId: "prog-1",
        code: "1.5",
        name: "CA Element",
      } as any);

      render(<WBSTree programId="prog-1" />, { wrapper });

      await screen.findByText("Project Root");

      fireEvent.click(screen.getByLabelText("Add child to Project Root"));

      fireEvent.change(screen.getByLabelText(/WBS Code/), {
        target: { value: "1.5" },
      });
      fireEvent.change(screen.getByLabelText(/Name \*/), {
        target: { value: "CA Element" },
      });

      // Check the control account checkbox
      const checkbox = screen.getByLabelText("Control Account");
      fireEvent.click(checkbox);

      fireEvent.click(screen.getByText("Add Element"));

      await waitFor(() => {
        expect(createWBSElement).toHaveBeenCalledWith(
          expect.objectContaining({
            isControlAccount: true,
          })
        );
      });
    });
  });

  // ============================================================
  // NEW TESTS: Delete WBS element with confirmation
  // ============================================================

  describe("delete WBS element", () => {
    it("shows confirmation dialog and deletes when confirmed", async () => {
      vi.mocked(getWBSTree).mockResolvedValue(mockTree);
      vi.mocked(deleteWBSElement).mockResolvedValue(undefined);
      const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);

      render(<WBSTree programId="prog-1" />, { wrapper });

      await screen.findByText("Project Root");

      // Click the delete button for Project Root
      const deleteBtn = screen.getByLabelText("Delete Project Root");
      fireEvent.click(deleteBtn);

      expect(confirmSpy).toHaveBeenCalledWith(
        'Delete "Project Root" and all its children? This action cannot be undone.'
      );

      await waitFor(() => {
        expect(deleteWBSElement).toHaveBeenCalledWith("wbs-1");
      });

      confirmSpy.mockRestore();
    });

    it("does not delete when confirmation is cancelled", async () => {
      vi.mocked(getWBSTree).mockResolvedValue(mockTree);
      const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);

      render(<WBSTree programId="prog-1" />, { wrapper });

      await screen.findByText("Project Root");

      const deleteBtn = screen.getByLabelText("Delete Project Root");
      fireEvent.click(deleteBtn);

      expect(confirmSpy).toHaveBeenCalled();
      expect(deleteWBSElement).not.toHaveBeenCalled();

      confirmSpy.mockRestore();
    });

    it("deletes a child element after expanding parent", async () => {
      vi.mocked(getWBSTree).mockResolvedValue(mockTree);
      vi.mocked(deleteWBSElement).mockResolvedValue(undefined);
      const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);

      render(<WBSTree programId="prog-1" />, { wrapper });

      await screen.findByText("Project Root");

      // Expand to see children
      fireEvent.click(screen.getByText("Expand All"));

      expect(screen.getByText("Design Phase")).toBeInTheDocument();

      // Delete Design Phase
      const deleteBtn = screen.getByLabelText("Delete Design Phase");
      fireEvent.click(deleteBtn);

      expect(confirmSpy).toHaveBeenCalledWith(
        'Delete "Design Phase" and all its children? This action cannot be undone.'
      );

      await waitFor(() => {
        expect(deleteWBSElement).toHaveBeenCalledWith("wbs-2");
      });

      confirmSpy.mockRestore();
    });
  });

  // ============================================================
  // NEW TESTS: Edit WBS element
  // ============================================================

  describe("edit WBS element", () => {
    it("opens edit modal with pre-filled data when edit button is clicked", async () => {
      vi.mocked(getWBSTree).mockResolvedValue(mockTree);

      render(<WBSTree programId="prog-1" />, { wrapper });

      await screen.findByText("Project Root");

      // Click edit button for Project Root
      const editBtn = screen.getByLabelText("Edit Project Root");
      fireEvent.click(editBtn);

      // Modal title should reflect editing mode
      expect(screen.getByText('Edit "Project Root"')).toBeInTheDocument();

      // Form should be pre-filled with element data
      const nameInput = screen.getByLabelText(/Name \*/) as HTMLInputElement;
      expect(nameInput.value).toBe("Project Root");

      // Budgeted cost should be pre-filled
      const costInput = screen.getByLabelText(/Budgeted Cost/) as HTMLInputElement;
      expect(costInput.value).toBe("100000");
    });

    it("does not show WBS Code field in edit mode", async () => {
      vi.mocked(getWBSTree).mockResolvedValue(mockTree);

      render(<WBSTree programId="prog-1" />, { wrapper });

      await screen.findByText("Project Root");

      fireEvent.click(screen.getByLabelText("Edit Project Root"));

      // WBS Code field should not be visible in edit mode
      expect(screen.queryByLabelText(/WBS Code/)).not.toBeInTheDocument();
    });

    it("submits edit form and calls updateWBSElement", async () => {
      vi.mocked(getWBSTree).mockResolvedValue(mockTree);
      vi.mocked(updateWBSElement).mockResolvedValue({
        id: "wbs-1",
        name: "Updated Root",
      } as any);

      render(<WBSTree programId="prog-1" />, { wrapper });

      await screen.findByText("Project Root");

      // Click edit
      fireEvent.click(screen.getByLabelText("Edit Project Root"));

      // Change the name
      fireEvent.change(screen.getByLabelText(/Name \*/), {
        target: { value: "Updated Root" },
      });

      // Submit - button text should be "Save Changes" in edit mode
      fireEvent.click(screen.getByText("Save Changes"));

      await waitFor(() => {
        expect(updateWBSElement).toHaveBeenCalledWith(
          "wbs-1",
          expect.objectContaining({
            name: "Updated Root",
          })
        );
      });
    });

    it("edits a child element with correct pre-filled data", async () => {
      vi.mocked(getWBSTree).mockResolvedValue(mockTree);
      vi.mocked(updateWBSElement).mockResolvedValue({
        id: "wbs-2",
        name: "Updated Design",
      } as any);

      render(<WBSTree programId="prog-1" />, { wrapper });

      await screen.findByText("Project Root");

      // Expand to see children
      fireEvent.click(screen.getByText("Expand All"));

      // Click edit on Design Phase
      fireEvent.click(screen.getByLabelText("Edit Design Phase"));

      // Verify pre-filled data
      expect(screen.getByText('Edit "Design Phase"')).toBeInTheDocument();
      const nameInput = screen.getByLabelText(/Name \*/) as HTMLInputElement;
      expect(nameInput.value).toBe("Design Phase");

      const descInput = screen.getByLabelText(/Description/) as HTMLTextAreaElement;
      expect(descInput.value).toBe("Design activities");

      const costInput = screen.getByLabelText(/Budgeted Cost/) as HTMLInputElement;
      expect(costInput.value).toBe("50000");

      // Control account checkbox should be checked for Design Phase
      const caCheckbox = screen.getByLabelText("Control Account") as HTMLInputElement;
      expect(caCheckbox.checked).toBe(true);

      // Change name and submit
      fireEvent.change(nameInput, {
        target: { value: "Updated Design" },
      });
      fireEvent.click(screen.getByText("Save Changes"));

      await waitFor(() => {
        expect(updateWBSElement).toHaveBeenCalledWith(
          "wbs-2",
          expect.objectContaining({
            name: "Updated Design",
          })
        );
      });
    });

    it("closes edit modal after successful submission", async () => {
      vi.mocked(getWBSTree).mockResolvedValue(mockTree);
      vi.mocked(updateWBSElement).mockResolvedValue({
        id: "wbs-1",
        name: "Updated Root",
      } as any);

      render(<WBSTree programId="prog-1" />, { wrapper });

      await screen.findByText("Project Root");

      fireEvent.click(screen.getByLabelText("Edit Project Root"));
      expect(screen.getByText('Edit "Project Root"')).toBeInTheDocument();

      fireEvent.change(screen.getByLabelText(/Name \*/), {
        target: { value: "Updated Root" },
      });
      fireEvent.click(screen.getByText("Save Changes"));

      await waitFor(() => {
        expect(screen.queryByText('Edit "Project Root"')).not.toBeInTheDocument();
      });
    });
  });

  // ============================================================
  // NEW TESTS: Empty tree state
  // ============================================================

  describe("empty tree state", () => {
    it("shows helpful empty message with add instruction", async () => {
      vi.mocked(getWBSTree).mockResolvedValue([]);

      render(<WBSTree programId="prog-1" />, { wrapper });

      const emptyMessage = await screen.findByText(/No WBS elements/);
      expect(emptyMessage).toBeInTheDocument();
      expect(emptyMessage.textContent).toContain("Add Root Element");
    });

    it("allows adding root element from empty state", async () => {
      vi.mocked(getWBSTree).mockResolvedValue([]);
      vi.mocked(createWBSElement).mockResolvedValue({
        id: "new-root",
        programId: "prog-1",
        code: "1.0",
        name: "First Element",
      } as any);

      render(<WBSTree programId="prog-1" />, { wrapper });

      await screen.findByText(/No WBS elements/);

      // Add Root Element button should still be available
      const addRootBtn = screen.getAllByRole("button").find(
        (btn) => btn.textContent?.includes("Add Root")
      );
      expect(addRootBtn).toBeDefined();
      expect(addRootBtn).not.toBeDisabled();

      fireEvent.click(addRootBtn!);

      expect(screen.getByText("Add Root Element")).toBeInTheDocument();
      expect(screen.getByLabelText(/WBS Code/)).toBeInTheDocument();
      expect(screen.getByLabelText(/Name \*/)).toBeInTheDocument();
    });
  });

  // ============================================================
  // NEW TESTS: Error state
  // ============================================================

  describe("error state", () => {
    it("displays specific error message from API", async () => {
      vi.mocked(getWBSTree).mockRejectedValue(new Error("Network timeout"));

      render(<WBSTree programId="prog-1" />, { wrapper });

      const errorEl = await screen.findByText(/Error loading WBS/);
      expect(errorEl.textContent).toContain("Network timeout");
    });

    it("displays fallback message for unknown errors", async () => {
      vi.mocked(getWBSTree).mockRejectedValue("some string error");

      render(<WBSTree programId="prog-1" />, { wrapper });

      const errorEl = await screen.findByText(/Error loading WBS/);
      expect(errorEl.textContent).toContain("Unknown error");
    });
  });

  // ============================================================
  // NEW TESTS: Modal overlay behavior
  // ============================================================

  describe("modal overlay behavior", () => {
    it("closes modal when overlay is clicked", async () => {
      vi.mocked(getWBSTree).mockResolvedValue([]);

      render(<WBSTree programId="prog-1" />, { wrapper });

      await screen.findByText(/No WBS elements/);

      // Open modal
      const addRootBtn = screen.getAllByRole("button").find(
        (btn) => btn.textContent?.includes("Add Root")
      );
      fireEvent.click(addRootBtn!);
      expect(screen.getByText("Add Root Element")).toBeInTheDocument();

      // Click the overlay (the parent div)
      const overlay = document.querySelector(".wbs-modal-overlay");
      expect(overlay).not.toBeNull();
      fireEvent.click(overlay!);

      await waitFor(() => {
        expect(screen.queryByText("Add Root Element")).not.toBeInTheDocument();
      });
    });

    it("does not close modal when modal content is clicked", async () => {
      vi.mocked(getWBSTree).mockResolvedValue([]);

      render(<WBSTree programId="prog-1" />, { wrapper });

      await screen.findByText(/No WBS elements/);

      // Open modal
      const addRootBtn = screen.getAllByRole("button").find(
        (btn) => btn.textContent?.includes("Add Root")
      );
      fireEvent.click(addRootBtn!);
      expect(screen.getByText("Add Root Element")).toBeInTheDocument();

      // Click inside the modal content (not the overlay)
      const modalContent = document.querySelector(".wbs-modal");
      expect(modalContent).not.toBeNull();
      fireEvent.click(modalContent!);

      // Modal should still be open
      expect(screen.getByText("Add Root Element")).toBeInTheDocument();
    });
  });

  // ============================================================
  // NEW TESTS: Selection state
  // ============================================================

  describe("selection state", () => {
    it("highlights the selected element", async () => {
      vi.mocked(getWBSTree).mockResolvedValue(mockTree);

      render(<WBSTree programId="prog-1" />, { wrapper });

      await screen.findByText("Project Root");

      fireEvent.click(screen.getByText("Project Root"));

      // The row should have 'selected' class
      const row = screen.getByText("Project Root").closest(".wbs-tree-item-row");
      expect(row?.classList.contains("selected")).toBe(true);
    });

    it("changes selection when a different element is clicked", async () => {
      vi.mocked(getWBSTree).mockResolvedValue(mockTree);
      const onSelect = vi.fn();

      render(<WBSTree programId="prog-1" onSelect={onSelect} />, { wrapper });

      await screen.findByText("Project Root");

      // Select root first
      fireEvent.click(screen.getByText("Project Root"));
      expect(onSelect).toHaveBeenCalledWith(
        expect.objectContaining({ id: "wbs-1" })
      );

      // Expand to see children
      fireEvent.click(screen.getByText("Expand All"));

      // Select child
      fireEvent.click(screen.getByText("Design Phase"));
      expect(onSelect).toHaveBeenCalledWith(
        expect.objectContaining({ id: "wbs-2", name: "Design Phase" })
      );
    });
  });

  // ============================================================
  // NEW TESTS: Form change handling
  // ============================================================

  describe("form change handling", () => {
    it("updates all form fields correctly", async () => {
      vi.mocked(getWBSTree).mockResolvedValue([]);

      render(<WBSTree programId="prog-1" />, { wrapper });

      await screen.findByText(/No WBS elements/);

      // Open add modal
      const addRootBtn = screen.getAllByRole("button").find(
        (btn) => btn.textContent?.includes("Add Root")
      );
      fireEvent.click(addRootBtn!);

      // Change WBS Code
      const codeInput = screen.getByLabelText(/WBS Code/) as HTMLInputElement;
      fireEvent.change(codeInput, { target: { value: "2.0" } });
      expect(codeInput.value).toBe("2.0");

      // Change Name
      const nameInput = screen.getByLabelText(/Name \*/) as HTMLInputElement;
      fireEvent.change(nameInput, { target: { value: "New Name" } });
      expect(nameInput.value).toBe("New Name");

      // Change Description
      const descInput = screen.getByLabelText(/Description/) as HTMLTextAreaElement;
      fireEvent.change(descInput, { target: { value: "Some description" } });
      expect(descInput.value).toBe("Some description");

      // Change Budgeted Cost
      const costInput = screen.getByLabelText(/Budgeted Cost/) as HTMLInputElement;
      fireEvent.change(costInput, { target: { value: "50000" } });
      expect(costInput.value).toBe("50000");

      // Toggle checkbox
      const checkbox = screen.getByLabelText("Control Account") as HTMLInputElement;
      expect(checkbox.checked).toBe(false);
      fireEvent.click(checkbox);
      expect(checkbox.checked).toBe(true);
    });

    it("resets form data when modal is reopened", async () => {
      vi.mocked(getWBSTree).mockResolvedValue(mockTree);

      render(<WBSTree programId="prog-1" />, { wrapper });

      await screen.findByText("Project Root");

      // Open add child modal, fill in some data
      fireEvent.click(screen.getByLabelText("Add child to Project Root"));
      fireEvent.change(screen.getByLabelText(/WBS Code/), {
        target: { value: "1.99" },
      });

      // Cancel
      fireEvent.click(screen.getByText("Cancel"));

      // Reopen
      fireEvent.click(screen.getByLabelText("Add child to Project Root"));

      // Form should be reset
      const codeInput = screen.getByLabelText(/WBS Code/) as HTMLInputElement;
      expect(codeInput.value).toBe("");
    });
  });
});
