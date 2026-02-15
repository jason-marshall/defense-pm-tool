import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BaselineList } from "../BaselineList";
import { ToastProvider } from "@/components/Toast";
import type { BaselineListResponse, BaselineComparison } from "@/types/baseline";

// Mock the hooks
const mockUseBaselines = vi.fn();
const mockApproveMutateAsync = vi.fn();
const mockDeleteMutateAsync = vi.fn();
const mockUseCompareBaselines = vi.fn();

vi.mock("@/hooks/useBaselines", () => ({
  useBaselines: (...args: unknown[]) => mockUseBaselines(...args),
  useApproveBaseline: () => ({
    mutateAsync: mockApproveMutateAsync,
    isPending: false,
  }),
  useDeleteBaseline: () => ({
    mutateAsync: mockDeleteMutateAsync,
    isPending: false,
  }),
  useCompareBaselines: (...args: unknown[]) =>
    mockUseCompareBaselines(...args),
}));

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

const Wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={queryClient}>
    <ToastProvider>{children}</ToastProvider>
  </QueryClientProvider>
);

const mockBaselines: BaselineListResponse = {
  items: [
    {
      id: "bl-1",
      program_id: "prog-1",
      name: "Initial Baseline",
      description: "First baseline",
      status: "approved",
      baseline_number: 1,
      snapshot_data: {},
      approved_by: "user-1",
      approved_at: "2026-01-15T00:00:00Z",
      created_at: "2026-01-10T00:00:00Z",
      updated_at: null,
    },
    {
      id: "bl-2",
      program_id: "prog-1",
      name: "Updated Baseline",
      description: null,
      status: "draft",
      baseline_number: 2,
      snapshot_data: {},
      approved_by: null,
      approved_at: null,
      created_at: "2026-02-01T00:00:00Z",
      updated_at: null,
    },
  ],
  total: 2,
};

