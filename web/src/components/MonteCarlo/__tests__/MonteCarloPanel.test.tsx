import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MonteCarloPanel } from "../MonteCarloPanel";
import { ToastProvider } from "@/components/Toast";
import type { MonteCarloResult } from "@/types/simulation";

// Mock recharts
vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div data-testid="responsive-container">{children}</div>,
  BarChart: ({ children }: { children: React.ReactNode }) => <div data-testid="bar-chart">{children}</div>,
  Bar: ({ children }: { children?: React.ReactNode }) => <div data-testid="bar">{children}</div>,
  Cell: ({ fill }: { fill: string }) => <div data-testid="cell" data-fill={fill} />,
  LineChart: ({ children }: { children: React.ReactNode }) => <div data-testid="line-chart">{children}</div>,
  Line: ({ name }: { name?: string }) => <div data-testid="line" data-name={name} />,
  Area: ({ name }: { name?: string }) => <div data-testid="area" data-name={name} />,
  XAxis: () => <div data-testid="x-axis" />,
  YAxis: () => <div data-testid="y-axis" />,
  CartesianGrid: () => <div data-testid="cartesian-grid" />,
  Tooltip: () => <div data-testid="tooltip" />,
  Legend: () => <div data-testid="legend" />,
  ReferenceLine: ({ label }: { label?: { value: string } }) => <div data-testid="reference-line" data-label={label?.value} />,
}));

// Mock the hooks
const mockUseSimulationResults = vi.fn();
const mockRunMutateAsync = vi.fn();

