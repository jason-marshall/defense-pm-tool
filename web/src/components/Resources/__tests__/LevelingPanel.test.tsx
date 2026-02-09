import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { LevelingPanel } from "../LevelingPanel";
import { ToastProvider } from "@/components/Toast";

const mockRunMutateAsync = vi.fn();
const mockParallelMutateAsync = vi.fn();
const mockApplyMutateAsync = vi.fn();
const mockCompareMutateAsync = vi.fn();

vi.mock("@/hooks/useLeveling", () => ({
  useRunLeveling: () => ({
    mutateAsync: mockRunMutateAsync,
    isPending: false,
  }),
  useRunParallelLeveling: () => ({
    mutateAsync: mockParallelMutateAsync,
    isPending: false,
  }),
  useApplyLeveling: () => ({
    mutateAsync: mockApplyMutateAsync,
    isPending: false,
  }),
  useCompareLevelingAlgorithms: () => ({
    mutateAsync: mockCompareMutateAsync,
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

const mockResult = {
  program_id: "prog-001",
  success: true,
  iterations_used: 12,
  activities_shifted: 2,
  shifts: [
    {
      activity_id: "act-001",
      activity_code: "A001",
      original_start: "2026-01-06",
      original_finish: "2026-01-10",
      new_start: "2026-01-13",
      new_finish: "2026-01-17",
      delay_days: 5,
      reason: "Resource overallocation",
    },
  ],
  remaining_overallocations: 0,
  new_project_finish: "2026-03-20",
  original_project_finish: "2026-03-10",
  schedule_extension_days: 10,
  warnings: [],
};

describe("LevelingPanel", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("renders options form", () => {
    render(<LevelingPanel programId="prog-001" />, { wrapper: Wrapper });

    expect(screen.getByText("Resource Leveling")).toBeInTheDocument();
    expect(screen.getByLabelText("Preserve Critical Path")).toBeInTheDocument();
    expect(screen.getByLabelText("Level Within Float Only")).toBeInTheDocument();
    expect(screen.getByText("Max Iterations")).toBeInTheDocument();
  });

  it("renders algorithm toggle with Serial/Parallel buttons", () => {
    render(<LevelingPanel programId="prog-001" />, { wrapper: Wrapper });

    expect(screen.getByText("Serial")).toBeInTheDocument();
    expect(screen.getByText("Parallel")).toBeInTheDocument();
  });

  it("renders Compare button", () => {
    render(<LevelingPanel programId="prog-001" />, { wrapper: Wrapper });

    expect(screen.getByText("Compare")).toBeInTheDocument();
  });

  it("runs serial leveling when Serial is selected", async () => {
    mockRunMutateAsync.mockResolvedValue(mockResult);

    render(<LevelingPanel programId="prog-001" />, { wrapper: Wrapper });

    fireEvent.click(screen.getByText("Run Serial Leveling"));

    await waitFor(() => {
      expect(mockRunMutateAsync).toHaveBeenCalled();
    });
  });

  it("runs parallel leveling when Parallel is selected", async () => {
    mockParallelMutateAsync.mockResolvedValue(mockResult);

    render(<LevelingPanel programId="prog-001" />, { wrapper: Wrapper });

    fireEvent.click(screen.getByText("Parallel"));
    fireEvent.click(screen.getByText("Run Parallel Leveling"));

    await waitFor(() => {
      expect(mockParallelMutateAsync).toHaveBeenCalled();
    });
  });

  it("shows results after running leveling", async () => {
    mockRunMutateAsync.mockResolvedValue(mockResult);

    render(<LevelingPanel programId="prog-001" />, { wrapper: Wrapper });

    fireEvent.click(screen.getByText("Run Serial Leveling"));

    await waitFor(() => {
      expect(screen.getByText("Leveling Results")).toBeInTheDocument();
      expect(screen.getByText("Activities Shifted")).toBeInTheDocument();
    });
  });

  it("shows comparison results when Compare clicked", async () => {
    mockCompareMutateAsync.mockResolvedValue({
      program_id: "prog-001",
      serial: {
        algorithm: "serial",
        execution_time_ms: 200,
        activities_shifted: 3,
        schedule_extension_days: 10,
        remaining_overallocations: 0,
      },
      parallel: {
        algorithm: "parallel",
        execution_time_ms: 100,
        activities_shifted: 3,
        schedule_extension_days: 8,
        remaining_overallocations: 0,
      },
      recommendation: "Parallel is recommended",
    });

    render(<LevelingPanel programId="prog-001" />, { wrapper: Wrapper });

    fireEvent.click(screen.getByText("Compare"));

    await waitFor(() => {
      expect(screen.getByText("Algorithm Comparison")).toBeInTheDocument();
      expect(screen.getByText("Parallel is recommended")).toBeInTheDocument();
    });
  });

  it("applies selected shifts", async () => {
    mockRunMutateAsync.mockResolvedValue(mockResult);
    mockApplyMutateAsync.mockResolvedValue({ applied_count: 1 });

    render(<LevelingPanel programId="prog-001" />, { wrapper: Wrapper });

    fireEvent.click(screen.getByText("Run Serial Leveling"));

    await waitFor(() => {
      expect(screen.getByText("Leveling Results")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText(/Apply 1 Change/));

    await waitFor(() => {
      expect(mockApplyMutateAsync).toHaveBeenCalled();
    });
  });

  it("resets on Reset button click", async () => {
    mockRunMutateAsync.mockResolvedValue(mockResult);

    render(<LevelingPanel programId="prog-001" />, { wrapper: Wrapper });

    fireEvent.click(screen.getByText("Run Serial Leveling"));

    await waitFor(() => {
      expect(screen.getByText("Leveling Results")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Reset"));

    await waitFor(() => {
      expect(screen.getByText("Run Serial Leveling")).toBeInTheDocument();
    });
  });

  it("shows no changes needed message", async () => {
    const emptyResult = { ...mockResult, shifts: [], activities_shifted: 0 };
    mockRunMutateAsync.mockResolvedValue(emptyResult);

    render(<LevelingPanel programId="prog-001" />, { wrapper: Wrapper });

    fireEvent.click(screen.getByText("Run Serial Leveling"));

    await waitFor(() => {
      expect(screen.getByText("No changes needed")).toBeInTheDocument();
    });
  });

  it("shows warnings when present", async () => {
    const warningResult = {
      ...mockResult,
      success: false,
      warnings: ["Activity A003 has zero float"],
    };
    mockRunMutateAsync.mockResolvedValue(warningResult);

    render(<LevelingPanel programId="prog-001" />, { wrapper: Wrapper });

    fireEvent.click(screen.getByText("Run Serial Leveling"));

    await waitFor(() => {
      expect(screen.getByText("Warnings")).toBeInTheDocument();
      expect(
        screen.getByText("Activity A003 has zero float")
      ).toBeInTheDocument();
    });
  });
});