describe("BaselineList", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
    mockUseCompareBaselines.mockReturnValue({ data: null });
  });

  it("renders loading state", () => {
    mockUseBaselines.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    });

    render(<BaselineList programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("Loading baselines...")).toBeInTheDocument();
  });

  it("renders error state", () => {
    mockUseBaselines.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error("Failed"),
    });

    render(<BaselineList programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("Error loading baselines")).toBeInTheDocument();
  });

  it("renders empty state when no baselines", () => {
    mockUseBaselines.mockReturnValue({
      data: { items: [], total: 0 },
      isLoading: false,
      error: null,
    });

    render(<BaselineList programId="prog-1" />, { wrapper: Wrapper });

    expect(
      screen.getByText(
        "No baselines created yet. Promote a scenario to create one."
      )
    ).toBeInTheDocument();
  });

  it("renders baseline table with data", () => {
    mockUseBaselines.mockReturnValue({
      data: mockBaselines,
      isLoading: false,
      error: null,
    });

    render(<BaselineList programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("Initial Baseline")).toBeInTheDocument();
    expect(screen.getByText("Updated Baseline")).toBeInTheDocument();
    expect(screen.getByText("approved")).toBeInTheDocument();
    expect(screen.getByText("draft")).toBeInTheDocument();
  });

  it("shows baseline numbers", () => {
    mockUseBaselines.mockReturnValue({
      data: mockBaselines,
      isLoading: false,
      error: null,
    });

    render(<BaselineList programId="prog-1" />, { wrapper: Wrapper });

    // Baseline numbers in the table
    expect(screen.getByText("1")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
  });

  it("shows Approve button only for draft baselines", () => {
    mockUseBaselines.mockReturnValue({
      data: mockBaselines,
      isLoading: false,
      error: null,
    });

    render(<BaselineList programId="prog-1" />, { wrapper: Wrapper });

    // Only one Approve button (for the draft baseline)
    const approveButtons = screen.getAllByTitle("Approve");
    expect(approveButtons).toHaveLength(1);
  });

  it("calls approve when Approve button is clicked", async () => {
    mockUseBaselines.mockReturnValue({
      data: mockBaselines,
      isLoading: false,
      error: null,
    });
    mockApproveMutateAsync.mockResolvedValue(undefined);

    render(<BaselineList programId="prog-1" />, { wrapper: Wrapper });

    const approveButton = screen.getByTitle("Approve");
    fireEvent.click(approveButton);

    await waitFor(() => {
      expect(mockApproveMutateAsync).toHaveBeenCalledWith("bl-2");
    });
  });

  it("handles delete with confirmation", () => {
    mockUseBaselines.mockReturnValue({
      data: mockBaselines,
      isLoading: false,
      error: null,
    });
    mockDeleteMutateAsync.mockResolvedValue(undefined);
    vi.spyOn(window, "confirm").mockReturnValue(true);

    render(<BaselineList programId="prog-1" />, { wrapper: Wrapper });

    const deleteButtons = screen.getAllByTitle("Delete");
    fireEvent.click(deleteButtons[0]);

    expect(window.confirm).toHaveBeenCalledWith("Delete this baseline?");
  });

  it("renders compare radio buttons for each baseline", () => {
    mockUseBaselines.mockReturnValue({
      data: mockBaselines,
      isLoading: false,
      error: null,
    });

    render(<BaselineList programId="prog-1" />, { wrapper: Wrapper });

    const radioButtons = screen.getAllByRole("radio");
    // 2 baselines x 2 radio groups (compareA + compareB)
    expect(radioButtons).toHaveLength(4);
  });

  // ---------- NEW TEST CASES ----------

  it("does not render table or empty message during loading", () => {
    mockUseBaselines.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    });

    render(<BaselineList programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    expect(
      screen.queryByText("No baselines created yet. Promote a scenario to create one.")
    ).not.toBeInTheDocument();
  });

  it("does not render table or empty message on error", () => {
    mockUseBaselines.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error("Network error"),
    });

    render(<BaselineList programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    expect(
      screen.queryByText("No baselines created yet. Promote a scenario to create one.")
    ).not.toBeInTheDocument();
  });

  it("does not show table headers in empty state", () => {
    mockUseBaselines.mockReturnValue({
      data: { items: [], total: 0 },
      isLoading: false,
      error: null,
    });

    render(<BaselineList programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.queryByText("Status")).not.toBeInTheDocument();
    expect(screen.queryByText("Compare")).not.toBeInTheDocument();
    expect(screen.queryByText("Actions")).not.toBeInTheDocument();
  });

  it("shows heading in empty state", () => {
    mockUseBaselines.mockReturnValue({
      data: { items: [], total: 0 },
      isLoading: false,
      error: null,
    });

    render(<BaselineList programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("Baselines")).toBeInTheDocument();
  });

  it("calls delete mutateAsync after confirmation accepted", async () => {
    mockUseBaselines.mockReturnValue({
      data: mockBaselines,
      isLoading: false,
      error: null,
    });
    mockDeleteMutateAsync.mockResolvedValue(undefined);
    vi.spyOn(window, "confirm").mockReturnValue(true);

    render(<BaselineList programId="prog-1" />, { wrapper: Wrapper });

    const deleteButtons = screen.getAllByTitle("Delete");
    fireEvent.click(deleteButtons[0]);

    await waitFor(() => {
      expect(mockDeleteMutateAsync).toHaveBeenCalledWith("bl-1");
    });
  });

  it("does not call delete mutateAsync when confirmation is cancelled", async () => {
    mockUseBaselines.mockReturnValue({
      data: mockBaselines,
      isLoading: false,
      error: null,
    });
    vi.spyOn(window, "confirm").mockReturnValue(false);

    render(<BaselineList programId="prog-1" />, { wrapper: Wrapper });

    const deleteButtons = screen.getAllByTitle("Delete");
    fireEvent.click(deleteButtons[0]);

    expect(window.confirm).toHaveBeenCalledWith("Delete this baseline?");
    expect(mockDeleteMutateAsync).not.toHaveBeenCalled();
  });

  it("deletes the second baseline when its delete button is clicked", async () => {
    mockUseBaselines.mockReturnValue({
      data: mockBaselines,
      isLoading: false,
      error: null,
    });
    mockDeleteMutateAsync.mockResolvedValue(undefined);
    vi.spyOn(window, "confirm").mockReturnValue(true);

    render(<BaselineList programId="prog-1" />, { wrapper: Wrapper });

    const deleteButtons = screen.getAllByTitle("Delete");
    fireEvent.click(deleteButtons[1]);

    await waitFor(() => {
      expect(mockDeleteMutateAsync).toHaveBeenCalledWith("bl-2");
    });
  });

  it("shows success toast after successful approval", async () => {
    mockUseBaselines.mockReturnValue({
      data: mockBaselines,
      isLoading: false,
      error: null,
    });
    mockApproveMutateAsync.mockResolvedValue(undefined);

    render(<BaselineList programId="prog-1" />, { wrapper: Wrapper });

    const approveButton = screen.getByTitle("Approve");
    fireEvent.click(approveButton);

    await waitFor(() => {
      expect(screen.getByText("Baseline approved")).toBeInTheDocument();
    });
  });

  it("shows error toast when approval fails", async () => {
    mockUseBaselines.mockReturnValue({
      data: mockBaselines,
      isLoading: false,
      error: null,
    });
    mockApproveMutateAsync.mockRejectedValue(new Error("Server error"));

    render(<BaselineList programId="prog-1" />, { wrapper: Wrapper });

    const approveButton = screen.getByTitle("Approve");
    fireEvent.click(approveButton);

    await waitFor(() => {
      expect(screen.getByText("Approval failed")).toBeInTheDocument();
    });
  });

  it("shows success toast after successful delete", async () => {
    mockUseBaselines.mockReturnValue({
      data: mockBaselines,
      isLoading: false,
      error: null,
    });
    mockDeleteMutateAsync.mockResolvedValue(undefined);
    vi.spyOn(window, "confirm").mockReturnValue(true);

    render(<BaselineList programId="prog-1" />, { wrapper: Wrapper });

    const deleteButtons = screen.getAllByTitle("Delete");
    fireEvent.click(deleteButtons[0]);

    await waitFor(() => {
      expect(screen.getByText("Baseline deleted")).toBeInTheDocument();
    });
  });

  it("shows error toast when delete fails", async () => {
    mockUseBaselines.mockReturnValue({
      data: mockBaselines,
      isLoading: false,
      error: null,
    });
    mockDeleteMutateAsync.mockRejectedValue(new Error("Delete server error"));
    vi.spyOn(window, "confirm").mockReturnValue(true);

    render(<BaselineList programId="prog-1" />, { wrapper: Wrapper });

    const deleteButtons = screen.getAllByTitle("Delete");
    fireEvent.click(deleteButtons[0]);

    await waitFor(() => {
      expect(screen.getByText("Delete failed")).toBeInTheDocument();
    });
  });

  it("selects compare radio A for a baseline", () => {
    mockUseBaselines.mockReturnValue({
      data: mockBaselines,
      isLoading: false,
      error: null,
    });

    render(<BaselineList programId="prog-1" />, { wrapper: Wrapper });

    const radioButtons = screen.getAllByRole("radio");
    // compareA radios are at index 0, 2 (first radio per row)
    // compareB radios are at index 1, 3 (second radio per row)
    const compareARadioFirst = radioButtons[0];
    fireEvent.click(compareARadioFirst);

    expect(compareARadioFirst).toBeChecked();
  });

  it("selects compare radio B for a baseline", () => {
    mockUseBaselines.mockReturnValue({
      data: mockBaselines,
      isLoading: false,
      error: null,
    });

    render(<BaselineList programId="prog-1" />, { wrapper: Wrapper });

    const radioButtons = screen.getAllByRole("radio");
    // compareB radios are at index 1, 3
    const compareBRadioSecond = radioButtons[3];
    fireEvent.click(compareBRadioSecond);

    expect(compareBRadioSecond).toBeChecked();
  });

  it("passes compareA and compareB to useCompareBaselines when both selected", () => {
    mockUseBaselines.mockReturnValue({
      data: mockBaselines,
      isLoading: false,
      error: null,
    });

    render(<BaselineList programId="prog-1" />, { wrapper: Wrapper });

    const radioButtons = screen.getAllByRole("radio");
    // Select compareA = bl-1 (first row, first radio)
    fireEvent.click(radioButtons[0]);
    // Select compareB = bl-2 (second row, second radio)
    fireEvent.click(radioButtons[3]);

    // After re-renders, the hook should have been called with the selected IDs
    expect(mockUseCompareBaselines).toHaveBeenCalledWith("bl-1", "bl-2");
  });

  it("renders comparison results with deltas", () => {
    mockUseBaselines.mockReturnValue({
      data: mockBaselines,
      isLoading: false,
      error: null,
    });

    const mockComparison: BaselineComparison = {
      baseline_a: { id: "bl-1", name: "Initial Baseline" },
      baseline_b: { id: "bl-2", name: "Updated Baseline" },
      deltas: [
        {
          activity_code: "ACT-001",
          activity_name: "Design Phase",
          field: "budgeted_cost",
          value_a: "10000",
          value_b: "12000",
          change_percent: "20.0",
        },
        {
          activity_code: "ACT-002",
          activity_name: "Build Phase",
          field: "duration",
          value_a: "30",
          value_b: "25",
          change_percent: "-16.7",
        },
      ],
    };

    mockUseCompareBaselines.mockReturnValue({ data: mockComparison });

    render(<BaselineList programId="prog-1" />, { wrapper: Wrapper });

    // Comparison header - h3 contains both names in "Comparison: A vs B" format
    const comparisonHeading = screen.getByRole("heading", { level: 3 });
    expect(comparisonHeading.textContent).toContain("Initial Baseline");
    expect(comparisonHeading.textContent).toContain("Updated Baseline");

    // Delta rows
    expect(screen.getByText("Design Phase")).toBeInTheDocument();
    expect(screen.getByText("budgeted_cost")).toBeInTheDocument();
    expect(screen.getByText("10000")).toBeInTheDocument();
    expect(screen.getByText("12000")).toBeInTheDocument();
    expect(screen.getByText("20.0%")).toBeInTheDocument();

    expect(screen.getByText("Build Phase")).toBeInTheDocument();
    expect(screen.getByText("duration")).toBeInTheDocument();
    expect(screen.getByText("30")).toBeInTheDocument();
    expect(screen.getByText("25")).toBeInTheDocument();
    expect(screen.getByText("-16.7%")).toBeInTheDocument();
  });

  it("renders comparison with no differences message", () => {
    mockUseBaselines.mockReturnValue({
      data: mockBaselines,
      isLoading: false,
      error: null,
    });

    const mockComparison: BaselineComparison = {
      baseline_a: { id: "bl-1", name: "Initial Baseline" },
      baseline_b: { id: "bl-2", name: "Updated Baseline" },
      deltas: [],
    };

    mockUseCompareBaselines.mockReturnValue({ data: mockComparison });

    render(<BaselineList programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("No differences found.")).toBeInTheDocument();
  });

  it("does not render comparison section when no comparison data", () => {
    mockUseBaselines.mockReturnValue({
      data: mockBaselines,
      isLoading: false,
      error: null,
    });
    mockUseCompareBaselines.mockReturnValue({ data: null });

    render(<BaselineList programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.queryByText("No differences found.")).not.toBeInTheDocument();
    expect(screen.queryByText(/Comparison:/)).not.toBeInTheDocument();
  });

  it("renders accessible aria-labels on approve buttons", () => {
    mockUseBaselines.mockReturnValue({
      data: mockBaselines,
      isLoading: false,
      error: null,
    });

    render(<BaselineList programId="prog-1" />, { wrapper: Wrapper });

    expect(
      screen.getByLabelText("Approve baseline Updated Baseline")
    ).toBeInTheDocument();
  });

  it("renders accessible aria-labels on delete buttons", () => {
    mockUseBaselines.mockReturnValue({
      data: mockBaselines,
      isLoading: false,
      error: null,
    });

    render(<BaselineList programId="prog-1" />, { wrapper: Wrapper });

    expect(
      screen.getByLabelText("Delete baseline Initial Baseline")
    ).toBeInTheDocument();
    expect(
      screen.getByLabelText("Delete baseline Updated Baseline")
    ).toBeInTheDocument();
  });

  it("renders delete button for all baselines regardless of status", () => {
    mockUseBaselines.mockReturnValue({
      data: mockBaselines,
      isLoading: false,
      error: null,
    });

    render(<BaselineList programId="prog-1" />, { wrapper: Wrapper });

    const deleteButtons = screen.getAllByTitle("Delete");
    expect(deleteButtons).toHaveLength(2);
  });

  it("does not show approve button for approved baselines", () => {
    mockUseBaselines.mockReturnValue({
      data: {
        items: [mockBaselines.items[0]], // Only the approved one
        total: 1,
      },
      isLoading: false,
      error: null,
    });

    render(<BaselineList programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.queryByTitle("Approve")).not.toBeInTheDocument();
  });

  it("renders status badges with correct styling for approved", () => {
    mockUseBaselines.mockReturnValue({
      data: mockBaselines,
      isLoading: false,
      error: null,
    });

    render(<BaselineList programId="prog-1" />, { wrapper: Wrapper });

    const approvedBadge = screen.getByText("approved");
    expect(approvedBadge).toHaveClass("bg-green-100", "text-green-700");
  });

  it("renders status badges with correct styling for draft", () => {
    mockUseBaselines.mockReturnValue({
      data: mockBaselines,
      isLoading: false,
      error: null,
    });

    render(<BaselineList programId="prog-1" />, { wrapper: Wrapper });

    const draftBadge = screen.getByText("draft");
    expect(draftBadge).toHaveClass("bg-gray-100", "text-gray-600");
  });

  it("renders status badge with correct styling for superseded", () => {
    const supersededBaseline = {
      id: "bl-3",
      program_id: "prog-1",
      name: "Old Baseline",
      description: null,
      status: "superseded" as const,
      baseline_number: 0,
      snapshot_data: {},
      approved_by: null,
      approved_at: null,
      created_at: "2025-12-01T00:00:00Z",
      updated_at: null,
    };

    mockUseBaselines.mockReturnValue({
      data: { items: [supersededBaseline], total: 1 },
      isLoading: false,
      error: null,
    });

    render(<BaselineList programId="prog-1" />, { wrapper: Wrapper });

    const supersededBadge = screen.getByText("superseded");
    expect(supersededBadge).toHaveClass("bg-yellow-100", "text-yellow-600");
  });

  it("renders formatted dates", () => {
    mockUseBaselines.mockReturnValue({
      data: mockBaselines,
      isLoading: false,
      error: null,
    });

    render(<BaselineList programId="prog-1" />, { wrapper: Wrapper });

    // Dates are formatted with toLocaleDateString, just check they render
    const dateStr = new Date("2026-01-10T00:00:00Z").toLocaleDateString();
    expect(screen.getByText(dateStr)).toBeInTheDocument();
  });

  it("renders table headers", () => {
    mockUseBaselines.mockReturnValue({
      data: mockBaselines,
      isLoading: false,
      error: null,
    });

    render(<BaselineList programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("#")).toBeInTheDocument();
    expect(screen.getByText("Name")).toBeInTheDocument();
    expect(screen.getByText("Status")).toBeInTheDocument();
    expect(screen.getByText("Created")).toBeInTheDocument();
    expect(screen.getByText("Compare")).toBeInTheDocument();
    expect(screen.getByText("Actions")).toBeInTheDocument();
  });

  it("passes programId to useBaselines", () => {
    mockUseBaselines.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    });

    render(<BaselineList programId="my-program-123" />, { wrapper: Wrapper });

    expect(mockUseBaselines).toHaveBeenCalledWith("my-program-123");
  });

  it("handles data with undefined items gracefully", () => {
    mockUseBaselines.mockReturnValue({
      data: {},
      isLoading: false,
      error: null,
    });

    render(<BaselineList programId="prog-1" />, { wrapper: Wrapper });

    // Falls back to empty array via `data?.items ?? []`
    expect(
      screen.getByText(
        "No baselines created yet. Promote a scenario to create one."
      )
    ).toBeInTheDocument();
  });

  it("does not show approve for superseded baselines", () => {
    const supersededBaseline = {
      id: "bl-3",
      program_id: "prog-1",
      name: "Old Baseline",
      description: null,
      status: "superseded" as const,
      baseline_number: 0,
      snapshot_data: {},
      approved_by: null,
      approved_at: null,
      created_at: "2025-12-01T00:00:00Z",
      updated_at: null,
    };

    mockUseBaselines.mockReturnValue({
      data: { items: [supersededBaseline], total: 1 },
      isLoading: false,
      error: null,
    });

    render(<BaselineList programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.queryByTitle("Approve")).not.toBeInTheDocument();
  });
});