vi.mock("@/hooks/useSimulations", () => ({
  useSimulationResults: (...args: unknown[]) =>
    mockUseSimulationResults(...args),
  useRunSimulation: () => ({
    mutateAsync: mockRunMutateAsync,
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

const mockResult: MonteCarloResult = {
  id: "sim-1",
  program_id: "prog-1",
  config: {
    iterations: 1000,
    distribution_type: "pert",
  },
  status: "completed",
  duration_results: {
    mean: 42.5,
    std_dev: 5.2,
    min: 30,
    max: 58,
    p10: 35.0,
    p25: 38.5,
    p50: 42.0,
    p75: 46.0,
    p80: 47.5,
    p90: 50.0,
    p95: 53.0,
    histogram: [
      { bin_start: 30, bin_end: 35, count: 100, frequency: 0.1 },
      { bin_start: 35, bin_end: 40, count: 250, frequency: 0.25 },
      { bin_start: 40, bin_end: 45, count: 350, frequency: 0.35 },
      { bin_start: 45, bin_end: 50, count: 200, frequency: 0.2 },
      { bin_start: 50, bin_end: 55, count: 80, frequency: 0.08 },
      { bin_start: 55, bin_end: 60, count: 20, frequency: 0.02 },
    ],
  },
  cost_results: null,
  sensitivity: [
    {
      activity_id: "act-1",
      activity_name: "Critical Design",
      correlation: 0.85,
      criticality_index: 0.95,
    },
    {
      activity_id: "act-2",
      activity_name: "Integration Testing",
      correlation: 0.62,
      criticality_index: 0.78,
    },
  ],
  s_curve_data: [],
  created_at: "2026-02-01T12:00:00Z",
};

describe("MonteCarloPanel", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("renders the panel heading", () => {
    mockUseSimulationResults.mockReturnValue({
      data: null,
      isLoading: false,
    });

    render(<MonteCarloPanel programId="prog-1" />, { wrapper: Wrapper });

    expect(
      screen.getByText("Monte Carlo Simulation")
    ).toBeInTheDocument();
  });

  it("renders configuration form", () => {
    mockUseSimulationResults.mockReturnValue({
      data: null,
      isLoading: false,
    });

    render(<MonteCarloPanel programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("Configuration")).toBeInTheDocument();
    expect(screen.getByLabelText("Iterations")).toBeInTheDocument();
    expect(screen.getByLabelText("Distribution")).toBeInTheDocument();
    expect(screen.getByText("Run Simulation")).toBeInTheDocument();
  });

  it("renders distribution options", () => {
    mockUseSimulationResults.mockReturnValue({
      data: null,
      isLoading: false,
    });

    render(<MonteCarloPanel programId="prog-1" />, { wrapper: Wrapper });

    const distSelect = screen.getByLabelText("Distribution");
    const options = distSelect.querySelectorAll("option");

    expect(options).toHaveLength(4);
    expect(options[0]).toHaveValue("pert");
    expect(options[1]).toHaveValue("triangular");
    expect(options[2]).toHaveValue("normal");
    expect(options[3]).toHaveValue("uniform");
  });

  it("shows empty state when no results exist", () => {
    mockUseSimulationResults.mockReturnValue({
      data: [],
      isLoading: false,
    });

    render(<MonteCarloPanel programId="prog-1" />, { wrapper: Wrapper });

    expect(
      screen.getByText(/No simulation results/)
    ).toBeInTheDocument();
  });

  it("shows loading state for results", () => {
    mockUseSimulationResults.mockReturnValue({
      data: undefined,
      isLoading: true,
    });

    render(<MonteCarloPanel programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("Loading results...")).toBeInTheDocument();
  });

  it("displays simulation results when available", () => {
    mockUseSimulationResults.mockReturnValue({
      data: [mockResult],
      isLoading: false,
    });

    render(<MonteCarloPanel programId="prog-1" />, { wrapper: Wrapper });

    // Mean duration
    expect(screen.getByText("Mean Duration")).toBeInTheDocument();
    expect(screen.getByText("42.5 days")).toBeInTheDocument();

    // Std deviation
    expect(screen.getByText("Std Deviation")).toBeInTheDocument();
    expect(screen.getByText("5.2 days")).toBeInTheDocument();

    // P80 duration
    expect(screen.getByText("P80 Duration")).toBeInTheDocument();
    expect(screen.getByText("47.5 days")).toBeInTheDocument();

    // Min / Max
    expect(screen.getByText("Min / Max")).toBeInTheDocument();
    expect(screen.getByText("30 - 58")).toBeInTheDocument();
  });

  it("displays sensitivity analysis", () => {
    mockUseSimulationResults.mockReturnValue({
      data: [mockResult],
      isLoading: false,
    });

    render(<MonteCarloPanel programId="prog-1" />, { wrapper: Wrapper });

    expect(
      screen.getByText("Sensitivity (Top Drivers)")
    ).toBeInTheDocument();
    expect(screen.getByText("Critical Design")).toBeInTheDocument();
    expect(screen.getByText("Integration Testing")).toBeInTheDocument();
    expect(screen.getByText("85%")).toBeInTheDocument();
    expect(screen.getByText("62%")).toBeInTheDocument();
  });

  it("calls run simulation with config", async () => {
    mockUseSimulationResults.mockReturnValue({
      data: null,
      isLoading: false,
    });
    mockRunMutateAsync.mockResolvedValue(mockResult);

    render(<MonteCarloPanel programId="prog-1" />, { wrapper: Wrapper });

    // Change iterations
    fireEvent.change(screen.getByLabelText("Iterations"), {
      target: { value: "5000" },
    });

    // Change distribution
    fireEvent.change(screen.getByLabelText("Distribution"), {
      target: { value: "triangular" },
    });

    fireEvent.click(screen.getByText("Run Simulation"));

    await waitFor(() => {
      expect(mockRunMutateAsync).toHaveBeenCalledWith({
        programId: "prog-1",
        config: {
          iterations: 5000,
          distribution_type: "triangular",
        },
      });
    });
  });

  it("displays percentile distribution", () => {
    mockUseSimulationResults.mockReturnValue({
      data: [mockResult],
      isLoading: false,
    });

    render(<MonteCarloPanel programId="prog-1" />, { wrapper: Wrapper });

    expect(
      screen.getByText("Percentile Distribution")
    ).toBeInTheDocument();
    expect(screen.getByText("P10")).toBeInTheDocument();
    expect(screen.getByText("P50")).toBeInTheDocument();
    expect(screen.getByText("P80")).toBeInTheDocument();
    expect(screen.getByText("P90")).toBeInTheDocument();
    expect(screen.getByText("P95")).toBeInTheDocument();
  });

  it("renders distribution histogram chart when histogram data exists", () => {
    mockUseSimulationResults.mockReturnValue({
      data: [mockResult],
      isLoading: false,
    });

    render(<MonteCarloPanel programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("Duration Distribution")).toBeInTheDocument();
  });

  it("renders tornado chart when sensitivity data exists", () => {
    mockUseSimulationResults.mockReturnValue({
      data: [mockResult],
      isLoading: false,
    });

    render(<MonteCarloPanel programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("Sensitivity Analysis (Tornado)")).toBeInTheDocument();
  });

  it("renders s-curve chart when s_curve_data exists", () => {
    const resultWithSCurve: MonteCarloResult = {
      ...mockResult,
      s_curve_data: [
        { period: "2026-01", bcws: "10000", bcwp: "9500", acwp: "10200" },
        { period: "2026-02", bcws: "25000", bcwp: "22000", acwp: "24000" },
      ],
    };

    mockUseSimulationResults.mockReturnValue({
      data: [resultWithSCurve],
      isLoading: false,
    });

    render(<MonteCarloPanel programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("S-Curve")).toBeInTheDocument();
  });

  it("does not render s-curve chart when s_curve_data is empty", () => {
    mockUseSimulationResults.mockReturnValue({
      data: [mockResult],
      isLoading: false,
    });

    render(<MonteCarloPanel programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.queryByText("S-Curve")).not.toBeInTheDocument();
  });
});
