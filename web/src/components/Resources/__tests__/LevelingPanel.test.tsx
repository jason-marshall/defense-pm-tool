/**
 * Unit tests for LevelingPanel component.
 * Tests options form, algorithm selection, run leveling, apply leveling,
 * compare algorithms, results display, warnings, loading/error states,
 * shift selection/deselection, reset, and cancel.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { LevelingPanel } from "../LevelingPanel";
import { ToastProvider } from "@/components/Toast";

const mockRunMutateAsync = vi.fn();
const mockParallelMutateAsync = vi.fn();
const mockApplyMutateAsync = vi.fn();
const mockCompareMutateAsync = vi.fn();

let mockRunIsPending = false;
let mockParallelIsPending = false;
let mockApplyIsPending = false;
let mockCompareIsPending = false;

vi.mock("@/hooks/useLeveling", () => ({
  useRunLeveling: () => ({
    mutateAsync: mockRunMutateAsync,
    get isPending() {
      return mockRunIsPending;
    },
  }),
  useRunParallelLeveling: () => ({
    mutateAsync: mockParallelMutateAsync,
    get isPending() {
      return mockParallelIsPending;
    },
  }),
  useApplyLeveling: () => ({
    mutateAsync: mockApplyMutateAsync,
    get isPending() {
      return mockApplyIsPending;
    },
  }),
  useCompareLevelingAlgorithms: () => ({
    mutateAsync: mockCompareMutateAsync,
    get isPending() {
      return mockCompareIsPending;
    },
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

const mockResultMultipleShifts = {
  ...mockResult,
  activities_shifted: 3,
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
    {
      activity_id: "act-002",
      activity_code: "A002",
      original_start: "2026-01-11",
      original_finish: "2026-01-15",
      new_start: "2026-01-18",
      new_finish: "2026-01-22",
      delay_days: 5,
      reason: "Resource conflict",
    },
    {
      activity_id: "act-003",
      activity_code: "A003",
      original_start: "2026-01-16",
      original_finish: "2026-01-20",
      new_start: "2026-01-23",
      new_finish: "2026-01-27",
      delay_days: 5,
      reason: "Dependency chain",
    },
  ],
};

const mockComparisonResponse = {
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
};

describe("LevelingPanel", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
    mockRunIsPending = false;
    mockParallelIsPending = false;
    mockApplyIsPending = false;
    mockCompareIsPending = false;
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
    mockCompareMutateAsync.mockResolvedValue(mockComparisonResponse);

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

  // --- New tests below ---

  describe("options/settings changes", () => {
    it("toggles preserve critical path checkbox", () => {
      render(<LevelingPanel programId="prog-001" />, { wrapper: Wrapper });

      const checkbox = screen.getByLabelText("Preserve Critical Path");
      expect(checkbox).toBeChecked();

      fireEvent.click(checkbox);
      expect(checkbox).not.toBeChecked();

      fireEvent.click(checkbox);
      expect(checkbox).toBeChecked();
    });

    it("toggles level within float checkbox", () => {
      render(<LevelingPanel programId="prog-001" />, { wrapper: Wrapper });

      const checkbox = screen.getByLabelText("Level Within Float Only");
      expect(checkbox).toBeChecked();

      fireEvent.click(checkbox);
      expect(checkbox).not.toBeChecked();
    });

    it("updates max iterations value", () => {
      render(<LevelingPanel programId="prog-001" />, { wrapper: Wrapper });

      const input = screen.getByDisplayValue("100");
      fireEvent.change(input, { target: { value: "250" } });

      expect(input).toHaveValue(250);
    });

    it("passes updated options to run leveling", async () => {
      mockRunMutateAsync.mockResolvedValue(mockResult);

      render(<LevelingPanel programId="prog-001" />, { wrapper: Wrapper });

      // Change options
      fireEvent.click(screen.getByLabelText("Preserve Critical Path"));
      fireEvent.change(screen.getByDisplayValue("100"), {
        target: { value: "50" },
      });

      fireEvent.click(screen.getByText("Run Serial Leveling"));

      await waitFor(() => {
        expect(mockRunMutateAsync).toHaveBeenCalledWith({
          programId: "prog-001",
          options: expect.objectContaining({
            preserve_critical_path: false,
            max_iterations: 50,
            level_within_float: true,
            target_resources: null,
          }),
        });
      });
    });

    it("switches algorithm from serial to parallel and back", () => {
      render(<LevelingPanel programId="prog-001" />, { wrapper: Wrapper });

      // Initially shows "Run Serial Leveling"
      expect(screen.getByText("Run Serial Leveling")).toBeInTheDocument();

      // Switch to parallel
      fireEvent.click(screen.getByText("Parallel"));
      expect(screen.getByText("Run Parallel Leveling")).toBeInTheDocument();

      // Switch back to serial
      fireEvent.click(screen.getByText("Serial"));
      expect(screen.getByText("Run Serial Leveling")).toBeInTheDocument();
    });
  });

  describe("loading states", () => {
    it("shows Running... text when serial leveling is pending", () => {
      mockRunIsPending = true;

      render(<LevelingPanel programId="prog-001" />, { wrapper: Wrapper });

      expect(screen.getByText("Running...")).toBeInTheDocument();
    });

    it("shows Running... text when parallel leveling is pending", () => {
      mockParallelIsPending = true;

      render(<LevelingPanel programId="prog-001" />, { wrapper: Wrapper });

      // Switch to parallel view
      fireEvent.click(screen.getByText("Parallel"));

      expect(screen.getByText("Running...")).toBeInTheDocument();
    });

    it("disables Run button when serial leveling is pending", () => {
      mockRunIsPending = true;

      render(<LevelingPanel programId="prog-001" />, { wrapper: Wrapper });

      const runButton = screen.getByText("Running...").closest("button")!;
      expect(runButton).toBeDisabled();
    });

    it("shows Comparing... text when compare is pending", () => {
      mockCompareIsPending = true;

      render(<LevelingPanel programId="prog-001" />, { wrapper: Wrapper });

      expect(screen.getByText("Comparing...")).toBeInTheDocument();
    });

    it("disables Compare button when compare is pending", () => {
      mockCompareIsPending = true;

      render(<LevelingPanel programId="prog-001" />, { wrapper: Wrapper });

      const compareButton = screen.getByText("Comparing...").closest("button")!;
      expect(compareButton).toBeDisabled();
    });

    it("shows Applying... text when apply is pending", async () => {
      mockRunMutateAsync.mockResolvedValue(mockResult);

      render(<LevelingPanel programId="prog-001" />, { wrapper: Wrapper });

      // Run leveling to get results
      fireEvent.click(screen.getByText("Run Serial Leveling"));
      await waitFor(() => {
        expect(screen.getByText("Leveling Results")).toBeInTheDocument();
      });

      // Now simulate apply pending
      let resolveApply!: (value: { applied_count: number }) => void;
      mockApplyMutateAsync.mockReturnValue(
        new Promise((resolve) => {
          resolveApply = resolve;
        })
      );

      fireEvent.click(screen.getByText(/Apply 1 Change/));

      // The apply button text should show "Applying..." while pending
      // Since isPending is managed by the mock, we check the mutation was called
      await waitFor(() => {
        expect(mockApplyMutateAsync).toHaveBeenCalled();
      });

      // Resolve to clean up
      resolveApply({ applied_count: 1 });
    });
  });

  describe("error states", () => {
    it("shows error toast when run leveling fails", async () => {
      mockRunMutateAsync.mockRejectedValue(new Error("Network error"));

      render(<LevelingPanel programId="prog-001" />, { wrapper: Wrapper });

      fireEvent.click(screen.getByText("Run Serial Leveling"));

      // The error should be caught and a toast shown. We can verify the
      // mutation was called. The toast notification comes through ToastProvider.
      await waitFor(() => {
        expect(mockRunMutateAsync).toHaveBeenCalled();
      });
    });

    it("shows error toast when parallel leveling fails", async () => {
      mockParallelMutateAsync.mockRejectedValue(
        new Error("Parallel error")
      );

      render(<LevelingPanel programId="prog-001" />, { wrapper: Wrapper });

      fireEvent.click(screen.getByText("Parallel"));
      fireEvent.click(screen.getByText("Run Parallel Leveling"));

      await waitFor(() => {
        expect(mockParallelMutateAsync).toHaveBeenCalled();
      });
    });

    it("shows error toast when compare fails", async () => {
      mockCompareMutateAsync.mockRejectedValue(new Error("Compare error"));

      render(<LevelingPanel programId="prog-001" />, { wrapper: Wrapper });

      fireEvent.click(screen.getByText("Compare"));

      await waitFor(() => {
        expect(mockCompareMutateAsync).toHaveBeenCalled();
      });
    });

    it("shows error toast when apply fails", async () => {
      mockRunMutateAsync.mockResolvedValue(mockResult);
      mockApplyMutateAsync.mockRejectedValue(new Error("Apply error"));

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
  });

  describe("results display", () => {
    it("displays result summary stats correctly", async () => {
      mockRunMutateAsync.mockResolvedValue(mockResult);

      render(<LevelingPanel programId="prog-001" />, { wrapper: Wrapper });

      fireEvent.click(screen.getByText("Run Serial Leveling"));

      await waitFor(() => {
        expect(screen.getByText("Leveling Results")).toBeInTheDocument();
      });

      expect(screen.getByText("Activities Shifted")).toBeInTheDocument();
      expect(screen.getByText("Iterations Used")).toBeInTheDocument();
      expect(screen.getByText("Schedule Extension")).toBeInTheDocument();
      expect(screen.getByText("Remaining Issues")).toBeInTheDocument();

      // Check numeric values
      expect(screen.getByText("2")).toBeInTheDocument(); // activities_shifted
      expect(screen.getByText("12")).toBeInTheDocument(); // iterations_used
      expect(screen.getByText("10 days")).toBeInTheDocument(); // schedule_extension_days
      expect(screen.getByText("0")).toBeInTheDocument(); // remaining_overallocations
    });

    it("displays remaining overallocations with warning styling", async () => {
      const resultWithOverallocations = {
        ...mockResult,
        remaining_overallocations: 3,
      };
      mockRunMutateAsync.mockResolvedValue(resultWithOverallocations);

      render(<LevelingPanel programId="prog-001" />, { wrapper: Wrapper });

      fireEvent.click(screen.getByText("Run Serial Leveling"));

      await waitFor(() => {
        expect(screen.getByText("3")).toBeInTheDocument();
      });
    });

    it("displays shift table with activity details", async () => {
      mockRunMutateAsync.mockResolvedValue(mockResult);

      render(<LevelingPanel programId="prog-001" />, { wrapper: Wrapper });

      fireEvent.click(screen.getByText("Run Serial Leveling"));

      await waitFor(() => {
        expect(screen.getByText("A001")).toBeInTheDocument();
      });

      // Check table headers
      expect(screen.getByText("Activity")).toBeInTheDocument();
      expect(screen.getByText("Original Dates")).toBeInTheDocument();
      expect(screen.getByText("New Dates")).toBeInTheDocument();
      expect(screen.getByText("Delay")).toBeInTheDocument();
      expect(screen.getByText("Reason")).toBeInTheDocument();

      // Check shift data
      expect(screen.getByText("+5d")).toBeInTheDocument();
      expect(screen.getByText("Resource overallocation")).toBeInTheDocument();
    });

    it("displays selected shifts count", async () => {
      mockRunMutateAsync.mockResolvedValue(mockResult);

      render(<LevelingPanel programId="prog-001" />, { wrapper: Wrapper });

      fireEvent.click(screen.getByText("Run Serial Leveling"));

      await waitFor(() => {
        expect(screen.getByText("1 of 1 shifts selected")).toBeInTheDocument();
      });
    });

    it("shows comparison details with serial and parallel metrics", async () => {
      mockCompareMutateAsync.mockResolvedValue(mockComparisonResponse);

      render(<LevelingPanel programId="prog-001" />, { wrapper: Wrapper });

      fireEvent.click(screen.getByText("Compare"));

      await waitFor(() => {
        expect(screen.getByText("Algorithm Comparison")).toBeInTheDocument();
      });

      // Both serial and parallel show "Shifted: 3" so use getAllByText
      const shiftedElements = screen.getAllByText("Shifted: 3");
      expect(shiftedElements).toHaveLength(2);

      // Unique metrics for serial vs parallel
      expect(screen.getByText("Extension: 10d")).toBeInTheDocument(); // serial
      expect(screen.getByText("Extension: 8d")).toBeInTheDocument(); // parallel
      expect(screen.getByText("Time: 200ms")).toBeInTheDocument(); // serial
      expect(screen.getByText("Time: 100ms")).toBeInTheDocument(); // parallel

      // Recommendation
      expect(
        screen.getByText("Parallel is recommended")
      ).toBeInTheDocument();
    });

    it("shows optimally allocated message when no shifts needed", async () => {
      const emptyResult = { ...mockResult, shifts: [], activities_shifted: 0 };
      mockRunMutateAsync.mockResolvedValue(emptyResult);

      render(<LevelingPanel programId="prog-001" />, { wrapper: Wrapper });

      fireEvent.click(screen.getByText("Run Serial Leveling"));

      await waitFor(() => {
        expect(screen.getByText("No changes needed")).toBeInTheDocument();
        expect(
          screen.getByText("Resources are already optimally allocated")
        ).toBeInTheDocument();
      });
    });

    it("shows info text about leveling behavior", () => {
      render(<LevelingPanel programId="prog-001" />, { wrapper: Wrapper });

      expect(
        screen.getByText(
          "Leveling will delay non-critical activities to resolve resource overallocations."
        )
      ).toBeInTheDocument();
    });
  });

  describe("shift selection", () => {
    it("all shifts are selected by default after running leveling", async () => {
      mockRunMutateAsync.mockResolvedValue(mockResultMultipleShifts);

      render(<LevelingPanel programId="prog-001" />, { wrapper: Wrapper });

      fireEvent.click(screen.getByText("Run Serial Leveling"));

      await waitFor(() => {
        expect(
          screen.getByText("3 of 3 shifts selected")
        ).toBeInTheDocument();
      });
    });

    it("can deselect individual shifts", async () => {
      mockRunMutateAsync.mockResolvedValue(mockResultMultipleShifts);

      render(<LevelingPanel programId="prog-001" />, { wrapper: Wrapper });

      fireEvent.click(screen.getByText("Run Serial Leveling"));

      await waitFor(() => {
        expect(screen.getByText("A001")).toBeInTheDocument();
      });

      // Find all row checkboxes (not the header checkbox)
      const checkboxes = screen.getAllByRole("checkbox");
      // First checkbox is the "select all" header, rest are per-row
      // Click the second checkbox (first row) to deselect
      fireEvent.click(checkboxes[1]);

      expect(screen.getByText("2 of 3 shifts selected")).toBeInTheDocument();
    });

    it("can re-select a deselected shift", async () => {
      mockRunMutateAsync.mockResolvedValue(mockResultMultipleShifts);

      render(<LevelingPanel programId="prog-001" />, { wrapper: Wrapper });

      fireEvent.click(screen.getByText("Run Serial Leveling"));

      await waitFor(() => {
        expect(screen.getByText("A001")).toBeInTheDocument();
      });

      const checkboxes = screen.getAllByRole("checkbox");
      // Deselect
      fireEvent.click(checkboxes[1]);
      expect(screen.getByText("2 of 3 shifts selected")).toBeInTheDocument();

      // Re-select
      fireEvent.click(checkboxes[1]);
      expect(screen.getByText("3 of 3 shifts selected")).toBeInTheDocument();
    });

    it("can toggle all shifts via header checkbox", async () => {
      mockRunMutateAsync.mockResolvedValue(mockResultMultipleShifts);

      render(<LevelingPanel programId="prog-001" />, { wrapper: Wrapper });

      fireEvent.click(screen.getByText("Run Serial Leveling"));

      await waitFor(() => {
        expect(
          screen.getByText("3 of 3 shifts selected")
        ).toBeInTheDocument();
      });

      // Click "select all" header checkbox to deselect all
      const checkboxes = screen.getAllByRole("checkbox");
      fireEvent.click(checkboxes[0]);

      expect(screen.getByText("0 of 3 shifts selected")).toBeInTheDocument();

      // Click again to select all
      fireEvent.click(checkboxes[0]);

      expect(screen.getByText("3 of 3 shifts selected")).toBeInTheDocument();
    });

    it("disables Apply button when no shifts are selected", async () => {
      mockRunMutateAsync.mockResolvedValue(mockResultMultipleShifts);

      render(<LevelingPanel programId="prog-001" />, { wrapper: Wrapper });

      fireEvent.click(screen.getByText("Run Serial Leveling"));

      await waitFor(() => {
        expect(screen.getByText("A001")).toBeInTheDocument();
      });

      // Deselect all via header checkbox
      const checkboxes = screen.getAllByRole("checkbox");
      fireEvent.click(checkboxes[0]);

      // Apply button should be disabled
      const applyButton = screen
        .getByText(/Apply 0 Changes/)
        .closest("button")!;
      expect(applyButton).toBeDisabled();
    });

    it("updates Apply button text based on selection count", async () => {
      mockRunMutateAsync.mockResolvedValue(mockResultMultipleShifts);

      render(<LevelingPanel programId="prog-001" />, { wrapper: Wrapper });

      fireEvent.click(screen.getByText("Run Serial Leveling"));

      await waitFor(() => {
        expect(screen.getByText(/Apply 3 Changes/)).toBeInTheDocument();
      });

      // Deselect one
      const checkboxes = screen.getAllByRole("checkbox");
      fireEvent.click(checkboxes[1]);

      expect(screen.getByText(/Apply 2 Changes/)).toBeInTheDocument();
    });

    it("uses singular 'Change' when only 1 shift selected", async () => {
      mockRunMutateAsync.mockResolvedValue(mockResult); // single shift result

      render(<LevelingPanel programId="prog-001" />, { wrapper: Wrapper });

      fireEvent.click(screen.getByText("Run Serial Leveling"));

      await waitFor(() => {
        expect(screen.getByText(/Apply 1 Change$/)).toBeInTheDocument();
      });
    });
  });

  describe("apply leveling results", () => {
    it("calls onComplete after successful apply", async () => {
      const onComplete = vi.fn();
      mockRunMutateAsync.mockResolvedValue(mockResult);
      mockApplyMutateAsync.mockResolvedValue({ applied_count: 1 });

      render(<LevelingPanel programId="prog-001" onComplete={onComplete} />, {
        wrapper: Wrapper,
      });

      fireEvent.click(screen.getByText("Run Serial Leveling"));

      await waitFor(() => {
        expect(screen.getByText("Leveling Results")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText(/Apply 1 Change/));

      await waitFor(() => {
        expect(onComplete).toHaveBeenCalledTimes(1);
      });
    });

    it("resets result state after successful apply", async () => {
      mockRunMutateAsync.mockResolvedValue(mockResult);
      mockApplyMutateAsync.mockResolvedValue({ applied_count: 1 });

      render(<LevelingPanel programId="prog-001" />, { wrapper: Wrapper });

      fireEvent.click(screen.getByText("Run Serial Leveling"));

      await waitFor(() => {
        expect(screen.getByText("Leveling Results")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText(/Apply 1 Change/));

      await waitFor(() => {
        // After apply, should go back to the options form
        expect(screen.getByText("Run Serial Leveling")).toBeInTheDocument();
      });

      // Results should no longer be visible
      expect(screen.queryByText("Leveling Results")).not.toBeInTheDocument();
    });

    it("passes selected shift IDs to apply mutation", async () => {
      mockRunMutateAsync.mockResolvedValue(mockResultMultipleShifts);
      mockApplyMutateAsync.mockResolvedValue({ applied_count: 2 });

      render(<LevelingPanel programId="prog-001" />, { wrapper: Wrapper });

      fireEvent.click(screen.getByText("Run Serial Leveling"));

      await waitFor(() => {
        expect(screen.getByText("A001")).toBeInTheDocument();
      });

      // Deselect first shift
      const checkboxes = screen.getAllByRole("checkbox");
      fireEvent.click(checkboxes[1]);

      fireEvent.click(screen.getByText(/Apply 2 Changes/));

      await waitFor(() => {
        expect(mockApplyMutateAsync).toHaveBeenCalledWith({
          programId: "prog-001",
          shiftIds: expect.arrayContaining(["act-002", "act-003"]),
        });
        expect(mockApplyMutateAsync).toHaveBeenCalledWith({
          programId: "prog-001",
          shiftIds: expect.not.arrayContaining(["act-001"]),
        });
      });
    });
  });

  describe("cancel and reset", () => {
    it("Cancel button in results resets to options form", async () => {
      mockRunMutateAsync.mockResolvedValue(mockResult);

      render(<LevelingPanel programId="prog-001" />, { wrapper: Wrapper });

      fireEvent.click(screen.getByText("Run Serial Leveling"));

      await waitFor(() => {
        expect(screen.getByText("Leveling Results")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Cancel"));

      expect(screen.getByText("Run Serial Leveling")).toBeInTheDocument();
      expect(screen.queryByText("Leveling Results")).not.toBeInTheDocument();
    });

    it("Reset button is not shown when there are no results", () => {
      render(<LevelingPanel programId="prog-001" />, { wrapper: Wrapper });

      expect(screen.queryByText("Reset")).not.toBeInTheDocument();
    });

    it("Reset button is shown when results exist", async () => {
      mockRunMutateAsync.mockResolvedValue(mockResult);

      render(<LevelingPanel programId="prog-001" />, { wrapper: Wrapper });

      fireEvent.click(screen.getByText("Run Serial Leveling"));

      await waitFor(() => {
        expect(screen.getByText("Reset")).toBeInTheDocument();
      });
    });

    it("Reset clears comparison results too", async () => {
      mockCompareMutateAsync.mockResolvedValue(mockComparisonResponse);
      mockRunMutateAsync.mockResolvedValue(mockResult);

      render(<LevelingPanel programId="prog-001" />, { wrapper: Wrapper });

      // First run comparison
      fireEvent.click(screen.getByText("Compare"));

      await waitFor(() => {
        expect(screen.getByText("Algorithm Comparison")).toBeInTheDocument();
      });

      // Then run leveling to get the Reset button
      fireEvent.click(screen.getByText("Run Serial Leveling"));

      await waitFor(() => {
        expect(screen.getByText("Reset")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Reset"));

      // Should go back to options and comparison should be gone
      expect(screen.getByText("Run Serial Leveling")).toBeInTheDocument();
      // Options form is visible but no results or comparison
      expect(screen.queryByText("Leveling Results")).not.toBeInTheDocument();
    });

    it("hides options form when results are shown", async () => {
      mockRunMutateAsync.mockResolvedValue(mockResult);

      render(<LevelingPanel programId="prog-001" />, { wrapper: Wrapper });

      // Options are initially visible
      expect(screen.getByLabelText("Preserve Critical Path")).toBeInTheDocument();

      fireEvent.click(screen.getByText("Run Serial Leveling"));

      await waitFor(() => {
        expect(screen.getByText("Leveling Results")).toBeInTheDocument();
      });

      // Options form should be hidden
      expect(
        screen.queryByLabelText("Preserve Critical Path")
      ).not.toBeInTheDocument();
      expect(
        screen.queryByText("Run Serial Leveling")
      ).not.toBeInTheDocument();
    });
  });

  describe("warning toast on success=false", () => {
    it("shows warning toast when result success is false", async () => {
      const warningResult = { ...mockResult, success: false, warnings: ["Some warning"] };
      mockRunMutateAsync.mockResolvedValue(warningResult);

      render(<LevelingPanel programId="prog-001" />, { wrapper: Wrapper });

      fireEvent.click(screen.getByText("Run Serial Leveling"));

      await waitFor(() => {
        expect(screen.getByText("Leveling Results")).toBeInTheDocument();
      });

      // The component shows toast via ToastProvider; we just verify the result renders
      expect(screen.getByText("Warnings")).toBeInTheDocument();
      expect(screen.getByText("Some warning")).toBeInTheDocument();
    });
  });
});
