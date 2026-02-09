import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BaselineList } from "../BaselineList";
import { ToastProvider } from "@/components/Toast";
import type { BaselineListResponse } from "@/types/baseline";

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
});
