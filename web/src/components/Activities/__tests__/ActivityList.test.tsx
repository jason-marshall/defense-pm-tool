import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ActivityList } from "../ActivityList";
import { ToastProvider } from "@/components/Toast";
import type { Activity, ActivityListResponse } from "@/types/activity";

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

// Mock ActivityFormModal - expose activity prop so we can verify edit passes the right data
vi.mock("../ActivityFormModal", () => ({
  ActivityFormModal: ({
    onClose,
    activity,
    programId,
  }: {
    onClose: () => void;
    activity?: Activity | null;
    programId: string;
  }) => (
    <div data-testid="activity-form-modal">
      <span data-testid="modal-program-id">{programId}</span>
      {activity && (
        <span data-testid="modal-editing-activity">{activity.name}</span>
      )}
      {!activity && <span data-testid="modal-create-mode">create</span>}
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

/** Helper to set up hook return with loaded activities */
function setupWithActivities(overrides?: Partial<ActivityListResponse>) {
  const data = overrides
    ? { ...mockActivities, ...overrides }
    : mockActivities;
  mockUseActivities.mockReturnValue({
    data,
    isLoading: false,
    error: null,
  });
}

describe("ActivityList", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  // ─── Loading State ──────────────────────────────────────────────────

  it("renders loading state", () => {
    mockUseActivities.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    });

    render(<ActivityList programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("Loading activities...")).toBeInTheDocument();
  });

  it("does not render table or empty state while loading", () => {
    mockUseActivities.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    });

    render(<ActivityList programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    expect(screen.queryByText("No activities yet.")).not.toBeInTheDocument();
  });

  // ─── Error State ────────────────────────────────────────────────────

  it("renders error state", () => {
    mockUseActivities.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error("Failed"),
    });

    render(<ActivityList programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("Error loading activities")).toBeInTheDocument();
  });

  it("does not render table or empty state on error", () => {
    mockUseActivities.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error("Network error"),
    });

    render(<ActivityList programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    expect(screen.queryByText("No activities yet.")).not.toBeInTheDocument();
    expect(screen.queryByText("Add Activity")).not.toBeInTheDocument();
  });

  // ─── Empty State ────────────────────────────────────────────────────

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

  it("opens form modal when 'Create your first activity' link is clicked in empty state", () => {
    mockUseActivities.mockReturnValue({
      data: { items: [], total: 0 },
      isLoading: false,
      error: null,
    });

    render(<ActivityList programId="prog-1" />, { wrapper: Wrapper });

    fireEvent.click(screen.getByText("Create your first activity"));

    expect(screen.getByTestId("activity-form-modal")).toBeInTheDocument();
    expect(screen.getByTestId("modal-create-mode")).toBeInTheDocument();
  });

  it("does not render table in empty state", () => {
    mockUseActivities.mockReturnValue({
      data: { items: [], total: 0 },
      isLoading: false,
      error: null,
    });

    render(<ActivityList programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  // ─── Table Rendering ───────────────────────────────────────────────

  it("renders activity table with data", () => {
    setupWithActivities();

    render(<ActivityList programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("DR-001")).toBeInTheDocument();
    expect(screen.getByText("Design Review")).toBeInTheDocument();
    expect(screen.getByText("MG-001")).toBeInTheDocument();
    expect(screen.getByText("Milestone Gate")).toBeInTheDocument();
    expect(screen.getByText("10d")).toBeInTheDocument();
    expect(screen.getByText("50.00%")).toBeInTheDocument();
  });

  it("renders table header columns", () => {
    setupWithActivities();

    render(<ActivityList programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("Code")).toBeInTheDocument();
    expect(screen.getByText("Name")).toBeInTheDocument();
    expect(screen.getByText("Duration")).toBeInTheDocument();
    expect(screen.getByText("% Complete")).toBeInTheDocument();
    expect(screen.getByText("ES")).toBeInTheDocument();
    expect(screen.getByText("EF")).toBeInTheDocument();
    expect(screen.getByText("TF")).toBeInTheDocument();
    expect(screen.getByText("Budget")).toBeInTheDocument();
    expect(screen.getByText("Actions")).toBeInTheDocument();
  });

  it("renders correct number of data rows", () => {
    setupWithActivities();

    render(<ActivityList programId="prog-1" />, { wrapper: Wrapper });

    // 1 header row + 2 data rows
    const rows = screen.getAllByRole("row");
    expect(rows).toHaveLength(3);
  });

  it("renders the heading 'Activities'", () => {
    setupWithActivities();

    render(<ActivityList programId="prog-1" />, { wrapper: Wrapper });

    expect(
      screen.getByRole("heading", { name: "Activities" })
    ).toBeInTheDocument();
  });

  // ─── Critical Path Highlighting ─────────────────────────────────────

  it("highlights critical activities with red background", () => {
    setupWithActivities();

    render(<ActivityList programId="prog-1" />, { wrapper: Wrapper });

    // The critical activity row should have bg-red-50 class
    const rows = screen.getAllByRole("row");
    // First data row (index 1) is critical
    expect(rows[1].className).toContain("bg-red-50");
    // Second data row (index 2) is not critical
    expect(rows[2].className).not.toContain("bg-red-50");
  });

  it("displays total float 0 with red styling for critical activities", () => {
    setupWithActivities();

    render(<ActivityList programId="prog-1" />, { wrapper: Wrapper });

    // The total_float=0 cell is in a <span> inside a <td> for the TF column.
    // Multiple cells may contain "0", so find the one with red styling.
    const allZeros = screen.getAllByText("0");
    const redZero = allZeros.find(
      (el) =>
        el.className.includes("text-red-600") &&
        el.className.includes("font-medium")
    );
    expect(redZero).toBeDefined();
  });

  it("displays non-zero total float with gray styling", () => {
    setupWithActivities();

    render(<ActivityList programId="prog-1" />, { wrapper: Wrapper });

    // The total_float=5 cell should have gray styling
    const nonZeroFloat = screen.getByText("5");
    expect(nonZeroFloat.className).toContain("text-gray-500");
    expect(nonZeroFloat.className).not.toContain("text-red-600");
  });

  // ─── Milestone Icon ─────────────────────────────────────────────────

  it("renders milestone icon for milestone activities", () => {
    setupWithActivities();

    render(<ActivityList programId="prog-1" />, { wrapper: Wrapper });

    // The milestone activity row has a Flag icon (lucide-react renders svg)
    // Milestone Gate (act-2) is_milestone=true, Design Review (act-1) is not
    // We can check for the aria-label on edit/delete buttons to identify rows
    // but the Flag component doesn't have accessible text by default.
    // Instead, verify the milestone row contains the code "MG-001"
    const milestoneCode = screen.getByText("MG-001");
    expect(milestoneCode).toBeInTheDocument();

    // The code cell is within a span that should also contain the Flag icon svg
    const codeCell = milestoneCode.closest("td");
    expect(codeCell).not.toBeNull();
    // The Flag icon renders an SVG within the span
    const svg = codeCell!.querySelector("svg");
    expect(svg).not.toBeNull();
  });

  // ─── Budget Formatting ──────────────────────────────────────────────

  it("formats budgeted cost as dollar amount", () => {
    setupWithActivities();

    render(<ActivityList programId="prog-1" />, { wrapper: Wrapper });

    // budgeted_cost "25000" should render as "$25,000"
    expect(screen.getByText("$25,000")).toBeInTheDocument();
  });

  it("renders $0 for zero budgeted cost string", () => {
    setupWithActivities();

    render(<ActivityList programId="prog-1" />, { wrapper: Wrapper });

    // budgeted_cost "0" is a truthy string, so the ternary renders "$0"
    expect(screen.getByText("$0")).toBeInTheDocument();
  });

  // ─── Null Field Rendering ───────────────────────────────────────────

  it("renders dash for null early_start and early_finish values", () => {
    const activityWithNulls: Activity = {
      id: "act-3",
      program_id: "prog-1",
      wbs_id: null,
      name: "Unscheduled Task",
      code: "UT-001",
      description: null,
      duration: 5,
      remaining_duration: null,
      percent_complete: "0.00",
      budgeted_cost: null as unknown as string,
      actual_cost: "0",
      constraint_type: null,
      constraint_date: null,
      early_start: null,
      early_finish: null,
      late_start: null,
      late_finish: null,
      total_float: null,
      free_float: null,
      is_critical: false,
      is_milestone: false,
      actual_start: null,
      actual_finish: null,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: null,
    };

    mockUseActivities.mockReturnValue({
      data: { items: [activityWithNulls], total: 1 },
      isLoading: false,
      error: null,
    });

    render(<ActivityList programId="prog-1" />, { wrapper: Wrapper });

    // Multiple cells should render "-" for null values
    const dashes = screen.getAllByText("-");
    // ES, EF, TF, Budget => at least 4 dashes
    expect(dashes.length).toBeGreaterThanOrEqual(4);
  });

  // ─── Add Activity (Create) ─────────────────────────────────────────

  it("opens form modal when Add Activity is clicked", () => {
    setupWithActivities();

    render(<ActivityList programId="prog-1" />, { wrapper: Wrapper });

    fireEvent.click(screen.getByText("Add Activity"));

    expect(screen.getByTestId("activity-form-modal")).toBeInTheDocument();
  });

  it("opens form modal in create mode (no activity) when Add Activity is clicked", () => {
    setupWithActivities();

    render(<ActivityList programId="prog-1" />, { wrapper: Wrapper });

    fireEvent.click(screen.getByText("Add Activity"));

    // The modal should be in create mode (activity is null)
    expect(screen.getByTestId("modal-create-mode")).toBeInTheDocument();
    expect(
      screen.queryByTestId("modal-editing-activity")
    ).not.toBeInTheDocument();
  });

  it("passes programId to the form modal", () => {
    setupWithActivities();

    render(<ActivityList programId="prog-1" />, { wrapper: Wrapper });

    fireEvent.click(screen.getByText("Add Activity"));

    expect(screen.getByTestId("modal-program-id")).toHaveTextContent(
      "prog-1"
    );
  });

  // ─── Edit Activity ─────────────────────────────────────────────────

  it("opens form modal in edit mode when Edit button is clicked", () => {
    setupWithActivities();

    render(<ActivityList programId="prog-1" />, { wrapper: Wrapper });

    // Click the edit button for the first activity
    const editButton = screen.getByLabelText("Edit activity Design Review");
    fireEvent.click(editButton);

    expect(screen.getByTestId("activity-form-modal")).toBeInTheDocument();
    expect(screen.getByTestId("modal-editing-activity")).toHaveTextContent(
      "Design Review"
    );
  });

  it("opens form modal with correct activity when editing second activity", () => {
    setupWithActivities();

    render(<ActivityList programId="prog-1" />, { wrapper: Wrapper });

    const editButton = screen.getByLabelText(
      "Edit activity Milestone Gate"
    );
    fireEvent.click(editButton);

    expect(screen.getByTestId("modal-editing-activity")).toHaveTextContent(
      "Milestone Gate"
    );
  });

  it("renders edit buttons with accessible aria-labels", () => {
    setupWithActivities();

    render(<ActivityList programId="prog-1" />, { wrapper: Wrapper });

    expect(
      screen.getByLabelText("Edit activity Design Review")
    ).toBeInTheDocument();
    expect(
      screen.getByLabelText("Edit activity Milestone Gate")
    ).toBeInTheDocument();
  });

  // ─── Close Modal ────────────────────────────────────────────────────

  it("closes form modal when onClose is called", () => {
    setupWithActivities();

    render(<ActivityList programId="prog-1" />, { wrapper: Wrapper });

    // Open modal
    fireEvent.click(screen.getByText("Add Activity"));
    expect(screen.getByTestId("activity-form-modal")).toBeInTheDocument();

    // Close modal
    fireEvent.click(screen.getByText("Close Form"));
    expect(
      screen.queryByTestId("activity-form-modal")
    ).not.toBeInTheDocument();
  });

  it("resets editing activity when modal is closed", () => {
    setupWithActivities();

    render(<ActivityList programId="prog-1" />, { wrapper: Wrapper });

    // Open in edit mode
    const editButton = screen.getByLabelText("Edit activity Design Review");
    fireEvent.click(editButton);
    expect(screen.getByTestId("modal-editing-activity")).toBeInTheDocument();

    // Close it
    fireEvent.click(screen.getByText("Close Form"));
    expect(
      screen.queryByTestId("activity-form-modal")
    ).not.toBeInTheDocument();

    // Re-open via Add Activity => should be in create mode, not edit
    fireEvent.click(screen.getByText("Add Activity"));
    expect(screen.getByTestId("modal-create-mode")).toBeInTheDocument();
    expect(
      screen.queryByTestId("modal-editing-activity")
    ).not.toBeInTheDocument();
  });

  // ─── Delete Activity ───────────────────────────────────────────────

  it("handles delete with confirmation", () => {
    setupWithActivities();
    mockDeleteMutateAsync.mockResolvedValue(undefined);
    vi.spyOn(window, "confirm").mockReturnValue(true);

    render(<ActivityList programId="prog-1" />, { wrapper: Wrapper });

    const deleteButtons = screen.getAllByTitle("Delete");
    fireEvent.click(deleteButtons[0]);

    expect(window.confirm).toHaveBeenCalledWith("Delete this activity?");
  });

  it("calls deleteActivity.mutateAsync with the activity id when confirmed", async () => {
    setupWithActivities();
    mockDeleteMutateAsync.mockResolvedValue(undefined);
    vi.spyOn(window, "confirm").mockReturnValue(true);

    render(<ActivityList programId="prog-1" />, { wrapper: Wrapper });

    const deleteButton = screen.getByLabelText(
      "Delete activity Design Review"
    );
    fireEvent.click(deleteButton);

    await waitFor(() => {
      expect(mockDeleteMutateAsync).toHaveBeenCalledWith("act-1");
    });
  });

  it("does not call mutateAsync when delete confirmation is cancelled", () => {
    setupWithActivities();
    vi.spyOn(window, "confirm").mockReturnValue(false);

    render(<ActivityList programId="prog-1" />, { wrapper: Wrapper });

    const deleteButton = screen.getByLabelText(
      "Delete activity Design Review"
    );
    fireEvent.click(deleteButton);

    expect(window.confirm).toHaveBeenCalledWith("Delete this activity?");
    expect(mockDeleteMutateAsync).not.toHaveBeenCalled();
  });

  it("shows success toast after successful deletion", async () => {
    setupWithActivities();
    mockDeleteMutateAsync.mockResolvedValue(undefined);
    vi.spyOn(window, "confirm").mockReturnValue(true);

    render(<ActivityList programId="prog-1" />, { wrapper: Wrapper });

    const deleteButton = screen.getByLabelText(
      "Delete activity Design Review"
    );
    fireEvent.click(deleteButton);

    await waitFor(() => {
      expect(screen.getByText("Activity deleted")).toBeInTheDocument();
    });
  });

  it("shows error toast when deletion fails", async () => {
    setupWithActivities();
    mockDeleteMutateAsync.mockRejectedValue(new Error("Server error"));
    vi.spyOn(window, "confirm").mockReturnValue(true);

    render(<ActivityList programId="prog-1" />, { wrapper: Wrapper });

    const deleteButton = screen.getByLabelText(
      "Delete activity Milestone Gate"
    );
    fireEvent.click(deleteButton);

    await waitFor(() => {
      expect(
        screen.getByText("Failed to delete activity")
      ).toBeInTheDocument();
    });
  });

  it("renders delete buttons with accessible aria-labels", () => {
    setupWithActivities();

    render(<ActivityList programId="prog-1" />, { wrapper: Wrapper });

    expect(
      screen.getByLabelText("Delete activity Design Review")
    ).toBeInTheDocument();
    expect(
      screen.getByLabelText("Delete activity Milestone Gate")
    ).toBeInTheDocument();
  });

  // ─── Data with undefined items ──────────────────────────────────────

  it("handles data response with no items property gracefully", () => {
    mockUseActivities.mockReturnValue({
      data: {},
      isLoading: false,
      error: null,
    });

    render(<ActivityList programId="prog-1" />, { wrapper: Wrapper });

    // Should render the empty state since items defaults to []
    expect(screen.getByText("No activities yet.")).toBeInTheDocument();
  });

  it("handles null data gracefully", () => {
    mockUseActivities.mockReturnValue({
      data: null,
      isLoading: false,
      error: null,
    });

    render(<ActivityList programId="prog-1" />, { wrapper: Wrapper });

    // data?.items ?? [] -> null?.items ?? [] -> undefined ?? [] -> []
    expect(screen.getByText("No activities yet.")).toBeInTheDocument();
  });

  // ─── Program ID Passed to Hook ──────────────────────────────────────

  it("passes programId to useActivities hook", () => {
    mockUseActivities.mockReturnValue({
      data: { items: [], total: 0 },
      isLoading: false,
      error: null,
    });

    render(<ActivityList programId="prog-42" />, { wrapper: Wrapper });

    expect(mockUseActivities).toHaveBeenCalledWith("prog-42");
  });

  // ─── Duration and Percentage Display ────────────────────────────────

  it("renders duration with 'd' suffix", () => {
    setupWithActivities();

    render(<ActivityList programId="prog-1" />, { wrapper: Wrapper });

    // act-1 has duration=10, act-2 has duration=0
    expect(screen.getByText("10d")).toBeInTheDocument();
    expect(screen.getByText("0d")).toBeInTheDocument();
  });

  it("renders percent complete with '%' suffix", () => {
    setupWithActivities();

    render(<ActivityList programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("50.00%")).toBeInTheDocument();
    expect(screen.getByText("0.00%")).toBeInTheDocument();
  });

  // ─── Early Start / Early Finish ─────────────────────────────────────

  it("renders early_start and early_finish values", () => {
    setupWithActivities();

    render(<ActivityList programId="prog-1" />, { wrapper: Wrapper });

    // act-1: ES=0, EF=10; act-2: ES=10, EF=10
    // "0" appears as ES for act-1, and also as total_float for act-1
    // "10" appears in multiple places (duration, ES, EF)
    // Just verify the values are present in the document
    const allTens = screen.getAllByText("10");
    expect(allTens.length).toBeGreaterThanOrEqual(1);
  });

  // ─── Single Activity Rendering ──────────────────────────────────────

  it("renders a single non-critical, non-milestone activity correctly", () => {
    const singleActivity: Activity = {
      id: "act-solo",
      program_id: "prog-1",
      wbs_id: null,
      name: "Simple Task",
      code: "ST-001",
      description: null,
      duration: 3,
      remaining_duration: null,
      percent_complete: "75.00",
      budgeted_cost: "5000",
      actual_cost: "4000",
      constraint_type: null,
      constraint_date: null,
      early_start: 2,
      early_finish: 5,
      late_start: 4,
      late_finish: 7,
      total_float: 2,
      free_float: 1,
      is_critical: false,
      is_milestone: false,
      actual_start: null,
      actual_finish: null,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: null,
    };

    mockUseActivities.mockReturnValue({
      data: { items: [singleActivity], total: 1 },
      isLoading: false,
      error: null,
    });

    render(<ActivityList programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("ST-001")).toBeInTheDocument();
    expect(screen.getByText("Simple Task")).toBeInTheDocument();
    expect(screen.getByText("3d")).toBeInTheDocument();
    expect(screen.getByText("75.00%")).toBeInTheDocument();
    expect(screen.getByText("$5,000")).toBeInTheDocument();

    // Row should not have critical styling
    const rows = screen.getAllByRole("row");
    expect(rows[1].className).not.toContain("bg-red-50");

    // Code cell should not have any icon svgs (not milestone, not critical)
    const codeCell = screen.getByText("ST-001").closest("td");
    const svgs = codeCell!.querySelectorAll("svg");
    expect(svgs.length).toBe(0);
  });

  // ─── Critical + Milestone Combined ──────────────────────────────────

  it("renders both critical and milestone icons when activity is both", () => {
    const criticalMilestone: Activity = {
      id: "act-cm",
      program_id: "prog-1",
      wbs_id: null,
      name: "Critical Milestone",
      code: "CM-001",
      description: null,
      duration: 0,
      remaining_duration: null,
      percent_complete: "0.00",
      budgeted_cost: "0",
      actual_cost: "0",
      constraint_type: null,
      constraint_date: null,
      early_start: 20,
      early_finish: 20,
      late_start: 20,
      late_finish: 20,
      total_float: 0,
      free_float: 0,
      is_critical: true,
      is_milestone: true,
      actual_start: null,
      actual_finish: null,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: null,
    };

    mockUseActivities.mockReturnValue({
      data: { items: [criticalMilestone], total: 1 },
      isLoading: false,
      error: null,
    });

    render(<ActivityList programId="prog-1" />, { wrapper: Wrapper });

    const codeCell = screen.getByText("CM-001").closest("td");
    // Should have both Flag and AlertTriangle icons (2 SVGs)
    const svgs = codeCell!.querySelectorAll("svg");
    expect(svgs.length).toBe(2);

    // Row should have critical bg
    const rows = screen.getAllByRole("row");
    expect(rows[1].className).toContain("bg-red-50");
  });

  // ─── Delete Second Activity ─────────────────────────────────────────

  it("calls delete with correct id when deleting second activity", async () => {
    setupWithActivities();
    mockDeleteMutateAsync.mockResolvedValue(undefined);
    vi.spyOn(window, "confirm").mockReturnValue(true);

    render(<ActivityList programId="prog-1" />, { wrapper: Wrapper });

    const deleteButton = screen.getByLabelText(
      "Delete activity Milestone Gate"
    );
    fireEvent.click(deleteButton);

    await waitFor(() => {
      expect(mockDeleteMutateAsync).toHaveBeenCalledWith("act-2");
    });
  });
});
