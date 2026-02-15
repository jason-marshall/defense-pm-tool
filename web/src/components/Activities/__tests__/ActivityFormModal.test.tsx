import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ActivityFormModal } from "../ActivityFormModal";
import { ToastProvider } from "@/components/Toast";

const mockMutateAsyncCreate = vi.fn();
const mockMutateAsyncUpdate = vi.fn();

vi.mock("@/hooks/useActivities", () => ({
  useCreateActivity: () => ({
    mutateAsync: mockMutateAsyncCreate,
    isPending: false,
  }),
  useUpdateActivity: () => ({
    mutateAsync: mockMutateAsyncUpdate,
    isPending: false,
  }),
}));

const mockActivity = {
  id: "act-1",
  program_id: "prog-1",
  name: "Design Review",
  code: "DR-001",
  description: "Review the design docs",
  duration: 10,
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
});
