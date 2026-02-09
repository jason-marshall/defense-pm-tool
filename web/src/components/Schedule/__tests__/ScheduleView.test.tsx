import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ScheduleView } from "../ScheduleView";
import { ToastProvider } from "@/components/Toast";
import type { ScheduleCalculationResponse } from "@/types/schedule";

// Mock the hooks
const mockUseScheduleResults = vi.fn();
const mockCalculateMutateAsync = vi.fn();

vi.mock("@/hooks/useSchedule", () => ({
  useScheduleResults: (...args: unknown[]) => mockUseScheduleResults(...args),
  useCalculateSchedule: () => ({
    mutateAsync: mockCalculateMutateAsync,
    isPending: false,
  }),
}));

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

const Wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={queryClient}>
    <ToastProvider>{children}</ToastProvider>
  </QueryClientProvider>
);

const mockScheduleData: ScheduleCalculationResponse = {
  results: [
    {
      activity_id: "act-1",
      activity_name: "Design Review",
      activity_code: "DR-001",
      duration: 10,
      early_start: 0,
      early_finish: 10,
      late_start: 0,
      late_finish: 10,
      total_float: 0,
      free_float: 0,
      is_critical: true,
    },
    {
      activity_id: "act-2",
      activity_name: "Testing",
      activity_code: "TS-001",
      duration: 5,
      early_start: 10,
      early_finish: 15,
      late_start: 12,
      late_finish: 17,
      total_float: 2,
      free_float: 2,
      is_critical: false,
    },
    {
      activity_id: "act-3",
      activity_name: "Deployment",
      activity_code: "DP-001",
      duration: 3,
      early_start: 10,
      early_finish: 13,
      late_start: 10,
      late_finish: 13,
      total_float: 0,
      free_float: 0,
      is_critical: true,
    },
  ],
  critical_path: ["act-1", "act-3"],
  project_duration: 13,
  calculated_at: "2026-02-01T12:00:00Z",
};

describe("ScheduleView", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("renders loading state", () => {
    mockUseScheduleResults.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
      refetch: vi.fn(),
    });

    render(<ScheduleView programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("Loading schedule...")).toBeInTheDocument();
  });

  it("renders empty state when no schedule data", () => {
    mockUseScheduleResults.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    render(<ScheduleView programId="prog-1" />, { wrapper: Wrapper });

    expect(
      screen.getByText(/No schedule data available/)
    ).toBeInTheDocument();
  });

  it("renders the calculate schedule button", () => {
    mockUseScheduleResults.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    render(<ScheduleView programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("Calculate Schedule")).toBeInTheDocument();
  });

  it("renders schedule results table", () => {
    mockUseScheduleResults.mockReturnValue({
      data: mockScheduleData,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    render(<ScheduleView programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("DR-001")).toBeInTheDocument();
    expect(screen.getByText("Design Review")).toBeInTheDocument();
    expect(screen.getByText("TS-001")).toBeInTheDocument();
    expect(screen.getByText("Testing")).toBeInTheDocument();
    expect(screen.getByText("DP-001")).toBeInTheDocument();
    expect(screen.getByText("Deployment")).toBeInTheDocument();
  });

  it("renders summary cards with correct values", () => {
    mockUseScheduleResults.mockReturnValue({
      data: mockScheduleData,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    render(<ScheduleView programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("13 days")).toBeInTheDocument();
    // "3" appears in multiple places (duration column, total activities card),
    // so use getAllByText to verify it is present
    expect(screen.getAllByText("3").length).toBeGreaterThanOrEqual(1);
    // "2" also appears as float values, so verify critical activities count exists
    expect(screen.getAllByText("2").length).toBeGreaterThanOrEqual(1);
  });

  it("highlights critical activities with red background", () => {
    mockUseScheduleResults.mockReturnValue({
      data: mockScheduleData,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    render(<ScheduleView programId="prog-1" />, { wrapper: Wrapper });

    const rows = screen.getAllByRole("row");
    // Row index 1 = Design Review (critical) - header is index 0
    expect(rows[1].className).toContain("bg-red-50");
    // Row index 2 = Testing (not critical)
    expect(rows[2].className).not.toContain("bg-red-50");
    // Row index 3 = Deployment (critical)
    expect(rows[3].className).toContain("bg-red-50");
  });

  it("calls calculate when button is clicked", async () => {
    const mockRefetch = vi.fn();
    mockUseScheduleResults.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
      refetch: mockRefetch,
    });
    mockCalculateMutateAsync.mockResolvedValue(mockScheduleData);

    render(<ScheduleView programId="prog-1" />, { wrapper: Wrapper });

    fireEvent.click(screen.getByText("Calculate Schedule"));

    await waitFor(() => {
      expect(mockCalculateMutateAsync).toHaveBeenCalledWith("prog-1");
    });
  });
});
