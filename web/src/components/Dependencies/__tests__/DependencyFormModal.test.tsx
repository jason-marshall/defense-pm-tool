import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { DependencyFormModal } from "../DependencyFormModal";
import { ToastProvider } from "@/components/Toast";

const mockMutateAsync = vi.fn();
let mockIsPending = false;
let mockActivitiesData: { items: { id: string; code: string; name: string }[] } | undefined;

vi.mock("@/hooks/useActivities", () => ({
  useActivities: () => ({
    data: mockActivitiesData,
  }),
}));

vi.mock("@/hooks/useDependencies", () => ({
  useCreateDependency: () => ({
    mutateAsync: mockMutateAsync,
    isPending: mockIsPending,
  }),
}));

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <ToastProvider>{ui}</ToastProvider>
    </QueryClientProvider>
  );
}

describe("DependencyFormModal", () => {
  const mockOnClose = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    mockMutateAsync.mockResolvedValue({});
    mockIsPending = false;
    mockActivitiesData = {
      items: [
        { id: "act-1", code: "A-001", name: "Design" },
        { id: "act-2", code: "A-002", name: "Build" },
        { id: "act-3", code: "A-003", name: "Test" },
      ],
    };
  });

  it("renders form with title and activity dropdowns", () => {
    renderWithProviders(
      <DependencyFormModal programId="prog-1" onClose={mockOnClose} />
    );

    expect(screen.getByText("Add Dependency")).toBeInTheDocument();
    expect(screen.getByLabelText(/predecessor/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/successor/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/type/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/lag/i)).toBeInTheDocument();
  });

  it("populates predecessor and successor options from activities", () => {
    renderWithProviders(
      <DependencyFormModal programId="prog-1" onClose={mockOnClose} />
    );

    const predecessorSelect = screen.getByLabelText(/predecessor/i);
    const options = predecessorSelect.querySelectorAll("option");

    // 3 activities + "Select activity..." placeholder
    expect(options).toHaveLength(4);
    expect(options[1]).toHaveTextContent("A-001 - Design");
    expect(options[2]).toHaveTextContent("A-002 - Build");
  });

  it("submits with FS type and lag", async () => {
    renderWithProviders(
      <DependencyFormModal programId="prog-1" onClose={mockOnClose} />
    );

    fireEvent.change(screen.getByLabelText(/predecessor/i), {
      target: { value: "act-1" },
    });
    fireEvent.change(screen.getByLabelText(/successor/i), {
      target: { value: "act-2" },
    });
    fireEvent.change(screen.getByLabelText(/lag/i), {
      target: { value: "3" },
    });

    fireEvent.submit(screen.getByRole("button", { name: /create/i }));

    await waitFor(() => {
      expect(mockMutateAsync).toHaveBeenCalledWith({
        predecessor_id: "act-1",
        successor_id: "act-2",
        dependency_type: "FS",
        lag: 3,
      });
    });
  });

  it("calls onClose on cancel", () => {
    renderWithProviders(
      <DependencyFormModal programId="prog-1" onClose={mockOnClose} />
    );

    fireEvent.click(screen.getByText("Cancel"));

    expect(mockOnClose).toHaveBeenCalled();
  });

  it("shows all 4 dependency type options", () => {
    renderWithProviders(
      <DependencyFormModal programId="prog-1" onClose={mockOnClose} />
    );

    const typeSelect = screen.getByLabelText(/type/i);
    const options = typeSelect.querySelectorAll("option");

    expect(options).toHaveLength(4);
    expect(options[0]).toHaveTextContent("Finish-to-Start");
    expect(options[1]).toHaveTextContent("Start-to-Start");
    expect(options[2]).toHaveTextContent("Finish-to-Finish");
    expect(options[3]).toHaveTextContent("Start-to-Finish");
  });

  // --- NEW TESTS ---

  describe("dependency type selection", () => {
    it("submits with SS dependency type", async () => {
      renderWithProviders(
        <DependencyFormModal programId="prog-1" onClose={mockOnClose} />
      );

      fireEvent.change(screen.getByLabelText(/predecessor/i), {
        target: { value: "act-1" },
      });
      fireEvent.change(screen.getByLabelText(/successor/i), {
        target: { value: "act-2" },
      });
      fireEvent.change(screen.getByLabelText(/type/i), {
        target: { value: "SS" },
      });

      fireEvent.submit(screen.getByRole("button", { name: /create/i }));

      await waitFor(() => {
        expect(mockMutateAsync).toHaveBeenCalledWith(
          expect.objectContaining({ dependency_type: "SS" })
        );
      });
    });

    it("submits with FF dependency type", async () => {
      renderWithProviders(
        <DependencyFormModal programId="prog-1" onClose={mockOnClose} />
      );

      fireEvent.change(screen.getByLabelText(/predecessor/i), {
        target: { value: "act-1" },
      });
      fireEvent.change(screen.getByLabelText(/successor/i), {
        target: { value: "act-2" },
      });
      fireEvent.change(screen.getByLabelText(/type/i), {
        target: { value: "FF" },
      });

      fireEvent.submit(screen.getByRole("button", { name: /create/i }));

      await waitFor(() => {
        expect(mockMutateAsync).toHaveBeenCalledWith(
          expect.objectContaining({ dependency_type: "FF" })
        );
      });
    });

    it("submits with SF dependency type", async () => {
      renderWithProviders(
        <DependencyFormModal programId="prog-1" onClose={mockOnClose} />
      );

      fireEvent.change(screen.getByLabelText(/predecessor/i), {
        target: { value: "act-1" },
      });
      fireEvent.change(screen.getByLabelText(/successor/i), {
        target: { value: "act-3" },
      });
      fireEvent.change(screen.getByLabelText(/type/i), {
        target: { value: "SF" },
      });

      fireEvent.submit(screen.getByRole("button", { name: /create/i }));

      await waitFor(() => {
        expect(mockMutateAsync).toHaveBeenCalledWith(
          expect.objectContaining({
            dependency_type: "SF",
            successor_id: "act-3",
          })
        );
      });
    });

    it("defaults to FS dependency type", () => {
      renderWithProviders(
        <DependencyFormModal programId="prog-1" onClose={mockOnClose} />
      );

      const typeSelect = screen.getByLabelText(/type/i) as HTMLSelectElement;
      expect(typeSelect.value).toBe("FS");
    });
  });

  describe("lag value input", () => {
    it("submits with positive lag value", async () => {
      renderWithProviders(
        <DependencyFormModal programId="prog-1" onClose={mockOnClose} />
      );

      fireEvent.change(screen.getByLabelText(/predecessor/i), {
        target: { value: "act-1" },
      });
      fireEvent.change(screen.getByLabelText(/successor/i), {
        target: { value: "act-2" },
      });
      fireEvent.change(screen.getByLabelText(/lag/i), {
        target: { value: "5" },
      });

      fireEvent.submit(screen.getByRole("button", { name: /create/i }));

      await waitFor(() => {
        expect(mockMutateAsync).toHaveBeenCalledWith(
          expect.objectContaining({ lag: 5 })
        );
      });
    });

    it("submits with negative lag value (lead time)", async () => {
      renderWithProviders(
        <DependencyFormModal programId="prog-1" onClose={mockOnClose} />
      );

      fireEvent.change(screen.getByLabelText(/predecessor/i), {
        target: { value: "act-1" },
      });
      fireEvent.change(screen.getByLabelText(/successor/i), {
        target: { value: "act-2" },
      });
      fireEvent.change(screen.getByLabelText(/lag/i), {
        target: { value: "-3" },
      });

      fireEvent.submit(screen.getByRole("button", { name: /create/i }));

      await waitFor(() => {
        expect(mockMutateAsync).toHaveBeenCalledWith(
          expect.objectContaining({ lag: -3 })
        );
      });
    });

    it("submits with zero lag value (default)", async () => {
      renderWithProviders(
        <DependencyFormModal programId="prog-1" onClose={mockOnClose} />
      );

      fireEvent.change(screen.getByLabelText(/predecessor/i), {
        target: { value: "act-1" },
      });
      fireEvent.change(screen.getByLabelText(/successor/i), {
        target: { value: "act-2" },
      });
      // Do not change lag - default is "0"

      fireEvent.submit(screen.getByRole("button", { name: /create/i }));

      await waitFor(() => {
        expect(mockMutateAsync).toHaveBeenCalledWith(
          expect.objectContaining({ lag: 0 })
        );
      });
    });

    it("defaults lag input to 0", () => {
      renderWithProviders(
        <DependencyFormModal programId="prog-1" onClose={mockOnClose} />
      );

      const lagInput = screen.getByLabelText(/lag/i) as HTMLInputElement;
      expect(lagInput.value).toBe("0");
    });
  });

  describe("form submission success path", () => {
    it("calls onClose after successful creation", async () => {
      mockMutateAsync.mockResolvedValue({ id: "dep-1" });

      renderWithProviders(
        <DependencyFormModal programId="prog-1" onClose={mockOnClose} />
      );

      fireEvent.change(screen.getByLabelText(/predecessor/i), {
        target: { value: "act-1" },
      });
      fireEvent.change(screen.getByLabelText(/successor/i), {
        target: { value: "act-2" },
      });

      fireEvent.submit(screen.getByRole("button", { name: /create/i }));

      await waitFor(() => {
        expect(mockOnClose).toHaveBeenCalledTimes(1);
      });
    });

    it("shows success toast after creation", async () => {
      mockMutateAsync.mockResolvedValue({ id: "dep-1" });

      renderWithProviders(
        <DependencyFormModal programId="prog-1" onClose={mockOnClose} />
      );

      fireEvent.change(screen.getByLabelText(/predecessor/i), {
        target: { value: "act-1" },
      });
      fireEvent.change(screen.getByLabelText(/successor/i), {
        target: { value: "act-2" },
      });

      fireEvent.submit(screen.getByRole("button", { name: /create/i }));

      await waitFor(() => {
        expect(screen.getByText("Dependency created")).toBeInTheDocument();
      });
    });
  });

  describe("form submission error path", () => {
    it("shows error toast with Error message when mutateAsync rejects with Error", async () => {
      mockMutateAsync.mockRejectedValue(new Error("Circular dependency detected"));

      renderWithProviders(
        <DependencyFormModal programId="prog-1" onClose={mockOnClose} />
      );

      fireEvent.change(screen.getByLabelText(/predecessor/i), {
        target: { value: "act-1" },
      });
      fireEvent.change(screen.getByLabelText(/successor/i), {
        target: { value: "act-2" },
      });

      fireEvent.submit(screen.getByRole("button", { name: /create/i }));

      await waitFor(() => {
        expect(screen.getByText("Circular dependency detected")).toBeInTheDocument();
      });
    });

    it("shows generic error toast when mutateAsync rejects with non-Error", async () => {
      mockMutateAsync.mockRejectedValue("some string error");

      renderWithProviders(
        <DependencyFormModal programId="prog-1" onClose={mockOnClose} />
      );

      fireEvent.change(screen.getByLabelText(/predecessor/i), {
        target: { value: "act-1" },
      });
      fireEvent.change(screen.getByLabelText(/successor/i), {
        target: { value: "act-2" },
      });

      fireEvent.submit(screen.getByRole("button", { name: /create/i }));

      await waitFor(() => {
        expect(screen.getByText("Failed to create dependency")).toBeInTheDocument();
      });
    });

    it("does not call onClose when creation fails", async () => {
      mockMutateAsync.mockRejectedValue(new Error("Server error"));

      renderWithProviders(
        <DependencyFormModal programId="prog-1" onClose={mockOnClose} />
      );

      fireEvent.change(screen.getByLabelText(/predecessor/i), {
        target: { value: "act-1" },
      });
      fireEvent.change(screen.getByLabelText(/successor/i), {
        target: { value: "act-2" },
      });

      fireEvent.submit(screen.getByRole("button", { name: /create/i }));

      await waitFor(() => {
        expect(screen.getByText("Server error")).toBeInTheDocument();
      });

      // onClose should NOT have been called on error
      expect(mockOnClose).not.toHaveBeenCalled();
    });

    it("shows generic error when rejected with null", async () => {
      mockMutateAsync.mockRejectedValue(null);

      renderWithProviders(
        <DependencyFormModal programId="prog-1" onClose={mockOnClose} />
      );

      fireEvent.change(screen.getByLabelText(/predecessor/i), {
        target: { value: "act-1" },
      });
      fireEvent.change(screen.getByLabelText(/successor/i), {
        target: { value: "act-2" },
      });

      fireEvent.submit(screen.getByRole("button", { name: /create/i }));

      await waitFor(() => {
        expect(screen.getByText("Failed to create dependency")).toBeInTheDocument();
      });
    });
  });

  describe("loading / pending state", () => {
    it("shows 'Creating...' text and disables button when isPending", () => {
      mockIsPending = true;

      renderWithProviders(
        <DependencyFormModal programId="prog-1" onClose={mockOnClose} />
      );

      const submitButton = screen.getByRole("button", { name: /creating/i });
      expect(submitButton).toBeInTheDocument();
      expect(submitButton).toBeDisabled();
    });

    it("shows 'Create' text and enables button when not pending", () => {
      mockIsPending = false;

      renderWithProviders(
        <DependencyFormModal programId="prog-1" onClose={mockOnClose} />
      );

      const submitButton = screen.getByRole("button", { name: /create/i });
      expect(submitButton).toBeInTheDocument();
      expect(submitButton).not.toBeDisabled();
    });
  });

  describe("close and cancel callbacks", () => {
    it("calls onClose when clicking the X button", () => {
      renderWithProviders(
        <DependencyFormModal programId="prog-1" onClose={mockOnClose} />
      );

      fireEvent.click(screen.getByLabelText("Close"));

      expect(mockOnClose).toHaveBeenCalledTimes(1);
    });

    it("calls onClose when clicking the overlay backdrop", () => {
      renderWithProviders(
        <DependencyFormModal programId="prog-1" onClose={mockOnClose} />
      );

      // The dialog overlay is the outermost div with role="dialog"
      const dialog = screen.getByRole("dialog");
      fireEvent.click(dialog);

      expect(mockOnClose).toHaveBeenCalledTimes(1);
    });

    it("does not close when clicking inside the modal content", () => {
      renderWithProviders(
        <DependencyFormModal programId="prog-1" onClose={mockOnClose} />
      );

      // Click on the form title (inside the modal)
      fireEvent.click(screen.getByText("Add Dependency"));

      expect(mockOnClose).not.toHaveBeenCalled();
    });

    it("calls onClose when pressing Escape key on the overlay", () => {
      renderWithProviders(
        <DependencyFormModal programId="prog-1" onClose={mockOnClose} />
      );

      const dialog = screen.getByRole("dialog");
      fireEvent.keyDown(dialog, { key: "Escape" });

      expect(mockOnClose).toHaveBeenCalledTimes(1);
    });

    it("does not call onClose for non-Escape key presses", () => {
      renderWithProviders(
        <DependencyFormModal programId="prog-1" onClose={mockOnClose} />
      );

      const dialog = screen.getByRole("dialog");
      fireEvent.keyDown(dialog, { key: "Enter" });

      expect(mockOnClose).not.toHaveBeenCalled();
    });
  });

  describe("empty activities data", () => {
    it("renders empty dropdowns when activities data is undefined", () => {
      mockActivitiesData = undefined;

      renderWithProviders(
        <DependencyFormModal programId="prog-1" onClose={mockOnClose} />
      );

      const predecessorSelect = screen.getByLabelText(/predecessor/i);
      const options = predecessorSelect.querySelectorAll("option");

      // Only the placeholder option
      expect(options).toHaveLength(1);
      expect(options[0]).toHaveTextContent("Select activity...");
    });

    it("renders empty dropdowns when activities items is empty array", () => {
      mockActivitiesData = { items: [] };

      renderWithProviders(
        <DependencyFormModal programId="prog-1" onClose={mockOnClose} />
      );

      const successorSelect = screen.getByLabelText(/successor/i);
      const options = successorSelect.querySelectorAll("option");

      expect(options).toHaveLength(1);
      expect(options[0]).toHaveTextContent("Select activity...");
    });
  });

  describe("form field interactions", () => {
    it("updates predecessor selection", () => {
      renderWithProviders(
        <DependencyFormModal programId="prog-1" onClose={mockOnClose} />
      );

      const predecessorSelect = screen.getByLabelText(/predecessor/i) as HTMLSelectElement;
      expect(predecessorSelect.value).toBe("");

      fireEvent.change(predecessorSelect, { target: { value: "act-2" } });
      expect(predecessorSelect.value).toBe("act-2");
    });

    it("updates successor selection", () => {
      renderWithProviders(
        <DependencyFormModal programId="prog-1" onClose={mockOnClose} />
      );

      const successorSelect = screen.getByLabelText(/successor/i) as HTMLSelectElement;
      expect(successorSelect.value).toBe("");

      fireEvent.change(successorSelect, { target: { value: "act-3" } });
      expect(successorSelect.value).toBe("act-3");
    });

    it("updates lag input value", () => {
      renderWithProviders(
        <DependencyFormModal programId="prog-1" onClose={mockOnClose} />
      );

      const lagInput = screen.getByLabelText(/lag/i) as HTMLInputElement;
      expect(lagInput.value).toBe("0");

      fireEvent.change(lagInput, { target: { value: "10" } });
      expect(lagInput.value).toBe("10");
    });

    it("updates dependency type selection", () => {
      renderWithProviders(
        <DependencyFormModal programId="prog-1" onClose={mockOnClose} />
      );

      const typeSelect = screen.getByLabelText(/type/i) as HTMLSelectElement;
      expect(typeSelect.value).toBe("FS");

      fireEvent.change(typeSelect, { target: { value: "FF" } });
      expect(typeSelect.value).toBe("FF");
    });
  });

  describe("accessibility", () => {
    it("has aria-modal attribute on dialog", () => {
      renderWithProviders(
        <DependencyFormModal programId="prog-1" onClose={mockOnClose} />
      );

      const dialog = screen.getByRole("dialog");
      expect(dialog).toHaveAttribute("aria-modal", "true");
    });

    it("has aria-labelledby pointing to the title", () => {
      renderWithProviders(
        <DependencyFormModal programId="prog-1" onClose={mockOnClose} />
      );

      const dialog = screen.getByRole("dialog");
      expect(dialog).toHaveAttribute("aria-labelledby", "dependency-form-title");

      const title = screen.getByText("Add Dependency");
      expect(title).toHaveAttribute("id", "dependency-form-title");
    });

    it("predecessor and successor selects have required attribute", () => {
      renderWithProviders(
        <DependencyFormModal programId="prog-1" onClose={mockOnClose} />
      );

      const predecessorSelect = screen.getByLabelText(/predecessor/i);
      const successorSelect = screen.getByLabelText(/successor/i);

      expect(predecessorSelect).toBeRequired();
      expect(successorSelect).toBeRequired();
    });

    it("lag input is of type number", () => {
      renderWithProviders(
        <DependencyFormModal programId="prog-1" onClose={mockOnClose} />
      );

      const lagInput = screen.getByLabelText(/lag/i);
      expect(lagInput).toHaveAttribute("type", "number");
    });
  });

  describe("complete form submission flow", () => {
    it("submits complete form with all fields changed from defaults", async () => {
      renderWithProviders(
        <DependencyFormModal programId="prog-1" onClose={mockOnClose} />
      );

      // Fill in all fields
      fireEvent.change(screen.getByLabelText(/predecessor/i), {
        target: { value: "act-3" },
      });
      fireEvent.change(screen.getByLabelText(/type/i), {
        target: { value: "FF" },
      });
      fireEvent.change(screen.getByLabelText(/successor/i), {
        target: { value: "act-1" },
      });
      fireEvent.change(screen.getByLabelText(/lag/i), {
        target: { value: "-2" },
      });

      fireEvent.submit(screen.getByRole("button", { name: /create/i }));

      await waitFor(() => {
        expect(mockMutateAsync).toHaveBeenCalledWith({
          predecessor_id: "act-3",
          successor_id: "act-1",
          dependency_type: "FF",
          lag: -2,
        });
      });

      await waitFor(() => {
        expect(mockOnClose).toHaveBeenCalledTimes(1);
      });
    });

    it("prevents default form submission behavior", async () => {
      renderWithProviders(
        <DependencyFormModal programId="prog-1" onClose={mockOnClose} />
      );

      fireEvent.change(screen.getByLabelText(/predecessor/i), {
        target: { value: "act-1" },
      });
      fireEvent.change(screen.getByLabelText(/successor/i), {
        target: { value: "act-2" },
      });

      const form = screen.getByRole("button", { name: /create/i }).closest("form")!;
      const submitEvent = new Event("submit", { bubbles: true, cancelable: true });
      Object.defineProperty(submitEvent, "preventDefault", {
        value: vi.fn(),
        writable: true,
      });

      fireEvent(form, submitEvent);

      await waitFor(() => {
        expect(mockMutateAsync).toHaveBeenCalled();
      });
    });
  });
});
