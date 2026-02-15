import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ActivityFormModal } from "../ActivityFormModal";
import { ToastProvider } from "@/components/Toast";

const mockMutateAsyncCreate = vi.fn();
const mockMutateAsyncUpdate = vi.fn();

let mockCreateIsPending = false;
let mockUpdateIsPending = false;

vi.mock("@/hooks/useActivities", () => ({
  useCreateActivity: () => ({
    mutateAsync: mockMutateAsyncCreate,
    isPending: mockCreateIsPending,
  }),
  useUpdateActivity: () => ({
    mutateAsync: mockMutateAsyncUpdate,
    isPending: mockUpdateIsPending,
  }),
}));

const mockActivity = {
  id: "act-1",
  program_id: "prog-1",
  name: "Design Review",
  code: "DR-001",
  description: "Review the design docs",
  duration: 10,
  remaining_duration: null,
  percent_complete: "50",
  budgeted_cost: "10000",
  is_milestone: false,
  actual_cost: "5000",
  wbs_id: null,
  constraint_type: null,
  constraint_date: null,
  early_start: null,
  early_finish: null,
  late_start: null,
  late_finish: null,
  total_float: null,
  free_float: null,
  is_critical: false,
  actual_start: null,
  actual_finish: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: null,
};

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

describe("ActivityFormModal", () => {
  const mockOnClose = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    mockMutateAsyncCreate.mockResolvedValue(mockActivity);
    mockMutateAsyncUpdate.mockResolvedValue(mockActivity);
    mockCreateIsPending = false;
    mockUpdateIsPending = false;
  });

  it("renders create mode title when no activity provided", () => {
    renderWithProviders(
      <ActivityFormModal programId="prog-1" onClose={mockOnClose} />
    );

    expect(screen.getByText("Create Activity")).toBeInTheDocument();
    expect(screen.getByText("Create")).toBeInTheDocument();
  });

  it("renders edit mode with pre-filled fields", () => {
    renderWithProviders(
      <ActivityFormModal
        programId="prog-1"
        activity={mockActivity}
        onClose={mockOnClose}
      />
    );

    expect(screen.getByText("Edit Activity")).toBeInTheDocument();
    expect(screen.getByText("Update")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Design Review")).toBeInTheDocument();
    expect(screen.getByDisplayValue("DR-001")).toBeInTheDocument();
  });

  it("submits create form", async () => {
    renderWithProviders(
      <ActivityFormModal programId="prog-1" onClose={mockOnClose} />
    );

    fireEvent.change(screen.getByLabelText(/name/i), {
      target: { value: "New Task" },
    });
    fireEvent.change(screen.getByLabelText(/code/i), {
      target: { value: "NT-001" },
    });
    fireEvent.submit(screen.getByRole("button", { name: /create/i }));

    await waitFor(() => {
      expect(mockMutateAsyncCreate).toHaveBeenCalledWith(
        expect.objectContaining({
          program_id: "prog-1",
          name: "New Task",
          code: "NT-001",
        })
      );
    });
  });

  it("submits edit form", async () => {
    renderWithProviders(
      <ActivityFormModal
        programId="prog-1"
        activity={mockActivity}
        onClose={mockOnClose}
      />
    );

    fireEvent.change(screen.getByLabelText(/name/i), {
      target: { value: "Updated Review" },
    });
    fireEvent.submit(screen.getByRole("button", { name: /update/i }));

    await waitFor(() => {
      expect(mockMutateAsyncUpdate).toHaveBeenCalledWith(
        expect.objectContaining({
          id: "act-1",
          data: expect.objectContaining({ name: "Updated Review" }),
        })
      );
    });
  });

  it("calls onClose on cancel", () => {
    renderWithProviders(
      <ActivityFormModal programId="prog-1" onClose={mockOnClose} />
    );

    fireEvent.click(screen.getByText("Cancel"));

    expect(mockOnClose).toHaveBeenCalled();
  });

  it("renders all form fields", () => {
    renderWithProviders(
      <ActivityFormModal programId="prog-1" onClose={mockOnClose} />
    );

    expect(screen.getByLabelText(/name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/code/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/description/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/duration \(days\)/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/% complete/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/budget/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/milestone/i)).toBeInTheDocument();
  });

  // ==========================================
  // New tests below
  // ==========================================

  describe("onSubmit success path", () => {
    it("calls onClose after successful create", async () => {
      renderWithProviders(
        <ActivityFormModal programId="prog-1" onClose={mockOnClose} />
      );

      fireEvent.change(screen.getByLabelText(/name \*/i), {
        target: { value: "Task A" },
      });
      fireEvent.change(screen.getByLabelText(/code \*/i), {
        target: { value: "TA-001" },
      });
      fireEvent.submit(screen.getByRole("button", { name: /create/i }));

      await waitFor(() => {
        expect(mockOnClose).toHaveBeenCalledTimes(1);
      });
    });

    it("shows success toast after create", async () => {
      renderWithProviders(
        <ActivityFormModal programId="prog-1" onClose={mockOnClose} />
      );

      fireEvent.change(screen.getByLabelText(/name \*/i), {
        target: { value: "Task B" },
      });
      fireEvent.change(screen.getByLabelText(/code \*/i), {
        target: { value: "TB-001" },
      });
      fireEvent.submit(screen.getByRole("button", { name: /create/i }));

      await waitFor(() => {
        expect(screen.getByText("Activity created")).toBeInTheDocument();
      });
    });

    it("calls onClose after successful update", async () => {
      renderWithProviders(
        <ActivityFormModal
          programId="prog-1"
          activity={mockActivity}
          onClose={mockOnClose}
        />
      );

      fireEvent.submit(screen.getByRole("button", { name: /update/i }));

      await waitFor(() => {
        expect(mockOnClose).toHaveBeenCalledTimes(1);
      });
    });

    it("shows success toast after update", async () => {
      renderWithProviders(
        <ActivityFormModal
          programId="prog-1"
          activity={mockActivity}
          onClose={mockOnClose}
        />
      );

      fireEvent.submit(screen.getByRole("button", { name: /update/i }));

      await waitFor(() => {
        expect(screen.getByText("Activity updated")).toBeInTheDocument();
      });
    });
  });

  describe("onSubmit error path", () => {
    it("shows error toast when create fails", async () => {
      mockMutateAsyncCreate.mockRejectedValueOnce(new Error("Network error"));

      renderWithProviders(
        <ActivityFormModal programId="prog-1" onClose={mockOnClose} />
      );

      fireEvent.change(screen.getByLabelText(/name \*/i), {
        target: { value: "Fail Task" },
      });
      fireEvent.change(screen.getByLabelText(/code \*/i), {
        target: { value: "FT-001" },
      });
      fireEvent.submit(screen.getByRole("button", { name: /create/i }));

      await waitFor(() => {
        expect(screen.getByText("Failed to save activity")).toBeInTheDocument();
      });
    });

    it("does not call onClose when create fails", async () => {
      mockMutateAsyncCreate.mockRejectedValueOnce(new Error("Server error"));

      renderWithProviders(
        <ActivityFormModal programId="prog-1" onClose={mockOnClose} />
      );

      fireEvent.change(screen.getByLabelText(/name \*/i), {
        target: { value: "Fail Task" },
      });
      fireEvent.change(screen.getByLabelText(/code \*/i), {
        target: { value: "FT-001" },
      });
      fireEvent.submit(screen.getByRole("button", { name: /create/i }));

      await waitFor(() => {
        expect(
          screen.getByText("Failed to save activity")
        ).toBeInTheDocument();
      });
      expect(mockOnClose).not.toHaveBeenCalled();
    });

    it("shows error toast when update fails", async () => {
      mockMutateAsyncUpdate.mockRejectedValueOnce(
        new Error("Update failed")
      );

      renderWithProviders(
        <ActivityFormModal
          programId="prog-1"
          activity={mockActivity}
          onClose={mockOnClose}
        />
      );

      fireEvent.submit(screen.getByRole("button", { name: /update/i }));

      await waitFor(() => {
        expect(screen.getByText("Failed to save activity")).toBeInTheDocument();
      });
    });

    it("does not call onClose when update fails", async () => {
      mockMutateAsyncUpdate.mockRejectedValueOnce(
        new Error("Update failed")
      );

      renderWithProviders(
        <ActivityFormModal
          programId="prog-1"
          activity={mockActivity}
          onClose={mockOnClose}
        />
      );

      fireEvent.submit(screen.getByRole("button", { name: /update/i }));

      await waitFor(() => {
        expect(
          screen.getByText("Failed to save activity")
        ).toBeInTheDocument();
      });
      expect(mockOnClose).not.toHaveBeenCalled();
    });
  });

  describe("edit mode pre-filled data", () => {
    it("populates description field from activity", () => {
      renderWithProviders(
        <ActivityFormModal
          programId="prog-1"
          activity={mockActivity}
          onClose={mockOnClose}
        />
      );

      expect(
        screen.getByDisplayValue("Review the design docs")
      ).toBeInTheDocument();
    });

    it("populates duration field from activity", () => {
      renderWithProviders(
        <ActivityFormModal
          programId="prog-1"
          activity={mockActivity}
          onClose={mockOnClose}
        />
      );

      expect(screen.getByDisplayValue("10")).toBeInTheDocument();
    });

    it("populates percent complete field from activity", () => {
      renderWithProviders(
        <ActivityFormModal
          programId="prog-1"
          activity={mockActivity}
          onClose={mockOnClose}
        />
      );

      expect(screen.getByDisplayValue("50")).toBeInTheDocument();
    });

    it("populates budgeted cost field from activity", () => {
      renderWithProviders(
        <ActivityFormModal
          programId="prog-1"
          activity={mockActivity}
          onClose={mockOnClose}
        />
      );

      expect(screen.getByDisplayValue("10000")).toBeInTheDocument();
    });

    it("sets milestone checkbox from activity", () => {
      const milestoneActivity = { ...mockActivity, is_milestone: true };

      renderWithProviders(
        <ActivityFormModal
          programId="prog-1"
          activity={milestoneActivity}
          onClose={mockOnClose}
        />
      );

      const checkbox = screen.getByLabelText(
        /milestone/i
      ) as HTMLInputElement;
      expect(checkbox.checked).toBe(true);
    });

    it("leaves milestone unchecked when activity is not milestone", () => {
      renderWithProviders(
        <ActivityFormModal
          programId="prog-1"
          activity={mockActivity}
          onClose={mockOnClose}
        />
      );

      const checkbox = screen.getByLabelText(
        /milestone/i
      ) as HTMLInputElement;
      expect(checkbox.checked).toBe(false);
    });

    it("handles activity with null description", () => {
      const noDescActivity = { ...mockActivity, description: null };

      renderWithProviders(
        <ActivityFormModal
          programId="prog-1"
          activity={noDescActivity}
          onClose={mockOnClose}
        />
      );

      const descField = screen.getByLabelText(
        /description/i
      ) as HTMLTextAreaElement;
      expect(descField.value).toBe("");
    });

    it("handles activity with empty budgeted_cost", () => {
      const noBudgetActivity = { ...mockActivity, budgeted_cost: "" };

      renderWithProviders(
        <ActivityFormModal
          programId="prog-1"
          activity={noBudgetActivity}
          onClose={mockOnClose}
        />
      );

      const budgetField = screen.getByLabelText(
        /budget/i
      ) as HTMLInputElement;
      expect(budgetField.value).toBe("");
    });
  });

  describe("duration input changes", () => {
    it("updates duration value on change", async () => {
      renderWithProviders(
        <ActivityFormModal programId="prog-1" onClose={mockOnClose} />
      );

      const durationInput = screen.getByLabelText(
        /duration \(days\)/i
      ) as HTMLInputElement;
      expect(durationInput.value).toBe("5"); // default value

      fireEvent.change(durationInput, { target: { value: "15" } });
      expect(durationInput.value).toBe("15");
    });

    it("submits with changed duration value", async () => {
      renderWithProviders(
        <ActivityFormModal programId="prog-1" onClose={mockOnClose} />
      );

      fireEvent.change(screen.getByLabelText(/name \*/i), {
        target: { value: "Duration Task" },
      });
      fireEvent.change(screen.getByLabelText(/code \*/i), {
        target: { value: "DT-001" },
      });
      fireEvent.change(screen.getByLabelText(/duration \(days\)/i), {
        target: { value: "20" },
      });
      fireEvent.submit(screen.getByRole("button", { name: /create/i }));

      await waitFor(() => {
        expect(mockMutateAsyncCreate).toHaveBeenCalledWith(
          expect.objectContaining({
            duration: 20,
          })
        );
      });
    });

    it("passes duration as a number (not a string)", async () => {
      renderWithProviders(
        <ActivityFormModal programId="prog-1" onClose={mockOnClose} />
      );

      fireEvent.change(screen.getByLabelText(/name \*/i), {
        target: { value: "Num Task" },
      });
      fireEvent.change(screen.getByLabelText(/code \*/i), {
        target: { value: "NUM-001" },
      });
      fireEvent.change(screen.getByLabelText(/duration \(days\)/i), {
        target: { value: "7" },
      });
      fireEvent.submit(screen.getByRole("button", { name: /create/i }));

      await waitFor(() => {
        const call = mockMutateAsyncCreate.mock.calls[0][0];
        expect(typeof call.duration).toBe("number");
        expect(call.duration).toBe(7);
      });
    });
  });

  describe("cost field input", () => {
    it("updates budget value on change", () => {
      renderWithProviders(
        <ActivityFormModal programId="prog-1" onClose={mockOnClose} />
      );

      const budgetInput = screen.getByLabelText(
        /budget/i
      ) as HTMLInputElement;
      expect(budgetInput.value).toBe(""); // default empty

      fireEvent.change(budgetInput, { target: { value: "25000" } });
      expect(budgetInput.value).toBe("25000");
    });

    it("submits with budgeted_cost when provided", async () => {
      renderWithProviders(
        <ActivityFormModal programId="prog-1" onClose={mockOnClose} />
      );

      fireEvent.change(screen.getByLabelText(/name \*/i), {
        target: { value: "Budget Task" },
      });
      fireEvent.change(screen.getByLabelText(/code \*/i), {
        target: { value: "BT-001" },
      });
      fireEvent.change(screen.getByLabelText(/budget/i), {
        target: { value: "50000.50" },
      });
      fireEvent.submit(screen.getByRole("button", { name: /create/i }));

      await waitFor(() => {
        expect(mockMutateAsyncCreate).toHaveBeenCalledWith(
          expect.objectContaining({
            budgeted_cost: "50000.50",
          })
        );
      });
    });

    it("sends undefined for budgeted_cost when empty", async () => {
      renderWithProviders(
        <ActivityFormModal programId="prog-1" onClose={mockOnClose} />
      );

      fireEvent.change(screen.getByLabelText(/name \*/i), {
        target: { value: "No Budget" },
      });
      fireEvent.change(screen.getByLabelText(/code \*/i), {
        target: { value: "NB-001" },
      });
      // Leave budget empty (default)
      fireEvent.submit(screen.getByRole("button", { name: /create/i }));

      await waitFor(() => {
        const call = mockMutateAsyncCreate.mock.calls[0][0];
        expect(call.budgeted_cost).toBeUndefined();
      });
    });
  });

  describe("milestone toggle", () => {
    it("defaults to unchecked in create mode", () => {
      renderWithProviders(
        <ActivityFormModal programId="prog-1" onClose={mockOnClose} />
      );

      const checkbox = screen.getByLabelText(
        /milestone/i
      ) as HTMLInputElement;
      expect(checkbox.checked).toBe(false);
    });

    it("toggles milestone checkbox on click", async () => {
      const user = userEvent.setup();
      renderWithProviders(
        <ActivityFormModal programId="prog-1" onClose={mockOnClose} />
      );

      const checkbox = screen.getByLabelText(
        /milestone/i
      ) as HTMLInputElement;
      expect(checkbox.checked).toBe(false);

      await user.click(checkbox);
      expect(checkbox.checked).toBe(true);

      await user.click(checkbox);
      expect(checkbox.checked).toBe(false);
    });

    it("submits with is_milestone true when checked", async () => {
      const user = userEvent.setup();
      renderWithProviders(
        <ActivityFormModal programId="prog-1" onClose={mockOnClose} />
      );

      fireEvent.change(screen.getByLabelText(/name \*/i), {
        target: { value: "Milestone Event" },
      });
      fireEvent.change(screen.getByLabelText(/code \*/i), {
        target: { value: "ME-001" },
      });
      await user.click(screen.getByLabelText(/milestone/i));
      fireEvent.submit(screen.getByRole("button", { name: /create/i }));

      await waitFor(() => {
        expect(mockMutateAsyncCreate).toHaveBeenCalledWith(
          expect.objectContaining({
            is_milestone: true,
          })
        );
      });
    });

    it("submits with is_milestone false when unchecked", async () => {
      renderWithProviders(
        <ActivityFormModal programId="prog-1" onClose={mockOnClose} />
      );

      fireEvent.change(screen.getByLabelText(/name \*/i), {
        target: { value: "Regular Task" },
      });
      fireEvent.change(screen.getByLabelText(/code \*/i), {
        target: { value: "RT-001" },
      });
      fireEvent.submit(screen.getByRole("button", { name: /create/i }));

      await waitFor(() => {
        expect(mockMutateAsyncCreate).toHaveBeenCalledWith(
          expect.objectContaining({
            is_milestone: false,
          })
        );
      });
    });
  });

  describe("cancel and close callbacks", () => {
    it("calls onClose when Cancel button is clicked", () => {
      renderWithProviders(
        <ActivityFormModal programId="prog-1" onClose={mockOnClose} />
      );

      fireEvent.click(screen.getByText("Cancel"));
      expect(mockOnClose).toHaveBeenCalledTimes(1);
    });

    it("calls onClose when X button is clicked", () => {
      renderWithProviders(
        <ActivityFormModal programId="prog-1" onClose={mockOnClose} />
      );

      fireEvent.click(screen.getByLabelText("Close"));
      expect(mockOnClose).toHaveBeenCalledTimes(1);
    });

    it("calls onClose when backdrop is clicked", () => {
      renderWithProviders(
        <ActivityFormModal programId="prog-1" onClose={mockOnClose} />
      );

      fireEvent.click(screen.getByRole("dialog"));
      expect(mockOnClose).toHaveBeenCalledTimes(1);
    });

    it("does not call onClose when modal content is clicked", () => {
      renderWithProviders(
        <ActivityFormModal programId="prog-1" onClose={mockOnClose} />
      );

      // Click inside the form content area (the inner div stops propagation)
      fireEvent.click(screen.getByLabelText(/name \*/i));
      expect(mockOnClose).not.toHaveBeenCalled();
    });

    it("calls onClose when Escape key is pressed", () => {
      renderWithProviders(
        <ActivityFormModal programId="prog-1" onClose={mockOnClose} />
      );

      fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape" });
      expect(mockOnClose).toHaveBeenCalledTimes(1);
    });

    it("does not call onClose for non-Escape keys", () => {
      renderWithProviders(
        <ActivityFormModal programId="prog-1" onClose={mockOnClose} />
      );

      fireEvent.keyDown(screen.getByRole("dialog"), { key: "Enter" });
      expect(mockOnClose).not.toHaveBeenCalled();
    });
  });

  describe("percent complete field", () => {
    it("defaults to 0 in create mode", () => {
      renderWithProviders(
        <ActivityFormModal programId="prog-1" onClose={mockOnClose} />
      );

      const pctInput = screen.getByLabelText(
        /% complete/i
      ) as HTMLInputElement;
      expect(pctInput.value).toBe("0");
    });

    it("updates percent complete on change", () => {
      renderWithProviders(
        <ActivityFormModal programId="prog-1" onClose={mockOnClose} />
      );

      const pctInput = screen.getByLabelText(
        /% complete/i
      ) as HTMLInputElement;
      fireEvent.change(pctInput, { target: { value: "75" } });
      expect(pctInput.value).toBe("75");
    });

    it("submits with updated percent_complete", async () => {
      renderWithProviders(
        <ActivityFormModal programId="prog-1" onClose={mockOnClose} />
      );

      fireEvent.change(screen.getByLabelText(/name \*/i), {
        target: { value: "Pct Task" },
      });
      fireEvent.change(screen.getByLabelText(/code \*/i), {
        target: { value: "PCT-001" },
      });
      fireEvent.change(screen.getByLabelText(/% complete/i), {
        target: { value: "30" },
      });
      fireEvent.submit(screen.getByRole("button", { name: /create/i }));

      await waitFor(() => {
        expect(mockMutateAsyncCreate).toHaveBeenCalledWith(
          expect.objectContaining({
            percent_complete: "30",
          })
        );
      });
    });
  });

  describe("description field", () => {
    it("defaults to empty in create mode", () => {
      renderWithProviders(
        <ActivityFormModal programId="prog-1" onClose={mockOnClose} />
      );

      const descField = screen.getByLabelText(
        /description/i
      ) as HTMLTextAreaElement;
      expect(descField.value).toBe("");
    });

    it("updates description on change", () => {
      renderWithProviders(
        <ActivityFormModal programId="prog-1" onClose={mockOnClose} />
      );

      const descField = screen.getByLabelText(
        /description/i
      ) as HTMLTextAreaElement;
      fireEvent.change(descField, {
        target: { value: "A detailed description" },
      });
      expect(descField.value).toBe("A detailed description");
    });

    it("submits with description when provided", async () => {
      renderWithProviders(
        <ActivityFormModal programId="prog-1" onClose={mockOnClose} />
      );

      fireEvent.change(screen.getByLabelText(/name \*/i), {
        target: { value: "Desc Task" },
      });
      fireEvent.change(screen.getByLabelText(/code \*/i), {
        target: { value: "DESC-001" },
      });
      fireEvent.change(screen.getByLabelText(/description/i), {
        target: { value: "Some description" },
      });
      fireEvent.submit(screen.getByRole("button", { name: /create/i }));

      await waitFor(() => {
        expect(mockMutateAsyncCreate).toHaveBeenCalledWith(
          expect.objectContaining({
            description: "Some description",
          })
        );
      });
    });

    it("sends undefined for description when empty", async () => {
      renderWithProviders(
        <ActivityFormModal programId="prog-1" onClose={mockOnClose} />
      );

      fireEvent.change(screen.getByLabelText(/name \*/i), {
        target: { value: "No Desc" },
      });
      fireEvent.change(screen.getByLabelText(/code \*/i), {
        target: { value: "ND-001" },
      });
      // Leave description empty
      fireEvent.submit(screen.getByRole("button", { name: /create/i }));

      await waitFor(() => {
        const call = mockMutateAsyncCreate.mock.calls[0][0];
        expect(call.description).toBeUndefined();
      });
    });
  });

  describe("pending state", () => {
    it("shows Saving text when create is pending", () => {
      mockCreateIsPending = true;

      renderWithProviders(
        <ActivityFormModal programId="prog-1" onClose={mockOnClose} />
      );

      expect(screen.getByText("Saving...")).toBeInTheDocument();
    });

    it("shows Saving text when update is pending", () => {
      mockUpdateIsPending = true;

      renderWithProviders(
        <ActivityFormModal
          programId="prog-1"
          activity={mockActivity}
          onClose={mockOnClose}
        />
      );

      expect(screen.getByText("Saving...")).toBeInTheDocument();
    });

    it("disables submit button when pending", () => {
      mockCreateIsPending = true;

      renderWithProviders(
        <ActivityFormModal programId="prog-1" onClose={mockOnClose} />
      );

      const submitBtn = screen.getByText("Saving...");
      expect(submitBtn).toBeDisabled();
    });

    it("submit button is enabled when not pending", () => {
      renderWithProviders(
        <ActivityFormModal programId="prog-1" onClose={mockOnClose} />
      );

      const submitBtn = screen.getByRole("button", { name: /create/i });
      expect(submitBtn).not.toBeDisabled();
    });
  });

  describe("full create payload", () => {
    it("sends complete payload with all fields filled", async () => {
      const user = userEvent.setup();
      renderWithProviders(
        <ActivityFormModal programId="prog-1" onClose={mockOnClose} />
      );

      fireEvent.change(screen.getByLabelText(/name \*/i), {
        target: { value: "Complete Task" },
      });
      fireEvent.change(screen.getByLabelText(/code \*/i), {
        target: { value: "CT-001" },
      });
      fireEvent.change(screen.getByLabelText(/description/i), {
        target: { value: "Full description" },
      });
      fireEvent.change(screen.getByLabelText(/duration \(days\)/i), {
        target: { value: "30" },
      });
      fireEvent.change(screen.getByLabelText(/% complete/i), {
        target: { value: "25" },
      });
      fireEvent.change(screen.getByLabelText(/budget/i), {
        target: { value: "99999.99" },
      });
      await user.click(screen.getByLabelText(/milestone/i));

      fireEvent.submit(screen.getByRole("button", { name: /create/i }));

      await waitFor(() => {
        expect(mockMutateAsyncCreate).toHaveBeenCalledWith({
          program_id: "prog-1",
          name: "Complete Task",
          code: "CT-001",
          description: "Full description",
          duration: 30,
          percent_complete: "25",
          budgeted_cost: "99999.99",
          is_milestone: true,
        });
      });
    });
  });

  describe("full update payload", () => {
    it("sends complete update payload", async () => {
      renderWithProviders(
        <ActivityFormModal
          programId="prog-1"
          activity={mockActivity}
          onClose={mockOnClose}
        />
      );

      fireEvent.change(screen.getByLabelText(/name \*/i), {
        target: { value: "Changed Name" },
      });
      fireEvent.change(screen.getByLabelText(/code \*/i), {
        target: { value: "CN-002" },
      });
      fireEvent.change(screen.getByLabelText(/description/i), {
        target: { value: "Updated desc" },
      });
      fireEvent.change(screen.getByLabelText(/duration \(days\)/i), {
        target: { value: "15" },
      });
      fireEvent.change(screen.getByLabelText(/% complete/i), {
        target: { value: "80" },
      });
      fireEvent.change(screen.getByLabelText(/budget/i), {
        target: { value: "20000" },
      });

      fireEvent.submit(screen.getByRole("button", { name: /update/i }));

      await waitFor(() => {
        expect(mockMutateAsyncUpdate).toHaveBeenCalledWith({
          id: "act-1",
          data: {
            name: "Changed Name",
            code: "CN-002",
            description: "Updated desc",
            duration: 15,
            percent_complete: "80",
            budgeted_cost: "20000",
            is_milestone: false,
          },
        });
      });
    });
  });

  describe("accessibility", () => {
    it("has role=dialog and aria-modal", () => {
      renderWithProviders(
        <ActivityFormModal programId="prog-1" onClose={mockOnClose} />
      );

      const dialog = screen.getByRole("dialog");
      expect(dialog).toHaveAttribute("aria-modal", "true");
    });

    it("has aria-labelledby referencing the title", () => {
      renderWithProviders(
        <ActivityFormModal programId="prog-1" onClose={mockOnClose} />
      );

      const dialog = screen.getByRole("dialog");
      expect(dialog).toHaveAttribute(
        "aria-labelledby",
        "activity-form-title"
      );
      expect(
        document.getElementById("activity-form-title")
      ).toHaveTextContent("Create Activity");
    });

    it("close button has aria-label", () => {
      renderWithProviders(
        <ActivityFormModal programId="prog-1" onClose={mockOnClose} />
      );

      expect(screen.getByLabelText("Close")).toBeInTheDocument();
    });
  });

  describe("create mode with null activity prop", () => {
    it("renders create mode when activity is null", () => {
      renderWithProviders(
        <ActivityFormModal
          programId="prog-1"
          activity={null}
          onClose={mockOnClose}
        />
      );

      expect(screen.getByText("Create Activity")).toBeInTheDocument();
      expect(screen.getByText("Create")).toBeInTheDocument();
    });

    it("does not pre-fill fields when activity is null", () => {
      renderWithProviders(
        <ActivityFormModal
          programId="prog-1"
          activity={null}
          onClose={mockOnClose}
        />
      );

      const nameInput = screen.getByLabelText(/name \*/i) as HTMLInputElement;
      const codeInput = screen.getByLabelText(/code \*/i) as HTMLInputElement;
      expect(nameInput.value).toBe("");
      expect(codeInput.value).toBe("");
    });
  });
});
