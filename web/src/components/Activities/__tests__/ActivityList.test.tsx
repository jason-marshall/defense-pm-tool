import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ActivityList } from "../ActivityList";
import { ToastProvider } from "@/components/Toast";
import type { ActivityListResponse } from "@/types/activity";

// Mock the hooks
const mockUseActivities = vi.fn();
const mockDeleteMutateAsync = vi.fn();

vi.mock("@/hooks/useActivities", () => ({
  useActivities: (...args: unknown[]) => mockUseActivities(...args),
  useDeleteActivity: () => ({
    mutateAsync: mockDeleteMutateAsync,
    isPending: false,
  }),
}));

// Mock ActivityFormModal to avoid deep dependencies
vi.mock("../ActivityFormModal", () => ({
  ActivityFormModal: ({ onClose }: { onClose: () => void }) => (
    <div data-testid="activity-form-modal">
      <button onClick={onClose}>Close Form</button>
    </div>
  ),
}));

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

const Wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={queryClient}>
    <ToastProvider>{children}</ToastProvider>
  </QueryClientProvider>
);

const mockActivities: ActivityListResponse = {
  items: [
    {
      id: "act-1",
      program_id: "prog-1",
      wbs_id: null,
      name: "Design Review",
      code: "DR-001",
      description: null,
      duration: 10,
      remaining_duration: null,
      percent_complete: "50.00",
      budgeted_cost: "25000",
      actual_cost: "12000",
      constraint_type: null,
      constraint_date: null,
      early_start: 0,
      early_finish: 10,
      late_start: 0,
      late_finish: 10,
      total_float: 0,
      free_float: 0,
      is_critical: true,
      is_milestone: false,
      actual_start: null,
      actual_finish: null,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: null,
    },
    {
      id: "act-2",
      program_id: "prog-1",
      wbs_id: null,
      name: "Milestone Gate",
      code: "MG-001",
      description: null,
      duration: 0,
      remaining_duration: null,
      percent_complete: "0.00",
      budgeted_cost: "0",
      actual_cost: "0",
      constraint_type: null,
      constraint_date: null,
      early_start: 10,
      early_finish: 10,
      late_start: 15,
      late_finish: 15,
      total_float: 5,
      free_float: 5,
      is_critical: false,
      is_milestone: true,
      actual_start: null,
      actual_finish: null,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: null,
    },
  ],
  total: 2,
};

describe("ActivityList", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("renders loading state", () => {
    mockUseActivities.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    });

    render(<ActivityList programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("Loading activities...")).toBeInTheDocument();
  });

  it("renders error state", () => {
    mockUseActivities.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error("Failed"),
    });

    render(<ActivityList programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("Error loading activities")).toBeInTheDocument();
  });

  it("renders empty state when no activities", () => {
    mockUseActivities.mockReturnValue({
      data: { items: [], total: 0 },
      isLoading: false,
      error: null,
    });

    render(<ActivityList programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("No activities yet.")).toBeInTheDocument();
    expect(
      screen.getByText("Create your first activity")
    ).toBeInTheDocument();
  });

  it("renders activity table with data", () => {
    mockUseActivities.mockReturnValue({
      data: mockActivities,
      isLoading: false,
      error: null,
    });

    render(<ActivityList programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("DR-001")).toBeInTheDocument();
    expect(screen.getByText("Design Review")).toBeInTheDocument();
    expect(screen.getByText("MG-001")).toBeInTheDocument();
    expect(screen.getByText("Milestone Gate")).toBeInTheDocument();
    expect(screen.getByText("10d")).toBeInTheDocument();
    expect(screen.getByText("50.00%")).toBeInTheDocument();
  });

  it("highlights critical activities with red background", () => {
    mockUseActivities.mockReturnValue({
      data: mockActivities,
      isLoading: false,
      error: null,
    });

    render(<ActivityList programId="prog-1" />, { wrapper: Wrapper });

    // The critical activity row should have bg-red-50 class
    const rows = screen.getAllByRole("row");
    // First data row (index 1) is critical
    expect(rows[1].className).toContain("bg-red-50");
    // Second data row (index 2) is not critical
    expect(rows[2].className).not.toContain("bg-red-50");
  });

  it("opens form modal when Add Activity is clicked", () => {
    mockUseActivities.mockReturnValue({
      data: mockActivities,
      isLoading: false,
      error: null,
    });

    render(<ActivityList programId="prog-1" />, { wrapper: Wrapper });

    fireEvent.click(screen.getByText("Add Activity"));

    expect(screen.getByTestId("activity-form-modal")).toBeInTheDocument();
  });

  it("handles delete with confirmation", () => {
    mockUseActivities.mockReturnValue({
      data: mockActivities,
      isLoading: false,
      error: null,
    });
    mockDeleteMutateAsync.mockResolvedValue(undefined);
    vi.spyOn(window, "confirm").mockReturnValue(true);

    render(<ActivityList programId="prog-1" />, { wrapper: Wrapper });

    const deleteButtons = screen.getAllByTitle("Delete");
    fireEvent.click(deleteButtons[0]);

    expect(window.confirm).toHaveBeenCalledWith("Delete this activity?");
  });
});
