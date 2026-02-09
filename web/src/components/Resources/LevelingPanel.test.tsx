import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { LevelingPanel } from "./LevelingPanel";
import { ToastProvider } from "@/components/Toast";

vi.mock("@/services/levelingApi", () => ({
  runLeveling: vi.fn(),
  previewLeveling: vi.fn(),
  applyLeveling: vi.fn(),
}));

import { runLeveling, applyLeveling } from "@/services/levelingApi";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false },
  },
});

const Wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={queryClient}>
    <ToastProvider>{children}</ToastProvider>
  </QueryClientProvider>
);

const mockResult = {
  program_id: "prog-1",
  success: true,
  activities_shifted: 3,
  iterations_used: 42,
  schedule_extension_days: 5,
  remaining_overallocations: 0,
  new_project_finish: "2026-02-19",
  original_project_finish: "2026-02-14",
  shifts: [
    {
      activity_id: "act-1",
      activity_code: "ACT-001",
      original_start: "2026-02-01",
      original_finish: "2026-02-10",
      new_start: "2026-02-05",
      new_finish: "2026-02-14",
      delay_days: 4,
      reason: "Resource conflict with ENG-001",
    },
    {
      activity_id: "act-2",
      activity_code: "ACT-002",
      original_start: "2026-02-03",
      original_finish: "2026-02-12",
      new_start: "2026-02-08",
      new_finish: "2026-02-17",
      delay_days: 5,
      reason: "Resource conflict with ENG-002",
    },
  ],
  warnings: [],
};

describe("LevelingPanel", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("renders options form initially", () => {
    render(<LevelingPanel programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("Resource Leveling")).toBeInTheDocument();
    expect(screen.getByLabelText("Preserve Critical Path")).toBeChecked();
    expect(screen.getByLabelText("Level Within Float Only")).toBeChecked();
    expect(screen.getByText("Run Leveling")).toBeInTheDocument();
  });

  it("has max iterations input", () => {
    render(<LevelingPanel programId="prog-1" />, { wrapper: Wrapper });

    const input = screen.getByDisplayValue("100");
    expect(input).toBeInTheDocument();
    expect(input).toHaveAttribute("type", "number");
  });

  it("runs leveling and shows results", async () => {
    vi.mocked(runLeveling).mockResolvedValue(mockResult);

    render(<LevelingPanel programId="prog-1" />, { wrapper: Wrapper });

    fireEvent.click(screen.getByText("Run Leveling"));

    await waitFor(() => {
      expect(screen.getByText("Leveling Results")).toBeInTheDocument();
    });

    expect(screen.getByText("3")).toBeInTheDocument(); // activities shifted
    expect(screen.getByText("42")).toBeInTheDocument(); // iterations
    expect(screen.getByText("5 days")).toBeInTheDocument(); // schedule extension
    expect(screen.getByText("0")).toBeInTheDocument(); // remaining issues
  });

  it("shows shifts table with activity data", async () => {
    vi.mocked(runLeveling).mockResolvedValue(mockResult);

    render(<LevelingPanel programId="prog-1" />, { wrapper: Wrapper });

    fireEvent.click(screen.getByText("Run Leveling"));

    await waitFor(() => {
      expect(screen.getByText("ACT-001")).toBeInTheDocument();
    });
    expect(screen.getByText("ACT-002")).toBeInTheDocument();
    expect(screen.getByText("+4d")).toBeInTheDocument();
    expect(screen.getByText("+5d")).toBeInTheDocument();
  });

  it("selects all shifts by default after run", async () => {
    vi.mocked(runLeveling).mockResolvedValue(mockResult);

    render(<LevelingPanel programId="prog-1" />, { wrapper: Wrapper });

    fireEvent.click(screen.getByText("Run Leveling"));

    await waitFor(() => {
      expect(screen.getByText("2 of 2 shifts selected")).toBeInTheDocument();
    });
  });

  it("toggles individual shifts", async () => {
    vi.mocked(runLeveling).mockResolvedValue(mockResult);

    render(<LevelingPanel programId="prog-1" />, { wrapper: Wrapper });

    fireEvent.click(screen.getByText("Run Leveling"));

    await waitFor(() => {
      expect(screen.getByText("2 of 2 shifts selected")).toBeInTheDocument();
    });

    // Uncheck one shift
    const checkboxes = screen.getAllByRole("checkbox");
    // First checkbox is select-all, others are individual shifts
    fireEvent.click(checkboxes[1]);

    expect(screen.getByText("1 of 2 shifts selected")).toBeInTheDocument();
  });

  it("applies selected shifts", async () => {
    vi.mocked(runLeveling).mockResolvedValue(mockResult);
    vi.mocked(applyLeveling).mockResolvedValue(undefined as any);
    const onComplete = vi.fn();

    render(
      <LevelingPanel programId="prog-1" onComplete={onComplete} />,
      { wrapper: Wrapper }
    );

    fireEvent.click(screen.getByText("Run Leveling"));

    await waitFor(() => {
      expect(screen.getByText("Leveling Results")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText(/Apply 2 Changes/));

    await waitFor(() => {
      expect(applyLeveling).toHaveBeenCalledWith("prog-1", ["act-1", "act-2"]);
    });
  });

  it("resets results when reset button is clicked", async () => {
    vi.mocked(runLeveling).mockResolvedValue(mockResult);

    render(<LevelingPanel programId="prog-1" />, { wrapper: Wrapper });

    fireEvent.click(screen.getByText("Run Leveling"));

    await waitFor(() => {
      expect(screen.getByText("Leveling Results")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Reset"));

    expect(screen.getByText("Run Leveling")).toBeInTheDocument();
    expect(screen.queryByText("Leveling Results")).not.toBeInTheDocument();
  });

  it("shows no changes needed when no shifts", async () => {
    vi.mocked(runLeveling).mockResolvedValue({
      ...mockResult,
      activities_shifted: 0,
      shifts: [],
    });

    render(<LevelingPanel programId="prog-1" />, { wrapper: Wrapper });

    fireEvent.click(screen.getByText("Run Leveling"));

    await waitFor(() => {
      expect(screen.getByText("No changes needed")).toBeInTheDocument();
    });
  });

  it("shows warnings when present", async () => {
    vi.mocked(runLeveling).mockResolvedValue({
      ...mockResult,
      success: false,
      warnings: ["Cannot level critical path activity ACT-003"],
    });

    render(<LevelingPanel programId="prog-1" />, { wrapper: Wrapper });

    fireEvent.click(screen.getByText("Run Leveling"));

    await waitFor(() => {
      expect(screen.getByText("Warnings")).toBeInTheDocument();
      expect(
        screen.getByText("Cannot level critical path activity ACT-003")
      ).toBeInTheDocument();
    });
  });

  it("shows error toast on run failure", async () => {
    vi.mocked(runLeveling).mockRejectedValue(new Error("Server error"));

    render(<LevelingPanel programId="prog-1" />, { wrapper: Wrapper });

    fireEvent.click(screen.getByText("Run Leveling"));

    await waitFor(() => {
      expect(screen.getByText("Failed to run leveling")).toBeInTheDocument();
    });
  });
});
