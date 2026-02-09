import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { CostSummaryPanel } from "../CostSummaryPanel";
import { ToastProvider } from "@/components/Toast";

const mockUseProgramCostSummary = vi.fn();
const mockSyncMutateAsync = vi.fn();

vi.mock("@/hooks/useCost", () => ({
  useProgramCostSummary: (...args: unknown[]) =>
    mockUseProgramCostSummary(...args),
  useSyncCostsToEVMS: () => ({
    mutateAsync: mockSyncMutateAsync,
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

const mockCostData = {
  program_id: "prog-001",
  total_planned_cost: "100000.00",
  total_actual_cost: "85000.00",
  total_cost_variance: "15000.00",
  labor_cost: "60000.00",
  equipment_cost: "15000.00",
  material_cost: "10000.00",
  resource_count: 5,
  activity_count: 20,
  wbs_breakdown: [
    {
      wbs_id: "wbs-001",
      wbs_code: "1.1",
      wbs_name: "Phase 1",
      planned_cost: "25000.00",
      actual_cost: "20000.00",
      cost_variance: "5000.00",
      activity_count: 5,
    },
  ],
};

describe("CostSummaryPanel", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("renders loading state", () => {
    mockUseProgramCostSummary.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    });

    render(<CostSummaryPanel programId="prog-001" />, { wrapper: Wrapper });

    expect(screen.getByText("Loading cost data...")).toBeInTheDocument();
  });

  it("renders error state", () => {
    mockUseProgramCostSummary.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error("Failed"),
    });

    render(<CostSummaryPanel programId="prog-001" />, { wrapper: Wrapper });

    expect(screen.getByText("Failed to load cost data")).toBeInTheDocument();
  });

  it("renders no data state", () => {
    mockUseProgramCostSummary.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
    });

    render(<CostSummaryPanel programId="prog-001" />, { wrapper: Wrapper });

    expect(screen.getByText("No cost data available")).toBeInTheDocument();
  });

  it("renders cost summary cards", () => {
    mockUseProgramCostSummary.mockReturnValue({
      data: mockCostData,
      isLoading: false,
      error: null,
    });

    render(<CostSummaryPanel programId="prog-001" />, { wrapper: Wrapper });

    expect(screen.getByText("Cost Summary")).toBeInTheDocument();
    expect(screen.getByText("Planned Cost")).toBeInTheDocument();
    expect(screen.getByText("Actual Cost")).toBeInTheDocument();
    expect(screen.getByText("Cost Variance")).toBeInTheDocument();
  });

  it("renders cost by type", () => {
    mockUseProgramCostSummary.mockReturnValue({
      data: mockCostData,
      isLoading: false,
      error: null,
    });

    render(<CostSummaryPanel programId="prog-001" />, { wrapper: Wrapper });

    expect(screen.getByText("Labor")).toBeInTheDocument();
    expect(screen.getByText("Equipment")).toBeInTheDocument();
    expect(screen.getByText("Material")).toBeInTheDocument();
  });

  it("renders WBS breakdown table", () => {
    mockUseProgramCostSummary.mockReturnValue({
      data: mockCostData,
      isLoading: false,
      error: null,
    });

    render(<CostSummaryPanel programId="prog-001" />, { wrapper: Wrapper });

    expect(screen.getByText("WBS Cost Breakdown")).toBeInTheDocument();
    expect(screen.getByText("1.1")).toBeInTheDocument();
    expect(screen.getByText("Phase 1")).toBeInTheDocument();
  });

  it("renders EVMS sync section", () => {
    mockUseProgramCostSummary.mockReturnValue({
      data: mockCostData,
      isLoading: false,
      error: null,
    });

    render(<CostSummaryPanel programId="prog-001" />, { wrapper: Wrapper });

    expect(screen.getByText("EVMS Sync")).toBeInTheDocument();
    expect(screen.getByText("Sync to EVMS")).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText("Enter period ID")
    ).toBeInTheDocument();
  });

  it("calls sync mutation when Sync button clicked", async () => {
    mockUseProgramCostSummary.mockReturnValue({
      data: mockCostData,
      isLoading: false,
      error: null,
    });
    mockSyncMutateAsync.mockResolvedValue({
      success: true,
      wbs_elements_updated: 3,
    });

    render(<CostSummaryPanel programId="prog-001" />, { wrapper: Wrapper });

    fireEvent.change(screen.getByPlaceholderText("Enter period ID"), {
      target: { value: "period-001" },
    });
    fireEvent.click(screen.getByText("Sync to EVMS"));

    await waitFor(() => {
      expect(mockSyncMutateAsync).toHaveBeenCalledWith({
        programId: "prog-001",
        periodId: "period-001",
      });
    });
  });

  it("shows negative variance in red", () => {
    const negativeVarianceData = {
      ...mockCostData,
      total_cost_variance: "-5000.00",
    };
    mockUseProgramCostSummary.mockReturnValue({
      data: negativeVarianceData,
      isLoading: false,
      error: null,
    });

    render(<CostSummaryPanel programId="prog-001" />, { wrapper: Wrapper });

    const varianceElement = screen.getByText("Cost Variance")
      .nextElementSibling;
    expect(varianceElement?.className).toContain("text-red-600");
  });
});
